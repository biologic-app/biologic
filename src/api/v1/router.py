from fastapi import APIRouter

from src.contexts.laboratory_workflow.presentation.router import router as workflow_router

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(workflow_router)
