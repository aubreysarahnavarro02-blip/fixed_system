#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# update.sh — Zero-downtime update for BOAR System
# Run from: /var/www/boar  as the boar user or root
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
APP_DIR="/var/www/boar"
GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[UPDATE]${NC} $1"; }

cd "${APP_DIR}"

log "Pulling latest code..."
git pull origin main

log "Installing dependencies..."
venv/bin/pip install -r requirements.txt --quiet

log "Running migrations..."
set -a; source .env; set +a
venv/bin/python manage.py migrate --noinput

log "Collecting static files..."
venv/bin/python manage.py collectstatic --noinput

log "Reloading gunicorn (zero-downtime)..."
systemctl reload boar 2>/dev/null || systemctl restart boar

log "Update complete! ✓"
