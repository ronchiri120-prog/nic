#!/bin/bash
# ═══════════════════════════════════════════════════════
#  QuickLender — Linux/Mac Start Script
# ═══════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "\n${CYAN} ⚡ QuickLender LMS — Starting...${NC}"
echo -e " ════════════════════════════════\n"

# Navigate to backend
cd "$(dirname "$0")/backend"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo " Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install requirements
echo " Checking dependencies..."
pip install -r requirements.txt --quiet --upgrade

# Run migrations
echo " Running migrations..."
python manage.py migrate || python manage.py migrate --run-syncdb

# Seed GL accounts
python manage.py seed_chart_of_accounts 2>/dev/null || true

# Create default admin
python manage.py createsuperuser_quick 2>/dev/null || true

echo -e "\n ════════════════════════════════════════════"
echo -e "  ${GREEN}✓${NC}  QuickLender is running!"
echo -e "  ${GREEN}✓${NC}  Open: ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  ${GREEN}✓${NC}  Login: admin@quicklender.co.ke"
echo -e "  ${GREEN}✓${NC}  Password: QuickLender@2026"
echo -e " ════════════════════════════════════════════\n"

python manage.py runserver 0.0.0.0:8000
