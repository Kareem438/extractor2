"""Import database backup using psycopg2"""
import psycopg2
import sys

def import_backup():
    """Import SQL backup file into PostgreSQL"""
    try:
        # Read SQL file
        print("Reading backup file...")
        with open(r"H:\12-extractor\db_backup.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Connect to database
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='knowledge_extraction'
        )
        conn.autocommit = False
        cur = conn.cursor()

        # Split SQL into statements (basic split by semicolon)
        print("Executing SQL statements...")
        statements = []
        current = []
        in_function = False

        for line in sql_content.split('\n'):
            # Skip pgvector extension line if it fails
            if 'CREATE EXTENSION' in line and 'vector' in line:
                print(f"Skipping: {line.strip()}")
                continue
            if 'COMMENT ON EXTENSION vector' in line:
                print(f"Skipping: {line.strip()}")
                continue

            current.append(line)

            # Detect function definitions
            if 'CREATE FUNCTION' in line or 'CREATE OR REPLACE FUNCTION' in line:
                in_function = True
            if in_function and line.strip().startswith('$$'):
                if '$$;' in line:
                    in_function = False
                    statements.append('\n'.join(current))
                    current = []
            elif not in_function and line.strip().endswith(';'):
                statements.append('\n'.join(current))
                current = []

        # Execute statements
        executed = 0
        skipped = 0
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if not stmt or stmt.startswith('--') or stmt == ';':
                continue

            try:
                cur.execute(stmt)
                executed += 1
                if executed % 100 == 0:
                    print(f"Executed {executed} statements...")
            except Exception as e:
                # Skip errors for optional extensions
                if 'extension' in str(e).lower() or 'vector' in str(e).lower():
                    skipped += 1
                    print(f"Skipped (extension): {str(e)[:100]}")
                else:
                    print(f"Warning: {str(e)[:200]}")
                    skipped += 1

        # Commit
        conn.commit()
        print(f"\nImport complete!")
        print(f"Executed: {executed} statements")
        print(f"Skipped: {skipped} statements")

        # Verify data
        cur.execute("SELECT COUNT(*) FROM books_metadata;")
        count = cur.fetchone()[0]
        print(f"\nBooks in database: {count}")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = import_backup()
    sys.exit(0 if success else 1)
