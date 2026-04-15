from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.orm import DataCenter, PowerPlant, Substation, TransmissionLine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    counts = {}
    for label, model in [
        ("power_plants", PowerPlant),
        ("substations", Substation),
        ("transmission_lines", TransmissionLine),
        ("data_centers", DataCenter),
    ]:
        counts[label] = int(
            (await session.execute(select(func.count()).select_from(model))).scalar()
            or 0
        )
    return {"status": "ok", "counts": counts}
