"""Clinical narrative rate limit (process-local, thread-safe)."""

import asyncio

import pytest

from tests.api.test_patient_clinical_narrative import NARRATIVE_URL, PATIENT_PAYLOAD, _register_and_login
from tests.support.clinical_api_test_helpers import assigned_patient_for_doctor


@pytest.mark.asyncio
async def test_narrative_rate_limit_blocks_excess_requests(
    client,
    app,
    user_repository,
    membership_repository,
) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={
            "clinical_narrative_rate_limit_enabled": True,
            "clinical_narrative_rate_limit": 3,
            "clinical_narrative_rate_window_seconds": 60,
        },
    )
    app.state.auth_rate_limiter.reset()
    headers = await _register_and_login(client, email="narr-rate@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    url = NARRATIVE_URL.format(patient_id=patient_id)
    for _ in range(3):
        assert (await client.post(url, headers=headers, json={})).status_code == 200
    blocked = await client.post(url, headers=headers, json={})
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_narrative_rate_limit_concurrent_no_overcount(
    client,
    app,
    user_repository,
    membership_repository,
) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={
            "clinical_narrative_rate_limit_enabled": True,
            "clinical_narrative_rate_limit": 3,
            "clinical_narrative_rate_window_seconds": 60,
        },
    )
    app.state.auth_rate_limiter.reset()
    headers = await _register_and_login(client, email="narr-rate-conc@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    url = NARRATIVE_URL.format(patient_id=patient_id)

    async def fire():
        return (await client.post(url, headers=headers, json={})).status_code

    codes = await asyncio.gather(*[fire() for _ in range(5)])
    assert codes.count(429) >= 1
    assert codes.count(200) <= 3
