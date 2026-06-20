import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from ..services.file_search import copy_files_for_batch, fetch_doc_ids, search_in_batch


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class FetchRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=365)
    date_str: Optional[str] = None
    root_folder: Optional[str] = None
    output_folder: Optional[str] = None


class CopyRequest(BaseModel):
    batch_file: str
    root_folder: Optional[str] = None


class SearchRequest(BaseModel):
    batch_folder: str
    search_terms: list


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ui", response_class=HTMLResponse)
async def ui_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def _client_error(exc):
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, OSError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/fetch")
def api_fetch(req: FetchRequest):
    if req.date_str:
        try:
            from_date = datetime.datetime.strptime(req.date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
            ) from exc
    else:
        from_date = datetime.datetime.now() - datetime.timedelta(days=req.days)
        from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        batches, output_folder = fetch_doc_ids(
            from_date,
            root_folder=req.root_folder,
            output_folder=req.output_folder,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        _client_error(exc)
    return {"batches": batches, "output_folder": output_folder}


@router.post("/copy")
def api_copy(req: CopyRequest):
    if not req.batch_file.strip():
        raise HTTPException(status_code=400, detail="Batch file is required")
    try:
        copied, skipped, total, destination = copy_files_for_batch(
            req.batch_file, root_folder=req.root_folder
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        _client_error(exc)
    return {
        "copied": copied,
        "skipped": skipped,
        "total": total,
        "destination": destination,
    }


@router.post("/search")
def api_search(req: SearchRequest):
    if not req.batch_folder.strip():
        raise HTTPException(status_code=400, detail="Batch folder is required")
    try:
        results = search_in_batch(req.batch_folder, req.search_terms)
    except (FileNotFoundError, ValueError, OSError) as exc:
        _client_error(exc)
    return {"results": results}
