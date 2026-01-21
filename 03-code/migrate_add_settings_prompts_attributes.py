"""
Migration Script: Add Diagram Prompts and Attribute Configuration to Settings Table

This script adds 15 new columns to all book settings tables:
- 3 diagram analysis prompts (diagram_prompt, equation_prompt, table_prompt)
- 6 attribute ID selections (ocr_attr1-3_id, manual_attr1-3_id)
- 6 custom labels (ocr_label1-3, manual_label1-3)

Run this migration AFTER the 40→80 attribute expansion migration.

Author: Claude Code
Date: 2026-01-07
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


def get_all_books():
    """Get all books from books_metadata."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT book_id, table_prefix, book_name
            FROM books_metadata
            ORDER BY book_id
        """))
        return result.fetchall()


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


def add_column(table_prefix, column_name, column_type, default_value=None):
    """Add a column to a settings table if it doesn't exist."""
    table_name = f"{table_prefix}_settings"

    if check_column_exists(table_name, column_name):
        logger.info(f"  ✓ Column {column_name} already exists in {table_name}, skipping")
        return False

    try:
        with engine.connect() as conn:
            # Build ALTER TABLE statement
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"

            if default_value is not None:
                sql += f" DEFAULT {default_value}"

            conn.execute(text(sql))
            conn.commit()

            logger.info(f"  ✅ Added column {column_name} to {table_name}")
            return True

    except ProgrammingError as e:
        logger.error(f"  ❌ Error adding column {column_name} to {table_name}: {e}")
        return False


def migrate_book(book_id, table_prefix, book_name):
    """Migrate a single book's settings table."""
    logger.info(f"\n📘 Processing book {book_id}: {book_name} (prefix: {table_prefix})")

    # Check if settings table exists
    table_name = f"{table_prefix}_settings"

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = :table_name
        """), {"table_name": table_name})

        if result.fetchone()[0] == 0:
            logger.warning(f"  ⚠️  Settings table {table_name} does not exist, skipping")
            return

    # Define columns to add
    columns = [
        # Diagram analysis prompts (large TEXT fields)
        ("diagram_prompt", "TEXT", None),
        ("equation_prompt", "TEXT", None),
        ("table_prompt", "TEXT", None),

        # OCR attribute selections (3 for rectangle-based OCR)
        ("ocr_attr1_id", "INTEGER", None),
        ("ocr_attr2_id", "INTEGER", None),
        ("ocr_attr3_id", "INTEGER", None),

        # Manual attribute selections (3 for typed/pasted text)
        ("manual_attr1_id", "INTEGER", None),
        ("manual_attr2_id", "INTEGER", None),
        ("manual_attr3_id", "INTEGER", None),

        # OCR text area labels (custom user-defined labels)
        ("ocr_label1", "VARCHAR(200)", None),
        ("ocr_label2", "VARCHAR(200)", None),
        ("ocr_label3", "VARCHAR(200)", None),

        # Manual text area labels (custom user-defined labels)
        ("manual_label1", "VARCHAR(200)", None),
        ("manual_label2", "VARCHAR(200)", None),
        ("manual_label3", "VARCHAR(200)", None),
    ]

    # Add columns
    added_count = 0
    for column_name, column_type, default_value in columns:
        if add_column(table_prefix, column_name, column_type, default_value):
            added_count += 1

    logger.info(f"  📊 Added {added_count} new columns to {table_name}")


def verify_migration(book_id, table_prefix):
    """Verify that migration was successful."""
    table_name = f"{table_prefix}_settings"

    expected_columns = [
        'diagram_prompt', 'equation_prompt', 'table_prompt',
        'ocr_attr1_id', 'ocr_attr2_id', 'ocr_attr3_id',
        'manual_attr1_id', 'manual_attr2_id', 'manual_attr3_id',
        'ocr_label1', 'ocr_label2', 'ocr_label3',
        'manual_label1', 'manual_label2', 'manual_label3'
    ]

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = ANY(:columns)
        """), {"table_name": table_name, "columns": expected_columns})

        found_columns = [row[0] for row in result]

    missing = set(expected_columns) - set(found_columns)

    if missing:
        logger.warning(f"  ⚠️  Missing columns in {table_name}: {missing}")
        return False
    else:
        logger.info(f"  ✅ All 15 columns verified in {table_name}")
        return True


def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("MIGRATION: Add Diagram Prompts and Attribute Configuration to Settings")
    logger.info("=" * 80)

    try:
        # Get all books
        books = get_all_books()
        logger.info(f"\n📚 Found {len(books)} books in database\n")

        if len(books) == 0:
            logger.warning("No books found in database. Migration complete (nothing to do).")
            return

        # Migrate each book
        migrated_count = 0
        verified_count = 0

        for book_id, table_prefix, book_name in books:
            migrate_book(book_id, table_prefix, book_name)
            migrated_count += 1

            # Verify migration
            if verify_migration(book_id, table_prefix):
                verified_count += 1

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Books processed: {migrated_count}/{len(books)}")
        logger.info(f"✅ Books verified: {verified_count}/{len(books)}")

        if verified_count == len(books):
            logger.info("\n🎉 Migration completed successfully!")
        else:
            logger.warning(f"\n⚠️  Migration completed with warnings ({verified_count}/{len(books)} verified)")

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ask for confirmation
    print("\n" + "=" * 80)
    print("MIGRATION: Add Diagram Prompts and Attribute Configuration")
    print("=" * 80)
    print("\nThis will add 15 new columns to all book settings tables:")
    print("  - 3 diagram analysis prompts (TEXT)")
    print("  - 6 attribute ID selections (INTEGER)")
    print("  - 6 custom labels (VARCHAR(200))")
    print("\nAll columns will default to NULL.")
    print("\nThis operation is SAFE and can be run multiple times (idempotent).")
    print("=" * 80)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        main()
    else:
        print("\n❌ Migration cancelled by user.")
        sys.exit(0)
