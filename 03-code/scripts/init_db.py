#!/usr/bin/env python3
"""
CHUNK-041: Database Initialization Script

Creates all necessary database tables and initial data.
"""

from src.database.connection import engine
from src.database.models.books_metadata import Base, BooksMetadata
from src.utils.logging_config import setup_logging, logger

def init_database():
    """Initialize database with all tables."""
    setup_logging()
    logger.info("Starting database initialization...")

    try:
        # Create all tables
        Base.metadata.create_all(engine)

        logger.info("Database tables created successfully!")
        logger.info("Tables created:")
        for table in Base.metadata.sorted_tables:
            logger.info(f"  - {table.name}")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)
