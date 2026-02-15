"""
Migration: Add V2 tables to existing books

Creates V2 extraction tables (v2_knowledge_pages, v2_extraction_log,
v2_few_shot_examples, v2_attribute_keys) for all existing books that
don't already have them.

Usage:
    python migrate_add_v2_tables.py
"""

from sqlalchemy import text
from src.database.connection import engine
from src.database.table_creator import create_v2_book_tables


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = :table
        """), {"table": table_name})
        return result.scalar() > 0


def migrate():
    """Run migration to add V2 tables to existing books."""
    print("=" * 60)
    print("Migration: Add V2 Tables to Existing Books")
    print("=" * 60)

    changes = 0

    with engine.connect() as db:
        # Get all existing books
        result = db.execute(text(
            "SELECT book_id, book_name, table_prefix FROM books_metadata ORDER BY book_id"
        ))
        books = result.fetchall()

        print(f"\nFound {len(books)} existing book(s)")

        for book_id, book_name, table_prefix in books:
            v2_kp_table = f"v2_{table_prefix}_knowledge_pages"

            if table_exists(v2_kp_table):
                print(f"  ⏭️  Book {book_id} ({book_name}): V2 tables already exist")
                continue

            print(f"  📦 Book {book_id} ({book_name}): Creating V2 tables...")
            try:
                create_v2_book_tables(table_prefix)
                print(f"     ✅ V2 tables created for {table_prefix}")
                changes += 1
            except Exception as e:
                print(f"     ❌ Error: {e}")

    print(f"\nMigration complete: {changes} book(s) updated with V2 tables")


if __name__ == "__main__":
    migrate()
