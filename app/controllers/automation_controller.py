"""Controlador principal del modulo AUTOPUBLICATE integrado."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.automation_account import AutomationAccount
from app.models.automation_log import AutomationLog
from app.models.automation_rule import AutomationRule
from app.models.automation_setting import AutomationSetting
from app.models.schemas import (
    AutomationAccountCreate,
    AutomationDashboardRead,
    AutomationEvergreenSettingsRead,
    AutomationEvergreenSettingsUpdate,
    AutomationKpis,
    AutomationPreparedPost,
    AutomationPreparedPublishPayload,
    AutomationQueueItem,
    AutomationRuleCreate,
    AutomationSchedulerState,
    AutomationSchedulerUpdate,
    AutomationWordPressCategory,
)
from app.services.automation_ai_service import generate_copies
from app.services.automation_social_service import post_to_facebook, post_to_instagram
from app.services.automation_wordpress_service import (
    AutomationSourcePost,
    get_all_categories,
    get_next_unprocessed_post,
    get_random_old_post,
    get_unprocessed_posts,
)
from app.services.integraciones_service import check_integraciones

SETTING_LAST_POST_ID = "automation.last_processed_post_id"
SETTING_REGULAR_ENABLED = "automation.scheduler.regular_enabled"
SETTING_REGULAR_INTERVAL = "automation.scheduler.regular_interval_minutes"
SETTING_REGULAR_LAST_RUN = "automation.scheduler.regular_last_run_at"
SETTING_EVERGREEN_ENABLED = "automation.scheduler.evergreen_enabled"
SETTING_EVERGREEN_INTERVAL = "automation.scheduler.evergreen_interval_minutes"
SETTING_EVERGREEN_LAST_RUN = "automation.scheduler.evergreen_last_run_at"
SETTING_EVERGREEN_CATEGORIES = "automation.evergreen.category_ids"


def _loads_value(raw: str, default: Any) -> Any:
    """Parsea value_json y devuelve default si falla."""

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _get_setting(db: Session, key: str, default: Any) -> Any:
    """Obtiene un setting JSON."""

    row = db.get(AutomationSetting, key)
    if row is None:
        return default
    return _loads_value(row.value_json, default)


def _set_setting(db: Session, key: str, value: Any) -> None:
    """Persiste un setting JSON."""

    row = db.get(AutomationSetting, key)
    payload = json.dumps(value, ensure_ascii=False)
    if row is None:
        row = AutomationSetting(key=key, value_json=payload)
        db.add(row)
    else:
        row.value_json = payload
    db.flush()


def _get_last_processed_post_id(db: Session) -> int:
    return int(_get_setting(db, SETTING_LAST_POST_ID, 0) or 0)


def _get_evergreen_category_ids(db: Session) -> list[int]:
    raw = _get_setting(db, SETTING_EVERGREEN_CATEGORIES, [])
    if not isinstance(raw, list):
        return []
    return [int(item) for item in raw if str(item).isdigit()]


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _next_run(enabled: bool, interval_minutes: int, last_run_at: datetime | None) -> datetime | None:
    if not enabled:
        return None
    if last_run_at is None:
        return datetime.now(timezone.utc)
    return last_run_at + timedelta(minutes=interval_minutes)


def get_scheduler_state(db: Session) -> AutomationSchedulerState:
    """Devuelve el estado operativo del scheduler."""

    regular_enabled = bool(_get_setting(db, SETTING_REGULAR_ENABLED, False))
    regular_interval = int(_get_setting(db, SETTING_REGULAR_INTERVAL, 60) or 60)
    regular_last_run = _parse_iso(_get_setting(db, SETTING_REGULAR_LAST_RUN, None))
    evergreen_enabled = bool(_get_setting(db, SETTING_EVERGREEN_ENABLED, False))
    evergreen_interval = int(_get_setting(db, SETTING_EVERGREEN_INTERVAL, 120) or 120)
    evergreen_last_run = _parse_iso(_get_setting(db, SETTING_EVERGREEN_LAST_RUN, None))

    return AutomationSchedulerState(
        regular_enabled=regular_enabled,
        regular_interval_minutes=regular_interval,
        regular_next_run_at=_next_run(regular_enabled, regular_interval, regular_last_run),
        evergreen_enabled=evergreen_enabled,
        evergreen_interval_minutes=evergreen_interval,
        evergreen_next_run_at=_next_run(evergreen_enabled, evergreen_interval, evergreen_last_run),
        last_processed_post_id=_get_last_processed_post_id(db),
    )


def update_scheduler(db: Session, payload: AutomationSchedulerUpdate) -> AutomationSchedulerState:
    """Actualiza configuracion del scheduler."""

    if payload.regular_enabled is not None:
        _set_setting(db, SETTING_REGULAR_ENABLED, payload.regular_enabled)
    if payload.regular_interval_minutes is not None:
        _set_setting(db, SETTING_REGULAR_INTERVAL, payload.regular_interval_minutes)
    if payload.evergreen_enabled is not None:
        _set_setting(db, SETTING_EVERGREEN_ENABLED, payload.evergreen_enabled)
    if payload.evergreen_interval_minutes is not None:
        _set_setting(db, SETTING_EVERGREEN_INTERVAL, payload.evergreen_interval_minutes)
    db.commit()
    return get_scheduler_state(db)


def list_accounts(db: Session) -> list[AutomationAccount]:
    """Lista cuentas extra registradas."""

    return list(db.scalars(select(AutomationAccount).order_by(AutomationAccount.created_at.desc())))


def create_account(db: Session, payload: AutomationAccountCreate) -> AutomationAccount:
    """Crea una cuenta extra de Facebook o Instagram."""

    account = AutomationAccount(
        name=payload.name,
        platform=payload.platform,
        page_id=payload.page_id,
    )
    account.set_access_token(payload.access_token)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account_id: int) -> None:
    """Elimina una cuenta extra."""

    account = db.get(AutomationAccount, account_id)
    if account is None:
        raise ValueError("Cuenta no encontrada.")
    db.delete(account)
    db.commit()


def list_rules(db: Session) -> list[AutomationRule]:
    """Lista reglas IA activas."""

    return list(db.scalars(select(AutomationRule).order_by(AutomationRule.category_slug.asc())))


def upsert_rule(db: Session, payload: AutomationRuleCreate) -> AutomationRule:
    """Crea o actualiza una regla IA."""

    rule = db.scalar(select(AutomationRule).where(AutomationRule.category_slug == payload.category_slug))
    if rule is None:
        rule = AutomationRule(category_slug=payload.category_slug, prompt_rule=payload.prompt_rule)
        db.add(rule)
    else:
        rule.prompt_rule = payload.prompt_rule
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> None:
    """Elimina una regla IA."""

    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise ValueError("Regla no encontrada.")
    db.delete(rule)
    db.commit()


async def get_evergreen_settings(db: Session) -> AutomationEvergreenSettingsRead:
    """Devuelve categorias disponibles y seleccionadas para evergreen."""

    categories = await get_all_categories()
    category_models = [
        AutomationWordPressCategory(
            id=int(item.get("id", 0)),
            name=str(item.get("name", "")),
            slug=str(item.get("slug", "")),
        )
        for item in categories
    ]
    return AutomationEvergreenSettingsRead(
        category_ids=_get_evergreen_category_ids(db),
        categories=category_models,
    )


async def save_evergreen_settings(db: Session, payload: AutomationEvergreenSettingsUpdate) -> AutomationEvergreenSettingsRead:
    """Guarda la seleccion de categorias evergreen."""

    _set_setting(db, SETTING_EVERGREEN_CATEGORIES, payload.category_ids)
    db.commit()
    return await get_evergreen_settings(db)


def list_recent_logs(db: Session, limit: int = 10) -> list[AutomationLog]:
    """Devuelve logs recientes."""

    return list(db.scalars(select(AutomationLog).order_by(AutomationLog.created_at.desc()).limit(limit)))


def get_kpis(db: Session) -> AutomationKpis:
    """Construye KPIs del modulo automation."""

    logs = list(db.scalars(select(AutomationLog)))
    return AutomationKpis(
        total_ejecuciones=len(logs),
        exitos_fb=sum(1 for log in logs if log.fb_success),
        exitos_ig=sum(1 for log in logs if log.ig_success),
        posts_regulares=sum(1 for log in logs if not log.is_evergreen),
        posts_evergreen=sum(1 for log in logs if log.is_evergreen),
    )


async def list_queue(db: Session, limit: int = 50) -> list[AutomationQueueItem]:
    """Devuelve la cola pendiente de WordPress."""

    posts = await get_unprocessed_posts(_get_last_processed_post_id(db), limit=limit)
    return [
        AutomationQueueItem(
            id=post.id,
            title=post.title,
            excerpt=post.excerpt,
            link=post.link,
            image_url=post.image_url,
            image_urls=post.image_urls,
            categories=post.categories,
        )
        for post in posts
    ]


def _build_custom_instructions(db: Session, categories: list[str]) -> str:
    """Compone reglas IA aplicables a las categorias del post."""

    rules = {rule.category_slug: rule.prompt_rule for rule in list_rules(db)}
    matched = [f"- CATEGORIA '{slug}': {rules[slug]}" for slug in categories if slug in rules]
    return "\n".join(matched)


def _build_utm_link(link: str) -> str:
    separator = "&" if "?" in link else "?"
    return f"{link}{separator}utm_source=facebook&utm_medium=autopost"


async def _prepare_source_post(db: Session, post: AutomationSourcePost, *, is_evergreen: bool) -> AutomationPreparedPost:
    """Genera la vista previa publicable para un post fuente."""

    copies = await generate_copies(
        title=post.title,
        excerpt=post.excerpt,
        custom_instructions=_build_custom_instructions(db, post.categories),
        is_evergreen=is_evergreen,
    )
    return AutomationPreparedPost(
        post_id=post.id,
        title=post.title,
        excerpt=post.excerpt,
        link=post.link,
        image_url=post.image_url,
        image_urls=post.image_urls,
        categories=post.categories,
        utm_link=_build_utm_link(post.link),
        fb_copy=copies.get("facebook_copy", ""),
        ig_copy=copies.get("instagram_copy", ""),
        is_evergreen=is_evergreen,
    )


async def prepare_regular_post(db: Session) -> AutomationPreparedPost:
    """Prepara el siguiente post regular pendiente."""

    post = await get_next_unprocessed_post(_get_last_processed_post_id(db))
    if post is None:
        raise ValueError("No hay posts pendientes en la cola de WordPress.")
    return await _prepare_source_post(db, post, is_evergreen=False)


async def prepare_evergreen_post(db: Session) -> AutomationPreparedPost:
    """Prepara un post evergreen aleatorio."""

    post = await get_random_old_post(allowed_categories=_get_evergreen_category_ids(db))
    if post is None:
        raise ValueError("No se encontraron posts evergreen disponibles en WordPress.")
    return await _prepare_source_post(db, post, is_evergreen=True)


def _build_log_error_message(*, fb_success: bool, ig_success: bool, raw_errors: list[str]) -> str:
    if raw_errors:
        return " | ".join(raw_errors)
    if not fb_success and not ig_success:
        return "Facebook e Instagram fallaron."
    if fb_success and not ig_success:
        return "Instagram fallo."
    if ig_success and not fb_success:
        return "Facebook fallo."
    return ""


async def publish_prepared_post(db: Session, payload: AutomationPreparedPublishPayload) -> AutomationLog:
    """Publica una vista previa preparada en cuentas base y/o multi-cuenta."""

    accounts = list_accounts(db)
    fb_success = False
    ig_success = False
    errors: list[str] = []

    if accounts:
        for account in accounts:
            if account.platform == "facebook":
                result = await post_to_facebook(
                    message=payload.fb_copy,
                    link=payload.utm_link,
                    image_url=payload.image_url,
                    page_id=account.page_id,
                    access_token=account.access_token,
                )
                fb_success = fb_success or bool(result["exito"])
                if result["error"]:
                    errors.append(f"FB {account.name}: {result['error']}")
            elif account.platform == "instagram":
                result = await post_to_instagram(
                    image_urls=payload.image_urls,
                    caption=payload.ig_copy,
                    account_id=account.page_id,
                    access_token=account.access_token,
                )
                ig_success = ig_success or bool(result["exito"])
                if result["error"]:
                    errors.append(f"IG {account.name}: {result['error']}")
    else:
        fb_result = await post_to_facebook(
            message=payload.fb_copy,
            link=payload.utm_link,
            image_url=payload.image_url,
        )
        ig_result = await post_to_instagram(
            image_urls=payload.image_urls,
            caption=payload.ig_copy,
        )
        fb_success = bool(fb_result["exito"])
        ig_success = bool(ig_result["exito"])
        if fb_result["error"]:
            errors.append(str(fb_result["error"]))
        if ig_result["error"]:
            errors.append(str(ig_result["error"]))

    log = AutomationLog(
        post_id=payload.post_id,
        title=payload.title,
        is_evergreen=payload.is_evergreen,
        fb_success=fb_success,
        ig_success=ig_success,
        error_msg=_build_log_error_message(fb_success=fb_success, ig_success=ig_success, raw_errors=errors),
    )
    db.add(log)

    if (fb_success or ig_success) and not payload.is_evergreen:
        _set_setting(db, SETTING_LAST_POST_ID, payload.post_id)

    db.commit()
    db.refresh(log)
    return log


async def run_regular_now(db: Session) -> AutomationLog:
    """Ejecuta el siguiente post regular completo."""

    prepared = await prepare_regular_post(db)
    payload = AutomationPreparedPublishPayload(
        post_id=prepared.post_id,
        title=prepared.title,
        image_url=prepared.image_url,
        image_urls=prepared.image_urls,
        utm_link=prepared.utm_link,
        fb_copy=prepared.fb_copy,
        ig_copy=prepared.ig_copy,
        is_evergreen=False,
    )
    return await publish_prepared_post(db, payload)


async def run_evergreen_now(db: Session) -> AutomationPreparedPost:
    """Devuelve una preview evergreen lista para revisar."""

    return await prepare_evergreen_post(db)


async def get_dashboard(db: Session) -> AutomationDashboardRead:
    """Arma el dashboard del modulo automation."""

    queue = await list_queue(db, limit=50)
    return AutomationDashboardRead(
        kpis=get_kpis(db),
        recent_logs=list_recent_logs(db, limit=10),
        scheduler=get_scheduler_state(db),
        integrations=await check_integraciones(),
        queue_count=len(queue),
        accounts_count=int(db.scalar(select(func.count()).select_from(AutomationAccount)) or 0),
        rules_count=int(db.scalar(select(func.count()).select_from(AutomationRule)) or 0),
    )


async def process_due_jobs(db: Session) -> list[str]:
    """Ejecuta los jobs de scheduler que esten vencidos."""

    executed: list[str] = []
    state = get_scheduler_state(db)
    now = datetime.now(timezone.utc)

    if state.regular_enabled and state.regular_next_run_at and state.regular_next_run_at <= now:
        _set_setting(db, SETTING_REGULAR_LAST_RUN, now.isoformat())
        db.commit()
        try:
            await run_regular_now(db)
        except Exception:
            pass
        executed.append("regular")

    if state.evergreen_enabled and state.evergreen_next_run_at and state.evergreen_next_run_at <= now:
        _set_setting(db, SETTING_EVERGREEN_LAST_RUN, now.isoformat())
        db.commit()
        try:
            preview = await prepare_evergreen_post(db)
            await publish_prepared_post(
                db,
                AutomationPreparedPublishPayload(
                    post_id=preview.post_id,
                    title=preview.title,
                    image_url=preview.image_url,
                    image_urls=preview.image_urls,
                    utm_link=preview.utm_link,
                    fb_copy=preview.fb_copy,
                    ig_copy=preview.ig_copy,
                    is_evergreen=True,
                ),
            )
        except Exception:
            pass
        executed.append("evergreen")

    return executed
