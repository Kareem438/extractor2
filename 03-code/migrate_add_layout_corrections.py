"""
Migration: Add layout_corrections table for YOLO Fine-Tuning (Requirement 7C)

This migration adds:
1. layout_corrections table for storing user corrections to YOLO detections
2. Indexes for efficient queries

Run with: python migrate_add_layout_corrections.py
"""

from sqlalchemy import text
from src.database.connection import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_book_prefixes():
    """Get all book table prefixes from books_metadata."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT book_id, table_prefix, book_name 
            FROM books_metadata 
            ORDER BY book_id
        """))
        return [(row[0], row[1], row[2]) for row in result.fetchall()]


def create_layout_corrections_table(table_prefix: str):
    """Create layout_corrections table for storing user corrections."""
    table_name = f"{table_prefix}_layout_corrections"
    pages_table = f"{table_prefix}_pages"
    
    # Check if table already exists
    with engine.connect() as conn:
        check_sql = text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """)
        exists = conn.execute(check_sql).scalar()
        
        if exists:
            logger.info(f"Table {table_name} already exists, skipping")
            return
    
    sql = text(f"""
    CREATE TABLE {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INT NOT NULL,
        
        -- Original YOLO detection
        original_x INT,
        original_y INT,
        original_width INT,
        original_height INT,
        original_class VARCHAR(50),
        original_confidence FLOAT,
        
        -- User correction
        corrected_x INT,
        corrected_y INT,
        corrected_width INT,
        corrected_height INT,
        corrected_class VARCHAR(50),
        
        -- Correction type: 'adjusted', 'deleted', 'added'
        correction_type VARCHAR(20) NOT NULL,
        
        -- Metadata
        model_version INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        
        -- Foreign key to pages table
        CONSTRAINT fk_{table_prefix}_corrections_page 
            FOREIGN KEY (page_number) 
            REFERENCES {pages_table}(page_number)
            ON DELETE CASCADE
    )
    """)
    
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
        logger.info(f"Created table {table_name}")


def create_indexes(table_prefix: str):
    """Create indexes for efficient queries on layout_corrections table."""
    table_name = f"{table_prefix}_layout_corrections"
    
    indexes = [
        f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_lc_page ON {table_name}(page_number)",
        f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_lc_type ON {table_name}(correction_type)",
        f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_lc_model ON {table_name}(model_version)",
        f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_lc_class ON {table_name}(corrected_class)"
    ]
    
    with engine.connect() as conn:
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")
        logger.info(f"Created indexes for {table_name}")


def add_correction_columns_to_detections(table_prefix: str):
    """
    Add correction tracking columns to existing layout_detections table.
    These columns store original values before user corrections.
    """
    table_name = f"raw_{table_prefix}_layout_detections"
    
    columns = [
        ("original_x", "INT"),
        ("original_y", "INT"),
        ("original_width", "INT"),
        ("original_height", "INT"),
        ("original_class", "VARCHAR(50)"),
        ("was_corrected", "BOOLEAN DEFAULT FALSE"),
        ("correction_type", "VARCHAR(30)"),  # 'manual_adjustment', 'manually_added', 'deleted'
        ("correction_timestamp", "TIMESTAMP")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns:
            try:
                sql = text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                conn.execute(sql)
                conn.commit()
                logger.info(f"Added column {col_name} to {table_name}")
            except Exception as e:
                logger.warning(f"Column {col_name} may already exist: {e}")


def run_migration():
    """Run the migration for all books."""
    logger.info("=" * 60)
    logger.info("Starting Layout Corrections Migration (Requirement 7C)")
    logger.info("=" * 60)
    
    books = get_all_book_prefixes()
    
    if not books:
        logger.warning("No books found in database")
        return
    
    logger.info(f"Found {len(books)} books to migrate")
    
    for book_id, table_prefix, book_name in books:
        logger.info(f"\nMigrating book {book_id}: {book_name} (prefix: {table_prefix})")
        
        try:
            # Add correction columns to existing detections table
            add_correction_columns_to_detections(table_prefix)
            
            # Create separate corrections table (for historical tracking)
            create_layout_corrections_table(table_prefix)
            
            # Create indexes
            create_indexes(table_prefix)
            
            logger.info(f"✓ Book {book_id} migration complete")
            
        except Exception as e:
            logger.error(f"✗ Error migrating book {book_id}: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_migration()
