from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import datetime
from pathlib import Path
from ..services.file_search import fetch_doc_ids, copy_files_for_batch, search_in_batch

router = APIRouter()

# Setup templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

class FetchRequest(BaseModel):
    days: int = 7
    date_str: str = None
    root_folder: str = None  # Optional custom root folder

class CopyRequest(BaseModel):
    batch_file: str
    root_folder: str = None  # Optional custom root folder

class SearchRequest(BaseModel):
    batch_folder: str
    search_terms: list

# ===================================
# UI ROUTE
# ===================================

@router.get("/ui", response_class=HTMLResponse)
async def ui_page(request: Request):
    """Serve the main UI page"""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect root to UI page"""
    return templates.TemplateResponse("index.html", {"request": request})

# ===================================
# API ROUTES
# ===================================


@router.post("/fetch")
def api_fetch(req: FetchRequest):
    print(f"\n📨 API REQUEST - /fetch")
    print(f"   Parameters: days={req.days}, date_str={req.date_str}, root_folder={req.root_folder}")
    
    if req.date_str:
        try:
            from_date = datetime.datetime.strptime(req.date_str, "%Y-%m-%d")
        except ValueError:
            print(f"   ❌ Invalid date format: {req.date_str}")
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        from_date = datetime.datetime.now() - datetime.timedelta(days=req.days)
        from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Pass custom root folder if provided
    batches, output_folder = fetch_doc_ids(from_date, root_folder=req.root_folder)
    
    print(f"   ✅ Response: {len(batches)} batch files generated")
    return {"batches": batches, "output_folder": output_folder}

@router.post("/copy")
def api_copy(req: CopyRequest):
    print(f"\n📨 API REQUEST - /copy")
    print(f"   Batch file: {req.batch_file}")
    print(f"   Root folder: {req.root_folder}")
    
    try:
        copied, skipped, total, dest = copy_files_for_batch(req.batch_file, root_folder=req.root_folder)
        print(f"   ✅ Response: {copied} copied, {skipped} skipped, {total} total")
        return {
            "copied": copied,
            "skipped": skipped,
            "total": total,
            "destination": dest
        }
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
def api_search(req: SearchRequest):
    print(f"\n📨 API REQUEST - /search")
    print(f"   Batch folder: {req.batch_folder}")
    print(f"   Search terms: {req.search_terms}")
    
    results = search_in_batch(req.batch_folder, req.search_terms)
    
    print(f"   ✅ Response: {len(results)} results found")
    return {"results": results}

