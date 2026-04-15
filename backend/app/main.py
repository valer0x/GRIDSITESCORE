from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_conf import configure_logging, get_logger
from app.routes import analyze, features, health

configure_logging()
log = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app.startup")
    yield
    log.info("app.shutdown")


app = FastAPI(
    title="Infrastructure Due Diligence Tool",
    description=(
        "Early-stage site analysis for energy, data center, and industrial "
        "projects using public geospatial datasets. Returns a weighted, "
        "explainable 0-100 score with per-rule reasoning."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(features.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "GridSiteScore",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/analyze?lat=&lng=",
            "/analyze/batch",
            "/analyze/report.pdf?lat=&lng=",
            "/features/substations?bbox=",
            "/features/transmission_lines?bbox=",
            "/features/power_plants?bbox=",
            "/features/data_centers",
        ],
    }
