"""
Migration Script: Add Layout Detection Tables for Automatic Boundaries

This script creates the database tables required for the DocLayout-YOLO
automatic boundary detection feature:

GLOBAL TABLES:
1. layout_models - Store model metadata and versions per book
2. layout_flagged_pages - Pages needing manual review
3. layout_training_history - Training run history

PER-BOOK TABLES (created via table_creator.py update):
4. raw_{prefix}_layout_detections - Detection results + corrections

The migration also:
- Adds layout_detection_config JSONB column to books_metadata
- Updates table_creator.py to create layout_detections table per book

Run this migration from the 03-code directory:
    cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe migrate_add_layout_detection.py

Author: Claude Code
Date: 2026-01-14
Phase: 1.1 of Automatic Boundaries Implementation
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/knowledge_extraction"
engine = create_engine(DATABASE_URL)


def check_column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        return result.fetchone()[0] > 0


def check_table_exists(table_name):
    """Check if a table exists."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = :table_name
        """), {"table_name": table_name})
        return result.fetchone()[0] > 0


def add_layout_detection_config_column():
    """Add layout_detection_config JSONB column to books_metadata table."""
    table_name = "books_metadata"
    column_name = "layout_detection_config"

    if check_column_exists(table_name, column_name):
        logger.info(f"Column {column_name} already exists in {table_name}, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSONB"
            conn.execute(text(sql))
            conn.commit()
            logger.info(f"Added column {column_name} to {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error adding column {column_name} to {table_name}: {e}")
        return False


def create_layout_models_table():
    """Create layout_models table for storing model metadata and versions."""
    table_name = "layout_models"

    if check_table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = text("""
            CREATE TABLE layout_models (
                id SERIAL PRIMARY KEY,
                book_id INTEGER REFERENCES books_metadata(book_id) ON DELETE CASCADE,
                model_version INTEGER NOT NULL,
                model_path VARCHAR(500) NOT NULL,
                model_filename VARCHAR(200) NOT NULL,

                -- Inheritance
                parent_model_id INTEGER REFERENCES layout_models(id),
                base_model VARCHAR(100) DEFAULT 'doclayout_yolo_docsynth300k',

                -- Training metadata
                training_images INTEGER DEFAULT 0,
                training_corrections INTEGER DEFAULT 0,
                training_epochs INTEGER,
                training_duration_seconds INTEGER,

                -- Metrics
                map_score FLOAT,
                map_50_score FLOAT,
                map_50_95_score FLOAT,
                per_class_accuracy JSONB,
                improvement_percent FLOAT,

                -- Enabled classes for this model
                enabled_classes JSONB,

                -- Status
                is_active BOOLEAN DEFAULT FALSE,
                training_status VARCHAR(50) DEFAULT 'idle',
                training_progress FLOAT DEFAULT 0,
                training_error TEXT,

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                trained_at TIMESTAMP,
                activated_at TIMESTAMP,

                UNIQUE(book_id, model_version)
            )
            """)
            conn.execute(sql)
            conn.commit()

            # Create indexes
            indexes = [
                "CREATE INDEX idx_layout_models_book ON layout_models(book_id)",
                "CREATE INDEX idx_layout_models_active ON layout_models(book_id) WHERE is_active = true",
                "CREATE INDEX idx_layout_models_parent ON layout_models(parent_model_id)"
            ]
            for idx_sql in indexes:
                conn.execute(text(idx_sql))
            conn.commit()

            logger.info(f"Created table {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def create_layout_flagged_pages_table():
    """Create layout_flagged_pages table for pages needing manual review."""
    table_name = "layout_flagged_pages"

    if check_table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = text("""
            CREATE TABLE layout_flagged_pages (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,

                -- Flag information
                flag_reason VARCHAR(100) NOT NULL,
                flag_details JSONB,

                -- Resolution
                resolved BOOLEAN DEFAULT FALSE,
                resolved_by VARCHAR(100),
                resolution_notes TEXT,

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                resolved_at TIMESTAMP,

                UNIQUE(book_id, page_number, flag_reason)
            )
            """)
            conn.execute(sql)
            conn.commit()

            # Create indexes
            indexes = [
                "CREATE INDEX idx_layout_flagged_book ON layout_flagged_pages(book_id)",
                "CREATE INDEX idx_layout_flagged_unresolved ON layout_flagged_pages(book_id) WHERE resolved = false"
            ]
            for idx_sql in indexes:
                conn.execute(text(idx_sql))
            conn.commit()

            logger.info(f"Created table {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def create_layout_training_history_table():
    """Create layout_training_history table for training run history."""
    table_name = "layout_training_history"

    if check_table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = text("""
            CREATE TABLE layout_training_history (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,
                model_id INTEGER REFERENCES layout_models(id),

                -- Training parameters
                batch_size INTEGER,
                epochs_requested INTEGER,
                epochs_completed INTEGER,
                learning_rate FLOAT,
                image_size INTEGER,

                -- Training data stats
                training_images INTEGER,
                validation_images INTEGER,
                corrections_used INTEGER,

                -- Results
                final_loss FLOAT,
                best_map_score FLOAT,
                training_log JSONB,
                loss_curve JSONB,

                -- Status
                status VARCHAR(50) DEFAULT 'pending',
                error_message TEXT,

                -- Timing
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER,

                created_at TIMESTAMP DEFAULT NOW()
            )
            """)
            conn.execute(sql)
            conn.commit()

            # Create index
            conn.execute(text(
                "CREATE INDEX idx_layout_training_history_book ON layout_training_history(book_id)"
            ))
            conn.commit()

            logger.info(f"Created table {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def create_layout_reference_patterns_table():
    """Create layout_reference_patterns table for custom reference patterns per book."""
    table_name = "layout_reference_patterns"

    if check_table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = text("""
            CREATE TABLE layout_reference_patterns (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,

                -- Pattern definition
                pattern_regex VARCHAR(500) NOT NULL,
                pattern_type VARCHAR(50) NOT NULL,
                pattern_label VARCHAR(200),

                -- Flags
                is_active BOOLEAN DEFAULT TRUE,
                is_standard BOOLEAN DEFAULT FALSE,

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """)
            conn.execute(sql)
            conn.commit()

            # Create index
            conn.execute(text(
                "CREATE INDEX idx_layout_reference_patterns_book ON layout_reference_patterns(book_id)"
            ))
            conn.commit()

            logger.info(f"Created table {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def create_layout_reference_links_table():
    """Create layout_reference_links table for diagram-paragraph links."""
    table_name = "layout_reference_links"

    if check_table_exists(table_name):
        logger.info(f"Table {table_name} already exists, skipping")
        return False

    try:
        with engine.connect() as conn:
            sql = text("""
            CREATE TABLE layout_reference_links (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES books_metadata(book_id) ON DELETE CASCADE,

                -- Link endpoints
                paragraph_id INTEGER NOT NULL,
                diagram_id INTEGER NOT NULL,

                -- Reference info
                reference_text VARCHAR(200),
                reference_type VARCHAR(50),

                -- Source
                detection_method VARCHAR(50) DEFAULT 'auto',
                confidence FLOAT,

                -- Verification
                verified BOOLEAN DEFAULT FALSE,
                verified_by VARCHAR(100),

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                verified_at TIMESTAMP,

                UNIQUE(book_id, paragraph_id, diagram_id)
            )
            """)
            conn.execute(sql)
            conn.commit()

            # Create indexes
            indexes = [
                "CREATE INDEX idx_layout_reference_links_book ON layout_reference_links(book_id)",
                "CREATE INDEX idx_layout_reference_links_paragraph ON layout_reference_links(paragraph_id)",
                "CREATE INDEX idx_layout_reference_links_diagram ON layout_reference_links(diagram_id)"
            ]
            for idx_sql in indexes:
                conn.execute(text(idx_sql))
            conn.commit()

            logger.info(f"Created table {table_name}")
            return True
    except ProgrammingError as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def create_layout_detections_for_existing_books():
    """Create layout_detections table for all existing books."""
    try:
        with engine.connect() as conn:
            # Get all existing books
            result = conn.execute(text("""
                SELECT book_id, table_prefix FROM books_metadata WHERE table_prefix IS NOT NULL
            """))
            books = result.fetchall()

            for book in books:
                book_id, table_prefix = book
                create_layout_detections_table(table_prefix, conn)
                logger.info(f"Created layout_detections table for book {book_id}")

            return True
    except Exception as e:
        logger.error(f"Error creating layout_detections tables: {e}")
        return False


def create_layout_detections_table(table_prefix, conn=None):
    """Create per-book layout_detections table.

    This function is also exported to be used by table_creator.py
    """
    table_name = f"raw_{table_prefix}_layout_detections"
    own_conn = False

    if conn is None:
        conn = engine.connect()
        own_conn = True

    try:
        # Check if table exists
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = :table_name
        """), {"table_name": table_name})

        if result.fetchone()[0] > 0:
            logger.info(f"Table {table_name} already exists, skipping")
            return False

        sql = text(f"""
        CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            page_number INTEGER NOT NULL,

            -- Detection info
            class_name VARCHAR(50) NOT NULL,
            class_id INTEGER,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            confidence FLOAT,

            -- Original detection (before corrections)
            original_x INTEGER,
            original_y INTEGER,
            original_width INTEGER,
            original_height INTEGER,
            original_class VARCHAR(50),

            -- Correction tracking
            was_corrected BOOLEAN DEFAULT FALSE,
            correction_type VARCHAR(30),
            correction_timestamp TIMESTAMP,

            -- Relationships
            parent_region_id INTEGER,

            -- Links to other tables
            linked_paragraph_id INTEGER,
            linked_diagram_id INTEGER,
            linked_knowledge_unit_id INTEGER,

            -- OCR result for this region
            ocr_text TEXT,
            ocr_confidence FLOAT,

            -- Review status
            review_status VARCHAR(30) DEFAULT 'pending',
            reviewed_at TIMESTAMP,

            -- Model info
            model_version INTEGER,
            detection_batch_id VARCHAR(50),

            -- Export tracking
            exported_for_training BOOLEAN DEFAULT FALSE,
            exported_at TIMESTAMP,

            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """)
        conn.execute(sql)

        # Create indexes
        indexes = [
            f"CREATE INDEX idx_{table_prefix}_layout_det_page ON {table_name}(page_number)",
            f"CREATE INDEX idx_{table_prefix}_layout_det_class ON {table_name}(class_name)",
            f"CREATE INDEX idx_{table_prefix}_layout_det_status ON {table_name}(review_status)",
            f"CREATE INDEX idx_{table_prefix}_layout_det_corrected ON {table_name}(was_corrected) WHERE was_corrected = true",
            f"CREATE INDEX idx_{table_prefix}_layout_det_parent ON {table_name}(parent_region_id)"
        ]
        for idx_sql in indexes:
            conn.execute(text(idx_sql))

        conn.commit()
        return True

    finally:
        if own_conn:
            conn.close()


