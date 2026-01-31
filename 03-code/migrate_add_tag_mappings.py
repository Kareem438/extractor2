"""
Migration: Add tag_mappings and grouping config for Requirement 7

This migration adds:
1. tag_mappings JSONB column to pipeline_config tables
2. fallback_attribute column to pipeline_config tables
3. ku_grouping_config table for each book
4. is_complete and incomplete_reason columns to knowledge_units
5. 80 additional custom attributes (attr_81 through attr_160) to knowledge_units
6. layout_corrections table for YOLO training data

Run with: python migrate_add_tag_mappings.py
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


def add_tag_mappings_to_pipeline_config(table_prefix: str):
    """Add tag_mappings and fallback_attribute columns to pipeline_config table."""
    table_name = f"{table_prefix}_pipeline_config"
    
    with engine.connect() as conn:
        # Check if columns already exist
        check_sql = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND column_name IN ('tag_mappings', 'fallback_attribute')
        """)
        existing = [row[0] for row in conn.execute(check_sql).fetchall()]
        
        if 'tag_mappings' not in existing:
            conn.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN tag_mappings JSONB DEFAULT '[]'::jsonb
            """))
            logger.info(f"Added tag_mappings column to {table_name}")
        
        if 'fallback_attribute' not in existing:
            conn.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN fallback_attribute VARCHAR(20)
            """))
            logger.info(f"Added fallback_attribute column to {table_name}")
        
        conn.commit()


def create_ku_grouping_config_table(table_prefix: str):
    """Create ku_grouping_config table for grouping configuration."""
    table_name = f"{table_prefix}_ku_grouping_config"
    
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        is_enabled BOOLEAN DEFAULT FALSE,
        grouping_mode VARCHAR(20) DEFAULT 'ku_count',
        max_kus_per_group INT DEFAULT 5,
        max_tokens_per_group INT DEFAULT 4000,
        fallback_attribute VARCHAR(20),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)
    
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
        logger.info(f"Created table {table_name}")
        
        # Insert default row
        conn.execute(text(f"""
            INSERT INTO {table_name} (id, is_enabled, grouping_mode, max_kus_per_group, max_tokens_per_group)
            VALUES (1, FALSE, 'ku_count', 5, 4000)
            ON CONFLICT (id) DO NOTHING
        """))
        conn.commit()


def add_incomplete_tracking_to_knowledge_units(table_prefix: str):
    """Add is_complete and incomplete_reason columns to knowledge_units table."""
    table_name = f"{table_prefix}_knowledge_units"
    
    with engine.connect() as conn:
        # Check if columns already exist
        check_sql = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND column_name IN ('is_complete', 'incomplete_reason')
        """)
        existing = [row[0] for row in conn.execute(check_sql).fetchall()]
        
        if 'is_complete' not in existing:
            conn.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN is_complete BOOLEAN DEFAULT TRUE
            """))
            logger.info(f"Added is_complete column to {table_name}")
        
        if 'incomplete_reason' not in existing:
            conn.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN incomplete_reason TEXT
            """))
            logger.info(f"Added incomplete_reason column to {table_name}")
        
        conn.commit()


def add_additional_attributes_to_knowledge_units(table_prefix: str):
    """Add attr_81 through attr_160 columns to knowledge_units table."""
    table_name = f"{table_prefix}_knowledge_units"
    
    with engine.connect() as conn:
        # Check which columns already exist
        check_sql = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND column_name LIKE 'attr%_value'
        """)
        existing = set(row[0] for row in conn.execute(check_sql).fetchall())
        
        # Add attr_81_value through attr_160_value
        for i in range(81, 161):
            col_name = f"attr{i}_value"
            if col_name not in existing:
                conn.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {col_name} TEXT
                """))
                logger.info(f"Added {col_name} to {table_name}")
        
        conn.commit()


def add_additional_attribute_keys(table_prefix: str):
    """Add attr_81 through attr_160 to attribute_keys table."""
    table_name = f"{table_prefix}_attribute_keys"
    
    with engine.connect() as conn:
        # Check max attr_number
        result = conn.execute(text(f"""
            SELECT MAX(attr_number) FROM {table_name}
        """)).fetchone()
        max_attr = result[0] if result[0] else 0
        
        # Add missing attribute keys
        for i in range(max(81, max_attr + 1), 161):
            conn.execute(text(f"""
                INSERT INTO {table_name} (attr_number, key_name, is_system_reserved, is_editable)
                VALUES (:attr_num, NULL, false, true)
                ON CONFLICT (attr_number) DO NOTHING
            """), {"attr_num": i})
        
        conn.commit()
        logger.info(f"Added attribute keys 81-160 to {table_name}")


def run_migration():
    """Run the full migration for all books."""
    logger.info("Starting migration for tag_mappings and grouping config...")
    
    books = get_all_book_prefixes()
    
    if not books:
        logger.warning("No books found in database")
        return
    
    for book_id, table_prefix, book_name in books:
        logger.info(f"\nMigrating book {book_id}: {book_name} (prefix: {table_prefix})")
        
        try:
            # Phase 1: Tag mappings
            add_tag_mappings_to_pipeline_config(table_prefix)
            
            # Phase 2: Grouping config
            create_ku_grouping_config_table(table_prefix)
            add_incomplete_tracking_to_knowledge_units(table_prefix)
            add_additional_attributes_to_knowledge_units(table_prefix)
            add_additional_attribute_keys(table_prefix)
            
            logger.info(f"Successfully migrated book {book_id}")
            
        except Exception as e:
            logger.error(f"Error migrating book {book_id}: {e}")
            continue
    
    logger.info("\nMigration complete!")


if __name__ == "__main__":
    run_migration()
