# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re

from app.repository import installation_hash
from app.config import Settings


def test_installation_hash_is_keyed_and_does_not_contain_source():
    source = "installation_0123456789abcdef"
    first = installation_hash("a" * 32, source)
    second = installation_hash("b" * 32, source)
    assert first != second
    assert source not in first
    assert len(first) == 64


def test_migration_never_persists_raw_payload_or_installation_id():
    migration = open("migrations/001_init.sql", encoding="utf-8").read().lower()
    assert re.search(r"\binstallation_id\b", migration) is None
    assert re.search(r"\bip_address\b", migration) is None
    assert re.search(r"\bclient_ip\b", migration) is None
    assert "payload_json" not in migration
    assert "request_body" not in migration


def test_runtime_disables_http_access_logs():
    compose = open("docker-compose.yml", encoding="utf-8").read()
    caddy = open("Caddyfile", encoding="utf-8").read()
    assert compose.count("--no-access-log") == 2
    assert "127.0.0.1:9443:9443" in compose
    assert "output discard" in caddy


def test_server_row_limit_cannot_exceed_schema_limit():
    settings = Settings(
        database_url="postgresql://telemetry:test@localhost/telemetry",
        installation_hmac_secret="h" * 32,
        admin_token="a" * 32,
        max_rows=501,
    )
    try:
        settings.validate()
    except ValueError as error:
        assert "MAX_AGGREGATED_ROWS" in str(error)
    else:
        raise AssertionError("oversized row limit should be rejected")
