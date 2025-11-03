import psycopg2
import getpass

# Neon DB credentials from .streamlit/secrets.toml
DB_HOST = "ep-muddy-heart-a4ht7hiy-pooler.us-east-1.aws.neon.tech"
DB_PORT = 5432
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_DrSgJpKb3eh1"

INSPECTION_ID = 24

conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
cur = conn.cursor()

print(f'Inspection Items for inspection_id={INSPECTION_ID}:')
cur.execute('SELECT id, category, item, rating, notes FROM inspection_items WHERE inspection_id = %s', (INSPECTION_ID,))
items = cur.fetchall()
for item in items:
    print(item)
    item_id = item[0]
    cur.execute('SELECT id, photo FROM inspection_item_photos WHERE inspection_item_id = %s', (item_id,))
    photos = cur.fetchall()
    print(f'  Photos: {[f"id={p[0]}, bytes={len(p[1]) if p[1] else 0}" for p in photos]}')
cur.close()
conn.close()
print('Done.')
