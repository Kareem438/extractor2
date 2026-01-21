import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='postgres',
    database='knowledge_extraction'
)
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
tables = [row[0] for row in cur.fetchall()]
print(f'Tables found: {len(tables)}')
for table in tables:
    print(f'  - {table}')

if 'books_metadata' in tables:
    cur.execute("SELECT COUNT(*) FROM books_metadata;")
    count = cur.fetchone()[0]
    print(f'\nBooks in books_metadata: {count}')

cur.close()
conn.close()
