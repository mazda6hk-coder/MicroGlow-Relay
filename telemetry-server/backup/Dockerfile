FROM postgres:16-alpine
COPY backup.sh /usr/local/bin/telemetry-backup
RUN chmod 0555 /usr/local/bin/telemetry-backup
ENTRYPOINT ["/usr/local/bin/telemetry-backup"]

