#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  QuickLender — Fresh Server Installation
#  Tested on Ubuntu 22.04 LTS
#  Usage: sudo bash install.sh
# ═══════════════════════════════════════════════════════════

set -euo pipefail

DOMAIN="${DOMAIN:-quicklender.co.ke}"
DB_PASS="${DB_PASS:-$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24)}"
APP_DIR="/var/www/quicklender"

echo "⚡ QuickLender Server Installation"
echo "   Domain: $DOMAIN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── System packages ──────────────────────────────────────
apt-get update -qq
apt-get install -y -qq \
    python3.11 python3.11-venv python3.11-dev \
    postgresql-15 postgresql-client-15 \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl wget build-essential \
    libpq-dev libssl-dev \
    supervisor \
    fail2ban \
    ufw

# ─── System user ──────────────────────────────────────────
useradd --system --home $APP_DIR --shell /bin/bash quicklender 2>/dev/null || true

# ─── Directories ──────────────────────────────────────────
mkdir -p $APP_DIR/{backend,frontend,static,media,logs}
mkdir -p /var/log/quicklender /var/run/quicklender /var/backups/quicklender
mkdir -p /etc/quicklender
chown -R quicklender:quicklender $APP_DIR /var/log/quicklender /var/run/quicklender /var/backups/quicklender

# ─── PostgreSQL setup ─────────────────────────────────────
systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE USER quicklender WITH PASSWORD '$DB_PASS';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER quicklender WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "CREATE DATABASE quicklender_db OWNER quicklender;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quicklender_db TO quicklender;"
echo "✓ PostgreSQL: quicklender_db created"

# ─── Redis setup ──────────────────────────────────────────
systemctl enable --now redis-server
echo "✓ Redis running"

# ─── Python venv ──────────────────────────────────────────
python3.11 -m venv $APP_DIR/venv
chown -R quicklender:quicklender $APP_DIR/venv
echo "✓ Python venv created"

# ─── SSL Certificate (Let's Encrypt) ─────────────────────
certbot certonly --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || \
    echo "⚠  SSL cert skipped (run certbot manually after DNS is ready)"

# ─── Nginx ────────────────────────────────────────────────
cp $APP_DIR/deployment/nginx/quicklender.conf /etc/nginx/sites-available/quicklender
ln -sf /etc/nginx/sites-available/quicklender /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl enable --now nginx
echo "✓ Nginx configured"

# ─── Systemd services ─────────────────────────────────────
cp $APP_DIR/deployment/scripts/quicklender-api.service    /etc/systemd/system/
cp $APP_DIR/deployment/scripts/quicklender-worker.service /etc/systemd/system/
cp $APP_DIR/deployment/scripts/quicklender-beat.service   /etc/systemd/system/
systemctl daemon-reload
systemctl enable quicklender-api quicklender-worker quicklender-beat
echo "✓ Systemd services installed"

# ─── Firewall ─────────────────────────────────────────────
ufw --force enable
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "✓ UFW firewall enabled (80, 443, SSH)"

# ─── Fail2ban ─────────────────────────────────────────────
cat > /etc/fail2ban/jail.d/quicklender.conf << 'FAIL2BAN'
[nginx-req-limit]
enabled  = true
filter   = nginx-req-limit
logpath  = /var/log/nginx/quicklender.error.log
maxretry = 10
findtime = 600
bantime  = 7200

[nginx-http-auth]
enabled  = true
logpath  = /var/log/nginx/quicklender.error.log
maxretry = 5
bantime  = 3600
FAIL2BAN
systemctl enable --now fail2ban
echo "✓ Fail2ban configured"

# ─── Write .env ───────────────────────────────────────────
cat > /etc/quicklender/.env << ENV
DJANGO_ENV=production
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN
DB_NAME=quicklender_db
DB_USER=quicklender
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
REDIS_URL=redis://localhost:6379/0
MPESA_ENV=sandbox
ENV
chmod 600 /etc/quicklender/.env
chown quicklender:quicklender /etc/quicklender/.env
echo "✓ /etc/quicklender/.env created"

# ─── Cron: SSL auto-renew ─────────────────────────────────
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
echo "✓ SSL auto-renewal cron set"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Server installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit /etc/quicklender/.env (add M-Pesa, AT, email credentials)"
echo "  2. sudo ./deployment/scripts/deploy.sh  (deploy the app)"
echo "  3. Access: https://$DOMAIN"
echo ""
echo "DB Password (save this!): $DB_PASS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
