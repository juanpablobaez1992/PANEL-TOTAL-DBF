"""Modelo SQLAlchemy para los canales de publicación."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TipoCanal
from app.utils.credentials import decrypt_config

if TYPE_CHECKING:
    from app.models.publicacion import Publicacion


class Canal(Base):
    """Canal configurable de publicación."""

    __tablename__ = "canales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[TipoCanal] = mapped_column(Enum(TipoCanal), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_publicar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    publicaciones: Mapped[list["Publicacion"]] = relationship(
        back_populates="canal",
        cascade="all, delete-orphan",
    )

    @property
    def config(self) -> dict[str, object]:
        """Devuelve la configuración descifrada del canal."""

        return decrypt_config(self.config_json)
