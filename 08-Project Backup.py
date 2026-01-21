#!/usr/bin/env python3
"""
08-Project Backup.py - Full Project Duplication Script

This script creates a complete copy of the Knowledge Extraction project including:
- All project files (excluding temp files)
- PostgreSQL database (dump and restore to new database)
- ChromaDB database (folder copy)
- Python virtual environment
- Updated configuration files (.env, CLAUDE.md)

================================================================================
FEATURES
================================================================================
| Feature          | Description                                               |
|------------------|-----------------------------------------------------------|
| Interactive      | Asks for source path, destination path, new DB name       |
| File copy        | Copies all files except temp_*, tmpclaude-*, __pycache__  |
| PostgreSQL       | Dumps current DB -> Creates new DB -> Restores data       |
| ChromaDB         | Copies entire chroma_db folder                            |
| Virtual env      | Copies entire venv folder                                 |
| .env update      | Updates DATABASE_URL and absolute paths                   |
| CLAUDE.md update | Updates all hardcoded paths                               |
| Verification     | Checks files exist, tests DB connection, compares counts  |

================================================================================
USAGE
================================================================================
    python "08-Project Backup.py"

================================================================================
INTERACTIVE PROMPTS
================================================================================
The script will prompt for:
    1. Source project folder path (default: script's directory)
    2. Destination folder path (will be created)
    3. New PostgreSQL database name (default: knowledge_extraction_copy)

================================================================================
AFTER BACKUP - TO RUN THE COPIED PROJECT
================================================================================
    cd <destination>/03-code
    <destination>/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7778

Note: Use a different port (e.g., 7778) if the original project is still running on 7777.

================================================================================
EXCLUDED FILES
================================================================================
The following are NOT copied:
    - temp_*.json files
    - tmpclaude-* folders
    - __pycache__ folders
    - *.pyc files
    - .git folder (re-initialize if needed)
    - .idea, .vscode folders

================================================================================
REQUIREMENTS
================================================================================
    - PostgreSQL 16+ installed with pg_dump and psql in PATH
    - Sufficient disk space for project copy + database dump
    - Write permissions on destination folder

================================================================================
EXAMPLE USAGE
================================================================================
Example: Copy project from H:\12-extractor to H:\13-extractor2

Step 1: Open Windows Terminal or Command Prompt

Step 2: Navigate to project folder and run script:
    cd H:\12-extractor
    H:\12-extractor\venv\Scripts\python.exe "08-Project Backup.py"

Step 3: When prompted, enter the following:

    ============================================================
      Knowledge Extraction Project Backup Tool
    ============================================================

    [Step 1] Source Folder
    Enter source project folder path [H:\12-extractor]: <press Enter>
      [OK] Source folder: H:\12-extractor

    [Step 2] Destination Folder
    Enter destination folder path (will be created): H:\13-extractor2
      [OK] Destination folder: H:\13-extractor2

    [Step 3] Database Configuration
      [OK] Current database: knowledge_extraction
      [INFO] Host: localhost:5432
      [INFO] User: postgres

    [Step 4] New Database Name
    Enter new database name [knowledge_extraction_copy]: extractor2_knowledge_base
      [OK] New database name: extractor2_knowledge_base

    ============================================================
      Confirmation
    ============================================================

    Source:      H:\12-extractor
    Destination: H:\13-extractor2
    Old DB:      knowledge_extraction
    New DB:      extractor2_knowledge_base

    Proceed with backup? (yes/no) [yes]: yes

Step 4: Wait for backup to complete (may take several minutes)

Step 5: After backup, run the copied project on a different port:
    cd H:\13-extractor2\03-code
    H:\13-extractor2\venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7778

Step 6: Access the copied project at: http://localhost:7778/library

================================================================================
TROUBLESHOOTING
================================================================================
If you get "WinError 87: The parameter is incorrect":
    - The script will automatically try alternative copy methods
    - Some files with very long paths may be skipped (reported at end)
    - These are usually cache files and won't affect functionality

If destination folder already exists:
    - Delete it first: rmdir /s /q H:\13-extractor2
    - Then run the script again

If database already exists:
    - Choose a different database name
    - Or drop the existing database first: DROP DATABASE extractor2_knowledge_base;
"""

