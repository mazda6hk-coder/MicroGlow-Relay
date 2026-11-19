# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import threading
from typing import Any

import maxminddb

from .schemas import ISO_ALPHA2


LOGGER = logging.getLogger("microglow.telemetry.geoip")
GEOIP_SOURCE = "GEOIP"
COUNTRY_SOURCE_GAP = "COUNTRY-SOURCE-GAP"


@dataclass(frozen=True, slots=True)
class CountryResolution:
    country_code: str | None
    country_source: str


GAP = CountryResolution(None, COUNTRY_SOURCE_GAP)


class GeoIPCountryResolver:
    """Reloadable local MMDB reader that never retains or logs query IPs."""

    def __init__(self, database_path: str | Path):
        self.path = Path(database_path)
        self._reader: Any | None = None
        self._signature: tuple[int, int] | None = None
        self._failed_signature: tuple[int, int] | None = None
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            if self._reader is not None:
                self._reader.close()
            self._reader = None
            self._signature = None

    def _current_signature(self) -> tuple[int, int] | None:
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    def _ensure_reader(self) -> Any | None:
        signature = self._current_signature()
        if signature is None:
            return None
        if self._reader is not None and signature == self._signature:
            return self._reader
        if self._reader is None and signature == self._failed_signature:
            return None
        with self._lock:
            signature = self._current_signature()
            if signature is None:
                return None
            if self._reader is not None and signature == self._signature:
                return self._reader
            try:
                # MODE_FILE avoids the optional C extension's Windows path
                # encoding limitation when the server directory is non-ASCII.
                replacement = maxminddb.open_database(self.path, mode=maxminddb.MODE_FILE)
            except Exception:
                self._failed_signature = signature
                LOGGER.warning("GeoIP database unavailable; country source gap is active")
                return None
            previous = self._reader
            self._reader = replacement
            self._signature = signature
            self._failed_signature = None
            if previous is not None:
                previous.close()
            LOGGER.info("GeoIP country database loaded")
            return replacement

    def lookup(self, source_address: str | None) -> CountryResolution:
        if not source_address:
            return GAP
        reader = self._ensure_reader()
        if reader is None:
            return GAP
        try:
            record = reader.get(source_address)
            country = record.get("country", {}) if isinstance(record, dict) else {}
            code = country.get("iso_code") if isinstance(country, dict) else None
            if code is None and isinstance(record, dict):
                code = record.get("country_code")
            if isinstance(code, str):
                code = code.upper()
            if code in ISO_ALPHA2:
                return CountryResolution(code, GEOIP_SOURCE)
        except Exception:
            # Deliberately omit the queried address and exception text. Some
            # reader errors include their input in the message.
            LOGGER.warning("GeoIP country lookup failed; country source gap is active")
        return GAP
