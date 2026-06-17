"""Backfill embeddings for existing PDFs using psycopg2 sync connection via Docker port."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from app.utils.embeddings import generate_embedding

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    user="ongc_user",
    password="ongc_pass",
    dbname="ongc_db",
)
cur = conn.cursor()

cur.execute(
    "SELECT id, file_name, search_text FROM files WHERE search_text IS NOT NULL AND search_text != '' AND embedding IS NULL"
)
rows = cur.fetchall()
print(f"Files to backfill: {len(rows)}")

for fid, fname, text in rows:
    emb = generate_embedding(text)
    if emb:
        vec_str = "[" + ",".join(str(v) for v in emb) + "]"
        cur.execute("UPDATE files SET embedding = %s::vector WHERE id = %s", (vec_str, fid))
        conn.commit()
        print(f"  {fid}: {fname}")
    else:
        print(f"  {fid}: {fname} -> no embedding (empty text)")

cur.close()
conn.close()
print("Done.")
