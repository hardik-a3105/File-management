"""Generate summaries for existing PDFs that have search_text but no summary."""
import psycopg2
import sys
sys.path.insert(0, "/Users/ruchatejaskumargandhi/Desktop/ONGC 3/ongc-portal/backend")
from app.utils.summarize import summarize

conn = psycopg2.connect(
    host="localhost", port=5433, user="ongc_user", password="ongc_pass", dbname="ongc_db"
)
cur = conn.cursor()
cur.execute("SELECT id, search_text FROM files WHERE search_text IS NOT NULL;")
rows = cur.fetchall()
print(f"Found {len(rows)} files needing summary")

for fid, txt in rows:
    if not txt or not txt.strip():
        continue
    try:
        s = summarize(txt, max_sentences=5)
        if s:
            cur.execute("UPDATE files SET summary = %s WHERE id = %s;", (s, fid))
            conn.commit()
            print(f"  File {fid}: {len(s)} chars summary generated")
        else:
            print(f"  File {fid}: empty summary (text too short?)")
    except Exception as e:
        conn.rollback()
        print(f"  File {fid}: ERROR {e}")

cur.close()
conn.close()
print("Done")
