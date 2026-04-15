from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import PowerPlant
from app.models.schemas import EnergySection
from app.utils.geo import is_renewable, shannon_diversity
from app.utils.queries import st_dwithin


async def compute_energy(
    session: AsyncSession, lat: float, lng: float
) -> EnergySection:
    stmt = (
        select(
            PowerPlant.fuel,
            func.count().label("n"),
            func.coalesce(func.sum(PowerPlant.capacity_mw), 0.0).label("cap"),
        )
        .where(st_dwithin(PowerPlant.geog, lat, lng, 50_000))
        .group_by(PowerPlant.fuel)
    )
    rows = (await session.execute(stmt)).all()

    total_plants = sum(int(r.n) for r in rows)
    total_cap = float(sum(float(r.cap or 0.0) for r in rows))
    cap_by_fuel: dict[str, float] = {
        (r.fuel or "unknown").lower(): float(r.cap or 0.0) for r in rows
    }
    mix_pct = (
        {k: round(100.0 * v / total_cap, 2) for k, v in cap_by_fuel.items()}
        if total_cap > 0
        else {}
    )
    renewable_cap = sum(v for k, v in cap_by_fuel.items() if is_renewable(k))
    renewable_share = (renewable_cap / total_cap) if total_cap > 0 else 0.0

    return EnergySection(
        plants_50km=total_plants,
        total_capacity_mw_50km=round(total_cap, 2),
        mix_pct=mix_pct,
        renewable_share=round(renewable_share, 4),
        fuel_diversity_shannon=round(shannon_diversity(cap_by_fuel), 4),
    )
