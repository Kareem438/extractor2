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
from src.utils.sanitization import generate_table_prefix


def get_all_books():
    """Get all books from the master books table"""
    sql = text("SELECT book_id, sanitized_name FROM books ORDER BY book_id")

    with engine.connect() as conn:
        result = conn.execute(sql)
        books = result.fetchall()

    return books


def migrate_book(book_id: int, sanitized_name: str):
    """Add the two new image tables to a book"""
    table_prefix = generate_table_prefix(book_id, sanitized_name)

    print(f"  📚 Book {book_id}: {sanitized_name}")
    print(f"     Table prefix: {table_prefix}")

    try:
        # Create paragraph images table
        create_raw_paragraph_images_table(table_prefix)
        print(f"     ✅ Created raw_{table_prefix}_paragraph_images")

        # Create diagram images table
        create_raw_diagram_images_table(table_prefix)
        print(f"     ✅ Created raw_{table_prefix}_diagram_images")

        return True
    except Exception as e:
        print(f"     ❌ Error: {e}")
        return False


def main():
    """Run migration for all books"""
    print("=" * 70)
    print("Migration: Add paragraph_images and diagram_images tables")
    print("=" * 70)
    print()

    # Get all books
    books = get_all_books()

    if not books:
        print("ℹ️  No books found in database. Nothing to migrate.")
        return

    print(f"Found {len(books)} book(s) in database")
    print()

    # Migrate each book
    success_count = 0
    fail_count = 0

    for book_id, sanitized_name in books:
        if migrate_book(book_id, sanitized_name):
            success_count += 1
        else:
            fail_count += 1
        print()

    # Summary
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {len(books)}")
    print()

    if fail_count == 0:
        print("🎉 Migration completed successfully!")
    else:
        print("⚠️  Some migrations failed. Check errors above.")


if __name__ == "__main__":
    main()
