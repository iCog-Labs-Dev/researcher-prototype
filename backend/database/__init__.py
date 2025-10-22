"""
Database layer for the researcher prototype application.

This module provides repository pattern implementations for all database operations,
replacing the scattered database logic across the application.
"""

from .motivation_repository import MotivationRepository
from .database_manager import DatabaseManager

__all__ = [
    "MotivationRepository",
    "DatabaseManager"
]
