"""Explicit opt-in consent and anonymous installation identity."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid


# Exact values from telemetry-server/.env.example and app/config.py.
CONSENT_VERSION_V1 = "2026-09"
CONSENT_VERSION_V2 = "v2.2026-09"
CONSENT_VERSIONS = {1: CONSENT_VERSION_V1, 2: CONSENT_VERSION_V2}
# Local disclosure acknowledgement, not a wire Schema or Consent version.
UPLOAD_DISCLOSURE = "channel-exit-upload-2026-10"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            json.dump(value, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class TelemetryConsent:
    """Persisted opt-in state; a missing or invalid file always means denied."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / "telemetry-consent.json"
        self.identity_path = self.directory / "telemetry-installation.json"
        self.lock = threading.RLock()
        self._installation_id = self._load_or_create_installation_id()

    def _load_or_create_installation_id(self) -> str:
        try:
            value = json.loads(self.identity_path.read_text(encoding="utf-8"))
            identity = value.get("installation_id")
            if isinstance(identity, str) and identity.startswith("installation_") and len(identity) == 45:
                return identity
        except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        identity = "installation_" + uuid.uuid4().hex
        _atomic_json(self.identity_path, {"schema": 1, "installation_id": identity})
        return identity

    def installation_id(self) -> str:
        """Return the local random identifier.  Callers must never log it."""
        return self._installation_id

    def state(self) -> dict:
        with self.lock:
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
                return {"consent": False, "schema_version": 2, "consent_version": CONSENT_VERSION_V2}
        schema_version = value.get("schema_version")
        consent_version = value.get("consent_version")
        valid = (
            value.get("consent") is True
            and schema_version in CONSENT_VERSIONS
            and consent_version == CONSENT_VERSIONS[schema_version]
        )
        return {
            "consent": bool(valid),
            "upload_disclosure": value.get("upload_disclosure"),
            "schema_version": schema_version if schema_version in CONSENT_VERSIONS else 2,
            "consent_version": consent_version if isinstance(consent_version, str) else CONSENT_VERSION_V2,
        }

    def is_granted(self, schema_version: int = 2) -> bool:
        state = self.state()
        return (
            state["consent"] is True
            and state["schema_version"] == schema_version
            and state["consent_version"] == CONSENT_VERSIONS.get(schema_version)
        )

    def upload_is_granted(self, schema_version: int = 2) -> bool:
        return self.is_granted(schema_version) and self.state().get("upload_disclosure") == UPLOAD_DISCLOSURE

    def grant(self, schema_version: int, consent_version: str, *, allow_upload: bool = False) -> None:
        expected = CONSENT_VERSIONS.get(schema_version)
        if expected is None or consent_version != expected:
            raise ValueError("Consent 版本必须与对应 schema 的服务端配置精确匹配。")
        self._save(True, schema_version, consent_version, allow_upload=allow_upload)

    def withdraw(self) -> None:
        current = self.state()
        self._save(False, current["schema_version"], current["consent_version"])

    def _save(self, consent: bool, schema_version: int, consent_version: str, *, allow_upload: bool = False) -> None:
        with self.lock:
            _atomic_json(self.path, {
                "schema": 1,
                "consent": bool(consent),
                "schema_version": int(schema_version),
                "consent_version": str(consent_version),
                "upload_disclosure": UPLOAD_DISCLOSURE if consent and allow_upload else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
