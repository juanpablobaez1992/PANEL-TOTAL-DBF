"""Configuración centralizada de la aplicación."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_env_file(path: Path) -> dict[str, str]:
    """Lee un archivo .env simple y devuelve sus pares clave/valor."""

    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@lru_cache(maxsize=1)
def _legacy_env_values() -> dict[str, str]:
    """Carga valores legacy desde AUTOPUBLICATE/.env si existe."""

    return _read_env_file(Path("AUTOPUBLICATE/.env"))


class Settings(BaseSettings):
    """Settings globales leídos desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Despacho", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(default="cambiar-esto", alias="SECRET_KEY")
    database_url: str = Field(default="sqlite:///./despacho.db", alias="DATABASE_URL")

    ai_provider: str = Field(default="gemini", alias="AI_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    claude_api_key: str = Field(default="", alias="CLAUDE_API_KEY")

    wp_url: str = Field(default="", alias="WP_URL")
    wp_user: str = Field(default="", alias="WP_USER")
    wp_app_password: str = Field(default="", alias="WP_APP_PASSWORD")

    meta_page_id: str = Field(default="", alias="META_PAGE_ID")
    meta_access_token: str = Field(default="", alias="META_ACCESS_TOKEN")
    meta_ig_account_id: str = Field(default="", alias="META_IG_ACCOUNT_ID")

    twitter_api_key: str = Field(default="", alias="TWITTER_API_KEY")
    twitter_api_secret: str = Field(default="", alias="TWITTER_API_SECRET")
    twitter_access_token: str = Field(default="", alias="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: str = Field(default="", alias="TWITTER_ACCESS_SECRET")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")
    meta_graph_version: str = Field(default="v23.0", alias="META_GRAPH_VERSION")
    panel_admin_username: str = Field(default="admin", alias="PANEL_ADMIN_USERNAME")
    panel_admin_password: str = Field(default="admin", alias="PANEL_ADMIN_PASSWORD")
    panel_token_ttl_minutes: int = Field(default=720, alias="PANEL_TOKEN_TTL_MINUTES")
    scheduler_interval_seconds: int = Field(default=30, alias="SCHEDULER_INTERVAL_SECONDS")

    auto_publish_global: bool = Field(default=False, alias="AUTO_PUBLISH_GLOBAL")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_image_size_mb: int = Field(default=10, alias="MAX_IMAGE_SIZE_MB")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")

    def _fallback_value(self, *keys: str) -> str:
        """Busca el primer valor no vacio en el .env legacy de AUTOPUBLICATE."""

        legacy = _legacy_env_values()
        for key in keys:
            value = legacy.get(key, "").strip()
            if value:
                return value
        return ""

    @property
    def resolved_gemini_api_key(self) -> str:
        """Devuelve GEMINI_API_KEY actual o fallback legacy."""

        return self.gemini_api_key or self._fallback_value("GEMINI_API_KEY")

    @property
    def resolved_wp_url(self) -> str:
        """Devuelve WP_URL actual o fallback legacy."""

        return self.wp_url or self._fallback_value("WP_URL")

    @property
    def resolved_meta_page_id(self) -> str:
        """Devuelve PAGE ID actual o alias legacy FB_PAGE_ID."""

        return self.meta_page_id or self._fallback_value("META_PAGE_ID", "FB_PAGE_ID")

    @property
    def resolved_meta_ig_account_id(self) -> str:
        """Devuelve IG account ID actual o alias legacy IG_ACCOUNT_ID."""

        return self.meta_ig_account_id or self._fallback_value("META_IG_ACCOUNT_ID", "IG_ACCOUNT_ID")

    @property
    def resolved_meta_access_token(self) -> str:
        """Devuelve access token actual o fallback legacy."""

        return self.meta_access_token or self._fallback_value("META_ACCESS_TOKEN")

    @property
    def upload_path(self) -> Path:
        """Devuelve el path absoluto del directorio de uploads."""

        return Path(self.upload_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instancia singleton de settings."""

    return Settings()


settings = get_settings()
