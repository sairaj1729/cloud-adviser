import logging
from typing import Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError
from mongomock_motor import AsyncMongoMockClient

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: Any = None
    db: Any = None
    is_connected: bool = False
    is_mock: bool = False

db_manager = MongoDB()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
    try:
        # Set short serverSelectionTimeoutMS so app startup doesn't hang if Mongo is offline
        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000
        )
        # Ping database server
        await db_manager.client.admin.command('ping')
        db_manager.db = db_manager.client[settings.MONGODB_DATABASE]
        db_manager.is_connected = True
        db_manager.is_mock = False

        # Create Indexes
        await create_db_indexes()
        logger.info("Connected to MongoDB server successfully.")
    except (ServerSelectionTimeoutError, Exception) as e:
        logger.warning(
            f"Could not connect to live MongoDB server at {settings.MONGODB_URI} ({e}). "
            "Falling back to in-memory AsyncMongoMockClient database."
        )
        db_manager.client = AsyncMongoMockClient()
        db_manager.db = db_manager.client[settings.MONGODB_DATABASE]
        db_manager.is_connected = True
        db_manager.is_mock = True
        await create_db_indexes()
        await auto_seed_mock_db()

async def auto_seed_mock_db():
    """Auto-seed mock database on app startup if empty."""
    try:
        from app.db.seed import seed_database_instance
        await seed_database_instance(db_manager.db)
        logger.info("Mock in-memory database auto-seeded successfully.")
    except Exception as e:
        logger.warning(f"Mock auto-seeding skipped: {e}")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_manager.client and not db_manager.is_mock:
        db_manager.client.close()
    logger.info("MongoDB connection closed.")

async def create_db_indexes():
    """Create MongoDB indexes as specified in V1 requirements."""
    db = db_manager.db
    if db is None:
        return

    try:
        # users: unique email
        await db.users.create_index("email", unique=True)

        # cloud_accounts: user_id + provider + account_identifier
        await db.cloud_accounts.create_index(
            [("user_id", 1), ("provider", 1), ("account_identifier", 1)],
            unique=True
        )

        # resources: user_id + provider + resource_id (non-unique to allow snapshots over time)
        await db.resources.create_index(
            [("user_id", 1), ("provider", 1), ("resource_id", 1)]
        )

        # rules: unique rule_id
        await db.rules.create_index("rule_id", unique=True)

        # findings: user_id + resource_id + rule_id
        await db.findings.create_index(
            [("user_id", 1), ("resource_id", 1), ("rule_id", 1)],
            unique=True
        )
    except Exception as e:
        logger.warning(f"Index creation skipped/failed: {e}")

async def get_database() -> Any:
    if db_manager.db is None:
        await connect_to_mongo()
    return db_manager.db
