import whois
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse

import tldextract


def _get_registrable_domain(url: str) -> tuple[str, str]:
    """
    Returns (registrable_domain, full_hostname).
    e.g. "https://www.wikipedia.org/" -> ("wikipedia.org", "www.wikipedia.org")
    WHOIS should always be queried on the registrable domain, not the subdomain.
    """
    try:
        hostname = urlparse(url).netloc.split(':')[0].lower()
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
    """
    Extracts WHOIS and SSL metadata for the domain.
    """
    registrable, hostname = _get_registrable_domain(url)

    metadata = {
        "domain": hostname,
        "registrable_domain": registrable,
        "age_days": None,
        "ssl_valid": False,
        "ssl_issuer": None,
        "resolved_ips": [],
        "mx_records": None,
        "rdns": None,
        "ti_summary": None,
        "error": None
    }

    # 1. WHOIS Lookup — use registrable domain (strips www. and other subdomains)
    try:
        w = whois.whois(registrable)
        creation_date = w.creation_date

        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date:
            # Handle both naive and timezone-aware datetimes
            now = datetime.now()
            if hasattr(creation_date, 'tzinfo') and creation_date.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            age = (now - creation_date).days
            metadata["age_days"] = age
    except Exception as e:
        metadata["error"] = f"WHOIS failed: {str(e)}"

    # 2. SSL Lookup — use full hostname, longer timeout for slow servers
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                metadata["ssl_valid"] = True

                issuer = dict(x[0] for x in cert['issuer'])
                metadata["ssl_issuer"] = issuer.get('organizationName', 'Unknown')
    except Exception as e:
        # SSL failure is NOT automatically a risk signal for well-known domains.
        # Only flag no-SSL if we also have other risk signals.
        metadata["ssl_valid"] = False
        metadata["ssl_error"] = str(e)

    # 3. DNS resolution (A records) — lightweight using socket
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips = list({i[4][0] for i in infos if i and i[4]})
        metadata["resolved_ips"] = ips
        # Reverse DNS for first IP (best-effort)
        if ips:
            try:
                metadata["rdns"] = socket.gethostbyaddr(ips[0])[0]
            except Exception:
                metadata["rdns"] = None
    except Exception:
        metadata["resolved_ips"] = []

    # 4. MX records (best-effort) — attempt to use dns.resolver if available
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(hostname, 'MX', lifetime=3)
            mxs = [str(r.exchange).rstrip('.') for r in answers]
            metadata["mx_records"] = mxs
        except Exception:
            metadata["mx_records"] = None
    except Exception:
        metadata["mx_records"] = None

    return metadata


def calculate_domain_risk(metadata: dict) -> dict:
    """
    Computes a risk score (0 to 1) based on domain metadata.
    """
    score = 0.0
    signals = []

    age = metadata.get("age_days")
    if age is not None:
        if age < 30:
            score += 0.6
            signals.append("domain_very_new")
        elif age < 180:
            score += 0.3
            signals.append("domain_relatively_new")
        # Domain older than 180 days → no penalty (trusted domains are old)
    else:
        # WHOIS failed — only add a small penalty, not 0.2
        # Many large legitimate domains block WHOIS or return no creation date
        score += 0.1
        signals.append("domain_age_unknown")

    if not metadata.get("ssl_valid"):
        # Only penalise missing SSL if WHOIS also failed or domain is very new
        # A timeout on SSL shouldn't automatically mean "suspicious"
        if age is None or (age is not None and age < 30):
            score += 0.3
            signals.append("no_valid_ssl")
        # else: SSL timeout on an established domain → ignore
    else:
        issuer = (metadata.get("ssl_issuer") or "").lower()
        if "let's encrypt" in issuer or "letsencrypt" in issuer:
            # Let's Encrypt is widely used legitimately — small signal only
            score += 0.1
            signals.append("free_ssl_certificate")

    # Cap score at 1.0
    score = min(score, 1.0)

    # 4. Threat intel signals
    try:
        from .ti_integration import check_url_against_feeds
        ti = check_url_against_feeds(f"https://{metadata.get('domain')}")
        metadata['ti_summary'] = ti
        if ti and ti.get('ti_hits', 0) > 0:
            signals.append('threat_intel_match')
            # Increase score moderately for TI hits
            score = min(score + 0.5, 1.0)
    except Exception:
        pass

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
        "metadata": metadata
    }
