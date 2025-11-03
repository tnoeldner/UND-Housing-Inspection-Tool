import psycopg2
import streamlit as st

def get_conn():
    db = st.secrets["database"]
    return psycopg2.connect(
        dbname=db["NEON_DB_NAME"],
        user=db["NEON_DB_USER"],
        password=db["NEON_DB_PASSWORD"],
        host=db["NEON_DB_HOST"],
        port=db["NEON_DB_PORT"]
    )

conn = get_conn()
cur = conn.cursor()

# Show table columns for inspections
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'inspections'")
inspections_cols = cur.fetchall()
st.write("Inspections table columns:", inspections_cols)

# Show table columns for inspection_items
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'inspection_items'")
items_cols = cur.fetchall()
st.write("Inspection_items table columns:", items_cols)

# Show sample data
cur.execute("SELECT * FROM inspections LIMIT 3")
inspections_sample = cur.fetchall()
st.write("Sample inspections:", inspections_sample)

cur.execute("SELECT * FROM inspection_items LIMIT 5")
items_sample = cur.fetchall()
st.write("Sample inspection_items:", items_sample)

cur.close()
conn.close()