def verify_migration():
    """Verify that all tables and columns were created."""
    all_ok = True

    # Check books_metadata column
    if check_column_exists("books_metadata", "layout_detection_config"):
        logger.info("✓ Column layout_detection_config exists in books_metadata")
    else:
        logger.error("✗ Column layout_detection_config NOT found in books_metadata")
        all_ok = False

    # Check global tables
    global_tables = [
        "layout_models",
        "layout_flagged_pages",
        "layout_training_history",
        "layout_reference_patterns",
        "layout_reference_links"
    ]

    for table in global_tables:
        if check_table_exists(table):
            logger.info(f"✓ Table {table} exists")
        else:
            logger.error(f"✗ Table {table} NOT found")
            all_ok = False

    return all_ok


def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("MIGRATION: Add Layout Detection Tables for Automatic Boundaries")
    logger.info("=" * 80)

    results = []

    try:
        # 1. Add column to books_metadata
        logger.info("\n[1/7] Adding layout_detection_config column to books_metadata...")
        results.append(("layout_detection_config column", add_layout_detection_config_column()))

        # 2. Create layout_models table
        logger.info("\n[2/7] Creating layout_models table...")
        results.append(("layout_models table", create_layout_models_table()))

        # 3. Create layout_flagged_pages table
        logger.info("\n[3/7] Creating layout_flagged_pages table...")
        results.append(("layout_flagged_pages table", create_layout_flagged_pages_table()))

        # 4. Create layout_training_history table
        logger.info("\n[4/7] Creating layout_training_history table...")
        results.append(("layout_training_history table", create_layout_training_history_table()))

        # 5. Create layout_reference_patterns table
        logger.info("\n[5/7] Creating layout_reference_patterns table...")
        results.append(("layout_reference_patterns table", create_layout_reference_patterns_table()))

        # 6. Create layout_reference_links table
        logger.info("\n[6/7] Creating layout_reference_links table...")
        results.append(("layout_reference_links table", create_layout_reference_links_table()))

        # 7. Create layout_detections tables for existing books
        logger.info("\n[7/7] Creating layout_detections tables for existing books...")
        results.append(("layout_detections for existing books", create_layout_detections_for_existing_books()))

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        for name, success in results:
            status = "CREATED" if success else "SKIPPED (exists)"
            logger.info(f"  {name}: {status}")

        # Verify
        if verify_migration():
            logger.info("\n" + "=" * 80)
            logger.info("MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info("\nNext step: Update table_creator.py to call create_layout_detections_table()")
            logger.info("for new books. This is done automatically by the service layer.")
        else:
            logger.error("\nMigration verification failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"\nMigration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MIGRATION: Add Layout Detection Tables")
    print("Phase 1.1 of Automatic Boundaries Implementation")
    print("=" * 80)
    print("\nThis will create the following database objects:")
    print("\n  GLOBAL TABLES:")
    print("    1. layout_models - Model metadata and versions")
    print("    2. layout_flagged_pages - Pages needing manual review")
    print("    3. layout_training_history - Training run history")
    print("    4. layout_reference_patterns - Custom reference patterns")
    print("    5. layout_reference_links - Diagram-paragraph links")
    print("\n  COLUMN:")
    print("    - books_metadata.layout_detection_config JSONB")
    print("\n  PER-BOOK TABLES:")
    print("    - raw_{prefix}_layout_detections for each existing book")
    print("\nThis operation is SAFE and can be run multiple times (idempotent).")
    print("=" * 80)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        main()
    else:
        print("\nMigration cancelled by user.")
        sys.exit(0)
