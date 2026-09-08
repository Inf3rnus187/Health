"""Phase 9: MFA (TOTP), account erasure, and crypto roundtrip."""

from __future__ import annotations

import pyotp
from app.core import crypto
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def test_crypto_passthrough_or_roundtrip() -> None:
    data = b"secret-bytes"
    assert crypto.decrypt(crypto.encrypt(data)) == data


async def test_mfa_enables_and_gates_login(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    setup = await client.post("/api/v1/auth/mfa/setup", headers=auth)
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    enabled = await client.post(
        "/api/v1/auth/mfa/enable", json={"code": code}, headers=auth
    )
    assert enabled.status_code == 200

    without = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert without.status_code == 401

    with_otp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "otp": pyotp.TOTP(secret).now(),
        },
    )
    assert with_otp.status_code == 200


async def test_account_erasure(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {"metric_key": "body.weight", "date_key": "2026-07-01", "value": 80}
        ]
    }
    await client.post("/api/v1/measurements", json=body, headers=auth)
    erased = await client.delete("/api/v1/me", headers=auth)
    assert erased.status_code == 200
    after = await client.get("/api/v1/auth/me", headers=auth)
    assert after.status_code == 401
