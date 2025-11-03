import streamlit as st
from psycopg2.extras import RealDictCursor
import psycopg2

def get_conn():
    db = st.secrets["database"]
    return psycopg2.connect(
        dbname=db["NEON_DB_NAME"],
        user=db["NEON_DB_USER"],
        password=db["NEON_DB_PASSWORD"],
        host=db["NEON_DB_HOST"],
        port=db["NEON_DB_PORT"]
    )

st.header("Inspection Items Debug")
edit_id = st.text_input("Inspection ID to debug:")
if edit_id:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM inspection_items WHERE inspection_id = %s", (edit_id,))
    items = cur.fetchall()
    st.write(f"Loaded {len(items)} items for inspection_id={edit_id}")
    for item in items:
        st.json(item)
    cur.close()
    conn.close()
else:
    st.info("Enter an inspection ID above to debug item loading.")
