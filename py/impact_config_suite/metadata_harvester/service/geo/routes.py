from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, EmailStr

from metadata_harvester.service.config import settings
from metadata_harvester.service.geo import db
from metadata_harvester.service.geo.scheduler import run_harvest
from metadata_harvester.service.geo.sources import DEFAULT_SOURCES

router = APIRouter()


class HarvestAllRequest(BaseModel):
    contact_email: Optional[EmailStr] = None
    num_workers: Optional[int] = None


@router.post("/harvest/start-all", status_code=202)
def start_harvest_all(payload: HarvestAllRequest, background_tasks: BackgroundTasks):
    """Kicks off the concurrent, dynamically-balanced A-Z harvest across all sources."""
    email = payload.contact_email or settings.contact_email
    if not email:
        raise HTTPException(
            status_code=400,
            detail="contact_email is required (in the request body, or via the "
                   "METADATA_HARVESTER_CONTACT_EMAIL env var).",
        )
    num_workers = payload.num_workers or settings.num_workers

    background_tasks.add_task(run_harvest, DEFAULT_SOURCES, email, num_workers)
    return {
        "status": "queued",
        "message": f"Dynamic alphabetical harvest started with {num_workers} workers.",
        "sources": list(DEFAULT_SOURCES.keys()),
    }


@router.get("/progress")
def get_progress():
    """Per-letter, per-source completion status."""
    with db.get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM geo_harvest_progress ORDER BY alpha_key, source"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/locations")
def get_locations(
    country: Optional[str] = Query(None, description="Substring filter on country"),
    alpha: Optional[str] = Query(None, description="Single-letter bucket filter, e.g. 'M'"),
    source: Optional[str] = Query(None, description="Filter by source: 'ror' or 'openalex'"),
    limit: int = Query(100, le=1000),
):
    with db.get_conn() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM geo_location_registry WHERE 1=1"
        args = []
        if country:
            q += " AND country LIKE ?"
            args.append(f"%{country}%")
        if alpha:
            q += " AND alpha_key = ?"
            args.append(alpha.upper())
        if source:
            q += " AND source = ?"
            args.append(source)
        q += " ORDER BY alpha_key LIMIT ?"
        args.append(limit)
        rows = conn.execute(q, args).fetchall()
        return [dict(r) for r in rows]


@router.get("/stats")
def get_stats():
    """Coverage count per letter, useful to watch the dynamic balancing in action."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT alpha_key, source, COUNT(*) as cnt FROM geo_location_registry "
            "GROUP BY alpha_key, source ORDER BY alpha_key"
        ).fetchall()
        return [{"alpha_key": r[0], "source": r[1], "count": r[2]} for r in rows]
