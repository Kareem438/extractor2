"""
Cleanup Orphaned Book Tables

This script finds and drops tables for books that no longer exist in books_metadata.
Run this after accidental deletions that only removed metadata but not tables.
"""

import psycopg2
from psycopg2 import sql

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'knowledge_extraction_2',
    'user': 'postgres',
    'password': 'postgres'
}


def get_existing_book_prefixes(cursor):
    """Get table prefixes for books that exist in books_metadata."""
    cursor.execute("SELECT table_prefix FROM books_metadata")
    return {row[0] for row in cursor.fetchall()}


def get_all_book_tables(cursor):
    """Get all book-related tables from the database."""
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (tablename LIKE 'book%' OR tablename LIKE 'raw_book%')
        AND tablename != 'books_metadata'
        ORDER BY tablename
    """)
    return [row[0] for row in cursor.fetchall()]


def extract_prefix_from_table(table_name):
    """Extract the book prefix from a table name."""
    # Tables follow patterns like:
    # book1_name_type -> prefix is book1_name
    # raw_book1_name_type -> prefix is book1_name
    
    # Remove 'raw_' prefix if present
    if table_name.startswith('raw_'):
        table_name = table_name[4:]
    
    # Known suffixes to strip
    suffixes = [
        '_attribute_keys', '_hierarchy', '_images', '_knowledge_units',
        '_level1_titles', '_level2_titles', '_pages', '_pipeline_config',
        '_processing_state', '_settings', '_step_progress', '_task_queue',
        '_diagram_images', '_paragraph_images', '_layout_detections'
    ]
    
    for suffix in suffixes:
        if table_name.endswith(suffix):
            return table_name[:-len(suffix)]
    
    return None


def find_orphaned_tables(cursor):
    """Find tables that belong to books no longer in books_metadata."""
    existing_prefixes = get_existing_book_prefixes(cursor)
    all_tables = get_all_book_tables(cursor)
    
    orphaned = []
    for table in all_tables:
        prefix = extract_prefix_from_table(table)
        if prefix and prefix not in existing_prefixes:
            orphaned.append(table)
    
    return orphaned


def drop_tables(cursor, tables, dry_run=True):
    """Drop the specified tables."""
    dropped = []
    for table in tables:
        if dry_run:
            print(f"  [DRY RUN] Would drop: {table}")
        else:
            try:
                cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                    sql.Identifier(table)
                ))
                dropped.append(table)
                print(f"  ✅ Dropped: {table}")
            except Exception as e:
                print(f"  ❌ Failed to drop {table}: {e}")
    return dropped


def main():
    print("=" * 60)
    print("Orphaned Book Tables Cleanup")
    print("=" * 60)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Find orphaned tables
        print("\n📋 Finding orphaned tables...")
        orphaned = find_orphaned_tables(cursor)
        
        if not orphaned:
            print("✅ No orphaned tables found!")
            return
        
        print(f"\n⚠️  Found {len(orphaned)} orphaned tables:")
        for table in orphaned:
            print(f"  - {table}")
        
        # Ask for confirmation
        print("\n" + "=" * 60)
        response = input("Do you want to DROP these tables? (yes/no): ").strip().lower()
        
        if response == 'yes':
            print("\n🗑️  Dropping orphaned tables...")
            dropped = drop_tables(cursor, orphaned, dry_run=False)
            conn.commit()
            print(f"\n✅ Successfully dropped {len(dropped)} tables")
        else:
            print("\n❌ Aborted. No tables were dropped.")
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
