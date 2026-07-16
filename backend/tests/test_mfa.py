import pytest

from app.core.config import settings

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, email="mia@example.com", password="Str0ngPass!23"):
    await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password, "full_name": "Mia"}
    )
    tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": False},
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_mfa_setup_and_enable_requires_correct_code(client):
    headers = await _signup_and_login(client)

    setup = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup.status_code == 200
    assert "secret" in setup.json()

    bad_code = await client.post(
        "/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=headers
    )
    assert bad_code.status_code == 401

    good_code = await client.post(
        "/api/v1/auth/mfa/enable", json={"code": settings.MFA_OTP_CODE}, headers=headers
    )
    assert good_code.status_code == 200


async def test_login_with_mfa_enabled_requires_challenge(client):
    headers = await _signup_and_login(client, email="nina@example.com")
    await client.post("/api/v1/auth/mfa/setup", headers=headers)
    await client.post(
        "/api/v1/auth/mfa/enable", json={"code": settings.MFA_OTP_CODE}, headers=headers
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nina@example.com", "password": "Str0ngPass!23", "remember_me": False},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body.get("mfa_required") is True
    mfa_token = body["mfa_token"]

    wrong = await client.post(
        "/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_token, "code": "000000"}
    )
    assert wrong.status_code == 401

    correct = await client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": settings.MFA_OTP_CODE},
    )
    assert correct.status_code == 200
    assert "access_token" in correct.json()


async def test_mfa_disable_requires_correct_code(client):
    headers = await _signup_and_login(client, email="oscar@example.com")
    await client.post("/api/v1/auth/mfa/setup", headers=headers)
    await client.post(
        "/api/v1/auth/mfa/enable", json={"code": settings.MFA_OTP_CODE}, headers=headers
    )

    bad = await client.post(
        "/api/v1/auth/mfa/disable", json={"code": "wrong"}, headers=headers
    )
    assert bad.status_code == 401

    good = await client.post(
        "/api/v1/auth/mfa/disable", json={"code": settings.MFA_OTP_CODE}, headers=headers
    )
    assert good.status_code == 200
