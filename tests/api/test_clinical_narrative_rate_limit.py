"""Clinical narrative rate limit (process-local, thread-safe)."""

import asyncio

import pytest

from tests.api.test_patient_clinical_narrative import NARRATIVE_URL, PATIENT_PAYLOAD, _register_and_login


@pytest.mark.asyncio
async def test_narrative_rate_limit_blocks_excess_requests(client, app) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={
            "clinical_narrative_rate_limit_enabled": True,
            "clinical_narrative_rate_limit": 3,
            "clinical_narrative_rate_window_seconds": 60,
        },
    )
    app.state.auth_rate_limiter.reset()
    headers = await _register_and_login(client, email="narr-rate@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    url = NARRATIVE_URL.format(patient_id=patient_id)
    for _ in range(3):
        assert (await client.post(url, headers=headers, json={})).status_code == 200
    blocked = await client.post(url, headers=headers, json={})
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_narrative_rate_limit_concurrent_no_overcount(client, app) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={
            "clinical_narrative_rate_limit_enabled": True,
            "clinical_narrative_rate_limit": 3,
            "clinical_narrative_rate_window_seconds": 60,
        },
    )
    app.state.auth_rate_limiter.reset()
    headers = await _register_and_login(client, email="narr-rate-conc@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    url = NARRATIVE_URL.format(patient_id=patient_id)

    async def fire():
        return (await client.post(url, headers=headers, json={})).status_code

    codes = await asyncio.gather(*[fire() for _ in range(5)])
    assert codes.count(429) >= 1
    assert codes.count(200) <= 3
