"""
Migration: Add global llm_providers table

Creates the llm_providers table for storing LLM provider configurations
(API keys, base URLs, model names) used by V2 cloud extraction.

This is a GLOBAL table (not per-book).

Usage:
    python migrate_add_llm_providers.py
"""

from sqlalchemy import text
from src.database.connection import engine


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = :table AND column_name = :col
        """), {"table": table_name, "col": column_name})
        return result.scalar() > 0


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = :table
        """), {"table": table_name})
        return result.scalar() > 0


def migrate():
    """Run migration to create llm_providers table."""
    print("=" * 60)
    print("Migration: Add LLM Providers Table")
    print("=" * 60)

    changes = 0

    with engine.connect() as db:
        # Create llm_providers table
        if not table_exists("llm_providers"):
            db.execute(text("""
                CREATE TABLE llm_providers (
                    id SERIAL PRIMARY KEY,
                    provider_name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    api_key TEXT NOT NULL,
                    base_url VARCHAR(500),
                    model_name VARCHAR(100) NOT NULL,
                    auth_header_style VARCHAR(50) DEFAULT 'bearer',
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            db.commit()
            print("  ✅ Created llm_providers table")
            changes += 1
        else:
            print("  ⏭️  llm_providers table already exists")

    print(f"\nMigration complete: {changes} change(s) applied")


if __name__ == "__main__":
    migrate()
