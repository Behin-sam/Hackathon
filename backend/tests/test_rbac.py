import pytest

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, email="bob@example.com", password="Str0ngPass!23"):
    await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password, "full_name": "Bob"}
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password, "remember_me": False}
    )
    tokens = resp.json()
    user = (
        await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
    ).json()
    return tokens, user


async def test_customer_cannot_list_users(client):
    tokens, _ = await _signup_and_login(client)
    resp = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


async def test_super_admin_can_list_users(client, admin_headers):
    resp = await client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_super_admin_can_assign_and_revoke_role(client, admin_headers):
    tokens, user = await _signup_and_login(client)
    user_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    assign = await client.post(
        "/api/v1/roles/assign",
        json={"user_id": user["id"], "role_name": "Fraud Analyst"},
        headers=admin_headers,
    )
    assert assign.status_code == 200

    profile = await client.get("/api/v1/users/profile", headers=user_headers)
    assert "Fraud Analyst" in profile.json()["roles"]

    revoke = await client.post(
        "/api/v1/roles/revoke",
        json={"user_id": user["id"], "role_name": "Fraud Analyst"},
        headers=admin_headers,
    )
    assert revoke.status_code == 200

    profile_after = await client.get("/api/v1/users/profile", headers=user_headers)
    assert "Fraud Analyst" not in profile_after.json()["roles"]


async def test_non_admin_cannot_assign_roles(client):
    tokens, user = await _signup_and_login(client)
    resp = await client.post(
        "/api/v1/roles/assign",
        json={"user_id": user["id"], "role_name": "Bank"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 403


async def test_compliance_officer_can_change_user_status(client, admin_headers):
    _, compliance_user = await _signup_and_login(client, email="carol@example.com")
    await client.post(
        "/api/v1/roles/assign",
        json={"user_id": compliance_user["id"], "role_name": "Compliance Officer"},
        headers=admin_headers,
    )
    compliance_tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "Str0ngPass!23", "remember_me": False},
        )
    ).json()
    compliance_headers = {"Authorization": f"Bearer {compliance_tokens['access_token']}"}

    _, target_user = await _signup_and_login(client, email="dave@example.com")

    resp = await client.put(
        f"/api/v1/users/{target_user['id']}/status",
        json={"status": "suspended"},
        headers=compliance_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"


async def test_suspended_user_cannot_login(client, admin_headers):
    _, user = await _signup_and_login(client, email="erin@example.com")
    await client.put(
        f"/api/v1/users/{user['id']}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "erin@example.com", "password": "Str0ngPass!23", "remember_me": False},
    )
    assert resp.status_code == 401
