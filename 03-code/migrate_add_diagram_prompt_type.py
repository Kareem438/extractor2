"""
Migration Script: Add prompt_type Column to Diagram Images Tables

This script adds a prompt_type column to all raw diagram images tables to track
which prompt was used for diagram analysis (diagram/equation/table).

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


def check_table_exists(table_name):
    """Check if a table exists."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = :table_name
        """), {"table_name": table_name})

        return result.fetchone()[0] > 0


def add_prompt_type_column(table_prefix):
    """Add prompt_type column to diagram images table."""
    table_name = f"raw_{table_prefix}_diagram_images"

    # Check if table exists
    if not check_table_exists(table_name):
        logger.warning(f"  ⚠️  Table {table_name} does not exist, skipping")
        return False

    # Check if column already exists
    if check_column_exists(table_name, "prompt_type"):
        logger.info(f"  ✓ Column prompt_type already exists in {table_name}, skipping")
        return False

    try:
        with engine.connect() as conn:
            # Add prompt_type column
            sql = f"""
            ALTER TABLE {table_name}
            ADD COLUMN prompt_type VARCHAR(20)
            """

            conn.execute(text(sql))
            conn.commit()

            logger.info(f"  ✅ Added prompt_type column to {table_name}")
            return True

    except ProgrammingError as e:
        logger.error(f"  ❌ Error adding prompt_type to {table_name}: {e}")
        return False


def verify_migration(table_prefix):
    """Verify that prompt_type column was added successfully."""
    table_name = f"raw_{table_prefix}_diagram_images"

    # Check if table exists
    if not check_table_exists(table_name):
        return False

    # Check if column exists
    if check_column_exists(table_name, "prompt_type"):
        logger.info(f"  ✅ Column prompt_type verified in {table_name}")
        return True
    else:
        logger.warning(f"  ⚠️  Column prompt_type NOT found in {table_name}")
        return False


def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("MIGRATION: Add prompt_type Column to Diagram Images Tables")
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
            logger.info(f"\n📘 Processing book {book_id}: {book_name} (prefix: {table_prefix})")

            if add_prompt_type_column(table_prefix):
                migrated_count += 1

            # Verify migration
            if verify_migration(table_prefix):
                verified_count += 1

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Books with diagram tables found: {verified_count}")
        logger.info(f"✅ New columns added: {migrated_count}")
        logger.info(f"✅ Columns verified: {verified_count}")

        if verified_count > 0:
            logger.info("\n🎉 Migration completed successfully!")
        else:
            logger.warning("\n⚠️  No diagram tables found (this may be normal if no diagrams exist yet)")

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ask for confirmation
    print("\n" + "=" * 80)
    print("MIGRATION: Add prompt_type Column to Diagram Images Tables")
    print("=" * 80)
    print("\nThis will add prompt_type VARCHAR(20) column to all raw diagram tables.")
    print("Valid values: 'diagram', 'equation', or 'table'")
    print("\nExisting diagrams will have NULL prompt_type (legacy diagrams).")
    print("New diagrams will always have a prompt_type.")
    print("\nThis operation is SAFE and can be run multiple times (idempotent).")
    print("=" * 80)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        main()
    else:
        print("\n❌ Migration cancelled by user.")
        sys.exit(0)
