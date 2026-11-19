# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Local-only classification of the actual upstream URL; no host is uploaded."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


CHANNELS = frozenset({"official", "relay", "unknown"})
OFFICIAL_HOSTS_PATH = Path(__file__).with_name("official_api_hosts.json")
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def _valid_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    return (len(ascii_host) <= 253 and "." in ascii_host
            and all(_DNS_LABEL.fullmatch(label) for label in ascii_host.split("."))) or ascii_host == "localhost"


def load_official_hosts(path: Path = OFFICIAL_HOSTS_PATH) -> frozenset[str] | None:
    """Fail closed: unavailable or invalid manifests yield unknown, not relay."""
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        providers = manifest["providers"]
        if not isinstance(providers, list) or not providers:
            return None
        hosts: set[str] = set()
        for provider in providers:
            if not isinstance(provider["provider"], str) or not isinstance(provider["documentation"], str):
                return None
            listed = provider["hosts"]
            if not isinstance(listed, list) or not listed:
                return None
            for host in listed:
                if not isinstance(host, str) or host != host.lower() or not _valid_host(host):
                    return None
                hosts.add(host)
        return frozenset(hosts)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return None


def classify_call_channel(upstream_url: object, *, hosts: frozenset[str] | None = None) -> str:
    """Use an exact, case-insensitive hostname match; never infer from a model."""
    if not isinstance(upstream_url, str) or not upstream_url or any(char.isspace() for char in upstream_url):
        return "unknown"
    try:
        parsed = urlsplit(upstream_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return "unknown"
        if parsed.username or parsed.password:
            return "unknown"
        host = parsed.hostname
        port = parsed.port  # Parse even though the port does not affect classification.
        if not host or not _valid_host(host) or (port is not None and not 1 <= port <= 65535):
            return "unknown"
    except ValueError:
        return "unknown"
    official = load_official_hosts() if hosts is None else hosts
    if official is None:
        return "unknown"
    return "official" if host.casefold() in official else "relay"
