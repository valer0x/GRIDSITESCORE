from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.schemas import AnalysisResponse, BatchRequest, BatchResponse
from app.services.orchestrator import analyze_point
from app.services.report import render_report_pdf

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.get("", response_model=AnalysisResponse)
async def analyze(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_session),
) -> AnalysisResponse:
    return await analyze_point(session, lat, lng)


@router.post("/batch", response_model=BatchResponse)
async def analyze_batch(
    payload: BatchRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchResponse:
    results = []
    for p in payload.points:
        results.append(await analyze_point(session, p.lat, p.lng))
    return BatchResponse(results=results)


@router.get("/report.pdf", response_class=Response)
async def analyze_report(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_session),
) -> Response:
    analysis = await analyze_point(session, lat, lng)
    pdf = render_report_pdf(analysis)
    filename = f"due_diligence_{lat:.4f}_{lng:.4f}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
