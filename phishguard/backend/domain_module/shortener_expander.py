"""
Shortener expander utilities for PhishGuard.

Provides a small helper to detect common URL shorteners and resolve their
final landing pages using the safer redirect unwrapping logic.

This module intentionally delegates to domain_module.redirect_unwrapper.unwrap_url
so shortener-specific heuristics (caching, known providers) can be applied here.
"""
from urllib.parse import urlparse
from .redirect_unwrapper import unwrap_url, validate_url_for_fetch

# A small curated list of popular shortener hostnames. This is not exhaustive —
# unknown hostnames will still be resolved but may not be flagged as 'shortener'.
KNOWN_SHORTENERS = {
    # Major shorteners
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    # Additional common shorteners
    "v.gd",
    "cutt.ly",
    "short.io",
    "rb.gy",
    "tiny.cc",
    "lnkd.in",
    "surl.li",
    "shorturl.at",
    "t.ly",
    "clck.ru",
    "qr.ae",
    "adf.ly",
    "bc.vc",
    "j.mp",
    "x.co",
    "su.pr",
    "soo.gd",
    "s.id",
    "rotf.lol",
    "cli.re",
    "bl.ink",
    "tiny.one",
    "hyperurl.co",
    "1url.com",
    "0rz.tw",
    "b.link",
}


def is_likely_shortener(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        return host in KNOWN_SHORTENERS
    except Exception:
        return False


def expand_short_url(url: str, timeout: int = 5, max_redirects: int = 10, cache_ttl: int | None = None) -> dict:
    """
    If the URL looks like a shortener, follow redirects (safely) and return structured
    expansion results. If it does not look like a shortener, the function will still
    attempt to resolve redirects and return the final target.

    Returns a dict similar to unwrap_url() output with keys: original_url, final_url,
    redirect_chain, num_redirects, loop_detected, suspicious_redirects, errors
    """
    try:
        validate_url_for_fetch(url)
    except ValueError as exc:
        return {
            "original_url": url,
            "final_url": url,
            "redirect_chain": [{"url": url, "status_code": None, "note": "unsafe_url"}],
            "num_redirects": 0,
            "loop_detected": False,
            "suspicious_redirects": False,
            "errors": [f"unsafe_url:{exc}"],
            "is_shortener": is_likely_shortener(url),
        }

    result = unwrap_url(url, max_redirects=max_redirects, timeout=timeout)
    result["is_shortener"] = is_likely_shortener(url)
    return result
