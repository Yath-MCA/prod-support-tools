from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, EmailStr

from metadata_harvester.service.crossref import db
from metadata_harvester.service.crossref.harvester import harvest_crossref_task

router = APIRouter()


class HarvestRequest(BaseModel):
    crossref_token: str
    user_agent_email: EmailStr
    rows_per_request: Optional[int] = 100
    max_total_records: Optional[int] = 1000


@router.post("/harvest/start", status_code=202)
def start_harvest(payload: HarvestRequest, background_tasks: BackgroundTasks):
    """Triggers the asynchronous harvesting pipeline using paid API credentials."""
    background_tasks.add_task(
        harvest_crossref_task,
        token=payload.crossref_token,
        email=payload.user_agent_email,
        rows=payload.rows_per_request,
        limit=payload.max_total_records,
    )
    return {"status": "Execution Injected", "message": "The pipeline task has been safely queued in the background."}


@router.get("/locations")
def get_stored_locations(
    country: Optional[str] = Query(None, description="Query and filter local entities by country name matching pattern"),
    limit: int = Query(50, le=500),
):
    """Fetches cached relational rows out of the crossref_location_registry table."""
    return db.query_locations(country, limit)
