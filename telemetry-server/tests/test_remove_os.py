from copy import deepcopy
import pytest
from app.schemas import TelemetryBatch
from app.repository import MemoryRepository, collapsed_rows, payload_hash
from app.main import create_public_app
from test_api import Client, settings


@pytest.mark.asyncio
async def test_new_no_os_and_legacy_os_ack_and_hash(valid_batch):
    repository = MemoryRepository("test-secret")
    app = create_public_app(settings(), repository)
    old = deepcopy(valid_batch)
    new = deepcopy(valid_batch)
    new["batch_id"] = "batch_no_os_0123456789abcdef"
    new["aggregated_rows"][0].pop("operating_system")
    batch = TelemetryBatch.model_validate(new)
    assert batch.aggregated_rows[0].operating_system is None
    assert collapsed_rows(batch)[0]["operating_system"] == ""
    assert "operating_system" not in new["aggregated_rows"][0]
    explicit = deepcopy(new)
    explicit["aggregated_rows"][0]["operating_system"] = "windows"
    assert payload_hash(batch) != payload_hash(TelemetryBatch.model_validate(explicit))
    async with Client(app) as client:
        for payload in (old, new):
            first = await client.post("/v1/telemetry/batches", json=payload)
            assert first.status_code == 200
            assert first.json()["ack"] is True
            repeat = await client.post("/v1/telemetry/batches", json=payload)
            assert repeat.json()["duplicate"] is True
        conflict = deepcopy(new)
        conflict["aggregated_rows"][0]["operating_system"] = "windows"
        assert (await client.post("/v1/telemetry/batches", json=conflict)).status_code == 409
        declined = deepcopy(new)
        declined["consent"] = False
        assert (await client.post("/v1/telemetry/batches", json=declined)).status_code == 422
