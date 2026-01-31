"""
Migration: Add yolo_model_path column to books_metadata

This migration adds the yolo_model_path column to track per-book YOLO models.

Requirement 8: Per-Book YOLO Model Fine-Tuning
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.connection import engine

def run_migration():
    """Add yolo_model_path column to books_metadata table."""
    
    print("=" * 60)
    print("Migration: Add yolo_model_path to books_metadata")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if column already exists
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'books_metadata' 
            AND column_name = 'yolo_model_path'
        """)
        result = conn.execute(check_sql).fetchone()
        
        if result:
            print("✓ Column 'yolo_model_path' already exists")
            return True
        
        # Add the column
        print("Adding 'yolo_model_path' column...")
        alter_sql = text("""
            ALTER TABLE books_metadata 
            ADD COLUMN IF NOT EXISTS yolo_model_path TEXT DEFAULT NULL
        """)
        conn.execute(alter_sql)
        conn.commit()
        print("✓ Column 'yolo_model_path' added successfully")
        
        # Verify
        verify_sql = text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'books_metadata' 
            AND column_name = 'yolo_model_path'
        """)
        result = conn.execute(verify_sql).fetchone()
        if result:
            print(f"  - Column: {result[0]}")
            print(f"  - Type: {result[1]}")
            print(f"  - Default: {result[2]}")
        
        print("\n✓ Migration completed successfully!")
        return True


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
