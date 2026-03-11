import uvicorn

try:
    # Works when executed as module: python -m search_service.run
    from .app.app import app
    _app_ref = "search_service.app.app:app"
except ImportError:
    # Fallback for direct script execution from search_service folder.
    from app.app import app
    _app_ref = "app.app:app"

if __name__ == "__main__":
    uvicorn.run(_app_ref, host="0.0.0.0", port=7000, reload=True)
