"""
Enhanced Threat Intelligence (TI) Integration Engine for PhishGuard.

Connects to multi-source open cybersecurity threat feeds:
- PhishTank (Online Valid Phishing Database)
- OpenPhish (Live Phishing Intelligence Feed)
- URLhaus / Abuse.ch (Malware & Zero-Day Phishing Feed)

Features fast O(1) in-memory set indexing, background thread sync,
and detailed source attribution for instant zero-latency match lookups.

Sync architecture
-----------------
* ``check_url_against_feeds`` NEVER triggers a feed synchronisation by itself.
  It only queries the in-memory index that was populated by the last sync.
* ``sync_threat_feeds_now`` is the single entry-point for refreshing the index.
  It uses a ``threading.Event`` so that concurrent callers block until the
  in-progress sync finishes rather than each starting a separate sync.
* Staleness checks (TTL-based) live in ``_ensure_feeds_loaded``, which is
  called by ``check_url_against_feeds`` when the index appears empty or stale.
  This is the only place that may transparently trigger a sync.
"""
import csv
import io
import logging
import os
import threading
import time
from urllib.parse import urlparse

import requests

logger = logging.getLogger("phishguard.ti")

# ── Per-URL result TTL cache ───────────────────────────────────────────────
_TI_CACHE_LOCK = threading.Lock()
_TI_CACHE: dict = {}
_DEFAULT_TTL = int(os.environ.get("TI_CACHE_TTL_SECONDS", str(6 * 60 * 60)))

# Feed URLs (overrideable via environment variables)
PHISHTANK_FEED_URL = os.environ.get(
    "PHISHTANK_FEED_URL", "https://data.phishtank.com/data/online-valid.csv"
)
OPENPHISH_FEED_URL = os.environ.get(
    "OPENPHISH_FEED_URL", "https://openphish.com/feed.txt"
)
URLHAUS_FEED_URL = os.environ.get(
    "URLHAUS_FEED_URL", "https://urlhaus.abuse.ch/downloads/csv_recent/"
)

# ── In-memory O(1) threat index ───────────────────────────────────────────
# Protected by _INDEX_LOCK for writes; reads are lock-free (GIL is enough for
# set membership tests on CPython, and correctness only requires visibility
# after _SYNC_DONE is set).
_INDEX_LOCK = threading.Lock()
_TI_URL_INDEX: set = set()
_TI_DOMAIN_INDEX: set = set()
_TI_SOURCE_MAP: dict = {}          # domain -> list[str]
_TI_SOURCE_STATUS: dict = {
    "openphish": {"status": "unavailable", "reason": "Feed has not been synchronized."},
    "urlhaus":   {"status": "unavailable", "reason": "Feed has not been synchronized."},
    "phishtank": {"status": "unavailable", "reason": "Feed has not been synchronized."},
}
_LAST_SYNC_TIME: float = 0.0

# ── Concurrency guard ─────────────────────────────────────────────────────
# _SYNC_LOCK ensures only one thread enters the network-fetch path at a time.
# _SYNC_IN_PROGRESS is a threading.Event: late-arriving threads wait on it
# instead of starting their own sync.  It is *set* once the sync is complete
# (or has failed) so waiters are always unblocked.
_SYNC_LOCK = threading.Lock()
_SYNC_IN_PROGRESS = threading.Event()
_SYNC_IN_PROGRESS.set()  # initially "done" (no sync running)

# How long (seconds) before the index is considered stale and a background
# sync is warranted.  Matches the per-URL result TTL by default.
_INDEX_TTL = _DEFAULT_TTL


def _set_source_status(source: str, status: str, reason: str | None = None) -> None:
    with _INDEX_LOCK:
        entry: dict = {"status": status}
        if reason:
            entry["reason"] = reason
        _TI_SOURCE_STATUS[source] = entry


# ── Per-URL result cache helpers ──────────────────────────────────────────

def _cache_get(key: str):
    now = time.time()
    with _TI_CACHE_LOCK:
        item = _TI_CACHE.get(key)
        if not item:
            return None
        expires_at, payload = item
        if expires_at < now:
            del _TI_CACHE[key]
            return None
        return payload


def _cache_set(key: str, payload, ttl: int | None = None) -> None:
    if ttl is None:
        ttl = _DEFAULT_TTL
    expires_at = time.time() + ttl
    with _TI_CACHE_LOCK:
        _TI_CACHE[key] = (expires_at, payload)


# ── Individual feed fetchers ──────────────────────────────────────────────

