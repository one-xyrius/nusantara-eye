"""SQLite cache dengan TTL. Ringan, tanpa dependensi eksternal."""
import json
import os
import sqlite3
import time

DB_PATH = os.environ.get("NE_DB", os.path.join(os.path.dirname(__file__), "..", "data", "cache.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    ttl        INTEGER NOT NULL
);
"""


def connect(path=None):
    p = os.path.abspath(path or DB_PATH)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    conn = sqlite3.connect(p)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def get(conn, key):
    row = conn.execute("SELECT payload, created_at, ttl FROM cache WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    payload, created_at, ttl = row
    if ttl > 0 and (time.time() - created_at) > ttl:
        return None
    return json.loads(payload)


def put(conn, key, value, ttl=3600):
    conn.execute(
        "INSERT INTO cache (key, payload, created_at, ttl) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, created_at=excluded.created_at, ttl=excluded.ttl",
        (key, json.dumps(value, ensure_ascii=False), int(time.time()), int(ttl)),
    )
    conn.commit()


def purge_expired(conn):
    now = int(time.time())
    cur = conn.execute("DELETE FROM cache WHERE ttl > 0 AND (? - created_at) > ttl", (now,))
    conn.commit()
    return cur.rowcount
