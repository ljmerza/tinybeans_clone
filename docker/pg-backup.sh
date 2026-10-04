#!/bin/sh
# Nightly pg_dump for the circles-pg-backup service (docker-compose.prod.yml).
#
#   pg-backup.sh         loop: dump once a day at PG_BACKUP_TIME (HH:MM, in TZ)
#   pg-backup.sh once    dump now and exit (manual or pre-migrate backups)
#
# Connection settings come from the app env file (POSTGRES_HOST/USER/DB/PASSWORD).
# Dumps are custom format (-Fc) in /backups; ones older than PG_BACKUP_KEEP_DAYS
# are deleted after each successful dump.
set -eu

BACKUP_DIR=/backups
KEEP_DAYS="${PG_BACKUP_KEEP_DAYS:-14}"
AT="${PG_BACKUP_TIME:-03:30}"

dump() {
    stamp="$(date +%Y%m%d-%H%M%S)"
    target="$BACKUP_DIR/circles-$stamp.dump"
    echo "$(date -Iseconds) pg_dump -> $target"
    # Write to a temp name first so a failed dump never looks like a good one.
    if PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump -Fc \
        -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" \
        -U "${POSTGRES_USER:-circles}" "${POSTGRES_DB:-circles}" > "$target.partial"; then
        mv "$target.partial" "$target"
        echo "$(date -Iseconds) done ($(du -h "$target" | cut -f1))"
        find "$BACKUP_DIR" -maxdepth 1 -name 'circles-*.dump' -mtime +"$((KEEP_DAYS - 1))" -print -delete
    else
        rm -f "$target.partial"
        echo "$(date -Iseconds) pg_dump FAILED" >&2
        return 1
    fi
}

mkdir -p "$BACKUP_DIR"

if [ "${1:-}" = "once" ]; then
    dump
    exit $?
fi

echo "$(date -Iseconds) circles-pg-backup: daily at $AT ($(date +%Z)), keeping $KEEP_DAYS days"
last=""
while true; do
    today="$(date +%Y-%m-%d)"
    if [ "$(date +%H:%M)" = "$AT" ] && [ "$last" != "$today" ]; then
        # A failed dump is logged and retried tomorrow; it doesn't stop the loop.
        dump || true
        last="$today"
    fi
    sleep 20
done
