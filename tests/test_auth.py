import pytest
from httpx import AsyncClient

BASE = "/api/v1/auth"

TEST_USER = {
    "email": "testuser@example.com",
    "full_name": "Test User",
    "password": "Passw0rd!",
}


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    r = await client.post(f"{BASE}/register", json=TEST_USER)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == TEST_USER["email"]
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    await client.post(f"{BASE}/register", json=TEST_USER)
    r = await client.post(f"{BASE}/register", json=TEST_USER)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(f"{BASE}/register", json=TEST_USER)
    r = await client.post(
        f"{BASE}/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(f"{BASE}/register", json=TEST_USER)
    r = await client.post(
        f"{BASE}/login",
        json={"email": TEST_USER["email"], "password": "wrongpassword"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post(f"{BASE}/register", json=TEST_USER)
    login_r = await client.post(
        f"{BASE}/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    tokens = login_r.json()

    r = await client.post(f"{BASE}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_tokens = r.json()
    assert "access_token" in new_tokens
    # Old refresh token should now be invalid
    r2 = await client.post(f"{BASE}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    await client.post(f"{BASE}/register", json=TEST_USER)
    login_r = await client.post(
        f"{BASE}/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    tokens = login_r.json()

    r = await client.post(f"{BASE}/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200

    # Refresh should fail after logout
    r2 = await client.post(f"{BASE}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_always_200(client: AsyncClient):
    r = await client.post(f"{BASE}/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200
