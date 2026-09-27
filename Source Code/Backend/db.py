"""
PhishGuard — Database layer (MongoDB via Motor).

Retry / reconnection behaviour
--------------------------------
``get_db()`` uses a *bounded* reconnection strategy: on first call it creates the
client; if that fails it records the failure timestamp and retries on the next
call only after a configurable back-off period (default 30 s, override via
``DB_RETRY_INTERVAL_SECONDS``).  This means:

* A transient network blip at startup does not permanently disable the database.
* Retries are capped — no infinite loop, no request-blocking spin.
* URL scanning never requires MongoDB; a ``None`` return is handled gracefully by
  every caller.

TLS configuration
-----------------
Certificate validation is **enabled by default**.  Set the environment variable
``MONGODB_TLS_ALLOW_INVALID_CERTIFICATES=true`` only for local development when
your MongoDB instance uses a self-signed certificate.  Production deployments
must leave this unset (or set it to ``false``).
"""
import hashlib
import hmac
import logging
import os
import time

import certifi
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("phishguard.db")

# ── Client state ──────────────────────────────────────────────────────────────
_db_client: AsyncIOMotorClient | None = None
_last_connect_attempt: float = 0.0          # epoch seconds
_connect_failed: bool = False               # True after a failed attempt

# Back-off before retrying a failed connection (seconds)
_RETRY_INTERVAL = float(os.environ.get("DB_RETRY_INTERVAL_SECONDS", "30"))

# ── TLS ───────────────────────────────────────────────────────────────────────
# Secure default: validate certificates.
# Override only for local dev with self-signed certs.
_ALLOW_INVALID_CERTS_RAW = os.environ.get(
    "MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false"
).strip().lower()
_ALLOW_INVALID_CERTS: bool = _ALLOW_INVALID_CERTS_RAW in ("1", "true", "yes")

if _ALLOW_INVALID_CERTS:
    logger.warning(
        "MONGODB_TLS_ALLOW_INVALID_CERTIFICATES is enabled. "
        "Certificate validation is disabled — do NOT use this in production."
    )

# ── Password hashing ──────────────────────────────────────────────────────────
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a plain-text password with PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a PBKDF2-HMAC-SHA256 hash."""
    try:
        if not stored_hash or not isinstance(stored_hash, str):
            return False
        if not stored_hash.startswith("pbkdf2_sha256$"):
            return False
        _, iterations, salt_hex, expected_hex = stored_hash.split("$", 3)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


# ── Connection ─────────────────────────────────────────────────────────────────

def _try_create_client() -> AsyncIOMotorClient | None:
    """Attempt to create a new Motor client. Returns the client or None."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    try:
        client = AsyncIOMotorClient(
            mongo_uri,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=_ALLOW_INVALID_CERTS,
            serverSelectionTimeoutMS=500,
        )
        logger.info("MongoDB client created (TLS validation: %s).", not _ALLOW_INVALID_CERTS)
        return client
    except Exception as exc:
        logger.warning("Failed to create MongoDB client: %s", exc)
        return None


def get_db():
    """Return the Motor database handle, or ``None`` if unavailable.

    Reconnection policy
    -------------------
    * First call: always attempts to create the client.
    * Subsequent calls after a failure: retried only once ``_RETRY_INTERVAL``
      seconds have elapsed since the last failed attempt.
    * Never blocks; never raises.
    """
    global _db_client, _last_connect_attempt, _connect_failed

    if _db_client is not None:
        try:
            return _db_client.phishguard
        except Exception:
            # Client became unusable (e.g. process fork); reset and try below.
            _db_client = None
            _connect_failed = True

    now = time.monotonic()
    if _connect_failed and (now - _last_connect_attempt) < _RETRY_INTERVAL:
        # Still within back-off window — skip this attempt.
        return None

    _last_connect_attempt = now
    client = _try_create_client()
    if client is None:
        _connect_failed = True
        return None

    _db_client = client
    _connect_failed = False
    try:
        return _db_client.phishguard
    except Exception:
        return None


def reset_db_client() -> None:
    """Force-reset the cached client (used in tests and after critical errors)."""
    global _db_client, _connect_failed, _last_connect_attempt
    _db_client = None
    _connect_failed = False
    _last_connect_attempt = 0.0


# ── Initialisation ─────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Initialise database defaults.  Safe to call even when MongoDB is down."""
    try:
        db = get_db()
        if db is None:
            logger.warning("Database unavailable at startup — skipping init_db.")
            return

        # Remove any lingering insecure demo credentials.
        await db.users.delete_many({"username": "demo"})

        # Seed global stats document if missing.
        global_stats = await db.stats.find_one({"_id": "global"})
        if not global_stats:
            await db.stats.insert_one(
                {"_id": "global", "total_scans": 0, "threats_blocked": 0}
            )
    except Exception as exc:
        logger.warning(
            "Database initialisation error (proceeding without DB): %s", exc
        )
