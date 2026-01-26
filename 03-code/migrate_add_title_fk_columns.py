"""
Migration: Add L1/L2 Title Foreign Key Columns

Adds the following columns to existing tables:
- raw_{prefix}_layout_detections: l1_title_id, l2_title_id
- raw_{prefix}_paragraph_images: l1_title_id, l2_title_id
- raw_{prefix}_diagram_images: l1_title_id, l2_title_id
- raw_{prefix}_pages: is_skipped (for Skip Pages feature)

Run: python migrate_add_title_fk_columns.py
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


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = :table_name AND column_name = :column_name
                )
            """),
            {"table_name": table_name, "column_name": column_name}
        ).scalar()
        return result
    finally:
        db.close()


def add_column_if_not_exists(table_name: str, column_name: str, column_type: str) -> bool:
    """Add a column to a table if it doesn't exist."""
    if not table_exists(table_name):
        print(f"    ⏭️  Table {table_name} does not exist, skipping")
        return False
    
    if column_exists(table_name, column_name):
        print(f"    ⏭️  Column {column_name} already exists in {table_name}")
        return False
    
    db = SessionLocal()
    try:
        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        db.commit()
        print(f"    ✅ Added column {column_name} to {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"    ❌ Error adding {column_name} to {table_name}: {e}")
        return False
    finally:
        db.close()


def add_index_if_not_exists(table_name: str, index_name: str, column_name: str) -> bool:
    """Add an index if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if index exists
        result = db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE tablename = :table_name AND indexname = :index_name
                )
            """),
            {"table_name": table_name, "index_name": index_name}
        ).scalar()
        
        if result:
            print(f"    ⏭️  Index {index_name} already exists")
            return False
        
        db.execute(text(f"CREATE INDEX {index_name} ON {table_name}({column_name})"))
        db.commit()
        print(f"    ✅ Created index {index_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"    ❌ Error creating index {index_name}: {e}")
        return False
    finally:
        db.close()


def migrate_layout_detections(table_prefix: str):
    """Add l1_title_id and l2_title_id columns to layout_detections table."""
    table_name = f"raw_{table_prefix}_layout_detections"
    print(f"\n  📋 Migrating {table_name}...")
    
    # Add l1_title_id column
    add_column_if_not_exists(table_name, "l1_title_id", "INTEGER")
    
    # Add l2_title_id column
    add_column_if_not_exists(table_name, "l2_title_id", "INTEGER")
    
    # Add indexes
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_ld_l1_title", "l1_title_id")
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_ld_l2_title", "l2_title_id")


def migrate_paragraph_images(table_prefix: str):
    """Add l1_title_id and l2_title_id columns to paragraph_images table."""
    table_name = f"raw_{table_prefix}_paragraph_images"
    print(f"\n  📋 Migrating {table_name}...")
    
    # Add l1_title_id column
    add_column_if_not_exists(table_name, "l1_title_id", "INTEGER")
    
    # Add l2_title_id column
    add_column_if_not_exists(table_name, "l2_title_id", "INTEGER")
    
    # Add indexes
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_para_l1_title", "l1_title_id")
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_para_l2_title", "l2_title_id")


def migrate_diagram_images(table_prefix: str):
    """Add l1_title_id and l2_title_id columns to diagram_images table."""
    table_name = f"raw_{table_prefix}_diagram_images"
    print(f"\n  📋 Migrating {table_name}...")
    
    # Add l1_title_id column
    add_column_if_not_exists(table_name, "l1_title_id", "INTEGER")
    
    # Add l2_title_id column
    add_column_if_not_exists(table_name, "l2_title_id", "INTEGER")
    
    # Add indexes
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_diag_l1_title", "l1_title_id")
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_diag_l2_title", "l2_title_id")


def migrate_pages_skip_status(table_prefix: str):
    """Add is_skipped column to pages table for Skip Pages feature."""
    table_name = f"raw_{table_prefix}_pages"
    print(f"\n  📋 Migrating {table_name} (Skip Pages)...")
    
    # Add is_skipped column
    add_column_if_not_exists(table_name, "is_skipped", "BOOLEAN DEFAULT FALSE")
    
    # Add is_ready_for_extraction column
    add_column_if_not_exists(table_name, "is_ready_for_extraction", "BOOLEAN DEFAULT FALSE")
    
    # Add indexes
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_pages_skipped", "is_skipped")
    add_index_if_not_exists(table_name, f"idx_{table_prefix}_pages_ready", "is_ready_for_extraction")


def migrate_book(book: dict):
    """Run migration for a single book."""
    print(f"\n📚 Migrating book: {book['book_name']} (ID: {book['book_id']})")
    print(f"   Table prefix: {book['table_prefix']}")
    
    # Add FK columns to layout_detections
    migrate_layout_detections(book['table_prefix'])
    
    # Add FK columns to paragraph_images
    migrate_paragraph_images(book['table_prefix'])
    
    # Add FK columns to diagram_images
    migrate_diagram_images(book['table_prefix'])
    
    # Add skip status to pages
    migrate_pages_skip_status(book['table_prefix'])


def main():
    print("=" * 60)
    print("Migration: Add L1/L2 Title FK Columns + Skip Pages")
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
