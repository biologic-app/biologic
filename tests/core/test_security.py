from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from jose import JWTError

from src.core.config import Settings
from src.core.security import (
    cookie_secure_flag,
    decode_jwt_token,
    encode_jwt_token,
    hash_password,
    is_jwt_error,
    token_expiration,
    token_refresh_version,
    token_subject,
    token_ttl_seconds,
    verify_password,
)


def _settings(**overrides: object) -> Settings:
    return Settings(jwt_secret_key="test-secret", **overrides)


def test_password_hash_and_verify_roundtrip() -> None:
    password_hash = hash_password("admin123")

    assert verify_password("admin123", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_encode_decode_token_and_claim_accessors() -> None:
    settings = _settings()
    user_id = uuid4()
    token, expires_at = encode_jwt_token(
        subject=user_id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=5),
        additional_claims={"rv": 7},
    )

    payload = decode_jwt_token(
        token,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expected_type="refresh",
    )

    assert token_subject(payload) == user_id
    assert token_refresh_version(payload) == 7
    assert token_expiration(payload) == expires_at


def test_decode_rejects_unexpected_token_type() -> None:
    settings = _settings()
    token, _ = encode_jwt_token(
        subject=uuid4(),
        token_type="access",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=1),
    )

    with pytest.raises(ValueError, match="Unexpected token type"):
        decode_jwt_token(
            token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expected_type="refresh",
        )


def test_cookie_secure_flag_resolution() -> None:
    assert cookie_secure_flag(_settings(is_dev=True, auth_cookie_secure=None)) is False
    assert cookie_secure_flag(_settings(is_dev=False, auth_cookie_secure=None)) is True
    assert cookie_secure_flag(_settings(is_dev=True, auth_cookie_secure=True)) is True
    assert cookie_secure_flag(_settings(is_dev=False, auth_cookie_secure=False)) is False


def test_misc_security_helpers() -> None:
    assert token_ttl_seconds(timedelta(minutes=3)) == 180
    assert is_jwt_error(JWTError("bad token")) is True
    assert is_jwt_error(ValueError("no")) is False
