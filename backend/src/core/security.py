from __future__ import annotations

import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from src.core.config import Settings

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        return False


def encode_jwt_token(
    *,
    subject: UUID,
    token_type: TokenType,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta,
    additional_claims: Mapping[str, Any] | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> tuple[str, datetime]:
    now = datetime.now(UTC).replace(microsecond=0)
    expires_at = now + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(UUID(int=secrets.randbits(128))),
    }
    if issuer is not None:
        payload["iss"] = issuer
    if audience is not None:
        payload["aud"] = audience
    if additional_claims:
        payload.update(dict(additional_claims))
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token, expires_at


def decode_jwt_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str,
    expected_type: TokenType | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    if algorithm not in {"HS256", "HS384", "HS512"}:
        raise ValueError("Unsupported JWT algorithm.")
    payload = cast(
        dict[str, Any],
        jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
            options={"verify_iss": issuer is not None, "verify_aud": audience is not None},
        ),
    )
    token_type = payload.get("typ")
    if expected_type is not None and token_type != expected_type:
        raise ValueError("Unexpected token type.")
    return payload


def token_subject(payload: Mapping[str, Any]) -> UUID:
    raw_subject = payload.get("sub")
    if not isinstance(raw_subject, str):
        raise ValueError("Token subject is missing.")
    return UUID(raw_subject)


def token_session_id(payload: Mapping[str, Any]) -> UUID:
    raw = payload.get("sid")
    if not isinstance(raw, str):
        raise ValueError("Token session is missing.")
    return UUID(raw)


def token_version(payload: Mapping[str, Any]) -> int:
    raw = payload.get("ver", payload.get("rv"))
    if not isinstance(raw, int) or raw < 0:
        raise ValueError("Token version is invalid.")
    return raw


def token_jti(payload: Mapping[str, Any]) -> UUID:
    raw = payload.get("jti")
    if not isinstance(raw, str):
        raise ValueError("Token id is missing.")
    return UUID(raw)


def token_refresh_version(payload: Mapping[str, Any]) -> int:
    raw_version = payload.get("ver", payload.get("rv"))
    if raw_version is None:
        raise ValueError("Refresh token version is missing.")
    if not isinstance(raw_version, int):
        raise ValueError("Refresh token version is invalid.")
    return raw_version


def token_expiration(payload: Mapping[str, Any]) -> datetime:
    raw_exp = payload.get("exp")
    if not isinstance(raw_exp, int):
        raise ValueError("Token expiration is missing.")
    return datetime.fromtimestamp(raw_exp, tz=UTC)


def cookie_secure_flag(settings: Settings) -> bool:
    if settings.auth_cookie_secure is not None:
        return settings.auth_cookie_secure
    return not settings.is_dev


def token_ttl_seconds(delta: timedelta) -> int:
    return int(delta.total_seconds())


def is_jwt_error(exc: Exception) -> bool:
    return isinstance(exc, JWTError)
