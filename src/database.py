"""MongoDB database connection and operations for NotebookLM Microservice."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import structlog

from .config import settings
from .models import UserNotebook, NotebookSource

logger = structlog.get_logger()


class Database:
    """MongoDB database handler."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB", database=settings.mongodb_database)
        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def get_user_notebook(self, user_email: str) -> Optional[UserNotebook]:
        """Get notebook mapping for a user."""
        if self.db is None:
            return None

        doc = await self.db.user_notebooks.find_one({"user_email": user_email})
        if doc:
            doc.pop("_id", None)
            return UserNotebook(**doc)
        return None

    async def save_user_notebook(self, notebook: UserNotebook) -> bool:
        """Save or update user notebook mapping."""
        if self.db is None:
            return False

        try:
            await self.db.user_notebooks.update_one(
                {"user_email": notebook.user_email},
                {"$set": notebook.model_dump()},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error("Failed to save user notebook", error=str(e))
            return False

    async def add_source_to_notebook(
        self,
        user_email: str,
        source: NotebookSource
    ) -> bool:
        """Add a source to user's notebook record."""
        if self.db is None:
            return False

        try:
            await self.db.user_notebooks.update_one(
                {"user_email": user_email},
                {
                    "$push": {"sources": source.model_dump()},
                    "$set": {"updated_at": source.added_at}
                }
            )
            return True
        except Exception as e:
            logger.error("Failed to add source", error=str(e))
            return False

    async def delete_user_notebook(self, user_email: str) -> bool:
        """Delete user notebook mapping."""
        if self.db is None:
            return False

        try:
            result = await self.db.user_notebooks.delete_one({"user_email": user_email})
            return result.deleted_count > 0
        except Exception as e:
            logger.error("Failed to delete user notebook", error=str(e))
            return False

    async def list_all_notebooks(self) -> list[UserNotebook]:
        """List all user notebook mappings."""
        if self.db is None:
            return []

        notebooks = []
        async for doc in self.db.user_notebooks.find():
            doc.pop("_id", None)
            notebooks.append(UserNotebook(**doc))
        return notebooks


# Global database instance
db = Database()
