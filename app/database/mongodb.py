from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    
    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        print("✅ Connected to MongoDB")
    
    @classmethod
    async def close_db(cls):
        cls.client.close()
        print("❌ Disconnected from MongoDB")
    
    @classmethod
    def get_database(cls):
        return cls.client[settings.DATABASE_NAME]


async def get_db():
    return MongoDB.get_database()
