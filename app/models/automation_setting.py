"""Modelo SQLAlchemy para configuraciones del modulo automation."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AutomationSetting(Base):
    """Clave/valor JSON para settings operativos del bot."""

    __tablename__ = "automation_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, default="null", nullable=False)
