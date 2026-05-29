#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — Daily backup for BOAR System (DB + media files)
# Add to crontab: 0 2 * * * /var/www/boar/backup.sh >> /var/log/boar/backup.log 2>&1
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
APP_DIR="/var/www/boar"
BACKUP_DIR="/var/backups/boar"
DATE="$(date +%Y-%m-%d_%H-%M)"
DB_NAME="boar_db"
KEEP_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting BOAR backup..."

# Database dump
sudo -u postgres pg_dump "${DB_NAME}" | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"
echo "[$(date)] Database backed up: db_${DATE}.sql.gz"

# Media files
tar -czf "${BACKUP_DIR}/media_${DATE}.tar.gz" -C "${APP_DIR}" media/ 2>/dev/null || true
echo "[$(date)] Media backed up: media_${DATE}.tar.gz"

# Clean old backups
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${KEEP_DAYS} -delete
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] Old backups cleaned (>${KEEP_DAYS} days)."

echo "[$(date)] Backup complete. Files in ${BACKUP_DIR}"
