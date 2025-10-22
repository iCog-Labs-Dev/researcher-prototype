"""
Database manager for dependency injection and repository management.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .motivation_repository import MotivationRepository
from services.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Database manager providing access to all repositories.
    
    This class serves as the main entry point for database operations,
    providing dependency injection for all repositories.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the database manager.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self._motivation_repository: Optional[MotivationRepository] = None
    
    @property
    def motivation(self) -> MotivationRepository:
        """
        Get the motivation repository.
        
        Returns:
            MotivationRepository instance
        """
        if self._motivation_repository is None:
            self._motivation_repository = MotivationRepository(self.session)
            logger.debug("Initialized motivation repository")
        
        return self._motivation_repository
    
    async def close(self):
        """Close the database session."""
        if self.session:
            await self.session.close()
            logger.debug("Database session closed")


