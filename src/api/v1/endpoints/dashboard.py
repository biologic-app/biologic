from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies import get_auth_service, get_dashboard_quick_actions_service
from src.core.config import Settings, get_settings
from src.core.errors import UnauthorizedError
from src.schemas.auth import AuthSessionDTO
from src.schemas.dashboard import (
    DashboardQuickActionCreateDTO,
    DashboardQuickActionCreateEnvelopeDTO,
    DashboardQuickActionDeleteEnvelopeDTO,
    DashboardQuickActionListEnvelopeDTO,
    DashboardQuickActionUpdateDTO,
    DashboardQuickActionUpdateEnvelopeDTO,
)
from src.services.auth_service import AuthService
from src.services.dashboard_service import DashboardQuickActionsService
from src.services.mock_auth_service import MockAuthService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _require_session(
    request: Request,
    auth_service: AuthService | MockAuthService,
    settings: Settings,
) -> AuthSessionDTO:
    access_token = request.cookies.get(settings.access_cookie_name)
    if access_token is None:
        raise UnauthorizedError("Access token is missing.")
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    return await auth_service.me(access_token, refresh_token)


def _permissions(session: AuthSessionDTO) -> list[tuple[str, str]]:
    return [(permission.resource, permission.action) for permission in session.permissions]


@router.get("/quick-actions", response_model=DashboardQuickActionListEnvelopeDTO)
async def list_quick_actions(
    request: Request,
    service: DashboardQuickActionsService = Depends(get_dashboard_quick_actions_service),
    auth_service: AuthService | MockAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> DashboardQuickActionListEnvelopeDTO:
    session = await _require_session(request, auth_service, settings)
    return await service.list(
        role_key=session.user.role_key,
        permissions=_permissions(session),
        offset=offset,
        limit=limit,
    )


@router.post(
    "/quick-actions",
    response_model=DashboardQuickActionCreateEnvelopeDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_quick_action(
    payload: DashboardQuickActionCreateDTO,
    request: Request,
    service: DashboardQuickActionsService = Depends(get_dashboard_quick_actions_service),
    auth_service: AuthService | MockAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> DashboardQuickActionCreateEnvelopeDTO:
    session = await _require_session(request, auth_service, settings)
    return await service.create(
        role_key=session.user.role_key,
        payload=payload,
        permissions=_permissions(session),
    )


@router.put(
    "/quick-actions/{quick_action_id}",
    response_model=DashboardQuickActionUpdateEnvelopeDTO,
)
async def update_quick_action(
    quick_action_id: int,
    payload: DashboardQuickActionUpdateDTO,
    request: Request,
    service: DashboardQuickActionsService = Depends(get_dashboard_quick_actions_service),
    auth_service: AuthService | MockAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> DashboardQuickActionUpdateEnvelopeDTO:
    session = await _require_session(request, auth_service, settings)
    return await service.update(
        role_key=session.user.role_key,
        quick_action_id=quick_action_id,
        payload=payload,
        permissions=_permissions(session),
    )


@router.delete(
    "/quick-actions/{quick_action_id}",
    response_model=DashboardQuickActionDeleteEnvelopeDTO,
)
async def delete_quick_action(
    quick_action_id: int,
    request: Request,
    service: DashboardQuickActionsService = Depends(get_dashboard_quick_actions_service),
    auth_service: AuthService | MockAuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> DashboardQuickActionDeleteEnvelopeDTO:
    session = await _require_session(request, auth_service, settings)
    await service.delete(
        role_key=session.user.role_key,
        quick_action_id=quick_action_id,
        permissions=_permissions(session),
    )
    return DashboardQuickActionDeleteEnvelopeDTO(ok=True)
