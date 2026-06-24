import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "rely_clinical.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

_alias_cache: dict[str, str] = {}

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
    with open(SCHEMA_PATH, "r") as f:
        schema_ddl = f.read()
    with get_db_connection() as conn:
        conn.executescript(schema_ddl)
        conn.commit()

def build_alias_cache():
    """Builds O(1) in-memory cache mapping normalized aliases to canonical codes."""
    global _alias_cache
    _alias_cache.clear()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT canonical_code, aliases FROM biomarker_registry WHERE is_active = 1").fetchall()
        for row in rows:
            canonical = row["canonical_code"]
            _alias_cache[canonical.upper()] = canonical
            if row["aliases"]:
                for alias in row["aliases"].split(","):
                    normalized = alias.strip().upper()
                    if normalized:
                        _alias_cache[normalized] = canonical

def find_registry_by_alias(raw_name: str) -> dict | None:
    canonical = _alias_cache.get(raw_name.strip().upper())
    if not canonical:
        return None
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM biomarker_registry WHERE canonical_code = ?", (canonical,)).fetchone()
        return dict(row) if row else None

def insert_audit_log(log_data: dict):
    query = """
        INSERT INTO audit_log (
            request_id, lab_ref, raw_name, canonical_code, value_num, unit, 
            ref_min, ref_max, z_score, baseline_confidence, severity, 
            is_panic, should_send_sms, resolution_status, reason
        ) VALUES (
            :request_id, :lab_ref, :raw_name, :canonical_code, :value_num, :unit, 
            :ref_min, :ref_max, :z_score, :baseline_confidence, :severity, 
            :is_panic, :should_send_sms, :resolution_status, :reason
        )
    """
    with get_db_connection() as conn:
        conn.execute(query, log_data)
        conn.commit()

def update_baseline(canonical_code: str, new_value: float):
    """Recursively updates Welford's algorithm statistics."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT baseline_count, baseline_mean, baseline_m2 FROM biomarker_registry WHERE canonical_code=?", (canonical_code,)).fetchone()
        if not row:
            return
            
        n = row["baseline_count"] + 1
        mean = row["baseline_mean"] or 0.0
        m2 = row["baseline_m2"] or 0.0
        
        delta = new_value - mean
        mean += delta / n
        m2 += delta * (new_value - mean)
        std = (m2 / n) ** 0.5 if n > 1 else 0.0
        
        confidence = "none" if n < 30 else "low" if n < 100 else "moderate" if n < 300 else "full"
        
        conn.execute("""
            UPDATE biomarker_registry 
            SET baseline_count=?, baseline_mean=?, baseline_m2=?, baseline_std=?, baseline_confidence=?
            WHERE canonical_code=?
        """, (n, mean, m2, std, confidence, canonical_code))
        conn.commit()