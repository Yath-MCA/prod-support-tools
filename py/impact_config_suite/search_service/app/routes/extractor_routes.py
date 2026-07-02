"""FastAPI routes for element extraction operations."""

import uuid
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.element_extraction_service import extraction_service

router = APIRouter(prefix="/extract", tags=["element-extraction"])

# In-memory job storage (in production, use Redis/database)
job_store: Dict[str, Dict] = {}


# Request/Response Models

class ExtractFolderRequest(BaseModel):
    source_path: str = Field(..., description="Path to folder containing files to scan")
    query_type: str = Field(..., description="Query type: Tag Name, CSS Selector, or XPath")
    queries: List[str] = Field(..., description="List of queries to execute")
    recursive: bool = Field(default=True, description="Scan subdirectories recursively")
    extensions: Optional[List[str]] = Field(default=None, description="File extensions to scan")
    filename_filter: Optional[str] = Field(default=None, description="Filename pattern filter")
    dtd_filter: Optional[str] = Field(default=None, description="DTD type filter")
    client_filter: Optional[str] = Field(default=None, description="Client filter")
    month_filter: str = Field(default="All Time", description="Modified date filter")
    custom_month: str = Field(default="", description="Custom month string (MM-YYYY or YYYY-MM) when month_filter is 'Custom'")
    batch_size: int = Field(default=0, ge=0, description="Batch size (0 = no limit)")
    batch_offset: int = Field(default=0, ge=0, description="Batch offset for resuming")
    use_parallel: bool = Field(default=True, description="Use parallel processing")
    max_workers: Optional[int] = Field(default=None, ge=1, le=16, description="Number of parallel workers")
    generate_reports: bool = Field(default=False, description="Generate HTML and CSV reports")
    output_dir: Optional[str] = Field(default=None, description="Directory for report output")
    attr_name: str = Field(default="", description="Attribute name filter (for Tag Name queries)")
    attr_val: str = Field(default="", description="Attribute value filter (for Tag Name queries)")


class ExtractFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to single file to extract from")
    query_type: str = Field(..., description="Query type: Tag Name, CSS Selector, or XPath")
    queries: List[str] = Field(..., description="List of queries to execute")
    attr_name: str = Field(default="", description="Attribute name filter (for Tag Name queries)")
    attr_val: str = Field(default="", description="Attribute value filter (for Tag Name queries)")


class ExtractionResponse(BaseModel):
    status: str
    source_path: str
    query_type: str
    queries: List[str]
    total_files: int
    total_matches: int
    has_more: bool
    next_offset: int
    results: List[Dict[str, Any]]
    report_paths: Optional[List[str]] = None
    processing_time_ms: int


class ExtractionJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _client_error(exc):
    """Convert exceptions to HTTP exceptions."""
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, OSError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/folder")
def extract_from_folder(req: ExtractFolderRequest):
    """
    Extract elements from files in a folder.

    Synchronous endpoint for smaller extractions.
    For large folders, use /folder/async endpoint.
    """
    try:
        start_time = time.time()

        result = extraction_service.extract_from_folder(
            source_path=req.source_path,
            query_type=req.query_type,
            queries=req.queries,
            recursive=req.recursive,
            extensions=req.extensions,
            filename_filter=req.filename_filter,
            dtd_filter=req.dtd_filter,
            client_filter=req.client_filter,
            month_filter=req.month_filter,
            custom_month=req.custom_month,
            batch_size=req.batch_size,
            batch_offset=req.batch_offset,
            use_parallel=req.use_parallel,
            max_workers=req.max_workers,
            output_dir=req.output_dir if req.generate_reports else None,
            attr_name=req.attr_name,
            attr_val=req.attr_val
        )

        processing_time = int((time.time() - start_time) * 1000)

        # Convert all_selector_results to list format
        results_list = []
        for selector_result in result.get("all_selector_results", []):
            results_list.append({
                "query": selector_result.get("query_val", ""),
                "query_type": selector_result.get("query_type", ""),
                "matches": selector_result.get("scan_results", {}),
                "total_matches": selector_result.get("total_matches", 0),
                "total_files": selector_result.get("total_files", 0)
            })

        return ExtractionResponse(
            status="success",
            source_path=req.source_path,
            query_type=req.query_type,
            queries=req.queries,
            total_files=result.get("total_files", 0),
            total_matches=result.get("total_matches", 0),
            has_more=result.get("has_more", False),
            next_offset=result.get("next_offset", 0),
            results=results_list,
            report_paths=result.get("report_paths"),
            processing_time_ms=processing_time
        )

    except (FileNotFoundError, ValueError, OSError) as exc:
        _client_error(exc)


@router.post("/folder/async", response_model=ExtractionJobResponse)
def extract_from_folder_async(
    req: ExtractFolderRequest,
    background_tasks: BackgroundTasks
):
    """
    Start async element extraction for large folders.

    Returns immediately with job_id. Poll /job/{job_id}/status for progress.
    """
    job_id = str(uuid.uuid4())

    job_store[job_id] = {
        "status": "pending",
        "progress": 0,
        "request": req.model_dump(),
        "result": None,
        "error": None
    }

    background_tasks.add_task(
        _run_async_extraction,
        job_id,
        req
    )

    return ExtractionJobResponse(
        job_id=job_id,
        status="pending",
        message="Extraction job started. Poll /job/{job_id}/status for progress."
    )


@router.get("/job/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Get status and progress of an async extraction job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        result=job.get("result"),
        error=job.get("error")
    )


@router.post("/file")
def extract_from_file(req: ExtractFileRequest):
    """Extract elements from a single file."""
    try:
        result = extraction_service.extract_from_file(
            file_path=req.file_path,
            query_type=req.query_type,
            queries=req.queries,
            attr_name=req.attr_name,
            attr_val=req.attr_val
        )
        return result
    except (FileNotFoundError, ValueError, OSError) as exc:
        _client_error(exc)


def _run_async_extraction(job_id: str, req: ExtractFolderRequest):
    """Background task runner for async extraction."""
    job_store[job_id]["status"] = "running"

    try:
        result = extraction_service.extract_from_folder(
            source_path=req.source_path,
            query_type=req.query_type,
            queries=req.queries,
            recursive=req.recursive,
            extensions=req.extensions,
            filename_filter=req.filename_filter,
            dtd_filter=req.dtd_filter,
            client_filter=req.client_filter,
            month_filter=req.month_filter,
            custom_month=req.custom_month,
            batch_size=req.batch_size,
            batch_offset=req.batch_offset,
            use_parallel=req.use_parallel,
            max_workers=req.max_workers,
            output_dir=req.output_dir if req.generate_reports else None,
            attr_name=req.attr_name,
            attr_val=req.attr_val
        )

        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = result
        job_store[job_id]["progress"] = 100

    except Exception as e:
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["progress"] = 0
