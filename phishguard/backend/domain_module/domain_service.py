import os
import time
import threading

from .redirect_unwrapper import unwrap_url
from .domain_intelligence import get_domain_metadata, calculate_domain_risk
from .shortener_expander import is_likely_shortener, expand_short_url

# Simple in-memory TTL cache for domain analysis results.
# Keys: original URL string; Values: (expires_at_ts, payload)
_CACHE_LOCK = threading.Lock()
_CACHE = {}
# Default TTL (seconds) — 6 hours by default (matches README cache guidance)
_DEFAULT_TTL = int(os.environ.get("REDIRECT_CACHE_TTL_SECONDS", str(6 * 60 * 60)))


def _cache_get(key: str):
    now = time.time()
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return None
        expires_at, payload = item
        if expires_at < now:
            # Expired
            del _CACHE[key]
            return None
        return payload


def _cache_set(key: str, payload: dict, ttl: int = None):
    if ttl is None:
        ttl = _DEFAULT_TTL
    expires_at = time.time() + ttl
    with _CACHE_LOCK:
        _CACHE[key] = (expires_at, payload)


def _build_redirect_analysis(original_url: str, unwrap_result: dict) -> dict:
    """Normalize resolver output into the stable per-scan redirect contract."""
    chain = unwrap_result.get("redirect_chain", []) or []
    return {
        "original_url": unwrap_result.get("original_url", original_url),
        "final_url": unwrap_result.get("final_url", original_url),
        "redirect_chain": chain,
        "num_redirects": unwrap_result.get("num_redirects", max(0, len(chain) - 1)),
        "loop_detected": bool(unwrap_result.get("loop_detected", False)),
        "suspicious_redirects": bool(unwrap_result.get("suspicious_redirects", False)),
        "has_meta_refresh": any(hop.get("note") == "meta_refresh" for hop in chain),
        "resolution_state": unwrap_result.get("resolution_state", "failed"),
        "errors": unwrap_result.get("errors", []) or [],
    }


def analyze_domain(
    url: str,
    use_browser: bool = False,
    cache_ttl: int | None = None,
    redirect_analysis: dict | None = None,
) -> dict:
    """
    Orchestrates redirect unwrapping and domain intelligence.

    Adds a lightweight in-memory cache to avoid repeated external network calls
    for the same input URL. The cache key is the original URL string (so short
    URLs and their final landing pages are stored per-request).

    Args:
        url: URL to analyze
        use_browser: if True, allows the redirect unwrapper to attempt browser-based
                     JS/meta-refresh detection (disabled by default)
        cache_ttl: optional TTL in seconds to override default cache duration
    """
    # Check cache first
    cache_key = f"analyze_domain:{url}"
    cached = _cache_get(cache_key)
    if cached is not None:
        # Return a shallow copy to avoid accidental mutation by callers
        return dict(cached)

    # 1. Resolve once for this analysis. The ensemble passes this result back
    # through XAI rather than resolving the same URL a second time.
    if redirect_analysis is None:
        if is_likely_shortener(url):
            unwrap_result = expand_short_url(url)
        else:
            unwrap_result = unwrap_url(url, use_browser=use_browser)
        redirect_analysis = _build_redirect_analysis(url, unwrap_result)
    else:
        redirect_analysis = _build_redirect_analysis(url, redirect_analysis)

    final_url = redirect_analysis["final_url"]

    # 2. Get Metadata for the final URL
    metadata = get_domain_metadata(final_url)

    # 3. Calculate Risk
    risk_result = calculate_domain_risk(metadata)

    # 4. Check Threat Intelligence Feeds (OpenPhish, PhishTank, URLhaus)
    try:
        from .ti_integration import check_url_against_feeds
        ti_res = check_url_against_feeds(final_url)
        if ti_res.get('ti_hits', 0) > 0:
            risk_result["domain_score"] = 1.0
            risk_result["domain_risk_level"] = "phishing"
            sources = ", ".join(ti_res.get('ti_sources', ['blacklisted']))
            risk_result.setdefault("domain_signals", []).append(f"threat_intel_match:{sources}")
            risk_result["ti_details"] = ti_res
    except Exception:
        pass

    # Combine redirect signals
    if redirect_analysis.get("suspicious_redirects"):
        risk_result["domain_score"] = min(risk_result["domain_score"] + 0.3, 1.0)
        risk_result.setdefault("domain_signals", []).append("suspicious_redirect_chain")

        # Re-evaluate risk level
        score = risk_result["domain_score"]
        if score >= 0.7:
            risk_result["domain_risk_level"] = "phishing"
        elif score >= 0.4:
            risk_result["domain_risk_level"] = "suspicious"

    risk_result["redirect_chain"] = redirect_analysis["redirect_chain"]
    risk_result["original_url"] = url
    risk_result["final_url"] = final_url
    risk_result["redirect_analysis"] = redirect_analysis

    # Attach any unwrap errors for observability
    if redirect_analysis["errors"]:
        risk_result.setdefault("warnings", []).extend(redirect_analysis["errors"])

    # Cache the assembled result
    _cache_set(cache_key, risk_result, ttl=cache_ttl)

    # Return a copy
    return dict(risk_result)
