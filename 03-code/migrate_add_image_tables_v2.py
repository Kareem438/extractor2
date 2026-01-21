"""
Migration script to add raw_paragraph_images and raw_diagram_images tables
to all existing books in the database.

Run this script once after deploying the new table schema.
"""

from sqlalchemy import text
from src.database.connection import engine
from src.database.table_creator import (
    create_raw_paragraph_images_table,
    create_raw_diagram_images_table
)


def get_all_books():
    """Get all books from the master books_metadata table"""
    sql = text("SELECT book_id, table_prefix, book_name FROM books_metadata ORDER BY book_id")

    with engine.connect() as conn:
        result = conn.execute(sql)
        books = result.fetchall()

    return books


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    sql = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        )
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"table_name": table_name})
        return result.scalar()


def migrate_book(book_id: int, table_prefix: str, book_name: str):
    """Add the two new image tables to a book"""
    print(f"  📚 Book {book_id}: {book_name}")
    print(f"     Table prefix: {table_prefix}")

    paragraph_table = f"raw_{table_prefix}_paragraph_images"
    diagram_table = f"raw_{table_prefix}_diagram_images"

    created_count = 0
    skipped_count = 0

    try:
        # Check and create paragraph images table
        if table_exists(paragraph_table):
            print(f"     ⏭️  {paragraph_table} already exists")
            skipped_count += 1
        else:
            create_raw_paragraph_images_table(table_prefix)
            print(f"     ✅ Created {paragraph_table}")
            created_count += 1

        # Check and create diagram images table
        if table_exists(diagram_table):
            print(f"     ⏭️  {diagram_table} already exists")
            skipped_count += 1
        else:
            create_raw_diagram_images_table(table_prefix)
            print(f"     ✅ Created {diagram_table}")
            created_count += 1

        return {"created": created_count, "skipped": skipped_count, "error": False}
    except Exception as e:
        print(f"     ❌ Error: {e}")
        return {"created": created_count, "skipped": skipped_count, "error": True}


def main():
    """Run migration for all books"""
    print("=" * 70)
    print("Migration: Add paragraph_images and diagram_images tables")
    print("=" * 70)
    print()

    # Get all books
    try:
        books = get_all_books()
    except Exception as e:
        print(f"❌ Failed to query books_metadata table: {e}")
        print()
        print("This might mean the master books table doesn't exist yet,")
        print("or you need to check your database connection.")
        return

    if not books:
        print("ℹ️  No books found in database. Nothing to migrate.")
        return

    print(f"Found {len(books)} book(s) in database")
    print()

    # Migrate each book
    total_created = 0
    total_skipped = 0
    total_errors = 0

    for book_id, table_prefix, book_name in books:
        result = migrate_book(book_id, table_prefix, book_name)
        total_created += result["created"]
        total_skipped += result["skipped"]
        if result["error"]:
            total_errors += 1
        print()

    # Summary
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"📊 Books processed: {len(books)}")
    print(f"✅ Tables created: {total_created}")
    print(f"⏭️  Tables skipped (already exist): {total_skipped}")
    print(f"❌ Books with errors: {total_errors}")
    print()

    if total_errors == 0:
        print("🎉 Migration completed successfully!")
    else:
        print(f"⚠️  {total_errors} book(s) had errors. Check output above.")


if __name__ == "__main__":
    main()
