# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import gzip
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Callable
from urllib.request import Request, urlopen

import maxminddb


LOGGER = logging.getLogger("microglow.telemetry.geoip_update")
SOURCE_PAGE = "https://db-ip.com/db/download/ip-to-country-lite"
LICENSE_NAME = "Creative Commons Attribution 4.0 International"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
DOWNLOAD_TEMPLATE = "https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_DATABASE_BYTES = 256 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_mmdb(path: Path) -> dict[str, object]:
    # MODE_FILE is portable across non-ASCII Windows paths and Linux mounts.
    reader = maxminddb.open_database(path, mode=maxminddb.MODE_FILE)
    try:
        metadata = reader.metadata()
        database_type = str(metadata.database_type)
        if "country" not in database_type.lower():
            raise ValueError("downloaded MMDB is not a country database")
        return {
            "database_type": database_type,
            "build_epoch": int(metadata.build_epoch),
            "ip_version": int(metadata.ip_version),
        }
    finally:
        reader.close()


def update_database(
    directory: str | Path,
    *,
    now: datetime | None = None,
    expected_compressed_sha256: str | None = None,
    opener: Callable[..., object] = urlopen,
    validator: Callable[[Path], dict[str, object]] = validate_mmdb,
) -> dict[str, object]:
    current = now or datetime.now(timezone.utc)
    month = current.astimezone(timezone.utc).strftime("%Y-%m")
    url = DOWNLOAD_TEMPLATE.format(month=month)
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    database_path = target_directory / "dbip-country-lite.mmdb"
    metadata_path = target_directory / "dbip-country-lite.metadata.json"

    if database_path.exists() and metadata_path.exists():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            if existing.get("release_month") == month and existing.get("mmdb_sha256") == _sha256(database_path):
                return {**existing, "updated": False}
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    compressed_temp: Path | None = None
    database_temp: Path | None = None
    metadata_temp: Path | None = None
    try:
        request = Request(url, headers={"User-Agent": "MicroGlow-Telemetry-GeoIP-Updater/1"})
        with opener(request, timeout=60) as response:
            headers = response.headers
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="dbip-", suffix=".mmdb.gz.part",
                dir=target_directory, delete=False,
            ) as output:
                compressed_temp = Path(output.name)
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_COMPRESSED_BYTES:
                        raise ValueError("compressed GeoIP database exceeds safety limit")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        if not compressed_temp or compressed_temp.stat().st_size == 0:
            raise ValueError("downloaded GeoIP archive is empty")
        compressed_sha256 = _sha256(compressed_temp)
        if expected_compressed_sha256 and compressed_sha256.lower() != expected_compressed_sha256.lower():
            raise ValueError("GeoIP archive checksum mismatch")

        with gzip.open(compressed_temp, "rb") as source, tempfile.NamedTemporaryFile(
            mode="wb", prefix="dbip-", suffix=".mmdb.part",
            dir=target_directory, delete=False,
        ) as output:
            database_temp = Path(output.name)
            total = 0
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DATABASE_BYTES:
                    raise ValueError("GeoIP database exceeds safety limit")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if not database_temp or database_temp.stat().st_size == 0:
            raise ValueError("decompressed GeoIP database is empty")

        database_metadata = validator(database_temp)
        last_modified = headers.get("Last-Modified")
        release_date = None
        if last_modified:
            try:
                release_date = parsedate_to_datetime(last_modified).astimezone(timezone.utc).date().isoformat()
            except (TypeError, ValueError, OverflowError):
                release_date = None
        metadata: dict[str, object] = {
            "source": "DB-IP Lite IP-to-Country",
            "source_page": SOURCE_PAGE,
            "download_url": url,
            "release_month": month,
            "release_date": release_date,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "license": LICENSE_NAME,
            "license_url": LICENSE_URL,
            "http_etag": headers.get("ETag"),
            "http_last_modified": last_modified,
            "compressed_sha256": compressed_sha256,
            "mmdb_sha256": _sha256(database_temp),
            **database_metadata,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="dbip-", suffix=".json.part",
            dir=target_directory, delete=False,
        ) as output:
            metadata_temp = Path(output.name)
            json.dump(metadata, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())

        os.replace(database_temp, database_path)
        database_temp = None
        os.replace(metadata_temp, metadata_path)
        metadata_temp = None
        return {**metadata, "updated": True}
    finally:
        for temporary in (compressed_temp, database_temp, metadata_temp):
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


def run_forever(directory: str | Path, interval_seconds: int) -> None:
    while True:
        try:
            result = update_database(
                directory,
                expected_compressed_sha256=os.getenv("DBIP_EXPECTED_SHA256") or None,
            )
            if result.get("updated"):
                LOGGER.info(
                    "DB-IP country database updated release=%s sha256=%s",
                    result.get("release_month"), result.get("mmdb_sha256"),
                )
        except Exception:
            # The previous database, if any, remains in place. Avoid logging
            # response bodies or network endpoint details from exceptions.
            LOGGER.warning("DB-IP country database update failed; retaining current database")
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the local DB-IP country database")
    parser.add_argument("--once", action="store_true")
    arguments = parser.parse_args()
    directory = os.getenv("GEOIP_DATA_DIRECTORY", "/geoip")
    interval = int(os.getenv("DBIP_UPDATE_CHECK_INTERVAL_SECONDS", "86400"))
    if interval < 3600:
        raise ValueError("DBIP_UPDATE_CHECK_INTERVAL_SECONDS must be at least 3600")
    if arguments.once:
        result = update_database(
            directory,
            expected_compressed_sha256=os.getenv("DBIP_EXPECTED_SHA256") or None,
        )
        LOGGER.info(
            "DB-IP country database ready release=%s sha256=%s",
            result.get("release_month"), result.get("mmdb_sha256"),
        )
        return 0
    run_forever(directory, interval)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
