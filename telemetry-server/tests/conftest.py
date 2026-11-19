from __future__ import annotations

from datetime import date
import os

import pytest


os.environ.setdefault("DATABASE_URL", "postgresql://telemetry:test@localhost/telemetry")
os.environ.setdefault("INSTALLATION_HMAC_SECRET", "test-hmac-secret-that-is-longer-than-32-characters")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-that-is-longer-than-32-characters")


@pytest.fixture
def valid_batch() -> dict:
    return {
        "schema_version": 1,
        "batch_id": "batch_0123456789abcdef",
        "installation_id": "installation_0123456789abcdef",
        "consent_version": "2026-09",
        "consent": True,
        "client_version": "5.0.0",
        "aggregated_rows": [{
            "country_code": "CN",
            "client_version": "5.0.0",
            "operating_system": "windows",
            "provider": "openai",
            "model": "gpt-5",
            "active_minutes": 20,
            "api_call_count": 10,
            "success_count": 8,
            "error_count": 2,
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
            "aggregation_day": date.today().isoformat(),
        }],
    }

