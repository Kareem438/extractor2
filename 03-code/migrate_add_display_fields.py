"""
Migration script to add display_order and is_enabled fields
to paragraph_images and diagram_images tables for all existing books.

Run this script once after deploying the new schema.
"""

from sqlalchemy import text
from src.database.connection import engine


def get_all_books():
    """Get all books from the master books_metadata table"""
    sql = text("SELECT book_id, table_prefix, book_name FROM books_metadata ORDER BY book_id")

    with engine.connect() as conn:
        result = conn.execute(sql)
        books = result.fetchall()

    return books


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    sql = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        )
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"table_name": table_name, "column_name": column_name})
        return result.scalar()


def migrate_table(table_name: str):
    """Add display_order and is_enabled columns to a table"""
    added_columns = []
    skipped_columns = []

    try:
        # Check and add display_order column
        if column_exists(table_name, "display_order"):
            print(f"     ⏭️  Column 'display_order' already exists")
            skipped_columns.append("display_order")
        else:
            # Add display_order column with default value 0
            add_order_sql = text(f"""
                ALTER TABLE {table_name}
                ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0
            """)
            with engine.connect() as conn:
                conn.execute(add_order_sql)
                conn.commit()

            # Set display_order based on creation order (id)
            # This preserves the current order
            update_order_sql = text(f"""
                UPDATE {table_name}
                SET display_order = id
            """)
            with engine.connect() as conn:
                conn.execute(update_order_sql)
                conn.commit()

            # Create index
            create_index_sql = text(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name.replace('raw_', '').replace('_images', '')}_order
                ON {table_name}(display_order)
            """)
            with engine.connect() as conn:
                conn.execute(create_index_sql)
                conn.commit()

            print(f"     ✅ Added 'display_order' column")
            added_columns.append("display_order")

        # Check and add is_enabled column
        if column_exists(table_name, "is_enabled"):
            print(f"     ⏭️  Column 'is_enabled' already exists")
            skipped_columns.append("is_enabled")
        else:
            # Add is_enabled column with default TRUE
            add_enabled_sql = text(f"""
                ALTER TABLE {table_name}
                ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT TRUE
            """)
            with engine.connect() as conn:
                conn.execute(add_enabled_sql)
                conn.commit()

            # Create index
            create_index_sql = text(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name.replace('raw_', '').replace('_images', '')}_enabled
                ON {table_name}(is_enabled)
            """)
            with engine.connect() as conn:
                conn.execute(create_index_sql)
                conn.commit()

            print(f"     ✅ Added 'is_enabled' column")
            added_columns.append("is_enabled")

        return {"added": added_columns, "skipped": skipped_columns, "error": False}

    except Exception as e:
        print(f"     ❌ Error: {e}")
        return {"added": added_columns, "skipped": skipped_columns, "error": True}


def migrate_book(book_id: int, table_prefix: str, book_name: str):
    """Add display fields to both paragraph and diagram tables for a book"""
    print(f"  📚 Book {book_id}: {book_name}")
    print(f"     Table prefix: {table_prefix}")

    total_added = 0
    total_skipped = 0
    errors = False

    # Migrate paragraph_images table
    paragraph_table = f"raw_{table_prefix}_paragraph_images"
    print(f"     📝 Migrating {paragraph_table}...")
    result = migrate_table(paragraph_table)
    total_added += len(result["added"])
    total_skipped += len(result["skipped"])
    if result["error"]:
        errors = True

    # Migrate diagram_images table
    diagram_table = f"raw_{table_prefix}_diagram_images"
    print(f"     📊 Migrating {diagram_table}...")
    result = migrate_table(diagram_table)
    total_added += len(result["added"])
    total_skipped += len(result["skipped"])
    if result["error"]:
        errors = True

    return {"added": total_added, "skipped": total_skipped, "error": errors}


def main():
    """Run migration for all books"""
    print("=" * 70)
    print("Migration: Add display_order and is_enabled fields")
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
    total_added = 0
    total_skipped = 0
    total_errors = 0

    for book_id, table_prefix, book_name in books:
        result = migrate_book(book_id, table_prefix, book_name)
        total_added += result["added"]
        total_skipped += result["skipped"]
        if result["error"]:
            total_errors += 1
        print()

    # Summary
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"📊 Books processed: {len(books)}")
    print(f"✅ Columns added: {total_added}")
    print(f"⏭️  Columns skipped (already exist): {total_skipped}")
    print(f"❌ Books with errors: {total_errors}")
    print()

    if total_errors == 0:
        print("🎉 Migration completed successfully!")
    else:
        print(f"⚠️  {total_errors} book(s) had errors. Check output above.")


if __name__ == "__main__":
    main()