import os
import sys
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step_num, text):
    """Print a step indicator."""
    print(f"\n[Step {step_num}] {text}")


def print_success(text):
    """Print success message."""
    print(f"  [OK] {text}")


def print_error(text):
    """Print error message."""
    print(f"  [ERROR] {text}")


def print_info(text):
    """Print info message."""
    print(f"  [INFO] {text}")


def get_input(prompt, default=None):
    """Get user input with optional default value."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def parse_env_file(env_path):
    """Parse .env file and return dictionary of key-value pairs."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def parse_database_url(url):
    """Parse DATABASE_URL and extract components."""
    # Format: postgresql://user:password@host:port/dbname
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, url)
    if match:
        return {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4),
            'dbname': match.group(5)
        }
    return None


def should_exclude(path, source_root):
    """Check if a path should be excluded from copy."""
    rel_path = str(path.relative_to(source_root))
    name = path.name

    # Exclude patterns
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        'temp_',
        'tmpclaude-',
        '.git',  # Git folder - user can re-init if needed
        '.idea',
        '.vscode',
        '*.log',
    ]

    for pattern in exclude_patterns:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif pattern in rel_path or name.startswith(pattern):
            return True

    return False


def copy_project_files(source, dest, exclusions_count):
    """Copy project files with exclusions."""
    copied_files = 0
    copied_dirs = 0
    excluded_count = 0
    failed_files = []

    for item in source.rglob('*'):
        if should_exclude(item, source):
            excluded_count += 1
            continue

        rel_path = item.relative_to(source)
        dest_path = dest / rel_path

        try:
            if item.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
                copied_dirs += 1
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # Try different copy methods for Windows compatibility
                try:
                    # Use long path prefix for Windows
                    src_str = str(item)
                    dst_str = str(dest_path)
                    if sys.platform == 'win32':
                        if not src_str.startswith('\\\\?\\'):
                            src_str = '\\\\?\\' + src_str.replace('/', '\\')
                        if not dst_str.startswith('\\\\?\\'):
                            dst_str = '\\\\?\\' + dst_str.replace('/', '\\')
                    shutil.copy2(src_str, dst_str)
                except OSError:
                    # Fallback: try simple copy without metadata
                    try:
                        shutil.copy(item, dest_path)
                    except OSError:
                        # Last resort: read and write binary
                        with open(item, 'rb') as f_src:
                            with open(dest_path, 'wb') as f_dst:
                                f_dst.write(f_src.read())
                copied_files += 1
        except Exception as e:
            failed_files.append((str(rel_path), str(e)))
            continue

    # Report failed files
    if failed_files:
        print(f"  [WARNING] {len(failed_files)} files could not be copied:")
        for path, error in failed_files[:5]:  # Show first 5
            print(f"    - {path}: {error[:50]}")
        if len(failed_files) > 5:
            print(f"    ... and {len(failed_files) - 5} more")

    return copied_files, copied_dirs, excluded_count


def dump_postgresql(db_config, dump_path):
    """Dump PostgreSQL database to SQL file."""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['user'],
        '-d', db_config['dbname'],
        '-f', str(dump_path),
        '--no-owner',
        '--no-privileges'
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def create_postgresql_database(db_config, new_dbname):
    """Create a new PostgreSQL database."""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    # First, check if database exists
    check_cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['user'],
        '-d', 'postgres',
        '-tAc', f"SELECT 1 FROM pg_database WHERE datname='{new_dbname}'"
    ]

    result = subprocess.run(check_cmd, env=env, capture_output=True, text=True)
    if result.stdout.strip() == '1':
        return False, f"Database '{new_dbname}' already exists"

    # Create the database
    create_cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['user'],
        '-d', 'postgres',
        '-c', f"CREATE DATABASE {new_dbname}"
    ]

    result = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def restore_postgresql(db_config, new_dbname, dump_path):
    """Restore PostgreSQL dump to new database."""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['user'],
        '-d', new_dbname,
        '-f', str(dump_path)
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def test_postgresql_connection(db_config, dbname):
    """Test connection to PostgreSQL database."""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']

    cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', db_config['port'],
        '-U', db_config['user'],
        '-d', dbname,
        '-c', 'SELECT 1'
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0


