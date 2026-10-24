"""
api/main.py
-----------
FastAPI application entry point for WayPointAI.

Run locally:
    uvicorn api.main:app --reload

The interactive docs are available at http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from .routes import router

app = FastAPI(
    title="WayPointAI API",
    description=(
        "Gap analysis API for WayPointAI (Component 3). "
        "Accepts a parsed resume and a role profile, returns a structured "
        "gap analysis result consumed by the roadmap engine (Component 4) "
        "and the frontend (Component 5)."
    ),
    version="0.1.0",
)

app.include_router(router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
