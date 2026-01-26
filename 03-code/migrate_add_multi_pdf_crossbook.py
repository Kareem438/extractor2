"""
Migration: Add Multi-PDF Upload & Cross-Book Attribute Access Support

Creates the following tables:
- pdf_uploads: Track multiple PDF files per book
- cross_book_access_log: Audit trail for cross-book writes

Modifies:
- books_metadata: Add has_multiple_pdfs, pdf_count columns
- {prefix}_level1_titles: Add external_writable_start, external_writable_end columns
- {prefix}_level2_titles: Add external_writable_start, external_writable_end columns

Run: python migrate_add_multi_pdf_crossbook.py
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


def create_pdf_uploads_table():
    """Create pdf_uploads table for tracking multiple PDFs per book."""
    table_name = "pdf_uploads"
    
    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False
    
    sql = """
    CREATE TABLE pdf_uploads (
        id                      SERIAL PRIMARY KEY,
        book_id                 INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,
        
        -- File Information
        filename                VARCHAR(255) NOT NULL,
        file_path               TEXT NOT NULL,
        file_size_bytes         BIGINT NOT NULL,
        
        -- Page Mapping
        pdf_start_page          INTEGER NOT NULL DEFAULT 1,
        book_start_page         INTEGER NOT NULL,
        total_pdf_pages         INTEGER NOT NULL,
        
        -- Calculated Range (for quick lookups)
        book_page_start         INTEGER NOT NULL,
        book_page_end           INTEGER NOT NULL,
        
        -- Status
        upload_order            INTEGER NOT NULL DEFAULT 1,
        status                  VARCHAR(50) DEFAULT 'active',
        
        -- Timestamps
        uploaded_at             TIMESTAMP DEFAULT NOW(),
        created_at              TIMESTAMP DEFAULT NOW()
    )
    """
    
    db = SessionLocal()
    try:
        db.execute(text(sql))
        
        # Create indexes
        db.execute(text("CREATE INDEX idx_pdf_uploads_book ON pdf_uploads(book_id)"))
        db.execute(text("CREATE INDEX idx_pdf_uploads_range ON pdf_uploads(book_id, book_page_start, book_page_end)"))
        db.execute(text("CREATE INDEX idx_pdf_uploads_status ON pdf_uploads(status)"))
        
        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def create_cross_book_access_log_table():
    """Create cross_book_access_log table for audit trail."""
    table_name = "cross_book_access_log"
    
    if table_exists(table_name):
        print(f"  ⏭️  Table {table_name} already exists, skipping")
        return False
    
    sql = """
    CREATE TABLE cross_book_access_log (
        id                      SERIAL PRIMARY KEY,
        
        -- Source (who wrote)
        source_book_id          INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,
        source_pipeline_rule    VARCHAR(255),
        source_pipeline_number  INTEGER,
        
        -- Target (where written)
        target_book_id          INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,
        target_level            VARCHAR(10) NOT NULL,
        target_title_id         INTEGER NOT NULL,
        target_attribute        VARCHAR(20) NOT NULL,
        
        -- Values
        old_value               TEXT,
        new_value               TEXT,
        operation               VARCHAR(20) NOT NULL,
        
        -- Timestamps
        created_at              TIMESTAMP DEFAULT NOW()
    )
    """
    
    db = SessionLocal()
    try:
        db.execute(text(sql))
        
        # Create indexes
        db.execute(text("CREATE INDEX idx_cross_book_log_source ON cross_book_access_log(source_book_id)"))
        db.execute(text("CREATE INDEX idx_cross_book_log_target ON cross_book_access_log(target_book_id, target_level, target_title_id)"))
        db.execute(text("CREATE INDEX idx_cross_book_log_time ON cross_book_access_log(created_at DESC)"))
        
        db.commit()
        print(f"  ✅ Created table {table_name}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error creating {table_name}: {e}")
        return False
    finally:
        db.close()


def add_books_metadata_columns():
    """Add multi-PDF columns to books_metadata table."""
    db = SessionLocal()
    try:
        changes = 0
        
        # Add has_multiple_pdfs column
        if not column_exists("books_metadata", "has_multiple_pdfs"):
            db.execute(text("ALTER TABLE books_metadata ADD COLUMN has_multiple_pdfs BOOLEAN DEFAULT FALSE"))
            print("  ✅ Added has_multiple_pdfs column to books_metadata")
            changes += 1
        else:
            print("  ⏭️  Column has_multiple_pdfs already exists in books_metadata")
        
        # Add pdf_count column
        if not column_exists("books_metadata", "pdf_count"):
            db.execute(text("ALTER TABLE books_metadata ADD COLUMN pdf_count INTEGER DEFAULT 1"))
            print("  ✅ Added pdf_count column to books_metadata")
            changes += 1
        else:
            print("  ⏭️  Column pdf_count already exists in books_metadata")
        
        if changes > 0:
            db.commit()
        
        return changes > 0
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error adding columns to books_metadata: {e}")
        return False
    finally:
        db.close()


def add_writable_range_columns(table_prefix: str, level: str, default_start: int, default_end: int):
    """Add external_writable_start and external_writable_end columns to title tables."""
    if level == "L1":
        table_name = f"{table_prefix}_level1_titles"
    else:
        table_name = f"{table_prefix}_level2_titles"
    
    if not table_exists(table_name):
        print(f"  ⏭️  Table {table_name} does not exist, skipping")
        return False
    
    db = SessionLocal()
    try:
        changes = 0
        
        # Add external_writable_start column
        if not column_exists(table_name, "external_writable_start"):
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN external_writable_start INTEGER DEFAULT {default_start}"))
            print(f"  ✅ Added external_writable_start column to {table_name}")
            changes += 1
        else:
            print(f"  ⏭️  Column external_writable_start already exists in {table_name}")
        
        # Add external_writable_end column
        if not column_exists(table_name, "external_writable_end"):
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN external_writable_end INTEGER DEFAULT {default_end}"))
            print(f"  ✅ Added external_writable_end column to {table_name}")
            changes += 1
        else:
            print(f"  ⏭️  Column external_writable_end already exists in {table_name}")
        
        if changes > 0:
            db.commit()
        
        return changes > 0
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error adding writable range columns to {table_name}: {e}")
        return False
    finally:
        db.close()


def migrate_existing_books_to_pdf_uploads():
    """Migrate existing books to have an entry in pdf_uploads table."""
    db = SessionLocal()
    try:
        # Get all books that don't have pdf_uploads entries
        result = db.execute(text("""
            SELECT bm.book_id, bm.book_name, bm.file_path, bm.file_size_bytes, bm.total_pages
            FROM books_metadata bm
            LEFT JOIN pdf_uploads pu ON bm.book_id = pu.book_id
            WHERE pu.id IS NULL AND bm.file_path IS NOT NULL
        """)).fetchall()
        
        if not result:
            print("  ⏭️  All existing books already have pdf_uploads entries")
            return False
        
        for row in result:
            book_id, book_name, file_path, file_size, total_pages = row
            
            # Extract filename from path
            filename = os.path.basename(file_path) if file_path else f"book_{book_id}.pdf"
            
            db.execute(text("""
                INSERT INTO pdf_uploads (
                    book_id, filename, file_path, file_size_bytes,
                    pdf_start_page, book_start_page, total_pdf_pages,
                    book_page_start, book_page_end, upload_order, status
                ) VALUES (
                    :book_id, :filename, :file_path, :file_size,
                    1, 1, :total_pages,
                    1, :total_pages, 1, 'active'
                )
            """), {
                "book_id": book_id,
                "filename": filename,
                "file_path": file_path or "",
                "file_size": file_size or 0,
                "total_pages": total_pages or 1
            })
            print(f"  ✅ Migrated book '{book_name}' (ID: {book_id}) to pdf_uploads")
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error migrating existing books: {e}")
        return False
    finally:
        db.close()


def migrate_book(book: dict):
    """Run migration for a single book's title tables."""
    print(f"\n📚 Migrating book: {book['book_name']} (ID: {book['book_id']})")
    print(f"   Table prefix: {book['table_prefix']}")
    
    # Add writable range columns to L1 titles (default: 151-200)
    add_writable_range_columns(book['table_prefix'], "L1", 151, 200)
    
    # Add writable range columns to L2 titles (default: 101-150)
    add_writable_range_columns(book['table_prefix'], "L2", 101, 150)


def main():
    print("=" * 60)
    print("Migration: Multi-PDF Upload & Cross-Book Attribute Access")
    print("=" * 60)
    
    # Step 1: Create shared tables
    print("\n📋 Step 1: Creating shared tables...")
    create_pdf_uploads_table()
    create_cross_book_access_log_table()
    
    # Step 2: Add columns to books_metadata
    print("\n📋 Step 2: Adding columns to books_metadata...")
    add_books_metadata_columns()
    
    # Step 3: Migrate existing books to pdf_uploads
    print("\n📋 Step 3: Migrating existing books to pdf_uploads...")
    migrate_existing_books_to_pdf_uploads()
    
    # Step 4: Add writable range columns to each book's title tables
    print("\n📋 Step 4: Adding writable range columns to title tables...")
    books = get_all_books()
    
    if not books:
        print("\n⚠️  No books found in database")
    else:
        print(f"\nFound {len(books)} book(s) to migrate")
        for book in books:
            migrate_book(book)
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
