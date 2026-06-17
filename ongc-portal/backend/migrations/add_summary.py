"""Add summary column to files table."""
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5433, user="ongc_user", password="ongc_pass", dbname="ongc_db"
)
cur = conn.cursor()
cur.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS summary TEXT;")
conn.commit()
cur.close()
conn.close()
print("Done: added summary column")
