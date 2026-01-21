"""
Migration: Expand attributes from 40 to 80 in knowledge_units tables.

This migration adds 40 new attribute columns (attr41_value through attr80_value)
to all existing {prefix}_knowledge_units tables, updates constraints, and adds
new attribute key records.

Changes:
- Adds attr41_value through attr80_value columns to knowledge_units tables
- Updates CHECK constraint on attribute_keys from (1-40) to (1-80)
- Inserts new attribute key records for attributes 41-80

Run from 03-code directory:
    cd H:/12-extractor/03-code
    H:/12-extractor/venv/Scripts/python.exe migrate_expand_attributes_40_to_80.py
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.connection import engine, SessionLocal
from src.utils.logging_config import logger

# Check for --auto-confirm flag
AUTO_CONFIRM = "--auto-confirm" in sys.argv or "-y" in sys.argv


def get_all_book_table_prefixes():
    """Get all table prefixes from books_metadata."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT table_prefix FROM books_metadata"))
        return [row[0] for row in result.fetchall()]
    finally:
        db.close()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        return result.fetchone() is not None
    finally:
        db.close()


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        return result.fetchone()[0]
    finally:
        db.close()


def add_attribute_columns(table_prefix: str):
    """Add attr41_value through attr80_value to knowledge_units table."""
    table_name = f"{table_prefix}_knowledge_units"

    # Check if table exists first
    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping")
        return 0, 0

    columns_added = 0
    columns_skipped = 0

    with engine.connect() as conn:
        # Add attr41_value through attr80_value
        for i in range(41, 81):
            column_name = f"attr{i}_value"

            # Check if column already exists
            if column_exists(table_name, column_name):
                logger.info(f"  Column {column_name} already exists in {table_name}, skipping")
                columns_skipped += 1
                continue

            # Add the column
            try:
                sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")
                conn.execute(sql)
                conn.commit()
                logger.info(f"  [OK] Added column {column_name} to {table_name}")
                columns_added += 1
            except Exception as e:
                logger.error(f"  [ERROR] Failed to add column {column_name} to {table_name}: {e}")
                raise

    return columns_added, columns_skipped


def update_attribute_keys_constraint(table_prefix: str):
    """Update CHECK constraint on attribute_keys table from (1-40) to (1-80)."""
    table_name = f"{table_prefix}_attribute_keys"

    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping constraint update")
        return False

    with engine.connect() as conn:
        try:
            # Drop all existing CHECK constraints on attr_number
            # Note: There may be multiple due to naming variations
            possible_names = [
                f"{table_prefix}_attribute_keys_attr_number_check",
                f"{table_prefix}_attribute_key_attr_number_check",  # singular 'key'
                f"{table_prefix}_attribute_keys_attr_number_chec",   # truncated name
            ]

            for constraint_name in possible_names:
                sql = text(f"""
                    ALTER TABLE {table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """)
                conn.execute(sql)
                conn.commit()

            # Add new constraint for range 1-80 with explicit shorter name
            new_constraint_name = f"{table_prefix}_attr_keys_1_to_80"
            sql = text(f"""
                ALTER TABLE {table_name}
                ADD CONSTRAINT {new_constraint_name}
                CHECK (attr_number BETWEEN 1 AND 80)
            """)
            conn.execute(sql)
            conn.commit()

            logger.info(f"  [OK] Updated CHECK constraint to (1-80) on {table_name}")
            return True
        except Exception as e:
            logger.error(f"  [ERROR] Failed to update constraint on {table_name}: {e}")
            raise


def insert_new_attribute_keys(table_prefix: str):
    """Insert attribute key records for attr41 through attr80."""
    table_name = f"{table_prefix}_attribute_keys"

    if not table_exists(table_name):
        logger.info(f"  Table {table_name} does not exist, skipping key insertion")
        return 0

    with engine.connect() as conn:
        keys_added = 0

        # Insert keys for attributes 41-80
        for i in range(41, 81):
            try:
                # Check if key already exists
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE attr_number = :attr_num
                """), {"attr_num": i})

                if result.fetchone()[0] > 0:
                    logger.info(f"  Key for attribute {i} already exists, skipping")
                    continue

                # Insert new attribute key
                sql = text(f"""
                    INSERT INTO {table_name}
                    (attr_number, key_name, is_system_reserved, is_editable)
                    VALUES (:attr_num, :key_name, FALSE, TRUE)
                """)

                conn.execute(sql, {
                    "attr_num": i,
                    "key_name": f"Attribute {i}"
                })
                conn.commit()
                keys_added += 1

            except Exception as e:
                logger.error(f"  [ERROR] Failed to insert key for attribute {i}: {e}")
                raise

        if keys_added > 0:
            logger.info(f"  [OK] Added {keys_added} new attribute keys (41-80)")

        return keys_added


def verify_migration(table_prefix: str):
    """Verify migration completed successfully."""
    print(f"\n  [INFO] Verifying migration for {table_prefix}...")

    knowledge_units_table = f"{table_prefix}_knowledge_units"
    attribute_keys_table = f"{table_prefix}_attribute_keys"

    with engine.connect() as conn:
        # Count columns in knowledge_units
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name LIKE 'attr%_value'
        """), {"table_name": knowledge_units_table})

        attr_columns = result.fetchone()[0]
        print(f"    Attribute columns in {knowledge_units_table}: {attr_columns}")

        # Count attribute keys
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM {attribute_keys_table}
        """))

        total_keys = result.fetchone()[0]
        print(f"    Total attribute keys in {attribute_keys_table}: {total_keys}")

        # Count user-defined keys (9-80)
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM {attribute_keys_table}
            WHERE attr_number BETWEEN 9 AND 80
        """))

        user_keys = result.fetchone()[0]
        print(f"    User-defined keys (9-80): {user_keys}")

        # Verify expected counts
        if attr_columns == 80 and total_keys == 80 and user_keys == 72:
            print(f"  [OK] Verification PASSED for {table_prefix}")
            return True
        else:
            print(f"  [WARNING] Verification issues for {table_prefix}:")
            if attr_columns != 80:
                print(f"      Expected 80 attribute columns, found {attr_columns}")
            if total_keys != 80:
                print(f"      Expected 80 total keys, found {total_keys}")
            if user_keys != 72:
                print(f"      Expected 72 user-defined keys (9-80), found {user_keys}")
            return False


