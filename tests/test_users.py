import pytest
from httpx import AsyncClient

AUTH_BASE = "/api/v1/auth"
USERS_BASE = "/api/v1/users"

USER_PAYLOAD = {
    "email": "profile_user@example.com",
    "full_name": "Profile User",
    "password": "Passw0rd!",
}


async def _register_and_login(client: AsyncClient, payload: dict = USER_PAYLOAD) -> str:
    await client.post(f"{AUTH_BASE}/register", json=payload)
    r = await client.post(
        f"{AUTH_BASE}/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_my_profile(client: AsyncClient):
    token = await _register_and_login(client)
    r = await client.get(f"{USERS_BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == USER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_update_my_profile(client: AsyncClient):
    token = await _register_and_login(client)
    r = await client.patch(
        f"{USERS_BASE}/me",
        json={"full_name": "Updated Name", "bio": "Hello world"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "Updated Name"
    assert data["bio"] == "Hello world"


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    r = await client.get(f"{USERS_BASE}/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_users_forbidden_for_regular_user(client: AsyncClient):
    token = await _register_and_login(client)
    r = await client.get(f"{USERS_BASE}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
