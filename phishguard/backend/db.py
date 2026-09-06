import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

logger = logging.getLogger("phishguard.db")
_db_client = None

def get_db():
    global _db_client
    if _db_client is None:
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        try:
            _db_client = AsyncIOMotorClient(
                mongo_uri, 
                tlsCAFile=certifi.where(),
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000
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
    """Initializes the database with defaults if necessary."""
    try:
        db = get_db()
        if db is None:
            logger.warning("Database unavailable, skipping init_db")
            return
        
        # Init default demo user if not exists
        users_coll = db.users
        demo_user = await users_coll.find_one({"username": "demo"})
        if not demo_user:
            await users_coll.insert_one({"username": "demo", "password": "demo"})
            
        # Init stats if not exists
        stats_coll = db.stats
        global_stats = await stats_coll.find_one({"_id": "global"})
        if not global_stats:
            await stats_coll.insert_one({
                "_id": "global",
                "total_scans": 0,
                "threats_blocked": 0
            })
    except Exception as e:
        logger.warning(f"Database initialization error (proceeding without DB): {e}")

