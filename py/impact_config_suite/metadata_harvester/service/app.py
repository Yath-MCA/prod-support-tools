from __future__ import annotations

from fastapi import FastAPI

from metadata_harvester.service.crossref import db as crossref_db
from metadata_harvester.service.crossref.routes import router as crossref_router
from metadata_harvester.service.geo import db as geo_db
from metadata_harvester.service.geo.routes import router as geo_router

app = FastAPI(
    title="Metadata Harvester",
    description=(
        "Combines two metadata harvesters behind one API: a paid-token "
        "Crossref DOI/affiliation harvester, and a free-tier ROR + OpenAlex "
        "alphabetical geo harvester. See /docs for interactive Swagger UI."
    ),
    version="1.0.0",
)

crossref_db.init_db()
geo_db.init_db()

app.include_router(crossref_router, prefix="/crossref", tags=["crossref"])
app.include_router(geo_router, prefix="/geo", tags=["geo"])


@app.get("/health")
def health():
    return {"status": "ok"}
