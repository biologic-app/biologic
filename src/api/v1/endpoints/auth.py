from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response

from src.api.dependencies import get_auth_service
from src.core.config import Settings, get_settings
from src.core.errors import UnauthorizedError
from src.core.security import cookie_secure_flag, token_ttl_seconds
from src.schemas.auth import (
    AuthLoginDTO,
    AuthLogoutEnvelopeDTO,
    AuthSessionEnvelopeDTO,
)
from src.schemas.base import ActionMetaDTO
from src.services.auth_service import AuthService, AuthTokenBundle

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, settings: Settings, tokens: AuthTokenBundle) -> None:
    secure = cookie_secure_flag(settings)
    response.set_cookie(
        key=settings.access_cookie_name,
        value=tokens.access_token,
        httponly=True,
        secure=secure,
        samesite=settings.auth_cookie_samesite,
        max_age=token_ttl_seconds(timedelta(minutes=settings.access_token_ttl_minutes)),
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens.refresh_token,
        httponly=True,
        secure=secure,
        samesite=settings.auth_cookie_samesite,
        max_age=token_ttl_seconds(timedelta(days=settings.refresh_token_ttl_days)),
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.access_cookie_name,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
    )


@router.post("/login", response_model=AuthSessionEnvelopeDTO)
async def auth_login(
    payload: AuthLoginDTO,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionEnvelopeDTO:
    session, tokens = await service.login(payload)
    _set_auth_cookies(response, settings, tokens)
    return AuthSessionEnvelopeDTO(data=session, meta=ActionMetaDTO(operation="login"))


@router.get("/me", response_model=AuthSessionEnvelopeDTO)
async def auth_me(
    request: Request,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionEnvelopeDTO:
    access_token = request.cookies.get(settings.access_cookie_name)
    if access_token is None:
        raise UnauthorizedError("Access token is missing.")
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    session = await service.me(access_token, refresh_token)
    return AuthSessionEnvelopeDTO(data=session, meta=ActionMetaDTO(operation="me"))


@router.post("/refresh", response_model=AuthSessionEnvelopeDTO)
async def auth_refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionEnvelopeDTO:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is None:
        raise UnauthorizedError("Refresh token is missing.")
    session, tokens = await service.refresh(refresh_token)
    _set_auth_cookies(response, settings, tokens)
    return AuthSessionEnvelopeDTO(data=session, meta=ActionMetaDTO(operation="refresh"))


@router.post("/logout", response_model=AuthLogoutEnvelopeDTO)
async def auth_logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthLogoutEnvelopeDTO:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    await service.logout(refresh_token)
    _clear_auth_cookies(response, settings)
    return AuthLogoutEnvelopeDTO(meta=ActionMetaDTO(operation="logout"))
