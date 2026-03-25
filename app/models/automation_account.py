"""Modelo SQLAlchemy para cuentas externas de autopublicacion."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.credentials import decrypt_config, encrypt_config


class AutomationAccount(Base):
    """Cuenta extra para publicar en Facebook o Instagram."""

    __tablename__ = "automation_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(120), nullable=False)
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def access_token(self) -> str:
        """Devuelve el token descifrado."""

        return str(decrypt_config(self.access_token_enc).get("access_token", ""))

    def set_access_token(self, token: str) -> None:
        """Cifra y guarda el token."""

        self.access_token_enc = encrypt_config({"access_token": token})

    @property
    def token_hint(self) -> str:
        """Devuelve un hint seguro para UI."""

        token = self.access_token
        if len(token) < 8:
            return "configurado"
        return f"{token[:4]}...{token[-4:]}"
