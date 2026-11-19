from __future__ import annotations

import ipaddress

from fastapi import Request


class TrustedSourceAddress:
    """Resolve a request source without trusting client-controlled headers.

    Forwarded addresses are considered only when the socket peer belongs to an
    explicitly configured trusted network.  No address is logged or persisted.
    """

    def __init__(self, trusted_proxy_cidrs: tuple[str, ...] | list[str]):
        self.networks = tuple(
            ipaddress.ip_network(value, strict=False) for value in trusted_proxy_cidrs
        )

    def _parse(self, value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(value.strip())
        except ValueError:
            return None

    def _trusted(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return any(address.version == network.version and address in network for network in self.networks)

    def resolve(self, request: Request) -> str | None:
        peer_value = request.client.host if request.client else ""
        peer = self._parse(peer_value)
        if peer is None:
            return None

        if not self._trusted(peer):
            return str(peer)

        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if not parts or len(parts) > 20:
            return None
        chain = [self._parse(part) for part in parts]
        if any(address is None for address in chain):
            return None

        # Work from the proxy nearest the application towards the client. This
        # avoids selecting an attacker-supplied left-most value when a trusted
        # proxy has appended the real source to an existing header.
        for address in reversed(chain):
            if address is not None and not self._trusted(address):
                return str(address)
        return None
