import os
import logging
import hashlib
import hmac
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

logger = logging.getLogger("phishguard.db")
_db_client = None

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a plain-text password with PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
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


def get_db():
    global _db_client
    if _db_client is None:
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        try:
            _db_client = AsyncIOMotorClient(
                mongo_uri,
                tlsCAFile=certifi.where(),
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,
            )
        except Exception as e:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            _db_client = None
            return None
    try:
        return _db_client.phishguard
    except Exception:
        return None


async def init_db():
    """Initialize database defaults without creating insecure demo credentials."""
    try:
        db = get_db()
        if db is None:
            logger.warning("Database unavailable, skipping init_db")
            return

        users_coll = db.users
        await users_coll.delete_many({"username": "demo"})

        stats_coll = db.stats
        global_stats = await stats_coll.find_one({"_id": "global"})
        if not global_stats:
            await stats_coll.insert_one({
                "_id": "global",
                "total_scans": 0,
                "threats_blocked": 0,
            })
    except Exception as e:
        logger.warning(f"Database initialization error (proceeding without DB): {e}")

