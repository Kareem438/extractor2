"""
Migration: Add Knowledge Pages and Cloud OCR Pages Tables

Creates the following tables for each book:
- {prefix}_knowledge_pages: Stores Qwen VL structured output as JSONB, grouped by L3 title
- {prefix}_cloud_ocr_pages: Per-page tracking for cloud OCR extraction status

Run: python migrate_add_knowledge_pages.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.connection import engine, SessionLocal


def get_all_books():
    """Get all books from the database."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT book_id, table_prefix, book_name FROM books_metadata ORDER BY book_id"))
        return [{"book_id": row[0], "table_prefix": row[1], "book_name": row[2]} for row in result.fetchall()]
    finally:
        db.close()


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
            {"name": table_name}
        ).scalar()
        return result
    finally:
        db.close()


def create_knowledge_pages_table(table_prefix: str):
    """Create knowledge_pages table for Qwen VL structured output."""
    table_name = f"{table_prefix}_knowledge_pages"

    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False

    sql = f"""
    CREATE TABLE {table_name} (
        id SERIAL PRIMARY KEY,

        -- L3 section boundaries
        l3_title TEXT,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,

        -- Parent title hierarchy (resolved server-side from title tables)
        l1_title_id INTEGER,
        l2_title_id INTEGER,
        l1_title_text VARCHAR(500),
        l2_title_text VARCHAR(500),

        -- The full structured content as JSON
        content JSONB NOT NULL,

        -- Processing metadata
        ocr_engine VARCHAR(50) DEFAULT 'qwen-cloud',
        model_name VARCHAR(100),
        cached_tokens INTEGER DEFAULT 0,
        total_input_tokens INTEGER DEFAULT 0,
        total_output_tokens INTEGER DEFAULT 0,

        -- Status: extracted -> reviewed -> ready_to_convert -> converted
        status VARCHAR(30) DEFAULT 'extracted',

        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """

    db = SessionLocal()
    try:
        db.execute(text(sql))

        # Create indexes
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_kp_pages ON {table_name}(start_page, end_page)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_kp_status ON {table_name}(status)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_kp_l3 ON {table_name}(l3_title)"))

        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def create_cloud_ocr_pages_table(table_prefix: str):
    """Create cloud_ocr_pages table for per-page extraction tracking."""
    table_name = f"{table_prefix}_cloud_ocr_pages"

    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False

    sql = f"""
    CREATE TABLE {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL UNIQUE,
        status VARCHAR(20) DEFAULT 'pending',
        error_message TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cached_tokens INTEGER,
        processing_time_ms INTEGER,
        model_name VARCHAR(100),
        attempt_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """

    db = SessionLocal()
    try:
        db.execute(text(sql))

        # Create indexes
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_cop_status ON {table_name}(status)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_cop_page ON {table_name}(page_number)"))

        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def migrate_book(book: dict):
    """Run migration for a single book."""
    print(f"\n📚 Migrating book: {book['book_name']} (ID: {book['book_id']})")
    print(f"   Table prefix: {book['table_prefix']}")

    create_knowledge_pages_table(book['table_prefix'])
    create_cloud_ocr_pages_table(book['table_prefix'])


def main():
    print("=" * 60)
    print("Migration: Add Knowledge Pages & Cloud OCR Pages Tables")
    print("=" * 60)

    books = get_all_books()

    if not books:
        print("\n⚠️  No books found in database")
        return

    print(f"\nFound {len(books)} book(s) to migrate")

    for book in books:
        migrate_book(book)

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
