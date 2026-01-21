"""
Migration Script: Add Auto-Slicer Configuration to Books Metadata

This script adds a JSONB column to the books_metadata table for storing
Auto-slicer configuration:
- auto_slicer_config JSONB

The column stores:
- Page range (start/end)
- Title configuration (3 levels with page ranges)
- Batch configuration (optional page range batches)
- OCR boundaries with multiple rectangles
- Execution state (for pause/resume)
- Last run results

Run this migration from the 03-code directory:
    python migrate_add_auto_slicer.py

Author: Claude Code
Date: 2026-01-12
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/knowledge_extraction"
engine = create_engine(DATABASE_URL)


def check_column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})

        return result.fetchone()[0] > 0


def add_auto_slicer_column():
    """Add auto_slicer_config column to books_metadata table."""
    table_name = "books_metadata"
    column_name = "auto_slicer_config"

    if check_column_exists(table_name, column_name):
        logger.info(f"Column {column_name} already exists in {table_name}, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSONB"
            conn.execute(text(sql))
            conn.commit()

            logger.info(f"Added column {column_name} to {table_name}")
            return True

    except ProgrammingError as e:
        logger.error(f"Error adding column {column_name} to {table_name}: {e}")
        return False


def verify_migration():
    """Verify that migration was successful."""
    table_name = "books_metadata"
    column_name = "auto_slicer_config"

    if check_column_exists(table_name, column_name):
        logger.info(f"Verified: Column {column_name} exists in {table_name}")
        return True
    else:
        logger.error(f"Verification failed: Column {column_name} not found in {table_name}")
        return False


def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("MIGRATION: Add Auto-Slicer Configuration to Books Metadata")
    logger.info("=" * 80)

    try:
        # Add the column
        result = add_auto_slicer_column()

        if result:
            logger.info("\nColumn added successfully!")
        else:
            logger.info("\nNo changes made (column may already exist)")

        # Verify
        if verify_migration():
            logger.info("\n" + "=" * 80)
            logger.info("MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
        else:
            logger.error("\nMigration verification failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"\nMigration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Display info
    print("\n" + "=" * 80)
    print("MIGRATION: Add Auto-Slicer Configuration")
    print("=" * 80)
    print("\nThis will add the following column to books_metadata table:")
    print("  - auto_slicer_config JSONB")
    print("\nThis stores Auto-slicer configuration per book:")
    print("  - Page range (start/end)")
    print("  - Title configuration (3 levels)")
    print("  - Batch configuration")
    print("  - OCR boundaries with multiple rectangles")
    print("  - Execution state (pause/resume)")
    print("  - Last run results")
    print("\nThis operation is SAFE and can be run multiple times (idempotent).")
    print("=" * 80)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        main()
    else:
        print("\nMigration cancelled by user.")
        sys.exit(0)
