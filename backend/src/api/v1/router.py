from fastapi import APIRouter

from src.contexts.laboratory_workflow.presentation.router import router as workflow_router
from src.contexts.notifications.presentation.push_router import router as push_router
from src.contexts.notifications.presentation.router import router as notifications_router
from src.contexts.telemetry.presentation.router import router as telemetry_router
from src.presentation.http.access_control.auth_router import router as auth_router
from src.presentation.http.access_control.router import router as access_control_router
from src.presentation.http.audit import router as audit_router
from src.presentation.http.catalogs.router import router as catalogs_router
from src.presentation.http.dashboard import router as dashboard_router

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(workflow_router)
router.include_router(dashboard_router)
router.include_router(notifications_router)
router.include_router(push_router)
router.include_router(auth_router)
router.include_router(access_control_router)
router.include_router(audit_router)
router.include_router(catalogs_router)
router.include_router(telemetry_router)
