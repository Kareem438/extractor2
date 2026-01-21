"""
PostgreSQL Database Backup Script

This script creates a backup of the knowledge_extraction PostgreSQL database
and saves it to the "06-PostgreSQL BACKUP" directory with a timestamp.

Usage:
    python "06-PostgreSQL Backup.py"

Output:
    - SQL dump file: knowledge_extraction_YYYY-MM-DD_HH-MM-SS.sql
    - Custom format dump: knowledge_extraction_YYYY-MM-DD_HH-MM-SS.dump
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path


def create_postgres_backup():
    """Create PostgreSQL database backup using pg_dump"""

    # Configuration
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_USER = "postgres"
    DB_PASSWORD = "postgres"
    DB_NAME = "knowledge_extraction"
    PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"

    # Backup directory
    backup_dir = Path(__file__).parent / "06-PostgreSQL BACKUP"
    backup_dir.mkdir(exist_ok=True)

    # Timestamp for backup files
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Backup file paths
    sql_backup = backup_dir / f"knowledge_extraction_{timestamp}.sql"
    dump_backup = backup_dir / f"knowledge_extraction_{timestamp}.dump"

    # Set password environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASSWORD

    print("=" * 70)
    print("PostgreSQL Database Backup")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Host: {DB_HOST}:{DB_PORT}")
    print(f"Backup Directory: {backup_dir}")
    print(f"Timestamp: {timestamp}")
    print("-" * 70)

    # Create SQL format backup (human-readable, easy to restore)
    print("\n[1/2] Creating SQL format backup...")
    try:
        result = subprocess.run([
            PG_DUMP_PATH,
            '-h', DB_HOST,
            '-p', DB_PORT,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-f', str(sql_backup),
            '--no-password',
            '--verbose'
        ], env=env, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            size_mb = sql_backup.stat().st_size / (1024 * 1024)
            print(f"[OK] SQL backup created: {sql_backup.name}")
            print(f"  Size: {size_mb:.2f} MB")
        else:
            print(f"[FAIL] SQL backup failed!")
            print(f"  Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("[FAIL] SQL backup timed out (5 minutes)")
        return False
    except Exception as e:
        print(f"[FAIL] SQL backup error: {e}")
        return False

    # Create custom format backup (compressed, faster restore)
    print("\n[2/2] Creating custom format backup (compressed)...")
    try:
        result = subprocess.run([
            PG_DUMP_PATH,
            '-h', DB_HOST,
            '-p', DB_PORT,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-f', str(dump_backup),
            '-F', 'c',  # Custom format
            '-b',       # Include large objects
            '-v',       # Verbose
            '--no-password'
        ], env=env, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            size_mb = dump_backup.stat().st_size / (1024 * 1024)
            print(f"[OK] Custom backup created: {dump_backup.name}")
            print(f"  Size: {size_mb:.2f} MB")
        else:
            print(f"[FAIL] Custom backup failed!")
            print(f"  Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("[FAIL] Custom backup timed out (5 minutes)")
        return False
    except Exception as e:
        print(f"[FAIL] Custom backup error: {e}")
        return False

    # Summary
    print("\n" + "=" * 70)
    print("BACKUP COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nBackup files created:")
    print(f"  1. {sql_backup}")
    print(f"  2. {dump_backup}")

    print(f"\nTo restore from SQL backup:")
    print(f'  psql -h localhost -p 5432 -U postgres -d knowledge_extraction < "{sql_backup}"')

    print(f"\nTo restore from custom backup:")
    print(f'  pg_restore -h localhost -p 5432 -U postgres -d knowledge_extraction "{dump_backup}"')

    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = create_postgres_backup()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nBackup cancelled by user.")
        exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        exit(1)
