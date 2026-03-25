"""Modelo SQLAlchemy para historial de ejecuciones de autopublicacion."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AutomationLog(Base):
    """Registro historico de ejecuciones regulares o evergreen."""

    __tablename__ = "automation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_evergreen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fb_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ig_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_msg: Mapped[str] = mapped_column(Text, default="", nullable=False)
