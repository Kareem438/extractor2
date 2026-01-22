"""
Migration: Add KU Creation Attribute Names

This migration updates the attribute_keys table for all books to add
the new attribute names used by the KU creation service:

- attr9: layout_class_type
- attr10: parent_paragraph_text
- attr11: answer_text
- attr12: raw_entity_reference

These attributes are used by the Knowledge Unit Creation workflow.
"""

from sqlalchemy import text
from src.database.connection import engine


def get_all_book_prefixes():
    """Get all table prefixes from books_metadata."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_prefix FROM books_metadata"))
        return [row[0] for row in result.fetchall()]


def update_attribute_keys(table_prefix: str):
    """Update attribute key names for a book."""
    table_name = f"{table_prefix}_attribute_keys"
    
    # New attribute names
    updates = {
        9: "layout_class_type",
        10: "parent_paragraph_text",
        11: "answer_text",
        12: "raw_entity_reference"
    }
    
    with engine.connect() as conn:
        for attr_num, key_name in updates.items():
            # Check if attribute exists
            check_sql = text(f"""
                SELECT id FROM {table_name} WHERE attr_number = :attr_num
            """)
            result = conn.execute(check_sql, {"attr_num": attr_num})
            
            if result.fetchone():
                # Update existing
                update_sql = text(f"""
                    UPDATE {table_name}
                    SET key_name = :key_name, updated_at = NOW()
                    WHERE attr_number = :attr_num
                """)
                conn.execute(update_sql, {"attr_num": attr_num, "key_name": key_name})
                print(f"  Updated attr{attr_num} = '{key_name}'")
            else:
                # Insert new
                insert_sql = text(f"""
                    INSERT INTO {table_name} (attr_number, key_name, is_system_reserved, is_editable)
                    VALUES (:attr_num, :key_name, false, true)
                """)
                conn.execute(insert_sql, {"attr_num": attr_num, "key_name": key_name})
                print(f"  Inserted attr{attr_num} = '{key_name}'")
        
        conn.commit()


def run_migration():
    """Run the migration for all books."""
    print("=" * 60)
    print("Migration: Add KU Creation Attribute Names")
    print("=" * 60)
    
    prefixes = get_all_book_prefixes()
    print(f"\nFound {len(prefixes)} books to update")
    
    for prefix in prefixes:
        print(f"\nUpdating {prefix}_attribute_keys...")
        try:
            update_attribute_keys(prefix)
            print(f"  ✅ Success")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
