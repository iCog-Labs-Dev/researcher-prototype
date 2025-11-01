"""
Base repository class providing common CRUD operations.
"""

import uuid
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import DeclarativeBase

from services.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """
    Base repository class providing common CRUD operations for all models.
    
    This class implements the repository pattern, providing a clean interface
    for database operations while abstracting away SQLAlchemy details.
    """
    
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        """
        Initialize the repository.
        
        Args:
            session: SQLAlchemy async session
            model_class: The SQLAlchemy model class this repository manages
        """
        self.session = session
        self.model_class = model_class
    
    # CREATE operations
    
    async def create(self, **kwargs) -> T:
        """
        Create a new record.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            The created model instance
        """
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            
            logger.debug(f"Created {self.model_class.__name__}: {instance.id}")
            return instance
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create {self.model_class.__name__}: {str(e)}")
            raise
    
    async def create_many(self, records: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records in a single transaction.
        
        Args:
            records: List of dictionaries containing field values
            
        Returns:
            List of created model instances
        """
        try:
            instances = []
            for record_data in records:
                instance = self.model_class(**record_data)
                self.session.add(instance)
                instances.append(instance)
            
            await self.session.commit()
            
            # Refresh all instances to get their IDs
            for instance in instances:
                await self.session.refresh(instance)
            
            logger.debug(f"Created {len(instances)} {self.model_class.__name__} records")
            return instances
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create multiple {self.model_class.__name__} records: {str(e)}")
            raise
    
    # READ operations
    
    async def get_by_id(self, record_id: uuid.UUID) -> Optional[T]:
        """
        Get a record by its ID.
        
        Args:
            record_id: The ID of the record to retrieve
            
        Returns:
            The model instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(self.model_class).where(self.model_class.id == record_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get {self.model_class.__name__} by ID {record_id}: {str(e)}")
            raise
    
    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all records with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        try:
            query = select(self.model_class)
            
            if offset > 0:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get all {self.model_class.__name__} records: {str(e)}")
            raise
    
    async def count(self) -> int:
        """
        Get the total count of records.
        
        Returns:
            Total number of records
        """
        try:
            result = await self.session.execute(
                select(func.count(self.model_class.id))
            )
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to count {self.model_class.__name__} records: {str(e)}")
            raise
    
    async def exists(self, record_id: uuid.UUID) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            record_id: The ID to check
            
        Returns:
            True if the record exists, False otherwise
        """
        try:
            result = await self.session.execute(
                select(self.model_class.id).where(self.model_class.id == record_id)
            )
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Failed to check existence of {self.model_class.__name__} {record_id}: {str(e)}")
            raise
    
    # UPDATE operations
    
    async def update(self, record_id: uuid.UUID, **kwargs) -> Optional[T]:
        """
        Update a record by ID.
        
        Args:
            record_id: The ID of the record to update
            **kwargs: Field values to update
            
        Returns:
            The updated model instance or None if not found
        """
        try:
            # First check if the record exists
            if not await self.exists(record_id):
                logger.warning(f"{self.model_class.__name__} with ID {record_id} not found for update")
                return None
            
            # Perform the update
            await self.session.execute(
                update(self.model_class)
                .where(self.model_class.id == record_id)
                .values(**kwargs)
            )
            await self.session.commit()
            
            # Return the updated record
            return await self.get_by_id(record_id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update {self.model_class.__name__} {record_id}: {str(e)}")
            raise
    
    async def update_many(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records.
        
        Args:
            updates: List of dictionaries containing 'id' and field values to update
            
        Returns:
            Number of records updated
        """
        try:
            updated_count = 0
            for update_data in updates:
                record_id = update_data.pop('id')
                if await self.update(record_id, **update_data):
                    updated_count += 1
            
            logger.debug(f"Updated {updated_count} {self.model_class.__name__} records")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update multiple {self.model_class.__name__} records: {str(e)}")
            raise
    
    # DELETE operations
    
    async def delete(self, record_id: uuid.UUID) -> bool:
        """
        Delete a record by ID.
        
        Args:
            record_id: The ID of the record to delete
            
        Returns:
            True if the record was deleted, False if not found
        """
        try:
            result = await self.session.execute(
                delete(self.model_class).where(self.model_class.id == record_id)
            )
            await self.session.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.debug(f"Deleted {self.model_class.__name__} with ID {record_id}")
                return True
            else:
                logger.warning(f"{self.model_class.__name__} with ID {record_id} not found for deletion")
                return False
                
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete {self.model_class.__name__} {record_id}: {str(e)}")
            raise
    
    async def delete_many(self, record_ids: List[uuid.UUID]) -> int:
        """
        Delete multiple records by IDs.
        
        Args:
            record_ids: List of IDs to delete
            
        Returns:
            Number of records deleted
        """
        try:
            result = await self.session.execute(
                delete(self.model_class).where(self.model_class.id.in_(record_ids))
            )
            await self.session.commit()
            
            deleted_count = result.rowcount
            logger.debug(f"Deleted {deleted_count} {self.model_class.__name__} records")
            return deleted_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete multiple {self.model_class.__name__} records: {str(e)}")
            raise
    
    async def delete_all(self) -> int:
        """
        Delete all records.
        
        Returns:
            Number of records deleted
        """
        try:
            result = await self.session.execute(delete(self.model_class))
            await self.session.commit()
            
            deleted_count = result.rowcount
            logger.warning(f"Deleted all {deleted_count} {self.model_class.__name__} records")
            return deleted_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete all {self.model_class.__name__} records: {str(e)}")
            raise


