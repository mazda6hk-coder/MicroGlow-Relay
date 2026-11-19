#!/bin/sh
set -eu

umask 077
mkdir -p /backups

while true; do
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    temporary="/backups/.telemetry-${stamp}.dump.tmp"
    destination="/backups/telemetry-${stamp}.dump"
    if pg_dump --format=custom --no-owner --no-acl --host="$POSTGRES_HOST" \
        --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$temporary"; then
        mv "$temporary" "$destination"
        find /backups -type f -name 'telemetry-*.dump' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
        echo "backup completed at ${stamp}"
    else
        rm -f "$temporary"
        echo "backup failed at ${stamp}" >&2
    fi
    sleep "${BACKUP_INTERVAL_SECONDS:-86400}"
done

