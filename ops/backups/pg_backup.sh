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
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="$BACKUP_DIR/laundrypro_${STAMP}.dump"
LATEST_LINK="$BACKUP_DIR/latest.dump"

pg_dump --format=custom --no-owner --no-acl --dbname="$DATABASE_URL" --file="$OUTPUT_FILE"
ln -sfn "$OUTPUT_FILE" "$LATEST_LINK"

find "$BACKUP_DIR" -type f -name 'laundrypro_*.dump' -mtime +"$RETENTION_DAYS" -delete

echo "Backup generado: $OUTPUT_FILE"
