import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import certifi
from dotenv import load_dotenv

load_dotenv()

async def test():
    try:
        uri = os.environ.get("MONGODB_URI")
        print(f"Connecting to: {uri[:30]}...")
        client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        # Attempt to fetch server info to trigger a connection
        info = await client.server_info()
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test())
