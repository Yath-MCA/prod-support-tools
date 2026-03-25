from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.routes.search_routes import router as search_router

# Get the app directory path
APP_DIR = Path(__file__).parent

def create_app():
    app = FastAPI(title="IMPACT Search API")

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    # Include Routes
    app.include_router(search_router)

    return app

app = create_app()
