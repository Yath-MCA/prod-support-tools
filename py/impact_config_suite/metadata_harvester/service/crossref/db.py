from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional

from metadata_harvester.service.config import settings


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.db_path, timeout=30)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initializes the crossref harvester's table. Called explicitly by service/app.py,
    NOT at import time (unlike the original fetchCrossRef/app.py), so import order
    never matters and tests can point at a temp DB before this runs."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crossref_location_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_affiliation TEXT UNIQUE,
                city TEXT,
                district_state TEXT,
                country TEXT,
                doi_source TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def insert_record(raw_affiliation: str, city: Optional[str], district: Optional[str],
                   country: Optional[str], doi: Optional[str]) -> bool:
    with get_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO crossref_location_registry
                    (raw_affiliation, city, district_state, country, doi_source)
                VALUES (?, ?, ?, ?, ?)
            """, (raw_affiliation, city, district, country, doi))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # already present, safe no-op


def query_locations(country: Optional[str], limit: int) -> list[dict]:
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if country:
            cursor.execute(
                "SELECT * FROM crossref_location_registry WHERE country LIKE ? LIMIT ?",
                (f"%{country}%", limit),
            )
        else:
            cursor.execute("SELECT * FROM crossref_location_registry LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
