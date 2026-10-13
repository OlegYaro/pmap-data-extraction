import uuid

import pytest

from core import settings

UNKNOWN_RUN_URL = f"/runs/{uuid.uuid4()}"


async def test_health_needs_no_key(client):
    response = await client.get("/health", headers={"X-API-Key": "wrong"})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "method, url", [("POST", "/runs"), ("GET", UNKNOWN_RUN_URL), ("GET", "/transactions")]
)
async def test_every_data_endpoint_rejects_a_missing_key(client, method, url):
    del client.headers["X-API-Key"]

    response = await client.request(method, url)

    assert response.status_code == 401


async def test_wrong_key_is_rejected(client):
    response = await client.get(UNKNOWN_RUN_URL, headers={"X-API-Key": "wrong"})

    assert response.status_code == 401


async def test_valid_key_reaches_the_endpoint(client):
    response = await client.get(UNKNOWN_RUN_URL)

    assert response.status_code == 404


async def test_unconfigured_key_closes_the_api(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", None)

    response = await client.get(UNKNOWN_RUN_URL)

    assert response.status_code == 503
