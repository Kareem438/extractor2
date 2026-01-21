#!/usr/bin/env python3
"""
Migration Script: Add Diagram Analysis Fields

Adds new columns to raw_*_diagram_images tables for AI analysis:
- extracted_text: OCR text from diagram
- diagram_type: Type classification (flowchart, hierarchy, etc.)
- structured_json: Structured analysis data
- ai_model: Model used for analysis
- ai_confidence: Confidence score
- analyzed_at: Timestamp of analysis
- linked_knowledge_unit_id: User-controlled link to related KU
- level: Level classification (like paragraphs)

Run with: PYTHONPATH=/mnt/h/12-extractor/03-code python3 migrate_add_diagram_analysis_fields.py
"""

from sqlalchemy import text
from src.database.connection import engine


def get_all_books():
    """Get all books from the master books_metadata table"""
    sql = text("SELECT book_id, table_prefix, book_name FROM books_metadata ORDER BY book_id")

    with engine.connect() as conn:
        result = conn.execute(sql)
        books = [{"book_id": row[0], "table_prefix": row[1], "book_name": row[2]} for row in result]
    return books


def add_diagram_analysis_columns(table_prefix: str):
    """Add new columns to diagram_images table for a specific book"""
    table_name = f"raw_{table_prefix}_diagram_images"

    columns_to_add = [
        ("extracted_text", "TEXT"),
        ("diagram_type", "VARCHAR(100)"),
        ("structured_json", "JSONB"),
        ("ai_model", "VARCHAR(100)"),
        ("ai_confidence", "NUMERIC(5,2)"),
        ("analyzed_at", "TIMESTAMP"),
        ("linked_knowledge_unit_id", "INTEGER"),
        ("level", "VARCHAR(50)")
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists
                check_sql = text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND column_name = :col_name
                """)
                result = conn.execute(check_sql, {"table_name": table_name, "col_name": col_name})

                if result.fetchone() is None:
                    # Column doesn't exist, add it
                    alter_sql = text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    conn.execute(alter_sql)
                    print(f"  ✅ Added column: {col_name} ({col_type})")
                else:
                    print(f"  ⏭️  Column already exists: {col_name}")

            except Exception as e:
                print(f"  ❌ Error adding column {col_name}: {e}")

        conn.commit()


def main():
    print("=" * 70)
    print("Migration: Add Diagram Analysis Fields")
    print("=" * 70)
    print()

    try:
        books = get_all_books()
    except Exception as e:
        print(f"❌ Failed to query books_metadata table: {e}")
        print()
        print("This might mean the master books table doesn't exist yet,")
        print("or you need to check your database connection.")
        return

    if not books:
        print("ℹ️  No books found in the database. Nothing to migrate.")
        return

    print(f"Found {len(books)} book(s) to migrate:")
    for book in books:
        print(f"  - Book {book['book_id']}: {book['book_name']}")
    print()

    for book in books:
        table_prefix = book['table_prefix']
        print(f"📚 Migrating book {book['book_id']}: {book['book_name']}")
        print(f"   Table: raw_{table_prefix}_diagram_images")

        try:
            add_diagram_analysis_columns(table_prefix)
            print(f"   ✅ Migration complete for book {book['book_id']}")
        except Exception as e:
            print(f"   ❌ Migration failed for book {book['book_id']}: {e}")

        print()

    print("=" * 70)
    print("Migration Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
