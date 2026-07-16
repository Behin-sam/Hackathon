import pytest

pytestmark = pytest.mark.asyncio


async def _signup(client, email="alice@example.com", password="Str0ngPass!23"):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Alice Example"},
    )
    return resp


async def _login(client, email="alice@example.com", password="Str0ngPass!23", remember_me=False):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "remember_me": remember_me},
    )


async def test_signup_creates_customer_by_default(client):
    resp = await _signup(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["is_email_verified"] is False
    assert body["status"] == "active"


async def test_signup_duplicate_email_conflicts(client):
    await _signup(client)
    resp = await _signup(client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


async def test_login_wrong_password_is_unauthorized(client):
    await _signup(client)
    resp = await _login(client, password="wrong-password")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


async def test_login_success_returns_token_pair(client):
    await _signup(client)
    resp = await _login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body


async def test_me_requires_bearer_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(client):
    await _signup(client)
    tokens = (await _login(client)).json()
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


async def test_refresh_token_rotation_issues_new_pair(client):
    await _signup(client)
    tokens = (await _login(client)).json()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"] != tokens["access_token"]


async def test_refresh_token_reuse_is_detected_and_revokes_all(client):
    await _signup(client)
    tokens = (await _login(client)).json()
    old_refresh = tokens["refresh_token"]

    # First use rotates successfully.
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]

    # Reusing the now-stale token should be rejected AND revoke the new one too.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
    assert "reuse" in reuse.json()["error"]["message"].lower()

    blocked = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert blocked.status_code == 401


async def test_logout_revokes_refresh_token(client):
    await _signup(client)
    tokens = (await _login(client)).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
    )
    assert resp.status_code == 200

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401


async def test_change_password_requires_correct_current_password(client):
    await _signup(client)
    tokens = (await _login(client)).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    bad = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "NewPass!234"},
        headers=headers,
    )
    assert bad.status_code == 401

    good = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Str0ngPass!23", "new_password": "NewPass!234"},
        headers=headers,
    )
    assert good.status_code == 200

    relogin = await _login(client, password="NewPass!234")
    assert relogin.status_code == 200


async def test_password_reset_flow(client):
    await _signup(client)

    request_resp = await client.post(
        "/api/v1/auth/reset-password/request", json={"email": "alice@example.com"}
    )
    assert request_resp.status_code == 200

    # Unknown emails get the same generic response (no enumeration).
    unknown_resp = await client.post(
        "/api/v1/auth/reset-password/request", json={"email": "nobody@example.com"}
    )
    assert unknown_resp.status_code == 200
    assert unknown_resp.json()["message"] == request_resp.json()["message"]


async def test_email_verification_flow(client):
    await _signup(client)
    tokens = (await _login(client)).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    req = await client.post("/api/v1/auth/email-verification/request", headers=headers)
    assert req.status_code == 200
    mock_token = req.json()["message"].split(": ")[-1]

    verify = await client.post("/api/v1/auth/email-verification/verify", json={"token": mock_token})
    assert verify.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["is_email_verified"] is True
