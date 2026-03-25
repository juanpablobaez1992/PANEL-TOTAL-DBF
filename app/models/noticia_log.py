"""Registro de auditoría de cambios en noticias."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NoticiaLog(Base):
    """Entrada de auditoría para una noticia: quién hizo qué y cuándo."""

    __tablename__ = "noticia_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    noticia_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("noticias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Quién realizó la acción (username del panel o "sistema" para scheduler/webhook)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False, default="sistema")
    # Acción realizada (ej: "crear", "generar", "aprobar", "publicar", "programar")
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    # Detalle opcional (ej: estado anterior→nuevo, canal publicado, error)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
