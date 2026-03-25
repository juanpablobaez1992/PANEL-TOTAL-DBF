"""Migra datos utiles de AUTOPUBLICATE al modulo automation actual."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.controllers.automation_controller import (
    SETTING_EVERGREEN_CATEGORIES,
    SETTING_LAST_POST_ID,
)
from app.database import Base, SessionLocal, engine
from app.models import automation_account as _automation_account  # noqa: F401
from app.models import automation_log as _automation_log  # noqa: F401
from app.models import automation_rule as _automation_rule  # noqa: F401
from app.models import automation_setting as _automation_setting  # noqa: F401
from app.models.automation_account import AutomationAccount
from app.models.automation_rule import AutomationRule
from app.models.automation_setting import AutomationSetting
from app.utils.db_schema import ensure_database_schema

LEGACY_DIR = Path("AUTOPUBLICATE")
RULES_FILE = LEGACY_DIR / "rules.json"
EVERGREEN_FILE = LEGACY_DIR / "evergreen_categories.json"
LAST_POST_FILE = LEGACY_DIR / "last_post_id.txt"
ACCOUNTS_FILE = LEGACY_DIR / "accounts.json"


def _load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _upsert_setting(db, key: str, value: object) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    row = db.get(AutomationSetting, key)
    if row is None:
        db.add(AutomationSetting(key=key, value_json=payload))
        return
    row.value_json = payload


def _import_rules(db) -> int:
    rules = _load_json(RULES_FILE, [])
    if not isinstance(rules, list):
        return 0

    imported = 0
    for item in rules:
        if not isinstance(item, dict):
            continue
        category_slug = str(item.get("category_slug", "")).strip()
        prompt_rule = str(item.get("prompt_rule", "")).strip()
        if not category_slug or not prompt_rule:
            continue

        rule = db.scalar(select(AutomationRule).where(AutomationRule.category_slug == category_slug))
        if rule is None:
            rule = AutomationRule(category_slug=category_slug, prompt_rule=prompt_rule)
            db.add(rule)
        else:
            rule.prompt_rule = prompt_rule
        imported += 1
    return imported


def _import_evergreen_categories(db) -> int:
    categories = _load_json(EVERGREEN_FILE, [])
    if not isinstance(categories, list):
        categories = []
    category_ids = [int(item) for item in categories if str(item).isdigit()]
    _upsert_setting(db, SETTING_EVERGREEN_CATEGORIES, category_ids)
    return len(category_ids)


def _import_last_processed_post(db) -> int:
    if not LAST_POST_FILE.exists():
        return 0
    raw_value = LAST_POST_FILE.read_text(encoding="utf-8").strip()
    if not raw_value.isdigit():
        return 0
    last_post_id = int(raw_value)
    _upsert_setting(db, SETTING_LAST_POST_ID, last_post_id)
    return last_post_id


def _import_accounts(db) -> int:
    accounts = _load_json(ACCOUNTS_FILE, [])
    if not isinstance(accounts, list):
        return 0

    imported = 0
    for item in accounts:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        platform = str(item.get("platform", "")).strip().lower()
        page_id = str(item.get("page_id", "")).strip()
        access_token = str(item.get("access_token", "")).strip()
        if not name or platform not in {"facebook", "instagram"} or not page_id or not access_token:
            continue

        existing = db.scalar(
            select(AutomationAccount).where(
                AutomationAccount.platform == platform,
                AutomationAccount.page_id == page_id,
            )
        )
        if existing is None:
            existing = AutomationAccount(name=name, platform=platform, page_id=page_id)
            db.add(existing)
        else:
            existing.name = name
        existing.set_access_token(access_token)
        imported += 1
    return imported


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_database_schema(engine)
    db = SessionLocal()
    try:
        imported_rules = _import_rules(db)
        evergreen_count = _import_evergreen_categories(db)
        last_post_id = _import_last_processed_post(db)
        imported_accounts = _import_accounts(db)
        db.commit()
    finally:
        db.close()

    print(
        json.dumps(
            {
                "rules": imported_rules,
                "evergreen_categories": evergreen_count,
                "last_processed_post_id": last_post_id,
                "accounts": imported_accounts,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
