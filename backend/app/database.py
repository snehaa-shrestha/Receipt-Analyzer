import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")
CLIENT = AsyncIOMotorClient(MONGO_DETAILS)
DATABASE = CLIENT.receipt_analyzer

import logging

logger = logging.getLogger(__name__)

async def check_db_connection():
    try:
        await CLIENT.admin.command('ping')
        logger.info("MongoDB connection successful")
        print("MongoDB connection successful")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        print(f"MongoDB connection failed: {e}")

def get_database():
    return DATABASE
