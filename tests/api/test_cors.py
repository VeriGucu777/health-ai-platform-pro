"""CORS preflight for local frontend dev origins."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_auth_me_allows_127_dev_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
