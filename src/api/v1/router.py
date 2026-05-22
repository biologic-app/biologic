from fastapi import APIRouter

from src.contexts.access_control.presentation.router import router as access_control_router
from src.contexts.audit.presentation.router import router as audit_router
from src.contexts.catalogs.presentation.router import router as catalogs_router
from src.contexts.laboratory_workflow.presentation.router import router as workflow_router
from src.contexts.notifications.presentation.router import router as notifications_router

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(workflow_router)
router.include_router(notifications_router)
router.include_router(access_control_router)
router.include_router(audit_router)
router.include_router(catalogs_router)
