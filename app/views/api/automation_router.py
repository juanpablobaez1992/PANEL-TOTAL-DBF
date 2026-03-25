"""Router HTTP del modulo AUTOPUBLICATE integrado al panel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers import automation_controller
from app.database import get_db
from app.models.schemas import (
    AutomationAccountCreate,
    AutomationAccountRead,
    AutomationDashboardRead,
    AutomationEvergreenSettingsRead,
    AutomationEvergreenSettingsUpdate,
    AutomationLogRead,
    AutomationPreparedPost,
    AutomationPreparedPublishPayload,
    AutomationQueueItem,
    AutomationRuleCreate,
    AutomationRuleRead,
    AutomationRunResult,
    AutomationSchedulerState,
    AutomationSchedulerUpdate,
)
from app.views.dependencies import require_permission

router = APIRouter(prefix="/api/panel/automation", tags=["Automation"])


@router.get("/dashboard", response_model=AutomationDashboardRead)
async def dashboard(
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> AutomationDashboardRead:
    """Devuelve el tablero principal de AUTOPUBLICATE."""

    return await automation_controller.get_dashboard(db)


@router.get("/queue", response_model=list[AutomationQueueItem])
async def queue(
    limit: int = 50,
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> list[AutomationQueueItem]:
    """Devuelve la cola pendiente desde WordPress."""

    try:
        return await automation_controller.list_queue(db, limit=limit)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/rules", response_model=list[AutomationRuleRead])
async def rules(
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> list[AutomationRuleRead]:
    """Lista reglas IA activas."""

    return automation_controller.list_rules(db)


@router.post("/rules", response_model=AutomationRuleRead, status_code=status.HTTP_201_CREATED)
async def save_rule(
    payload: AutomationRuleCreate,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationRuleRead:
    """Crea o actualiza una regla IA."""

    return automation_controller.upsert_rule(db, payload)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> None:
    """Elimina una regla IA."""

    try:
        automation_controller.delete_rule(db, rule_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/accounts", response_model=list[AutomationAccountRead])
async def accounts(
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> list[AutomationAccountRead]:
    """Lista cuentas extras de Meta."""

    return automation_controller.list_accounts(db)


@router.post("/accounts", response_model=AutomationAccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AutomationAccountCreate,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationAccountRead:
    """Crea una cuenta extra de Facebook o Instagram."""

    return automation_controller.create_account(db, payload)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> None:
    """Elimina una cuenta extra."""

    try:
        automation_controller.delete_account(db, account_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/scheduler", response_model=AutomationSchedulerState)
async def scheduler_state(
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> AutomationSchedulerState:
    """Estado del scheduler de automation."""

    return automation_controller.get_scheduler_state(db)


@router.put("/scheduler", response_model=AutomationSchedulerState)
async def scheduler_update(
    payload: AutomationSchedulerUpdate,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationSchedulerState:
    """Actualiza configuracion del scheduler."""

    return automation_controller.update_scheduler(db, payload)


@router.get("/evergreen", response_model=AutomationEvergreenSettingsRead)
async def evergreen_settings(
    _user: dict[str, object] = Depends(require_permission("automation.view")),
    db: Session = Depends(get_db),
) -> AutomationEvergreenSettingsRead:
    """Devuelve categorias evergreen disponibles y seleccionadas."""

    try:
        return await automation_controller.get_evergreen_settings(db)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.put("/evergreen", response_model=AutomationEvergreenSettingsRead)
async def evergreen_update(
    payload: AutomationEvergreenSettingsUpdate,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationEvergreenSettingsRead:
    """Guarda categorias permitidas para evergreen."""

    try:
        return await automation_controller.save_evergreen_settings(db, payload)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/run/regular", response_model=AutomationRunResult)
async def run_regular(
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationRunResult:
    """Publica el siguiente post regular ahora."""

    try:
        log = await automation_controller.run_regular_now(db)
        return AutomationRunResult(message="Publicacion regular ejecutada.", log=AutomationLogRead.model_validate(log))
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/run/evergreen/prepare", response_model=AutomationPreparedPost)
async def prepare_evergreen(
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationPreparedPost:
    """Genera una vista previa evergreen editable."""

    try:
        return await automation_controller.run_evergreen_now(db)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/run/evergreen/publish", response_model=AutomationRunResult)
async def publish_evergreen(
    payload: AutomationPreparedPublishPayload,
    _user: dict[str, object] = Depends(require_permission("automation.manage")),
    db: Session = Depends(get_db),
) -> AutomationRunResult:
    """Publica una vista previa evergreen revisada manualmente."""

    try:
        log = await automation_controller.publish_prepared_post(db, payload)
        return AutomationRunResult(message="Publicacion evergreen ejecutada.", log=AutomationLogRead.model_validate(log))
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
