"""
Migration: Add missing columns to knowledge_units table to match specification.

This migration adds the following columns to {prefix}_knowledge_units:
- text_length INTEGER - Length of text_content in characters
- line_count INTEGER - Number of lines in the text
- position_width INTEGER - Width of bounding box
- position_height INTEGER - Height of bounding box
- extraction_method VARCHAR(50) - OCR method used (PaddleOCR, Surya, Tesseract)
- verified_at TIMESTAMP - When the record was verified
- verified_by VARCHAR(100) - User who verified the record

These columns were defined in the specification (02-architecture/database-schema.md)
but were missing in the initial implementation.

Run this migration from the 03-code directory:
    cd H:/12-extractor/03-code
    H:/12-extractor/venv/Scripts/python.exe migrate_add_knowledge_unit_missing_columns.py
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


def add_missing_columns(table_prefix: str):
    """Add the missing columns to a knowledge_units table."""
    table_name = f"{table_prefix}_knowledge_units"

    # Check if table exists first
    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping")
        return False

    # Define columns to add with their types and default values
    columns_to_add = [
        # Text metrics
        ("text_length", "INTEGER", None),
        ("line_count", "INTEGER", None),

        # Complete bounding box (width and height are missing)
        ("position_width", "INTEGER", None),
        ("position_height", "INTEGER", None),

        # Extraction method tracking
        ("extraction_method", "VARCHAR(50)", None),

        # Verification tracking
        ("verified_at", "TIMESTAMP", None),
        ("verified_by", "VARCHAR(100)", None),
    ]

    columns_added = 0
    columns_skipped = 0

    with engine.connect() as conn:
        for column_info in columns_to_add:
            column_name = column_info[0]
            column_type = column_info[1]
            default_value = column_info[2] if len(column_info) > 2 else None

            # Check if column already exists
            if column_exists(table_name, column_name):
                logger.info(f"  Column {column_name} already exists in {table_name}, skipping")
                columns_skipped += 1
                continue

            # Add the column
            try:
                if default_value:
                    sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
                else:
                    sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

                conn.execute(sql)
                conn.commit()
                logger.info(f"  ✅ Added column {column_name} ({column_type}) to {table_name}")
                columns_added += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to add column {column_name} to {table_name}: {e}")
                raise

    return columns_added, columns_skipped


def populate_text_metrics(table_prefix: str):
    """Populate text_length and line_count for existing records."""
    table_name = f"{table_prefix}_knowledge_units"

    if not table_exists(table_name):
        return 0

    # Check if columns exist
    if not column_exists(table_name, "text_length"):
        return 0

    with engine.connect() as conn:
        try:
            # Update text_length based on text_content
            sql = text(f"""
                UPDATE {table_name}
                SET text_length = LENGTH(text_content)
                WHERE text_content IS NOT NULL
                AND text_length IS NULL
            """)
            result = conn.execute(sql)
            updated_length = result.rowcount

            # Update line_count based on newline characters in text_content
            sql = text(f"""
                UPDATE {table_name}
                SET line_count = (LENGTH(text_content) - LENGTH(REPLACE(text_content, E'\\n', '')) + 1)
                WHERE text_content IS NOT NULL
                AND line_count IS NULL
            """)
            result = conn.execute(sql)
            updated_lines = result.rowcount

            conn.commit()
            logger.info(f"  Updated text_length for {updated_length} records")
            logger.info(f"  Updated line_count for {updated_lines} records")

            return updated_length
        except Exception as e:
            logger.error(f"  Failed to populate text metrics: {e}")
            return 0


def populate_extraction_method(table_prefix: str):
    """Populate extraction_method based on ocr_method if available."""
    table_name = f"{table_prefix}_knowledge_units"

    if not table_exists(table_name):
        return 0

    # Check if both columns exist
    if not column_exists(table_name, "extraction_method"):
        return 0

    if not column_exists(table_name, "ocr_method"):
        logger.info(f"  ocr_method column doesn't exist, skipping extraction_method population")
        return 0

    with engine.connect() as conn:
        try:
            # Copy ocr_method to extraction_method for existing records
            sql = text(f"""
                UPDATE {table_name}
                SET extraction_method = ocr_method
                WHERE ocr_method IS NOT NULL
                AND extraction_method IS NULL
            """)
            result = conn.execute(sql)
            updated = result.rowcount
            conn.commit()

            logger.info(f"  Updated extraction_method for {updated} records")
            return updated
        except Exception as e:
            logger.error(f"  Failed to populate extraction_method: {e}")
            return 0


def run_migration():
    """Run the migration for all books."""
    print("=" * 80)
    print("Migration: Add Missing Columns to Knowledge Units Table")
    print("=" * 80)
    print("\nThis migration adds 7 missing columns defined in the specification:")
    print("  • text_length, line_count - Text metrics")
    print("  • position_width, position_height - Complete bounding box")
    print("  • extraction_method - OCR engine tracking")
    print("  • verified_at, verified_by - Verification audit trail")
    print("=" * 80)

    # Get all book table prefixes
    table_prefixes = get_all_book_table_prefixes()

    if not table_prefixes:
        print("\n❌ No books found in database.")
        return

    print(f"\n📚 Found {len(table_prefixes)} books to migrate\n")

    total_added = 0
    total_skipped = 0
    total_populated = 0

    for prefix in table_prefixes:
        print(f"{'─' * 80}")
        print(f"📖 Migrating: {prefix}_knowledge_units")
        print(f"{'─' * 80}")

        try:
            # Add missing columns
            result = add_missing_columns(prefix)
            if result:
                columns_added, columns_skipped = result
                total_added += columns_added
                total_skipped += columns_skipped

                print(f"  ✅ Added {columns_added} new columns")
                if columns_skipped > 0:
                    print(f"  ⏭️  Skipped {columns_skipped} existing columns")

                # Populate text metrics if columns were added
                if columns_added > 0:
                    print(f"\n  📊 Populating calculated fields...")
                    populated = populate_text_metrics(prefix)
                    populate_extraction_method(prefix)
                    total_populated += populated

                print(f"  ✅ Migration complete for {prefix}\n")
            else:
                print(f"  ⏭️  Skipped (table does not exist)\n")
        except Exception as e:
            print(f"  ❌ Migration failed: {e}\n")
            raise

    print("=" * 80)
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    print(f"  Total columns added: {total_added}")
    print(f"  Total columns skipped (already exist): {total_skipped}")
    print(f"  Total records with populated metrics: {total_populated}")
    print("=" * 80)
    print("✅ Migration completed successfully!")
    print("=" * 80)
    print("\n📝 NEXT STEPS:")
    print("  1. Update code to use new columns (text_length, line_count, etc.)")
    print("  2. Update OCR extraction to populate extraction_method")
    print("  3. Update verification UI to set verified_at and verified_by")
    print("  4. Consider adding indexes on frequently queried columns")
    print("=" * 80)


if __name__ == "__main__":
    run_migration()