def run_migration():
    """Run the migration for all books."""
    print("=" * 80)
    print("MIGRATION: Expand Attributes from 40 to 80")
    print("=" * 80)
    print("\nThis migration will:")
    print("  * Add 40 new columns (attr41_value through attr80_value) to knowledge_units")
    print("  * Update CHECK constraint on attribute_keys from (1-40) to (1-80)")
    print("  * Insert 40 new attribute key records (41-80)")
    print("\n" + "=" * 80)

    # Get all book table prefixes
    table_prefixes = get_all_book_table_prefixes()

    if not table_prefixes:
        print("\n[ERROR] No books found in database.")
        print("\nMigration aborted - no tables to migrate.")
        return

    print(f"\nFound {len(table_prefixes)} book(s) to migrate:")
    for prefix in table_prefixes:
        print(f"  - {prefix}")

    print("\n" + "=" * 80)

    # Confirm before proceeding
    print("\n[WARNING] This migration will modify your database schema.")
    print("          Make sure you have a backup before proceeding!")
    print(f"\n          Backup location: H:\\12-extractor\\06-PostgreSQL BACKUP\\")

    if AUTO_CONFIRM:
        print("\n[AUTO-CONFIRMED] Proceeding with migration (--auto-confirm flag used)")
        response = 'yes'
    else:
        response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\n[CANCELLED] Migration cancelled by user.")
        return

    print("\n" + "=" * 80)
    print("STARTING MIGRATION")
    print("=" * 80)

    total_columns_added = 0
    total_columns_skipped = 0
    total_keys_added = 0
    migrations_completed = 0

    for prefix in table_prefixes:
        print(f"\n{'-' * 80}")
        print(f"Migrating: {prefix}")
        print(f"{'-' * 80}")

        try:
            # Step 1: Add columns to knowledge_units
            print(f"\n  [Step 1/4] Adding columns to {prefix}_knowledge_units...")
            columns_added, columns_skipped = add_attribute_columns(prefix)
            total_columns_added += columns_added
            total_columns_skipped += columns_skipped

            if columns_added > 0:
                print(f"  [OK] Added {columns_added} new columns")
            if columns_skipped > 0:
                print(f"  [SKIP] Skipped {columns_skipped} existing columns")

            # Step 2: Update constraint on attribute_keys
            print(f"\n  [Step 2/4] Updating constraint on {prefix}_attribute_keys...")
            constraint_updated = update_attribute_keys_constraint(prefix)

            if constraint_updated:
                print(f"  [OK] Constraint updated successfully")

            # Step 3: Insert new attribute keys
            print(f"\n  [Step 3/4] Inserting new attribute keys (41-80)...")
            keys_added = insert_new_attribute_keys(prefix)
            total_keys_added += keys_added

            # Step 4: Verify migration
            print(f"\n  [Step 4/4] Verifying migration...")
            verification_passed = verify_migration(prefix)

            if verification_passed:
                migrations_completed += 1
                print(f"\n  [OK] Migration complete for {prefix}")
            else:
                print(f"\n  [WARNING] Migration completed with warnings for {prefix}")

        except Exception as e:
            print(f"\n  [ERROR] Migration failed for {prefix}: {e}")
            print(f"\n  Rolling back changes...")
            raise

    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"  Books migrated: {migrations_completed}/{len(table_prefixes)}")
    print(f"  Total columns added: {total_columns_added}")
    print(f"  Total columns skipped (already exist): {total_columns_skipped}")
    print(f"  Total attribute keys added: {total_keys_added}")
    print("=" * 80)

    if migrations_completed == len(table_prefixes):
        print("\n[SUCCESS] MIGRATION COMPLETED SUCCESSFULLY!")
        print("\nNEXT STEPS:")
        print("  1. Update table_creator.py to include new columns for future books")
        print("  2. Update service layer (attribute_key_service.py) to use 1-80 range")
        print("  3. Update frontend templates and JavaScript")
        print("  4. Update documentation")
        print("  5. Test attribute creation and editing")
    else:
        print("\n[WARNING] MIGRATION COMPLETED WITH WARNINGS")
        print("          Please review the warnings above and verify data integrity.")

    print("=" * 80)


if __name__ == "__main__":
    run_migration()
