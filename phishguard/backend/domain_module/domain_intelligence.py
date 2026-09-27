"""
PhishGuard — Domain Intelligence

Extracts WHOIS, SSL, and DNS metadata for a domain, then computes a risk score.

TI lookup scope
---------------
``calculate_domain_risk`` no longer issues its own TI lookup internally.
The caller (``domain_service.analyze_domain``) is responsible for running
``check_url_against_feeds`` against the correct final URL and passing the result
in via the ``ti_result`` parameter.  This eliminates the double TI lookup that
previously occurred (once here against a bare ``https://{hostname}`` and again
in domain_service against the actual final URL with path/query).

Passing ``ti_result=None`` preserves backward compatibility: the function will
skip TI scoring rather than performing a potentially incorrect lookup.
"""
import logging
import socket
import ssl
from datetime import datetime
from urllib.parse import urlparse

import tldextract
import whois

logger = logging.getLogger("phishguard.domain_intelligence")


def _get_registrable_domain(url: str) -> tuple[str, str]:
    """Return (registrable_domain, full_hostname).

    e.g. ``"https://www.wikipedia.org/"`` → ``("wikipedia.org", "www.wikipedia.org")``

    WHOIS should always be queried on the registrable domain, not the subdomain.
    """
    try:
        hostname = urlparse(url).netloc.split(":")[0].lower()
        if not hostname:
            hostname = url.lower()
    except Exception:
        hostname = url.lower()

    try:
        ext = tldextract.extract(hostname)
        if ext.domain and ext.suffix:
            registrable = f"{ext.domain}.{ext.suffix}"
        else:
            registrable = hostname
    except Exception:
        registrable = hostname

    return registrable, hostname


def get_domain_metadata(url: str) -> dict:
    """Extract WHOIS and SSL metadata for the domain of *url*."""
    registrable, hostname = _get_registrable_domain(url)

    metadata: dict = {
        "domain": hostname,
        "registrable_domain": registrable,
        "age_days": None,
        "ssl_valid": False,
        "ssl_issuer": None,
        "resolved_ips": [],
        "mx_records": None,
        "rdns": None,
        "ti_summary": None,
        "error": None,
    }

    # 1. WHOIS — query the registrable domain (strips subdomains)
    try:
        w = whois.whois(registrable)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if creation_date:
            now = datetime.now()
            if hasattr(creation_date, "tzinfo") and creation_date.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            metadata["age_days"] = (now - creation_date).days
    except Exception as exc:
        metadata["error"] = f"WHOIS failed: {exc}"

    # 2. SSL — use the full hostname, longer timeout for slow servers
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                metadata["ssl_valid"] = True
                issuer = dict(x[0] for x in cert["issuer"])
                metadata["ssl_issuer"] = issuer.get("organizationName", "Unknown")
    except Exception as exc:
        # SSL failure is NOT automatically a risk signal for well-known domains.
        # Only flag no-SSL if combined with other risk signals.
        metadata["ssl_valid"] = False
        metadata["ssl_error"] = str(exc)

    # 3. DNS resolution (A records) — lightweight via socket
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips = list({i[4][0] for i in infos if i and i[4]})
        metadata["resolved_ips"] = ips
        # Reverse DNS for the first IP — best-effort, failure is non-fatal
        if ips:
            try:
                metadata["rdns"] = socket.gethostbyaddr(ips[0])[0]
            except Exception as exc:
                logger.debug("Reverse DNS lookup failed for %s: %s", ips[0], exc)
                metadata["rdns"] = None
    except Exception as exc:
        logger.debug("DNS resolution failed for %s: %s", hostname, exc)
        metadata["resolved_ips"] = []

    # 4. MX records — best-effort via dnspython if installed
    try:
        import dns.resolver  # optional dependency
        try:
            answers = dns.resolver.resolve(hostname, "MX", lifetime=3)
            metadata["mx_records"] = [str(r.exchange).rstrip(".") for r in answers]
        except Exception as exc:
            logger.debug("MX lookup failed for %s: %s", hostname, exc)
            metadata["mx_records"] = None
    except ImportError:
        metadata["mx_records"] = None

    return metadata


def calculate_domain_risk(metadata: dict, ti_result: dict | None = None) -> dict:
    """Compute a risk score (0–1) from domain metadata.

    Parameters
    ----------
    metadata:
        Output of :func:`get_domain_metadata`.
    ti_result:
        Pre-fetched TI result from ``check_url_against_feeds`` called against
        the **correct final URL** by the caller (``domain_service.analyze_domain``).
        When provided, TI hit information is incorporated into the score and
        signals list.  When ``None``, TI scoring is skipped — the caller is
        expected to apply TI evidence separately.
    """
    score = 0.0
    signals: list[str] = []

    age = metadata.get("age_days")
    if age is not None:
        if age < 30:
            score += 0.6
            signals.append("domain_very_new")
        elif age < 180:
            score += 0.3
            signals.append("domain_relatively_new")
        # Domain ≥ 180 days → no age penalty
    else:
        # WHOIS failed — small penalty; many legitimate domains block WHOIS
        score += 0.1
        signals.append("domain_age_unknown")

    if not metadata.get("ssl_valid"):
        # Only penalise missing SSL when WHOIS also failed or domain is very new
        if age is None or (age is not None and age < 30):
            score += 0.3
            signals.append("no_valid_ssl")
        # SSL timeout on an established domain → ignore
    else:
        issuer = (metadata.get("ssl_issuer") or "").lower()
        if "let's encrypt" in issuer or "letsencrypt" in issuer:
            # Let's Encrypt is widely used legitimately — small signal only
            score += 0.1
            signals.append("free_ssl_certificate")

    score = min(score, 1.0)

    # TI signals — only applied when caller supplies a pre-fetched result.
    # The caller must pass the result of check_url_against_feeds(final_url),
    # not a URL constructed here from metadata['domain'].
    if ti_result is not None:
        metadata["ti_summary"] = ti_result
        if ti_result.get("ti_hits", 0) > 0:
            signals.append("threat_intel_match")
            score = min(score + 0.5, 1.0)

    if score >= 0.7:
        risk_level = "phishing"
    elif score >= 0.4:
        risk_level = "suspicious"
    else:
        risk_level = "safe"

    return {
        "domain_score": round(score, 4),
        "domain_risk_level": risk_level,
        "domain_signals": signals,
        "metadata": metadata,
    }
