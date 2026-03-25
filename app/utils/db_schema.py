"""Ajustes simples de esquema para SQLite sin migraciones externas."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_database_schema(engine: Engine) -> None:
    """Agrega columnas nuevas simples si aún no existen."""

    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "noticias" in tables:
            columns = {
                row[1] for row in connection.execute(text("PRAGMA table_info(noticias)")).fetchall()
            }
            if "programada_para" not in columns:
                connection.execute(
                    text("ALTER TABLE noticias ADD COLUMN programada_para DATETIME")
                )
            if "generado_at" not in columns:
                connection.execute(
                    text("ALTER TABLE noticias ADD COLUMN generado_at DATETIME")
                )
            if "aprobado_at" not in columns:
                connection.execute(
                    text("ALTER TABLE noticias ADD COLUMN aprobado_at DATETIME")
                )
        if "panel_users" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS panel_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL,
                        activo BOOLEAN NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL,
                        last_login_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_panel_users_username ON panel_users (username)")
            )
        if "panel_sessions" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS panel_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
                        user_agent TEXT,
                        created_at DATETIME NOT NULL,
                        last_used_at DATETIME,
                        expires_at DATETIME NOT NULL,
                        revoked_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES panel_users(id)
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_panel_sessions_user_id ON panel_sessions (user_id)")
            )
