"""Modelo SQLAlchemy para publicaciones por canal."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EstadoPublicacion


def utcnow() -> datetime:
    """Devuelve la fecha actual en UTC."""

    return datetime.now(timezone.utc)


class Publicacion(Base):
    """Publicación de una noticia en un canal específico."""

    __tablename__ = "publicaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    noticia_id: Mapped[int] = mapped_column(ForeignKey("noticias.id"), nullable=False, index=True)
    canal_id: Mapped[int] = mapped_column(ForeignKey("canales.id"), nullable=False, index=True)
    contenido: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagen_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[EstadoPublicacion] = mapped_column(
        Enum(EstadoPublicacion),
        default=EstadoPublicacion.pendiente,
        nullable=False,
    )
    auto_publicar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publicado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    noticia: Mapped["Noticia"] = relationship(back_populates="publicaciones")
    canal: Mapped["Canal"] = relationship(back_populates="publicaciones")


from app.models.canal import Canal  # noqa: E402  pylint: disable=wrong-import-position
from app.models.noticia import Noticia  # noqa: E402  pylint: disable=wrong-import-position
