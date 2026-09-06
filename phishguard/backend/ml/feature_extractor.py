"""
PhishGuard — URL Feature Extractor
Extracts 14 structural features from a URL for ML-based phishing detection.
All features are computed from the URL string alone (no network calls).
"""

import math
import re
from urllib.parse import urlparse

import tldextract


# Keywords commonly found in phishing URLs
SUSPICIOUS_KEYWORDS = [
    "login", "verify", "secure", "account", "update", "confirm",
    "bank", "paypal", "signin", "password", "credential", "suspend",
    "alert", "expire", "unlock", "validate", "billing", "invoice",
    "wallet", "recover", "restore", "authenticate", "authorize",
]

# IP address regex
IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

FEATURE_NAMES = [
    "url_length",
    "hostname_length",
    "path_length",
    "query_length",
    "num_query_params",
    "num_dots",
    "num_hyphens",
    "num_at",
    "num_special_chars",
    "num_digits_in_domain",
    "has_ip_address",
    "entropy",
    "suspicious_keywords",
    "uses_https",

    # New features for v2 URL feature engine
    "num_subdomains",          # count of subdomain labels (e.g., a.b.c -> 3)
    "has_unicode",            # hostname contains non-ascii chars (potential IDN/homograph)
    "is_punycode",            # any label starts with xn--
    "confusable_chars",       # count of known confusable unicode lookalikes in hostname
    "mixed_script_changes",   # number of script block changes across hostname
]


