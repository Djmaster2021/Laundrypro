#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/backup.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL no definido" >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/var/backups/laundrypro}"
RESTORE_DB_NAME="${RESTORE_DB_NAME:-laundrypro_restore_check}"
RESTORE_RETENTION="${RESTORE_RETENTION:-6}"

LATEST_DUMP="$BACKUP_DIR/latest.dump"
if [[ ! -f "$LATEST_DUMP" ]]; then
  echo "No existe $LATEST_DUMP" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/restore_test_${STAMP}.log"

TMP_CONN="${DATABASE_URL%/*}/postgres"

dropdb --if-exists --dbname="$TMP_CONN" "$RESTORE_DB_NAME"
createdb --dbname="$TMP_CONN" "$RESTORE_DB_NAME"
pg_restore --clean --if-exists --no-owner --no-acl --dbname="${DATABASE_URL%/*}/$RESTORE_DB_NAME" "$LATEST_DUMP"

TABLE_COUNT="$(psql "${DATABASE_URL%/*}/$RESTORE_DB_NAME" -tAc "select count(*) from information_schema.tables where table_schema='public';")"
echo "[$(date --iso-8601=seconds)] restore_ok tables_public=$TABLE_COUNT dump=$LATEST_DUMP" | tee "$LOG_FILE"

dropdb --dbname="$TMP_CONN" "$RESTORE_DB_NAME"

find "$BACKUP_DIR" -type f -name 'restore_test_*.log' | sort | head -n -"$RESTORE_RETENTION" | xargs -r rm -f

echo "Restore test completado. Log: $LOG_FILE"
