from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_conf import configure_logging, get_logger
from app.routes import analyze, health

configure_logging()
log = get_logger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "Infrastructure Due Diligence Tool",
        "docs": "/docs",
        "endpoints": ["/health", "/analyze?lat=&lng=", "/analyze/batch"],
    }
