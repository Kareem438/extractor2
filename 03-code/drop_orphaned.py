import psycopg2
from psycopg2 import sql

conn = psycopg2.connect(host='localhost', port=5432, database='knowledge_extraction_2', user='postgres', password='postgres')
cursor = conn.cursor()

cursor.execute('SELECT table_prefix FROM books_metadata')
existing = {row[0] for row in cursor.fetchall()}
print(f'Existing prefixes: {existing}')

cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND (tablename LIKE 'book%%' OR tablename LIKE 'raw_book%%') AND tablename != 'books_metadata'")
tables = [row[0] for row in cursor.fetchall()]
print(f'Total tables: {len(tables)}')

suffixes = ['_attribute_keys', '_hierarchy', '_images', '_knowledge_units', '_level1_titles', '_level2_titles', '_pages', '_pipeline_config', '_processing_state', '_settings', '_step_progress', '_task_queue', '_diagram_images', '_paragraph_images', '_layout_detections']

orphaned = []
for t in tables:
    name = t[4:] if t.startswith('raw_') else t
    for s in suffixes:
        if name.endswith(s):
            prefix = name[:-len(s)]
            if prefix not in existing:
                orphaned.append(t)
            break

print(f'Orphaned tables: {len(orphaned)}')
for t in orphaned:
    cursor.execute(sql.SQL('DROP TABLE IF EXISTS {} CASCADE').format(sql.Identifier(t)))
    print(f'Dropped: {t}')

conn.commit()
conn.close()
print('Done!')
