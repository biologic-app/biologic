from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.application.access_control.use_cases.auth import AuthSession, AuthUseCase
from src.core.config import Settings, get_settings
from src.core.responses import ResponseMeta, SingleResponse
from src.core.security import (
    cookie_secure_flag,
    encode_jwt_token,
    token_ttl_seconds,
)
from src.presentation.http.access_control.auth_schemas import LoginRequest
from src.presentation.http.access_control.dependencies import (
    get_auth_use_case,
    get_current_user_id,
)

router = APIRouter(tags=["auth"])

AuthUC = Annotated[AuthUseCase, Depends(get_auth_use_case)]


def _set_auth_cookies(
    response: Response, session: AuthSession, settings: Settings
) -> tuple[datetime, datetime]:
    access_delta = timedelta(seconds=settings.access_token_ttl_seconds)
    refresh_delta = timedelta(seconds=settings.refresh_token_ttl_seconds)

    access_token, access_exp = encode_jwt_token(
        subject=session.user_id,
        token_type="access",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=access_delta,
    )
    refresh_token, refresh_exp = encode_jwt_token(
        subject=session.user_id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=refresh_delta,
        additional_claims={"rv": session.refresh_token_version},
    )

    for cookie_name, token, delta in (
        (settings.access_cookie_name, access_token, access_delta),
        (settings.refresh_cookie_name, refresh_token, refresh_delta),
    ):
        response.set_cookie(
            key=cookie_name,
            value=token,
            max_age=token_ttl_seconds(delta),
            httponly=True,
            samesite=settings.auth_cookie_samesite,
            secure=cookie_secure_flag(settings),
            domain=settings.auth_cookie_domain or None,
            path=settings.auth_cookie_path,
        )
    return access_exp, refresh_exp


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
    access_exp, refresh_exp = _set_auth_cookies(response, session, settings)
    return _session_envelope(session, access_exp, refresh_exp, "auth.login")


@router.get("/auth/me")
async def me(
    response: Response,
    use_case: AuthUC,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SingleResponse[dict[str, object]]:
    settings = get_settings()
    session = await use_case.session_for_user(user_id)
    access_exp, refresh_exp = _set_auth_cookies(response, session, settings)
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
