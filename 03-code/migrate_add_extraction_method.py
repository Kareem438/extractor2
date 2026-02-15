"""
Migration: Add extraction_method column to books_metadata

Adds extraction_method column (VARCHAR, default 'v2') to books_metadata table.
This controls whether a book uses V1 (YOLO + manual review) or V2 (cloud LLM extraction).

Usage:
    python migrate_add_extraction_method.py
"""

from sqlalchemy import text
from src.database.connection import engine


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = :table AND column_name = :col
        """), {"table": table_name, "col": column_name})
        return result.scalar() > 0


def migrate():
    """Run migration to add extraction_method column."""
    print("=" * 60)
    print("Migration: Add extraction_method to books_metadata")
    print("=" * 60)

    changes = 0

    with engine.connect() as db:
        if not column_exists("books_metadata", "extraction_method"):
            db.execute(text("""
                ALTER TABLE books_metadata
                ADD COLUMN extraction_method VARCHAR(10) DEFAULT 'v2'
            """))
            db.commit()
            print("  ✅ Added extraction_method column (default 'v2')")
            changes += 1
        else:
            print("  ⏭️  extraction_method column already exists")

    print(f"\nMigration complete: {changes} change(s) applied")


if __name__ == "__main__":
    migrate()
