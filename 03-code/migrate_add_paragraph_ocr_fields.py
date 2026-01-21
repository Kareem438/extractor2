#!/usr/bin/env python3
"""
Migration: Add OCR fields to paragraph_images table

Adds the following columns to raw_{prefix}_paragraph_images:
- extracted_text TEXT (copy of OCR text)
- ocr_confidence NUMERIC(5,2)
- linked_knowledge_unit_id INTEGER
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.connection import engine
from src.utils.logging_config import logger


def get_all_book_prefixes():
    """Get all book table prefixes from books_metadata"""
    sql = text("""
        SELECT book_id, table_prefix
        FROM books_metadata
        ORDER BY book_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)
        return [(row[0], row[1]) for row in result.fetchall()]


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    sql = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :table_name
        )
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"table_name": table_name})
        return result.scalar()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    sql = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
        )
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"table_name": table_name, "column_name": column_name})
        return result.scalar()


def add_paragraph_ocr_columns(table_prefix: str):
    """Add OCR columns to paragraph_images table"""
    table_name = f"raw_{table_prefix}_paragraph_images"

    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping")
        return False

    columns_to_add = [
        ("extracted_text", "TEXT"),
        ("ocr_confidence", "NUMERIC(5,2)"),
        ("linked_knowledge_unit_id", "INTEGER"),
    ]

    with engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            if column_exists(table_name, column_name):
                logger.info(f"  Column {column_name} already exists in {table_name}, skipping")
                continue

            sql = text(f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {column_type}
            """)
            conn.execute(sql)
            logger.info(f"  Added column {column_name} to {table_name}")

        conn.commit()

    return True


def main():
    print("=" * 60)
    print("Migration: Add OCR Fields to Paragraph Images")
    print("=" * 60)
    print()

    # Get all book prefixes
    books = get_all_book_prefixes()
    print(f"Found {len(books)} books to migrate:\n")

    for book_id, table_prefix in books:
        print(f"Migrating: raw_{table_prefix}_paragraph_images")
        try:
            success = add_paragraph_ocr_columns(table_prefix)
            if success:
                print(f"  ✅ Success\n")
            else:
                print(f"  ⏭️ Skipped (table does not exist)\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print("=" * 60)
    print("Migration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