def fetch_openphish_feed(timeout: int = 10) -> list:
    """Fetch OpenPhish plain-text URL feed (one URL per line)."""
    try:
        resp = requests.get(OPENPHISH_FEED_URL, timeout=timeout)
        if resp.status_code == 200:
            _set_source_status("openphish", "available")
            return [
                line.strip()
                for line in resp.text.splitlines()
                if line.strip() and not line.startswith("#")
            ]
        _set_source_status(
            "openphish", "unavailable", f"Feed returned HTTP {resp.status_code}."
        )
    except Exception as exc:
        logger.warning("Failed to fetch OpenPhish feed: %s", exc)
        _set_source_status("openphish", "unavailable", str(exc))
    return []


def fetch_urlhaus_feed(timeout: int = 10) -> list:
    """Fetch URLhaus recent CSV feed."""
    try:
        resp = requests.get(URLHAUS_FEED_URL, timeout=timeout)
        if resp.status_code == 200:
            _set_source_status("urlhaus", "available")
            urls: list = []
            for line in resp.text.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split('","')
                if len(parts) >= 3:
                    raw_url = parts[2].strip('"').strip()
                    if raw_url.startswith("http"):
                        urls.append(raw_url)
            return urls
        _set_source_status(
            "urlhaus", "unavailable", f"Feed returned HTTP {resp.status_code}."
        )
    except Exception as exc:
        logger.warning("Failed to fetch URLhaus feed: %s", exc)
        _set_source_status("urlhaus", "unavailable", str(exc))
    return []


def fetch_phishtank_csv(timeout: int = 10) -> str | None:
    """Fetch PhishTank online-valid CSV feed (cached by the per-URL TTL cache)."""
    cache_key = "phishtank_csv"
    cached = _cache_get(cache_key)
    if cached is not None:
        _set_source_status("phishtank", "available")
        return cached
    try:
        resp = requests.get(PHISHTANK_FEED_URL, timeout=timeout)
        if resp.status_code == 200:
            _cache_set(cache_key, resp.text)
            _set_source_status("phishtank", "available")
            return resp.text
        _set_source_status(
            "phishtank", "unavailable", f"Feed returned HTTP {resp.status_code}."
        )
    except Exception as exc:
        logger.warning("Failed to fetch PhishTank feed: %s", exc)
        _set_source_status("phishtank", "unavailable", str(exc))
    return None


def _fetch_phishtank_csv(timeout: int = 10) -> str | None:
    """Backward-compatible alias for tests and internal callers."""
    return fetch_phishtank_csv(timeout)


# ── Index synchronisation ─────────────────────────────────────────────────

def sync_threat_feeds_now() -> dict:
    """Synchronously refresh and re-index all active TI feeds.

    Concurrency guarantee
    ---------------------
    If a sync is already running (``_SYNC_IN_PROGRESS`` is *clear*), this
    function blocks until that sync finishes, then returns the current status
    without performing a second network round-trip.

    Only one goroutine/thread at a time ever touches the network feeds.
    """
    global _LAST_SYNC_TIME, _TI_URL_INDEX, _TI_DOMAIN_INDEX, _TI_SOURCE_MAP

    # Fast path: another sync is already running — wait for it, then return.
    if not _SYNC_IN_PROGRESS.is_set():
        # Block (up to 120 s) until the in-progress sync finishes.
        _SYNC_IN_PROGRESS.wait(timeout=120)
        return get_ti_feed_status()

    # Slow path: try to acquire the mutex so only one caller proceeds.
    acquired = _SYNC_LOCK.acquire(blocking=False)
    if not acquired:
        # Another thread just took the lock; wait for it to finish.
        _SYNC_IN_PROGRESS.wait(timeout=120)
        return get_ti_feed_status()

    # We hold _SYNC_LOCK — signal that a sync is now in progress.
    _SYNC_IN_PROGRESS.clear()
    try:
        new_urls: set = set()
        new_domains: set = set()
        new_source_map: dict = {}

        # 1. OpenPhish
        for url in fetch_openphish_feed():
            new_urls.add(url.lower())
            parsed = urlparse(url)
            dom = parsed.netloc.split(":")[0].lower() if parsed.netloc else ""
            if dom:
                new_domains.add(dom)
                new_source_map.setdefault(dom, set()).add("openphish")

        # 2. URLhaus
        for url in fetch_urlhaus_feed():
            new_urls.add(url.lower())
            parsed = urlparse(url)
            dom = parsed.netloc.split(":")[0].lower() if parsed.netloc else ""
            if dom:
                new_domains.add(dom)
                new_source_map.setdefault(dom, set()).add("urlhaus")

        # 3. PhishTank
        pt_text = _fetch_phishtank_csv()
        if pt_text:
            reader = csv.reader(io.StringIO(pt_text))
            next(reader, None)  # skip header
            for row in reader:
                if not row:
                    continue
                pt_url: str | None = None
                for field in row:
                    candidate = field.strip().strip('"').strip("'")
                    if candidate.startswith("http://") or candidate.startswith("https://"):
                        pt_url = candidate
                        break
                if not pt_url:
                    continue
                new_urls.add(pt_url.lower())
                parsed = urlparse(pt_url)
                dom = parsed.netloc.split(":")[0].lower() if parsed.netloc else ""
                if dom:
                    new_domains.add(dom)
                    new_source_map.setdefault(dom, set()).add("phishtank")

        # Atomically swap in the new index.
        with _INDEX_LOCK:
            _TI_URL_INDEX = new_urls
            _TI_DOMAIN_INDEX = new_domains
            _TI_SOURCE_MAP = {k: list(v) for k, v in new_source_map.items()}
            _LAST_SYNC_TIME = time.time()

        logger.info(
            "[PhishGuard TI] Sync complete: %d URLs, %d domains indexed.",
            len(new_urls),
            len(new_domains),
        )
    except Exception as exc:
        logger.error("[PhishGuard TI] Sync failed: %s", exc)
    finally:
        # Always unblock waiting threads and release the mutex.
        _SYNC_IN_PROGRESS.set()
        _SYNC_LOCK.release()

    return get_ti_feed_status()


