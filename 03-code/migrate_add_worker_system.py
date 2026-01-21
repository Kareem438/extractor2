"""
Migration Script: Add Worker System Tables

Creates global tables for the backend worker system:
- worker_status: Worker heartbeat and current state
- pipeline_templates: Default/template pipeline configurations
- worker_commands: Commands to control worker (start/stop)

Run this script once to set up the worker system infrastructure.
"""

from sqlalchemy import text
from src.database.connection import engine


def create_worker_status_table():
    """Create worker_status table (global, not per-book)"""

    sql = text("""
    CREATE TABLE IF NOT EXISTS worker_status (
        id SERIAL PRIMARY KEY,
        worker_id VARCHAR(50) NOT NULL UNIQUE,
        status VARCHAR(20) DEFAULT 'stopped',  -- stopped, running, paused, rate_limited
        current_book_id INTEGER,
        current_entity_type VARCHAR(20),       -- paragraph, diagram
        current_record_id INTEGER,
        current_step INTEGER,
        total_steps INTEGER,
        records_processed INTEGER DEFAULT 0,
        records_failed INTEGER DEFAULT 0,
        records_remaining INTEGER DEFAULT 0,
        last_heartbeat TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP,
        rate_limited_until TIMESTAMP,
        last_error TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
        print("[OK] Created worker_status table")


def create_pipeline_templates_table():
    """Create pipeline_templates table (for copying to new books)"""

    sql = text("""
    CREATE TABLE IF NOT EXISTS pipeline_templates (
        id SERIAL PRIMARY KEY,
        template_name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        steps JSONB NOT NULL,  -- Array of step configurations
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
        print("[OK] Created pipeline_templates table")


def create_worker_commands_table():
    """Create worker_commands table for UI to send commands to worker"""

    sql = text("""
    CREATE TABLE IF NOT EXISTS worker_commands (
        id SERIAL PRIMARY KEY,
        worker_id VARCHAR(50) NOT NULL,
        command VARCHAR(20) NOT NULL,  -- start, stop, pause, resume
        parameters JSONB,
        status VARCHAR(20) DEFAULT 'pending',  -- pending, executed, failed
        created_at TIMESTAMP DEFAULT NOW(),
        executed_at TIMESTAMP,
        result TEXT
    )
    """)

    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()

        # Create index for efficient polling
        index_sql = text("""
        CREATE INDEX IF NOT EXISTS idx_worker_commands_pending
        ON worker_commands (worker_id, status, created_at)
        WHERE status = 'pending'
        """)
        conn.execute(index_sql)
        conn.commit()
        print("[OK] Created worker_commands table")


def insert_default_template():
    """Insert a default empty pipeline template"""

    sql = text("""
    INSERT INTO pipeline_templates (template_name, description, steps, is_default)
    VALUES (
        'Empty Pipeline',
        'Start with no pipeline steps',
        '[]'::jsonb,
        true
    )
    ON CONFLICT (template_name) DO NOTHING
    """)

    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
        print("[OK] Inserted default empty template")


def main():
    """Run all migrations"""
    print("Starting worker system migration...")
    print()

    try:
        create_worker_status_table()
        create_pipeline_templates_table()
        create_worker_commands_table()
        insert_default_template()

        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Run the per-book table migration")
        print("2. Start the worker process")
        print("3. Configure pipeline steps in the UI")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
