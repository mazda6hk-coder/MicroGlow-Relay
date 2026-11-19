#!/bin/sh
set -eu

if [ -z "${TUNNEL_PEER_CIDR:-}" ]; then
    route_hex="$(awk '$2 == "00000000" { print $3; exit }' /proc/net/route)"
    if [ "${#route_hex}" -ne 8 ]; then
        echo 'Cannot identify the Docker host gateway for Tunnel trust' >&2
        exit 1
    fi
    case "$route_hex" in
        *[!0-9A-Fa-f]*)
            echo 'Invalid Docker gateway route' >&2
            exit 1
            ;;
    esac
    set -- $(printf '%s' "$route_hex" | sed 's/../& /g')
    TUNNEL_PEER_CIDR="$(printf '%d.%d.%d.%d/32' "0x$4" "0x$3" "0x$2" "0x$1")"
fi

export TUNNEL_PEER_CIDR
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