def _ensure_feeds_loaded() -> None:
    """Trigger a sync only when the index is empty or the TTL has expired.

    This is the *only* place where a transparent sync may be initiated by
    ``check_url_against_feeds``.  Concurrent callers are serialised through
    ``sync_threat_feeds_now``'s Event-based guard, so at most one network
    round-trip occurs.
    """
    now = time.time()
    index_is_stale = (_LAST_SYNC_TIME == 0.0) or (now - _LAST_SYNC_TIME > _INDEX_TTL)
    if index_is_stale:
        logger.debug("[PhishGuard TI] Index empty or stale — triggering sync.")
        sync_threat_feeds_now()


# ── Public query API ──────────────────────────────────────────────────────

def check_domain_in_phishtank(domain: str) -> list:
    """Legacy helper maintained for backward compatibility."""
    if domain.lower() in _TI_DOMAIN_INDEX:
        return [f"Threat Intel match found for domain: {domain}"]
    return []


def check_url_against_feeds(url: str) -> dict:
    """Check the given URL against all loaded TI feeds with O(1) latency.

    This function NEVER triggers a full feed synchronisation directly.
    It returns cached per-URL results when available, and falls back to the
    in-memory index (which ``_ensure_feeds_loaded`` may refresh if stale).

    Returns::

        {
            'ti_hits': int,
            'ti_sources': ['openphish', 'phishtank', 'urlhaus'],
            'is_exact_url_match': bool,
            'details': {'domain': ..., 'matched_sources': [...]},
            'status': 'available' | 'unavailable',
        }
    """
    clean_url = url.strip().lower()
    parsed = urlparse(clean_url)
    domain = parsed.netloc.split(":")[0].lower() if parsed.netloc else clean_url

    # 1. Return per-URL cached result if still fresh.
    cache_key = f"ti:{clean_url}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # 2. Ensure the index is populated / not stale (may trigger a sync once).
    _ensure_feeds_loaded()

    # 3. Gather feed availability for the result envelope.
    feed_status = get_ti_feed_status()["source_statuses"]
    available_sources = [
        source
        for source, status in feed_status.items()
        if status.get("status") == "available"
    ]

    result: dict = {
        "ti_hits": 0,
        "ti_sources": [],
        "is_exact_url_match": False,
        "details": {},
        "status": "available" if available_sources else "unavailable",
        "unavailable_sources": [
            source
            for source, status in feed_status.items()
            if status.get("status") != "available"
        ],
    }
    if not available_sources:
        result["reason"] = "No threat-intelligence feeds are currently available."

    # 4. O(1) exact URL match.
    if clean_url in _TI_URL_INDEX:
        result["ti_hits"] += 1
        result["is_exact_url_match"] = True

    # 5. O(1) domain match.
    if domain in _TI_DOMAIN_INDEX:
        sources = _TI_SOURCE_MAP.get(domain, ["known_feed"])
        result["ti_hits"] += len(sources)
        result["ti_sources"] = list(set(result["ti_sources"] + sources))
        result["details"]["domain"] = domain
        result["details"]["matched_sources"] = sources

    _cache_set(cache_key, result)
    return result


def get_ti_feed_status() -> dict:
    """Return status telemetry of the TI feeds."""
    with _INDEX_LOCK:
        return {
            "status": "active",
            "total_blacklisted_urls": len(_TI_URL_INDEX),
            "total_blacklisted_domains": len(_TI_DOMAIN_INDEX),
            "sources": ["openphish", "phishtank", "urlhaus"],
            "source_statuses": {key: dict(value) for key, value in _TI_SOURCE_STATUS.items()},
            "last_sync_timestamp": _LAST_SYNC_TIME,
            "is_syncing": not _SYNC_IN_PROGRESS.is_set(),
        }
