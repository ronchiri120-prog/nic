#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  QuickLender — Zero-downtime Deploy Script
#  Usage: ./deployment/scripts/deploy.sh [version]
#  Requires: git, python3, systemd
# ═══════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ─── Config ───────────────────────────────────────────────
APP_DIR="/var/www/quicklender"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV="$APP_DIR/venv"
REPO="https://github.com/yourusername/quicklender.git"
BRANCH="${1:-main}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()    { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
warn()   { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠  $1${NC}"; }
error()  { echo -e "${RED}[$(date +'%H:%M:%S')] ✗  $1${NC}"; exit 1; }

# ─── Pre-flight checks ────────────────────────────────────
log "Starting QuickLender deploy (branch: $BRANCH)"

[[ $EUID -ne 0 ]] && error "Run as root: sudo ./deploy.sh"
[[ -d $APP_DIR ]]  || error "App dir not found: $APP_DIR  (run install.sh first)"

# ─── Backup DB before deploy ──────────────────────────────
log "Backing up database..."
BACKUP_FILE="/var/backups/quicklender/db_$TIMESTAMP.sql.gz"
mkdir -p /var/backups/quicklender
sudo -u postgres pg_dump quicklender_db | gzip > "$BACKUP_FILE"
log "  DB backup: $BACKUP_FILE"

# Keep only last 10 backups
ls -t /var/backups/quicklender/db_*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f

# ─── Pull latest code ─────────────────────────────────────
log "Pulling code from $BRANCH..."
cd $APP_DIR
sudo -u quicklender git fetch origin
sudo -u quicklender git checkout $BRANCH
sudo -u quicklender git reset --hard origin/$BRANCH
log "  Commit: $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"

# ─── Backend deps ─────────────────────────────────────────
log "Installing Python dependencies..."
sudo -u quicklender $VENV/bin/pip install -r $BACKEND_DIR/requirements.txt -q

# ─── Collect static files ─────────────────────────────────
log "Collecting static files..."
cd $BACKEND_DIR
DJANGO_ENV=production sudo -u quicklender $VENV/bin/python manage.py collectstatic --noinput -v 0

# ─── Run migrations ───────────────────────────────────────
log "Running database migrations..."
DJANGO_ENV=production sudo -u quicklender $VENV/bin/python manage.py migrate --noinput

# ─── Reload services (zero-downtime via Gunicorn HUP) ────
log "Reloading services..."
# Reload Gunicorn gracefully (keeps serving during reload)
systemctl reload quicklender-api || systemctl restart quicklender-api

# Restart workers (brief gap is acceptable)
systemctl restart quicklender-worker
sleep 2
systemctl restart quicklender-beat

# Reload Nginx (test config first)
nginx -t && systemctl reload nginx

# ─── Health check ─────────────────────────────────────────
log "Running health check..."
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://quicklender.co.ke/health/)
if [[ $HTTP_CODE == "200" ]]; then
    log "  Health check passed (HTTP $HTTP_CODE)"
else
    warn "  Health check returned HTTP $HTTP_CODE"
fi

# ─── Copy frontend ────────────────────────────────────────
log "Deploying frontend..."
rsync -av --delete $APP_DIR/frontend/ /var/www/quicklender/frontend/ --exclude '.git'

# ─── Done ─────────────────────────────────────────────────
log "══════════════════════════════════════════"
log "✅ Deploy complete!"
log "   Commit: $(git -C $APP_DIR rev-parse --short HEAD)"
log "   URL:    https://quicklender.co.ke"
log "   API:    https://quicklender.co.ke/api/docs/"
log "══════════════════════════════════════════"
