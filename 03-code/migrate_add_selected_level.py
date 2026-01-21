"""
Migration: Add selected_level_number and selected_level_text columns to paragraph_images and diagram_images tables.

This migration adds the following columns to both tables:
- selected_level_number INTEGER (1-5)
- selected_level_text VARCHAR(500)

These columns store the hierarchy level that was selected when the paragraph/diagram was saved,
along with the actual text of that level (since level meanings change page to page).

Run this migration from the 03-code directory:
    python migrate_add_selected_level.py
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


def add_selected_level_columns(table_name: str):
    """Add the selected_level_number and selected_level_text columns to a table."""
    columns_to_add = [
        ("selected_level_number", "INTEGER"),
        ("selected_level_text", "VARCHAR(500)"),
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


def run_migration():
    """Run the migration for all books."""
    print("=" * 60)
    print("Migration: Add Selected Level Columns")
    print("=" * 60)

    # Get all book table prefixes
    table_prefixes = get_all_book_table_prefixes()

    if not table_prefixes:
        print("No books found in database.")
        return

    print(f"\nFound {len(table_prefixes)} books to migrate:\n")

    for prefix in table_prefixes:
        # Migrate paragraph_images table
        paragraph_table = f"raw_{prefix}_paragraph_images"
        print(f"Migrating: {paragraph_table}")
        if table_exists(paragraph_table):
            try:
                add_selected_level_columns(paragraph_table)
                print(f"  ✅ Success\n")
            except Exception as e:
                print(f"  ❌ Failed: {e}\n")
        else:
            print(f"  ⏭️ Skipped (table does not exist)\n")

        # Migrate diagram_images table
        diagram_table = f"raw_{prefix}_diagram_images"
        print(f"Migrating: {diagram_table}")
        if table_exists(diagram_table):
            try:
                add_selected_level_columns(diagram_table)
                print(f"  ✅ Success\n")
            except Exception as e:
                print(f"  ❌ Failed: {e}\n")
        else:
            print(f"  ⏭️ Skipped (table does not exist)\n")

    print("=" * 60)
    print("Migration completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
