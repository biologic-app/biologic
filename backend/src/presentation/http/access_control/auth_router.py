from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from src.application.access_control.use_cases.auth import AuthSession, AuthUseCase
from src.core.config import Settings, get_settings
from src.core.errors import UnauthorizedError
from src.core.responses import ResponseMeta, SingleResponse
from src.core.security import (
    cookie_secure_flag,
    decode_jwt_token,
    encode_jwt_token,
    token_expiration,
    token_refresh_version,
    token_subject,
    token_ttl_seconds,
)
from src.presentation.http.access_control.auth_schemas import LoginRequest
from src.presentation.http.access_control.dependencies import (
    get_auth_use_case,
    get_current_user_id,
)

router = APIRouter(tags=["auth"])

AuthUC = Annotated[AuthUseCase, Depends(get_auth_use_case)]


def _write_cookie(
    response: Response, name: str, token: str, delta: timedelta, settings: Settings
) -> None:
    response.set_cookie(
        key=name,
        value=token,
        max_age=token_ttl_seconds(delta),
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=cookie_secure_flag(settings),
        domain=settings.auth_cookie_domain or None,
        path=settings.auth_cookie_path,
    )


def _mint_access_cookie(
    response: Response, user_id: UUID, settings: Settings
) -> datetime:
    delta = timedelta(seconds=settings.access_token_ttl_seconds)
    token, access_exp = encode_jwt_token(
        subject=user_id,
        token_type="access",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=delta,
    )
    _write_cookie(response, settings.access_cookie_name, token, delta, settings)
    return access_exp


def _mint_refresh_cookie(
    response: Response, session: AuthSession, settings: Settings, *, remember: bool
) -> datetime:
    ttl_seconds = (
        settings.refresh_token_remember_ttl_seconds
        if remember
        else settings.refresh_token_ttl_seconds
    )
    delta = timedelta(seconds=ttl_seconds)
    token, refresh_exp = encode_jwt_token(
        subject=session.user_id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=delta,
        additional_claims={"rv": session.refresh_token_version},
    )
    _write_cookie(response, settings.refresh_cookie_name, token, delta, settings)
    return refresh_exp


def _decode_refresh_cookie(request: Request, settings: Settings) -> dict[str, object]:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise UnauthorizedError("Missing refresh token.")
    try:
        return decode_jwt_token(
            token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expected_type="refresh",
        )
    except Exception as exc:  # noqa: BLE001 — any decode failure is a 401
        raise UnauthorizedError("Invalid or expired refresh token.") from exc


def _read_refresh_expiry(
    request: Request, settings: Settings, fallback: datetime
) -> datetime:
    """Best-effort read of the current refresh token's expiry so `/auth/me`
    and `/auth/refresh` can report it without re-minting the refresh cookie
    (the refresh window is fixed at login and never extended)."""
    try:
        return token_expiration(_decode_refresh_cookie(request, settings))
    except Exception:  # noqa: BLE001 — expiry is informational only
        return fallback


def _session_envelope(
    session: AuthSession, access_exp: datetime, refresh_exp: datetime, operation: str
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data={
            "user": {
                "id": str(session.user_id),
                "username": session.username,
                "role_key": session.role_key,
                "role_name": session.role_name,
                "first_name": session.first_name,
                "last_name": session.last_name,
                "patronymic": session.patronymic,
            },
            "permissions": session.permissions,
            "access_expires_at": access_exp.isoformat(),
            "refresh_expires_at": refresh_exp.isoformat(),
        },
        meta=ResponseMeta(operation=operation),
    )


@router.post("/auth/login")
async def login(
    payload: LoginRequest, response: Response, use_case: AuthUC
) -> SingleResponse[dict[str, object]]:
    settings = get_settings()
    session = await use_case.authenticate(payload.username, payload.password)
    access_exp = _mint_access_cookie(response, session.user_id, settings)
    refresh_exp = _mint_refresh_cookie(
        response, session, settings, remember=payload.remember_me
    )
    return _session_envelope(session, access_exp, refresh_exp, "auth.login")


@router.post("/auth/refresh")
async def refresh(
    request: Request, response: Response, use_case: AuthUC
) -> SingleResponse[dict[str, object]]:
    settings = get_settings()
    payload = _decode_refresh_cookie(request, settings)
    user_id = token_subject(payload)
    refresh_version = token_refresh_version(payload)
    refresh_exp = token_expiration(payload)

    session = await use_case.session_for_user(user_id)
    if session.refresh_token_version != refresh_version:
        raise UnauthorizedError("Refresh token has been revoked.")

    # Fixed window: only the access cookie is re-minted; the refresh cookie is
    # left untouched so its absolute expiry (30 days / 1 day) is preserved.
    access_exp = _mint_access_cookie(response, session.user_id, settings)
    return _session_envelope(session, access_exp, refresh_exp, "auth.refresh")


@router.get("/auth/me")
async def me(
    request: Request,
    response: Response,
    use_case: AuthUC,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SingleResponse[dict[str, object]]:
    settings = get_settings()
    session = await use_case.session_for_user(user_id)
    access_exp = _mint_access_cookie(response, session.user_id, settings)
    refresh_exp = _read_refresh_expiry(request, settings, fallback=access_exp)
    return _session_envelope(session, access_exp, refresh_exp, "auth.me")


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> SingleResponse[dict[str, object]]:
    settings = get_settings()
    for name in (settings.access_cookie_name, settings.refresh_cookie_name):
        response.delete_cookie(
            key=name,
            domain=settings.auth_cookie_domain or None,
            path=settings.auth_cookie_path,
        )
    return SingleResponse(data={"ok": True}, meta=ResponseMeta(operation="auth.logout"))
