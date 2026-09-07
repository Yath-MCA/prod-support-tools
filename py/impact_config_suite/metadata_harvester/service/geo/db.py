from __future__ import annotations

import sqlite3
import string
import threading
from contextlib import contextmanager
from typing import Dict

from metadata_harvester.service.config import settings
from metadata_harvester.service.geo.sources.base import LocationRecord

ALPHABET = list(string.ascii_uppercase)

db_lock = threading.Lock()


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.db_path, timeout=30)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS geo_location_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                institution_name TEXT,
                city TEXT,
                district_state TEXT,
                country TEXT,
                alpha_key TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS geo_harvest_progress (
                source TEXT NOT NULL,
                alpha_key TEXT NOT NULL,
                records_fetched INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, alpha_key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_alpha ON geo_location_registry(alpha_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_country ON geo_location_registry(country)")
        conn.commit()


def get_alpha_counts() -> Dict[str, int]:
    """Current row count per alphabet bucket, used to seed the priority heap."""
    with db_lock, get_conn() as conn:
        rows = conn.execute(
            "SELECT alpha_key, COUNT(*) FROM geo_location_registry GROUP BY alpha_key"
        ).fetchall()
    counts = {k: v for k, v in rows}
    return {letter: counts.get(letter, 0) for letter in ALPHABET}


def is_letter_completed(source: str, letter: str) -> bool:
    with db_lock, get_conn() as conn:
        row = conn.execute(
            "SELECT completed FROM geo_harvest_progress WHERE source=? AND alpha_key=?",
            (source, letter),
        ).fetchone()
    return bool(row and row[0])


def mark_progress(source: str, letter: str, fetched_count: int, completed: bool) -> None:
    with db_lock, get_conn() as conn:
        conn.execute("""
            INSERT INTO geo_harvest_progress (source, alpha_key, records_fetched, completed, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source, alpha_key) DO UPDATE SET
                records_fetched = records_fetched + excluded.records_fetched,
                completed = excluded.completed,
                updated_at = CURRENT_TIMESTAMP
        """, (source, letter, fetched_count, int(completed)))
        conn.commit()


def record_exists(source: str, source_id: str) -> bool:
    with db_lock, get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM geo_location_registry WHERE source=? AND source_id=?",
            (source, source_id),
        ).fetchone()
    return row is not None


def insert_record(record: LocationRecord, alpha_key: str) -> bool:
    """Insert a fetched record, relying on the UNIQUE(source, source_id) constraint for dedup."""
    if not record.country:
        return False
    with db_lock, get_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO geo_location_registry
                    (source, source_id, institution_name, city, district_state, country, alpha_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.source,
                record.source_id,
                record.name,
                record.city,
                record.district,
                record.country,
                alpha_key,
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # already present, safe no-op
