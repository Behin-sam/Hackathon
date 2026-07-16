import pytest

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, email="frank@example.com", password="Str0ngPass!23"):
    await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password, "full_name": "Frank"}
    )
    tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": False},
        )
    ).json()
    user = (
        await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}, user


async def test_new_user_has_unverified_identity(client):
    headers, _ = await _signup_and_login(client)
    resp = await client.get("/api/v1/identity/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "unverified"
    assert 0.0 <= body["confidence_score"] <= 1.0


async def test_user_can_update_own_region(client):
    headers, _ = await _signup_and_login(client)
    resp = await client.put("/api/v1/identity/me", json={"region": "EU-WEST"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["region"] == "EU-WEST"


async def test_customer_cannot_read_others_identity(client, admin_headers):
    _, target_user = await _signup_and_login(client, email="grace@example.com")
    customer_headers, _ = await _signup_and_login(client, email="henry@example.com")

    resp = await client.get(f"/api/v1/identity/{target_user['id']}", headers=customer_headers)
    assert resp.status_code == 403


async def test_compliance_officer_can_verify_identity(client, admin_headers):
    _, target_user = await _signup_and_login(client, email="ivy@example.com")

    # Promote a fresh user to Compliance Officer.
    _, officer_user = await _signup_and_login(client, email="jack@example.com")
    await client.post(
        "/api/v1/roles/assign",
        json={"user_id": officer_user["id"], "role_name": "Compliance Officer"},
        headers=admin_headers,
    )
    officer_tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "jack@example.com", "password": "Str0ngPass!23", "remember_me": False},
        )
    ).json()
    officer_headers = {"Authorization": f"Bearer {officer_tokens['access_token']}"}

    verify_resp = await client.post(
        f"/api/v1/identity/{target_user['id']}/verify",
        json={"verification_type": "document", "notes": "Passport checked"},
        headers=officer_headers,
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["verification_status"] == "verified"
    assert len(body["verification_history"]) == 1

    history_resp = await client.get(
        f"/api/v1/identity/{target_user['id']}/history", headers=officer_headers
    )
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1


async def test_fraud_analyst_can_add_identity_signal(client, admin_headers):
    _, target_user = await _signup_and_login(client, email="karen@example.com")

    _, analyst_user = await _signup_and_login(client, email="leo@example.com")
    await client.post(
        "/api/v1/roles/assign",
        json={"user_id": analyst_user["id"], "role_name": "Fraud Analyst"},
        headers=admin_headers,
    )
    analyst_tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "leo@example.com", "password": "Str0ngPass!23", "remember_me": False},
        )
    ).json()
    analyst_headers = {"Authorization": f"Bearer {analyst_tokens['access_token']}"}

    resp = await client.post(
        f"/api/v1/identity/{target_user['id']}/signals",
        json={"signal_key": "device_fingerprint_match", "signal_value": "true", "confidence_delta": 0.1},
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any(s["signal_key"] == "device_fingerprint_match" for s in body["signals"])
