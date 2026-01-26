"""
Migration: Add Hierarchical Title Tables (L1 and L2)

Creates the following tables for each book:
- {prefix}_level1_titles: 200 custom attributes for chapter-level titles
- {prefix}_level2_titles: 150 custom attributes for section-level titles

Also ensures l3_title_id column exists in layout_detections table.

Run: python migrate_add_title_hierarchy.py
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


def create_level1_titles_table(table_prefix: str):
    """Create level1_titles table with 200 custom attributes."""
    table_name = f"{table_prefix}_level1_titles"
    
    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False
    
    # Build attribute columns (200 pairs of name/value)
    attr_columns = []
    for i in range(1, 201):
        attr_columns.append(f"attr{i}_name VARCHAR(100)")
        attr_columns.append(f"attr{i}_value TEXT")
    
    attr_columns_sql = ",\n        ".join(attr_columns)
    
    sql = f"""
    CREATE TABLE {table_name} (
        id SERIAL PRIMARY KEY,
        title_text VARCHAR(500) NOT NULL,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,
        display_order INTEGER DEFAULT 0,
        
        -- 200 custom attributes (name + value pairs)
        {attr_columns_sql},
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """
    
    db = SessionLocal()
    try:
        db.execute(text(sql))
        
        # Create indexes
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_l1_pages ON {table_name}(start_page, end_page)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_l1_order ON {table_name}(display_order)"))
        
        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def create_level2_titles_table(table_prefix: str):
    """Create level2_titles table with 150 custom attributes."""
    table_name = f"{table_prefix}_level2_titles"
    l1_table = f"{table_prefix}_level1_titles"
    
    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False
    
    # Build attribute columns (150 pairs of name/value)
    attr_columns = []
    for i in range(1, 151):
        attr_columns.append(f"attr{i}_name VARCHAR(100)")
        attr_columns.append(f"attr{i}_value TEXT")
    
    attr_columns_sql = ",\n        ".join(attr_columns)
    
    sql = f"""
    CREATE TABLE {table_name} (
        id SERIAL PRIMARY KEY,
        title_text VARCHAR(500) NOT NULL,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,
        parent_l1_id INTEGER,
        display_order INTEGER DEFAULT 0,
        
        -- 150 custom attributes (name + value pairs)
        {attr_columns_sql},
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """
    
    db = SessionLocal()
    try:
        db.execute(text(sql))
        
        # Create indexes
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_l2_pages ON {table_name}(start_page, end_page)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_l2_parent ON {table_name}(parent_l1_id)"))
        db.execute(text(f"CREATE INDEX idx_{table_prefix}_l2_order ON {table_name}(display_order)"))
        
        # Add foreign key if L1 table exists
        if table_exists(l1_table):
            db.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD CONSTRAINT fk_{table_prefix}_l2_l1 
                FOREIGN KEY (parent_l1_id) REFERENCES {l1_table}(id) ON DELETE SET NULL
            """))
        
        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def add_l3_title_id_column(table_prefix: str):
    """Add l3_title_id column to layout_detections table if not exists."""
    table_name = f"raw_{table_prefix}_layout_detections"
    
    if not table_exists(table_name):
        print(f"  ⏭️  Table {table_name} does not exist, skipping")
        return False
    
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = :table_name AND column_name = 'l3_title_id'
                )
            """),
            {"table_name": table_name}
        ).scalar()
        
        if result:
            print(f"  ⏭️  Column l3_title_id already exists in {table_name}")
            return False
        
        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN l3_title_id INTEGER"))
        db.commit()
        print(f"  ✅ Added l3_title_id column to {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error adding l3_title_id to {table_name}: {e}")
        return False
    finally:
        db.close()


def migrate_book(book: dict):
    """Run migration for a single book."""
    print(f"\n📚 Migrating book: {book['book_name']} (ID: {book['book_id']})")
    print(f"   Table prefix: {book['table_prefix']}")
    
    # Create L1 titles table
    create_level1_titles_table(book['table_prefix'])
    
    # Create L2 titles table
    create_level2_titles_table(book['table_prefix'])
    
    # Add l3_title_id column to layout_detections
    add_l3_title_id_column(book['table_prefix'])


def main():
    print("=" * 60)
    print("Migration: Add Hierarchical Title Tables (L1 and L2)")
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
