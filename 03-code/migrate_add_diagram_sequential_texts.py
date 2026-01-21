"""
Migration: Add Sequential Text Columns to Diagram Images Table

This migration adds 6 columns to the diagram_images table to support
the Phase 4/5 sequential OCR and manual text feature:
- ocr_text_1, ocr_text_2, ocr_text_3: OCR-extracted texts from rectangles
- manual_text_1, manual_text_2, manual_text_3: User-typed manual texts

These columns store the context texts that will be used in Claude API
pipeline processing for enhanced diagram analysis.

Run this migration BEFORE using the POST /api/sequential-texts/save endpoint.

Usage:
    python migrate_add_diagram_sequential_texts.py
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


def get_all_diagram_tables():
    """Get all diagram_images tables in the database."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name LIKE 'raw_%_diagram_images'
            ORDER BY table_name
        """))
        return [row[0] for row in result.fetchall()]


def check_column_exists(table_name, column_name):
    """Check if a column already exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        return result.scalar() > 0


def add_sequential_text_columns(table_name):
    """Add 6 sequential text columns to a diagram_images table."""
    columns_to_add = [
        'ocr_text_1',
        'ocr_text_2',
        'ocr_text_3',
        'manual_text_1',
        'manual_text_2',
        'manual_text_3'
    ]

    added_columns = []
    skipped_columns = []

    with engine.connect() as conn:
        for column_name in columns_to_add:
            if check_column_exists(table_name, column_name):
                logger.info(f"  Column '{column_name}' already exists in {table_name}, skipping")
                skipped_columns.append(column_name)
            else:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN {column_name} TEXT
                    """))
                    conn.commit()
                    logger.info(f"  Added column '{column_name}' to {table_name}")
                    added_columns.append(column_name)
                except ProgrammingError as e:
                    logger.error(f"  Failed to add column '{column_name}': {e}")
                    conn.rollback()

    return added_columns, skipped_columns


def main():
    """Main migration function."""
    logger.info("=" * 70)
    logger.info("Migration: Add Sequential Text Columns to Diagram Images Tables")
    logger.info("=" * 70)

    try:
        # Get all diagram_images tables
        logger.info("Finding all diagram_images tables...")
        tables = get_all_diagram_tables()

        if not tables:
            logger.warning("No diagram_images tables found!")
            return

        logger.info(f"Found {len(tables)} diagram_images table(s)")
        logger.info("")

        # Process each table
        total_added = 0
        total_skipped = 0

        for table in tables:
            logger.info(f"Processing table: {table}")
            added, skipped = add_sequential_text_columns(table)
            total_added += len(added)
            total_skipped += len(skipped)
            logger.info("")

        # Summary
        logger.info("=" * 70)
        logger.info("Migration completed successfully!")
        logger.info("=" * 70)
        logger.info(f"Summary:")
        logger.info(f"  - Tables processed: {len(tables)}")
        logger.info(f"  - Columns added: {total_added}")
        logger.info(f"  - Columns skipped (already exist): {total_skipped}")
        logger.info("")
        logger.info("The following columns are now available:")
        logger.info("  - ocr_text_1, ocr_text_2, ocr_text_3 (OCR-extracted texts)")
        logger.info("  - manual_text_1, manual_text_2, manual_text_3 (User-typed texts)")
        logger.info("")
        logger.info("You can now use POST /api/sequential-texts/save endpoint!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
