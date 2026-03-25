"""Controlador de canales."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.canal import Canal
from app.models.enums import TipoCanal
from app.models.schemas import CanalCreate, CanalUpdate
from app.utils.credentials import ENCRYPTED_PREFIX, decrypt_config, encrypt_config

DEFAULT_CHANNELS: list[dict[str, object]] = [
    {"nombre": "WordPress (sitio web)", "tipo": TipoCanal.wordpress, "orden": 1},
    {"nombre": "Facebook Page", "tipo": TipoCanal.facebook, "orden": 2},
    {"nombre": "Instagram", "tipo": TipoCanal.instagram, "orden": 3},
    {"nombre": "Twitter/X", "tipo": TipoCanal.twitter, "orden": 4},
    {"nombre": "WhatsApp Channel", "tipo": TipoCanal.whatsapp, "orden": 5},
    {"nombre": "Telegram", "tipo": TipoCanal.telegram, "orden": 6},
]


def list_canales(db: Session) -> list[Canal]:
    """Lista todos los canales ordenados."""

    return list(db.scalars(select(Canal).order_by(Canal.orden, Canal.id)))


def get_canal(db: Session, canal_id: int) -> Canal | None:
    """Obtiene un canal por ID."""

    return db.get(Canal, canal_id)


def create_canal(db: Session, payload: CanalCreate) -> Canal:
    """Crea un canal nuevo."""

    existing = db.scalar(select(Canal).where(Canal.tipo == payload.tipo))
    if existing is not None:
        raise ValueError(f"Ya existe un canal configurado para el tipo {payload.tipo.value}.")

    data = payload.model_dump(exclude={"config"})
    canal = Canal(**data)
    canal.config_json = encrypt_config(payload.config)
    db.add(canal)
    db.commit()
    db.refresh(canal)
    return canal


def update_canal(db: Session, canal_id: int, payload: CanalUpdate) -> Canal:
    """Actualiza un canal existente."""

    canal = db.get(Canal, canal_id)
    if canal is None:
        raise ValueError("Canal no encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "config":
            canal.config_json = encrypt_config(value or {})
            continue
        setattr(canal, field, value)

    db.commit()
    db.refresh(canal)
    return canal


def toggle_canal_activo(db: Session, canal_id: int) -> Canal:
    """Alterna el flag activo de un canal."""

    canal = db.get(Canal, canal_id)
    if canal is None:
        raise ValueError("Canal no encontrado.")
    canal.activo = not canal.activo
    db.commit()
    db.refresh(canal)
    return canal


def toggle_canal_auto(db: Session, canal_id: int) -> Canal:
    """Alterna el flag de auto publicación de un canal."""

    canal = db.get(Canal, canal_id)
    if canal is None:
        raise ValueError("Canal no encontrado.")
    canal.auto_publicar = not canal.auto_publicar
    db.commit()
    db.refresh(canal)
    return canal


def seed_default_canales(db: Session) -> list[Canal]:
    """Crea los canales por defecto si la tabla está vacía."""

    existing = db.scalar(select(Canal.id).limit(1))
    if existing is not None:
        return list_canales(db)

    canales: list[Canal] = []
    for item in DEFAULT_CHANNELS:
        canal = Canal(
            nombre=str(item["nombre"]),
            tipo=item["tipo"],
            activo=True,
            auto_publicar=False,
            config_json=encrypt_config({}),
            orden=int(item["orden"]),
        )
        db.add(canal)
        canales.append(canal)
    db.commit()
    for canal in canales:
        db.refresh(canal)
    return canales


def migrate_legacy_channel_configs(db: Session) -> int:
    """Migra config_json legacy en texto plano a formato cifrado."""

    canales = list_canales(db)
    migrated = 0
    for canal in canales:
        if canal.config_json.startswith(ENCRYPTED_PREFIX):
            continue
        canal.config_json = encrypt_config(decrypt_config(canal.config_json))
        migrated += 1
    if migrated:
        db.commit()
    return migrated
