"""Modelo SQLAlchemy para usuarios del panel."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RolPanel


def utcnow() -> datetime:
    """Devuelve la fecha actual en UTC."""

    return datetime.now(timezone.utc)


class PanelUser(Base):
    """Usuario autenticable del panel."""

    __tablename__ = "panel_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RolPanel] = mapped_column(Enum(RolPanel), default=RolPanel.editor, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sesiones: Mapped[list["PanelSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


from app.models.panel_session import PanelSession  # noqa: E402  pylint: disable=wrong-import-position
