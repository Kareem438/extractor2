"""
ChromaDB Database Backup Script

This script creates a backup of the ChromaDB vector database
and saves it to the "07-Chroma BACKUP" directory with a timestamp.

ChromaDB stores data in:
  - SQLite database (chroma.sqlite3)
  - Collection directories with parquet files

Usage:
    python "07-Chroma Backup.py"

Output:
    - Compressed archive: chroma_backup_YYYY-MM-DD_HH-MM-SS.zip
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path


def create_chroma_backup():
    """Create ChromaDB backup by archiving the entire chroma_db directory"""

    # Configuration
    chroma_db_path = Path(__file__).parent / "chroma_db"
    backup_dir = Path(__file__).parent / "07-Chroma BACKUP"

    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)

    # Check if ChromaDB directory exists
    if not chroma_db_path.exists():
        print(f"ERROR: ChromaDB directory not found at {chroma_db_path}")
        return False

    # Timestamp for backup file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = backup_dir / f"chroma_backup_{timestamp}.zip"

    print("=" * 70)
    print("ChromaDB Vector Database Backup")
    print("=" * 70)
    print(f"Source: {chroma_db_path}")
    print(f"Backup Directory: {backup_dir}")
    print(f"Timestamp: {timestamp}")
    print("-" * 70)

    # Check ChromaDB contents
    print("\nAnalyzing ChromaDB contents...")
    db_files = list(chroma_db_path.glob("**/*"))
    total_size = sum(f.stat().st_size for f in db_files if f.is_file())
    total_size_mb = total_size / (1024 * 1024)

    print(f"  Files found: {len([f for f in db_files if f.is_file()])}")
    print(f"  Total size: {total_size_mb:.2f} MB")

    # Key files to verify
    sqlite_file = chroma_db_path / "chroma.sqlite3"
    if sqlite_file.exists():
        sqlite_size_mb = sqlite_file.stat().st_size / (1024 * 1024)
        print(f"  SQLite DB: {sqlite_size_mb:.2f} MB")
    else:
        print("  SQLite DB: Not found")

    # Count collections
    collections = [d for d in chroma_db_path.iterdir() if d.is_dir()]
    print(f"  Collections: {len(collections)}")

    # Create backup
    print(f"\nCreating compressed backup archive...")
    print(f"  Output: {backup_file.name}")

    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from chroma_db directory
            for file_path in db_files:
                if file_path.is_file():
                    # Get relative path for archive
                    arcname = file_path.relative_to(chroma_db_path.parent)
                    zipf.write(file_path, arcname)

                    # Show progress for large files
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    if file_size_mb > 1:
                        print(f"    Adding: {file_path.name} ({file_size_mb:.2f} MB)")

        # Verify backup
        backup_size_mb = backup_file.stat().st_size / (1024 * 1024)
        compression_ratio = (1 - backup_size_mb / total_size_mb) * 100 if total_size_mb > 0 else 0

        print(f"\n[OK] Backup created successfully!")
        print(f"  Backup file: {backup_file.name}")
        print(f"  Original size: {total_size_mb:.2f} MB")
        print(f"  Backup size: {backup_size_mb:.2f} MB")
        print(f"  Compression: {compression_ratio:.1f}%")

        # Summary
        print("\n" + "=" * 70)
        print("BACKUP COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nBackup file created:")
        print(f"  {backup_file}")

        print(f"\nTo restore ChromaDB:")
        print(f"  1. Stop any processes using ChromaDB")
        print(f"  2. Rename/backup existing chroma_db directory")
        print(f'  3. Extract: unzip "{backup_file.name}"')
        print(f"  4. Restart application")

        print("\n" + "=" * 70)

        return True

    except Exception as e:
        print(f"\n[FAIL] Backup failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = create_chroma_backup()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nBackup cancelled by user.")
        exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        exit(1)
