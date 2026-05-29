#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh  —  Barangay Official Attendance Registry
# Full VPS deployment script (Ubuntu 22.04 / 24.04)
# Run as: sudo bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config — edit these before running ───────────────────────────────────────
APP_DIR="/var/www/boar"
APP_USER="boar"
DOMAIN="yourdomain.com"            # ← change to your domain or VPS IP
DB_NAME="boar_db"
DB_USER="boar_user"
DB_PASS="$(openssl rand -base64 24)"  # auto-generated password
PYTHON="python3.11"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BOAR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

[[ $EUID -ne 0 ]] && err "Run as root: sudo bash deploy.sh"

# ── 1. System update & packages ───────────────────────────────────────────────
log "Updating system packages..."
apt-get update -q && apt-get upgrade -yq
apt-get install -yq \
    python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib \
    nginx certbot python3-certbot-nginx \
    git curl wget build-essential libpq-dev \
    supervisor ufw fail2ban

# ── 2. Firewall ───────────────────────────────────────────────────────────────
log "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── 3. PostgreSQL ─────────────────────────────────────────────────────────────
log "Setting up PostgreSQL..."
systemctl enable postgresql --now
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null || \
    warn "Database ${DB_NAME} already exists."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

# ── 4. App user ───────────────────────────────────────────────────────────────
log "Creating app user: ${APP_USER}..."
id "${APP_USER}" &>/dev/null || useradd -m -s /bin/bash "${APP_USER}"
mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:www-data" "${APP_DIR}"
chmod -R 755 "${APP_DIR}"

# ── 5. Python virtualenv & packages ──────────────────────────────────────────
log "Creating Python virtualenv..."
sudo -u "${APP_USER}" bash -c "
    cd ${APP_DIR}
    ${PYTHON} -m venv venv
    venv/bin/pip install --upgrade pip wheel
    venv/bin/pip install -r requirements.txt
"

# ── 6. Environment file ───────────────────────────────────────────────────────
log "Writing .env file..."
SECRET_KEY="$(openssl rand -base64 50 | tr -d '\n')"
cat > "${APP_DIR}/.env" << ENV
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}
DB_ENGINE=postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=localhost
DB_PORT=5432
BARANGAY_NAME=Brgy. San Jose
BARANGAY_CITY=Surigao City
BARANGAY_PROVINCE=Surigao del Norte
ENV
chmod 600 "${APP_DIR}/.env"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

# ── 7. Django setup ───────────────────────────────────────────────────────────
log "Running Django migrations & setup..."
sudo -u "${APP_USER}" bash -c "
    cd ${APP_DIR}
    set -a; source .env; set +a
    venv/bin/python manage.py migrate --noinput
    venv/bin/python manage.py collectstatic --noinput
    echo 'from django.contrib.auth.models import User; \
          User.objects.filter(username=\"admin\").exists() or \
          User.objects.create_superuser(\"admin\",\"admin@boar.local\",\"Admin@BOAR2025!\")' \
    | venv/bin/python manage.py shell
"

# ── 8. Log directory ──────────────────────────────────────────────────────────
log "Creating log directory..."
mkdir -p /var/log/boar
chown "${APP_USER}:www-data" /var/log/boar

# ── 9. systemd service ────────────────────────────────────────────────────────
log "Installing systemd service..."
cp "${APP_DIR}/boar.service" /etc/systemd/system/boar.service
systemctl daemon-reload
systemctl enable boar
systemctl restart boar

# ── 10. Nginx ─────────────────────────────────────────────────────────────────
log "Configuring Nginx..."
sed "s/yourdomain.com/${DOMAIN}/g" "${APP_DIR}/nginx.conf" > /etc/nginx/sites-available/boar
ln -sf /etc/nginx/sites-available/boar /etc/nginx/sites-enabled/boar
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── 11. Fail2ban ──────────────────────────────────────────────────────────────
log "Enabling Fail2ban..."
systemctl enable fail2ban --now

# ── 12. Summary ───────────────────────────────────────────────────────────────
log "═══════════════════════════════════════════════════════════"
log "  BOAR System Deployment Complete!"
log "═══════════════════════════════════════════════════════════"
echo ""
echo "  URL:          http://${DOMAIN}  (add SSL with: certbot --nginx -d ${DOMAIN})"
echo "  Admin login:  admin / Admin@BOAR2025!"
echo "  DB Password:  ${DB_PASS}"
echo ""
warn "IMPORTANT: Change the admin password immediately after first login!"
warn "           Run: sudo certbot --nginx -d ${DOMAIN}  for HTTPS"
log "═══════════════════════════════════════════════════════════"
