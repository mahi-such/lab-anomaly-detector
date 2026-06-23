import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "rely_clinical.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

@contextmanager
def get_db_connection():
    """Yields a database connection with WAL mode enabled and Row factory configured."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    print(f"[DB] Executing database setup at: {DB_PATH}")
    with open(SCHEMA_PATH, "r") as f:
        schema_ddl = f.read()
    
    with get_db_connection() as conn:
        conn.executescript(schema_ddl)
        conn.commit()
    print("[DB] Database environment check/creation successful.")

if __name__ == "__main__":
    init_db()