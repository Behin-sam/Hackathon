import pytest

pytestmark = pytest.mark.asyncio


async def _signup(client, email="paula@example.com", password="Str0ngPass!23"):
    await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password, "full_name": "Paula"}
    )


async def _login(client, email="paula@example.com", password="Str0ngPass!23"):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password, "remember_me": False}
    )
    return resp.json()


async def test_list_sessions_shows_active_logins(client):
    await _signup(client)
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Log in again to create a second session.
    await _login(client)

    resp = await client.get("/api/v1/sessions/", headers=headers)
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 2
    assert all(s["is_active"] for s in sessions)


async def test_revoke_own_session(client):
    await _signup(client)
    tokens = await _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    sessions = (await client.get("/api/v1/sessions/", headers=headers)).json()
    session_id = sessions[0]["id"]

    resp = await client.post(f"/api/v1/sessions/{session_id}/revoke", headers=headers)
    assert resp.status_code == 200

    remaining = (await client.get("/api/v1/sessions/", headers=headers)).json()
    assert session_id not in {s["id"] for s in remaining}


async def test_cannot_revoke_another_users_session(client):
    await _signup(client, email="quinn@example.com")
    quinn_tokens = await _login(client, email="quinn@example.com")
    quinn_headers = {"Authorization": f"Bearer {quinn_tokens['access_token']}"}
    quinn_sessions = (await client.get("/api/v1/sessions/", headers=quinn_headers)).json()
    quinn_session_id = quinn_sessions[0]["id"]

    await _signup(client, email="rex@example.com")
    rex_tokens = await _login(client, email="rex@example.com")
    rex_headers = {"Authorization": f"Bearer {rex_tokens['access_token']}"}

    resp = await client.post(f"/api/v1/sessions/{quinn_session_id}/revoke", headers=rex_headers)
    assert resp.status_code == 403