def _shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string (measures randomness)."""
    if not text:
        return 0.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(text)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )


def extract_features(url: str) -> dict:
    """
    Extract 14 structural features from a URL.

    Returns a dict with feature names as keys and numeric values.
    Designed to be extremely fast (~0.1ms per URL).
    """
    url = url.strip()

    # Parse URL components
    try:
        parsed = urlparse(url)
    except Exception:
        parsed = urlparse("http://invalid.url")

    hostname = parsed.netloc.lower() if parsed.netloc else ""
    path = parsed.path if parsed.path else ""
    query = parsed.query if parsed.query else ""
    url_lower = url.lower()

    # Extract domain parts using tldextract
    try:
        ext = tldextract.extract(url)
        domain_part = ext.domain
        subdomain_part = ext.subdomain
    except Exception:
        domain_part = hostname
        subdomain_part = ""

    # Feature 1: Total URL length
    url_length = len(url)

    # Feature 2: Hostname length
    hostname_length = len(hostname)

    # Feature 3: Path length — path segment only (no query string)
    # e.g. "/courses" from "https://site.com/courses?foo=bar"
    path_length = len(path)

    # Feature 4: Query string length — separated from path
    # Long query strings in legitimate URLs (ad tracking) should not inflate path_length
    query_length = len(query)

    # Feature 5: Number of query parameters
    # e.g. "a=1&b=2&c=3" -> 3 params; empty query -> 0
    num_query_params = query.count("&") + 1 if query else 0

    # Feature 6: Number of dots in hostname (subdomain indicator)
    num_dots = hostname.count(".")

    # Feature 7: Number of hyphens in hostname
    num_hyphens = hostname.count("-")

    # Feature 8: Number of @ signs (redirect trick)
    num_at = url.count("@")

    # Feature 9: Count of special characters (path + hostname only, not query)
    # Excluding query string prevents legitimate tracking params from inflating this
    path_and_host = parsed.scheme + "://" + hostname + path
    special_chars = set("?&=%#!~+|")
    num_special_chars = sum(1 for c in path_and_host if c in special_chars)

    # Feature 10: Digits in the domain
    num_digits_in_domain = sum(1 for c in hostname if c.isdigit())

    # Feature 11: Is the domain a raw IP address?
    host_no_port = hostname.split(":")[0] if ":" in hostname else hostname
    has_ip_address = 1 if IP_PATTERN.match(host_no_port) else 0

    # Feature 12: Shannon entropy of hostname + path only (not query)
    # Query strings from legitimate ad tracking have high entropy but aren't phishing signals
    entropy = _shannon_entropy(parsed.scheme + "://" + hostname + path)

    # Feature 13: Count of suspicious keywords in URL
    suspicious_keywords = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in url_lower)

    # Feature 14: Uses HTTPS?
    uses_https = 1 if parsed.scheme == "https" else 0

    # --- New features ---
    # Number of subdomain labels (split subdomain by '.')
    num_subdomains = len([s for s in subdomain_part.split('.') if s]) if subdomain_part else 0

    # Has unicode characters in hostname (IDN / homograph potential)
    has_unicode = 1 if any(ord(c) > 127 for c in hostname) else 0

    # Punycode labels start with 'xn--'
    is_punycode = 1 if any(label.startswith('xn--') for label in hostname.split('.')) else 0

    # Count of simple confusable unicode chars (common Cyrillic/Greek lookalikes)
    CONFUSABLES = set([
        '\u0430', # Cyrillic small a
        '\u0435', # Cyrillic small e
        '\u043E', # Cyrillic small o
        '\u03BF', # Greek small omicron
        '\u0131', # dotless i
        '\u00F1', # n-tilde
    ])
    confusable_chars = sum(1 for c in hostname if c in CONFUSABLES)

    # Mixed script changes: rough count of script transitions in hostname
    def _script_of(ch):
        o = ord(ch)
        # Latin basic
        if 0x0041 <= o <= 0x007A or o <= 127:
            return 'LATIN'
        if 0x0400 <= o <= 0x04FF:
            return 'CYRILLIC'
        if 0x0370 <= o <= 0x03FF:
            return 'GREEK'
        if 0x0590 <= o <= 0x05FF:
            return 'HEBREW'
        if 0x0600 <= o <= 0x06FF:
            return 'ARABIC'
        if 0x4E00 <= o <= 0x9FFF:
            return 'CJK'
        return 'OTHER'

    last_script = None
    script_changes = 0
    for ch in hostname:
        if ch == '.' or ch == ':':
            continue
        s = _script_of(ch)
        if last_script is None:
            last_script = s
        elif s != last_script:
            script_changes += 1
            last_script = s

    return {
        "url_length": url_length,
        "hostname_length": hostname_length,
        "path_length": path_length,
        "query_length": query_length,
        "num_query_params": num_query_params,
        "num_dots": num_dots,
        "num_hyphens": num_hyphens,
        "num_at": num_at,
        "num_special_chars": num_special_chars,
        "num_digits_in_domain": num_digits_in_domain,
        "has_ip_address": has_ip_address,
        "entropy": round(entropy, 4),
        "suspicious_keywords": suspicious_keywords,
        "uses_https": uses_https,
        "num_subdomains": num_subdomains,
        "has_unicode": has_unicode,
        "is_punycode": is_punycode,
        "confusable_chars": confusable_chars,
        "mixed_script_changes": script_changes,
    }


def extract_features_list(url: str) -> list:
    """Return features as an ordered list (for model input)."""
    feats = extract_features(url)
    return [feats[name] for name in FEATURE_NAMES]


# Quick self-test
if __name__ == "__main__":
    test_urls = [
        "https://www.google.com/search?q=hello",
        "http://192.168.1.1/admin/login.php",
        "https://paypa1-secure-login.tk/verify/account/update",
        "https://github.com/user/repo",
        "http://xn--pypal-4ve.com/signin?id=12345&token=abc",
        "https://www.geeksforgeeks.org/courses?source=google&medium=cpc&device=c&keyword=geeksforgeeks&matchtype=b&campaignid=20039445781",
    ]
    for u in test_urls:
        feats = extract_features(u)
        print(f"\n{'='*60}")
        print(f"URL: {u}")
        for k, v in feats.items():
            print(f"  {k:25s} = {v}")
