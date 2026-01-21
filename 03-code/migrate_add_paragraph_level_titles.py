"""
Migration: Add 4 level title columns to paragraph_images table.

This migration adds the following columns:
- level_1_title VARCHAR(500)
- level_2_title VARCHAR(500)
- level_3_title VARCHAR(500)
- level_4_title VARCHAR(500)

These columns store the hierarchy level titles for each paragraph,
allowing users to position paragraphs within the book structure.
This is used by the "Load Titles" feature.

Run this migration from the 03-code directory:
    python migrate_add_paragraph_level_titles.py
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.connection import engine, SessionLocal
from src.utils.logging_config import logger


def get_all_book_table_prefixes():
    """Get all table prefixes from books_metadata."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT table_prefix FROM books_metadata"))
        return [row[0] for row in result.fetchall()]
    finally:
        db.close()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        return result.fetchone() is not None
    finally:
        db.close()


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        return result.fetchone()[0]
    finally:
        db.close()


def add_level_title_columns(table_prefix: str):
    """Add the 4 level title columns to a paragraph_images table."""
    table_name = f"raw_{table_prefix}_paragraph_images"

    # Check if table exists first
    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping")
        return False

    columns_to_add = [
        ("level_1_title", "VARCHAR(500)"),
        ("level_2_title", "VARCHAR(500)"),
        ("level_3_title", "VARCHAR(500)"),
        ("level_4_title", "VARCHAR(500)"),
    ]

    with engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            # Check if column already exists
            if column_exists(table_name, column_name):
                logger.info(f"  Column {column_name} already exists in {table_name}, skipping")
                continue

            # Add the column
            try:
                sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                conn.execute(sql)
                conn.commit()
                logger.info(f"  Added column {column_name} to {table_name}")
            except Exception as e:
                logger.error(f"  Failed to add column {column_name} to {table_name}: {e}")
                raise

    return True


def run_migration():
    """Run the migration for all books."""
    print("=" * 60)
    print("Migration: Add Level Title Columns to Paragraph Images")
    print("=" * 60)

    # Get all book table prefixes
    table_prefixes = get_all_book_table_prefixes()

    if not table_prefixes:
        print("No books found in database.")
        return

    print(f"\nFound {len(table_prefixes)} books to migrate:\n")

    for prefix in table_prefixes:
        print(f"Migrating: raw_{prefix}_paragraph_images")
        try:
            result = add_level_title_columns(prefix)
            if result:
                print(f"  ✅ Success\n")
            else:
                print(f"  ⏭️ Skipped (table does not exist)\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            raise

    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
