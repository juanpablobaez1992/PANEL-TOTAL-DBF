"""Modelo SQLAlchemy para noticias."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CategoriaNoticia, EstadoNoticia, UrgenciaNoticia

if TYPE_CHECKING:
    from app.models.publicacion import Publicacion


def utcnow() -> datetime:
    """Devuelve la fecha actual en UTC."""

    return datetime.now(timezone.utc)


class Noticia(Base):
    """Noticia principal ingresada por el periodista."""

    __tablename__ = "noticias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hecho: Mapped[str] = mapped_column(Text, nullable=False)
    lugar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_hecho: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    categoria: Mapped[CategoriaNoticia] = mapped_column(
        Enum(CategoriaNoticia),
        default=CategoriaNoticia.general,
        nullable=False,
    )
    urgencia: Mapped[UrgenciaNoticia] = mapped_column(
        Enum(UrgenciaNoticia),
        default=UrgenciaNoticia.normal,
        nullable=False,
    )
    imagen_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    titular: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bajada: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuerpo: Mapped[str | None] = mapped_column(Text, nullable=True)
    generado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aprobado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    programada_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    estado: Mapped[EstadoNoticia] = mapped_column(
        Enum(EstadoNoticia),
        default=EstadoNoticia.borrador,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    publicaciones: Mapped[list["Publicacion"]] = relationship(
        back_populates="noticia",
        cascade="all, delete-orphan",
    )