def update_env_file(env_path, old_source, new_dest, new_dbname, db_config):
    """Update .env file with new paths and database name."""
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update DATABASE_URL with new database name
    old_db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    new_db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{new_dbname}"
    content = content.replace(old_db_url, new_db_url)

    # Also try simpler replacement for database name
    content = content.replace(f"/{db_config['dbname']}", f"/{new_dbname}")

    # Update any absolute paths
    old_source_str = str(old_source).replace('\\', '/')
    new_dest_str = str(new_dest).replace('\\', '/')
    content = content.replace(old_source_str, new_dest_str)

    # Also try with backslashes for Windows paths
    old_source_str_win = str(old_source).replace('/', '\\')
    new_dest_str_win = str(new_dest).replace('/', '\\')
    content = content.replace(old_source_str_win, new_dest_str_win)

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_claude_md(claude_path, old_source, new_dest, new_dbname):
    """Update CLAUDE.md with new paths."""
    if not claude_path.exists():
        return False

    with open(claude_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update paths - handle both forward and back slashes
    old_source_str = str(old_source).replace('\\', '/')
    new_dest_str = str(new_dest).replace('\\', '/')
    content = content.replace(old_source_str, new_dest_str)

    # Also replace the folder name pattern (e.g., H:/12-extractor -> new path)
    old_source_str_win = str(old_source)
    new_dest_str_win = str(new_dest)
    content = content.replace(old_source_str_win, new_dest_str_win)

    with open(claude_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def count_files(folder):
    """Count files in a folder recursively."""
    count = 0
    for item in Path(folder).rglob('*'):
        if item.is_file():
            count += 1
    return count


def verify_backup(source, dest, new_dbname, db_config):
    """Verify the backup was successful."""
    issues = []

    # Check key folders exist
    key_folders = ['03-code', 'venv', 'chroma_db', '02-architecture']
    for folder in key_folders:
        if not (dest / folder).exists():
            issues.append(f"Missing folder: {folder}")

    # Check key files exist
    key_files = ['CLAUDE.md', '03-code/.env', '03-code/src/main.py']
    for file in key_files:
        if not (dest / file).exists():
            issues.append(f"Missing file: {file}")

    # Test database connection
    if not test_postgresql_connection(db_config, new_dbname):
        issues.append(f"Cannot connect to new database: {new_dbname}")

    # Compare file counts (approximate, due to exclusions)
    source_count = count_files(source / '03-code')
    dest_count = count_files(dest / '03-code')
    if abs(source_count - dest_count) > 10:  # Allow small difference due to exclusions
        issues.append(f"File count mismatch in 03-code: source={source_count}, dest={dest_count}")

    return issues


def main():
    """Main function."""
    print_header("Knowledge Extraction Project Backup Tool")
    print("\nThis tool creates a complete copy of the project including databases.")
    print("It will:")
    print("  1. Copy all project files (excluding temp files)")
    print("  2. Dump and restore PostgreSQL to a new database")
    print("  3. Copy ChromaDB folder")
    print("  4. Copy Python virtual environment")
    print("  5. Update configuration files with new paths")

    # Get script's directory as default source
    script_dir = Path(__file__).parent.resolve()

    # Step 1: Get source folder
    print_step(1, "Source Folder")
    source_path = get_input("Enter source project folder path", str(script_dir))
    source = Path(source_path).resolve()

    if not source.exists():
        print_error(f"Source folder does not exist: {source}")
        sys.exit(1)

    # Verify it's a valid project folder
    env_file = source / '03-code' / '.env'
    if not env_file.exists():
        print_error(f"Not a valid project folder (missing 03-code/.env): {source}")
        sys.exit(1)

    print_success(f"Source folder: {source}")

    # Step 2: Get destination folder
    print_step(2, "Destination Folder")
    dest_path = get_input("Enter destination folder path (will be created)")
    dest = Path(dest_path).resolve()

    if dest.exists():
        print_error(f"Destination folder already exists: {dest}")
        confirm = get_input("Do you want to overwrite? (yes/no)", "no")
        if confirm.lower() != 'yes':
            print_info("Backup cancelled.")
            sys.exit(0)
        shutil.rmtree(dest)

    print_success(f"Destination folder: {dest}")

    # Step 3: Parse current database config
    print_step(3, "Database Configuration")
    env_vars = parse_env_file(env_file)
    db_url = env_vars.get('DATABASE_URL', '')

    if not db_url:
        print_error("DATABASE_URL not found in .env file")
        sys.exit(1)

    db_config = parse_database_url(db_url)
    if not db_config:
        print_error(f"Could not parse DATABASE_URL: {db_url}")
        sys.exit(1)

    print_success(f"Current database: {db_config['dbname']}")
    print_info(f"Host: {db_config['host']}:{db_config['port']}")
    print_info(f"User: {db_config['user']}")

    # Step 4: Get new database name
    print_step(4, "New Database Name")
    default_new_db = f"{db_config['dbname']}_copy"
    new_dbname = get_input("Enter new database name", default_new_db)

    # Validate database name
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', new_dbname):
        print_error("Invalid database name. Use only letters, numbers, and underscores.")
        sys.exit(1)

    print_success(f"New database name: {new_dbname}")

    # Confirmation
    print_header("Confirmation")
    print(f"\nSource:      {source}")
    print(f"Destination: {dest}")
    print(f"Old DB:      {db_config['dbname']}")
    print(f"New DB:      {new_dbname}")

    confirm = get_input("\nProceed with backup? (yes/no)", "yes")
    if confirm.lower() != 'yes':
        print_info("Backup cancelled.")
        sys.exit(0)

    start_time = datetime.now()

    # Step 5: Copy project files
    print_step(5, "Copying Project Files")
    print_info("This may take a few minutes...")

    dest.mkdir(parents=True, exist_ok=True)
    copied_files, copied_dirs, excluded = copy_project_files(source, dest, 0)

    print_success(f"Copied {copied_files} files in {copied_dirs} directories")
    print_info(f"Excluded {excluded} items (temp files, __pycache__, etc.)")

    # Step 6: Dump PostgreSQL
    print_step(6, "Dumping PostgreSQL Database")
    dump_path = dest / 'temp_db_dump.sql'

    success, error = dump_postgresql(db_config, dump_path)
    if not success:
        print_error(f"Failed to dump database: {error}")
        sys.exit(1)

    dump_size = dump_path.stat().st_size / (1024 * 1024)
    print_success(f"Database dumped ({dump_size:.2f} MB)")

    # Step 7: Create new database
    print_step(7, "Creating New PostgreSQL Database")
    success, error = create_postgresql_database(db_config, new_dbname)
    if not success:
        print_error(f"Failed to create database: {error}")
        # Clean up dump file
        dump_path.unlink(missing_ok=True)
        sys.exit(1)

    print_success(f"Database '{new_dbname}' created")

    # Step 8: Restore to new database
    print_step(8, "Restoring Database to New Database")
    success, error = restore_postgresql(db_config, new_dbname, dump_path)
    if not success:
        print_error(f"Warning - some restore errors (may be normal): {error[:200] if error else 'None'}")

    # Clean up dump file
    dump_path.unlink(missing_ok=True)
    print_success("Database restored")

    # Step 9: Update .env file
    print_step(9, "Updating Configuration Files")
    new_env_path = dest / '03-code' / '.env'
    update_env_file(new_env_path, source, dest, new_dbname, db_config)
    print_success("Updated .env file with new database and paths")

    # Step 10: Update CLAUDE.md
    claude_path = dest / 'CLAUDE.md'
    if update_claude_md(claude_path, source, dest, new_dbname):
        print_success("Updated CLAUDE.md with new paths")
    else:
        print_info("CLAUDE.md not found, skipping")

    # Step 11: Verify backup
    print_step(11, "Verifying Backup")
    issues = verify_backup(source, dest, new_dbname, db_config)

    if issues:
        print_error("Verification found issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print_success("All verification checks passed")

    # Summary
    elapsed = datetime.now() - start_time
    print_header("Backup Complete!")
    print(f"\nTime elapsed: {elapsed.total_seconds():.1f} seconds")
    print(f"\nProject copied to: {dest}")
    print(f"New database: {new_dbname}")
    print("\nTo use the copied project:")
    print(f"  1. cd {dest / '03-code'}")
    print(f"  2. {dest / 'venv' / 'Scripts' / 'python.exe'} -m uvicorn src.main:app --host 0.0.0.0 --port 7778")
    print("\nNote: Use a different port (e.g., 7778) if original project is still running.")


if __name__ == '__main__':
    main()
