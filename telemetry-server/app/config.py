# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    installation_hmac_secret: str
    admin_token: str
    max_body_bytes: int = 1_048_576
    max_rows: int = 500
    public_rate_limit_per_minute: int = 60
    admin_rate_limit_per_minute: int = 30
    consent_version_v1: str = "2026-09"
    consent_version_v2: str = "v2.2026-09"
    geoip_database_path: str = "/geoip/dbip-country-lite.mmdb"
    trusted_proxy_cidrs: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            database_url=os.environ["DATABASE_URL"],
            installation_hmac_secret=os.environ["INSTALLATION_HMAC_SECRET"],
            admin_token=os.environ["ADMIN_TOKEN"],
            max_body_bytes=_positive_int("MAX_BODY_BYTES", 1_048_576),
            max_rows=_positive_int("MAX_AGGREGATED_ROWS", 500),
            public_rate_limit_per_minute=_positive_int("PUBLIC_RATE_LIMIT_PER_MINUTE", 60),
            admin_rate_limit_per_minute=_positive_int("ADMIN_RATE_LIMIT_PER_MINUTE", 30),
            consent_version_v1=os.getenv("CONSENT_VERSION_V1", "2026-09"),
            consent_version_v2=os.getenv("CONSENT_VERSION_V2", "v2.2026-09"),
            geoip_database_path=os.getenv(
                "GEOIP_DATABASE_PATH", "/geoip/dbip-country-lite.mmdb"
            ),
            trusted_proxy_cidrs=tuple(
                item.strip()
                for item in os.getenv("TRUSTED_PROXY_CIDRS", "").split(",")
                if item.strip()
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must reference PostgreSQL")
        if len(self.installation_hmac_secret) < 32:
            raise ValueError("INSTALLATION_HMAC_SECRET must be at least 32 characters")
        if len(self.admin_token) < 32:
            raise ValueError("ADMIN_TOKEN must be at least 32 characters")
        if self.max_rows > 500:
            raise ValueError("MAX_AGGREGATED_ROWS may not exceed 500")
        if not self.consent_version_v1 or not self.consent_version_v2:
            raise ValueError("consent versions may not be empty")
        if self.consent_version_v1 == self.consent_version_v2:
            raise ValueError("schema consent versions must be distinct")
        if not self.geoip_database_path:
            raise ValueError("GEOIP_DATABASE_PATH may not be empty")
        for cidr in self.trusted_proxy_cidrs:
            try:
                ipaddress.ip_network(cidr, strict=False)
            except ValueError as error:
                raise ValueError("TRUSTED_PROXY_CIDRS contains an invalid network") from error
