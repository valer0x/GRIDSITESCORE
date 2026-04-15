from geoalchemy2 import Geography, Geometry
from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PowerPlant(Base):
    __tablename__ = "power_plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str | None] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String(3))
    fuel: Mapped[str | None] = mapped_column(String, index=True)
    capacity_mw: Mapped[float | None] = mapped_column(Float)
    geog = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    __table_args__ = (Index("ix_power_plants_geog", "geog", postgresql_using="gist"),)


class Substation(Base):
    __tablename__ = "substations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str | None] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String)
    voltage_kv: Mapped[float | None] = mapped_column(Float)
    geog = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    __table_args__ = (Index("ix_substations_geog", "geog", postgresql_using="gist"),)


class TransmissionLine(Base):
    __tablename__ = "transmission_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str | None] = mapped_column(String, index=True)
    voltage_kv: Mapped[float | None] = mapped_column(Float)
    geog = mapped_column(
        Geography(geometry_type="LINESTRING", srid=4326), nullable=False
    )
    geom = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))

    __table_args__ = (
        Index("ix_transmission_lines_geog", "geog", postgresql_using="gist"),
    )


class DataCenter(Base):
    __tablename__ = "data_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    operator: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String(3))
    geog = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    __table_args__ = (Index("ix_data_centers_geog", "geog", postgresql_using="gist"),)
