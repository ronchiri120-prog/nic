# ⚡ QuickLender — Microfinance LMS

A complete Loan Management System for Kenyan microfinance institutions.

## Tech Stack
| Layer    | Technology |
|----------|-----------|
| Backend  | Django 4.2 + PostgreSQL + Celery + Redis |
| Frontend | Vanilla HTML / CSS / JS (no build step) |
| Payments | Safaricom Daraja (M-Pesa STK, B2C, C2B) |
| SMS      | Africa's Talking |
| Auth     | JWT (SimpleJWT) + 2FA TOTP |

## Quick Start

### Windows
```
Double-click start.bat
```

### Linux / Mac
```bash
bash start.sh
```

### Manual
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env          # Edit credentials
python manage.py migrate
python manage.py createsuperuser_quick
python manage.py runserver
```

Open **http://127.0.0.1:8000** → Login: `admin@quicklender.co.ke` / `QuickLender@2026`

## Default Credentials
| Field    | Value |
|----------|-------|
| Email    | admin@quicklender.co.ke |
| Password | QuickLender@2026 |
| Role     | Super Admin (full access) |

## M-Pesa (Daraja Sandbox)
Already configured with sandbox credentials in `.env`.
Test the connection: **Settings → M-Pesa → Test Connection**

## User Roles
| Role | Access Level |
|------|-------------|
| SUPER_ADMIN | Everything |
| GM / RM | Full management |
| BRANCH_MANAGER | Branch operations |
| RO (Relationship Officer) | Leads, customers, loans |
| BA (Brand Ambassador) | Create leads only |
| LOAN_OFFICER / CREDIT_OFFICER | Loans, customers |
| COLLECTIONS / COLLECTIONS_MGR | Collections workflow |
| SURGE_TEAM | Collections only |
| ACCOUNTANT | Accounting, reports |
| HOP / HOP_ASST | Products, settings |
| BDM / ASST_BDM / BDO | Business development |
| MARKETING_MGR / MARKETING_ASST | Leads, reports |

## Lead Origination Flow
```
BA captures Lead → RO qualifies → RO converts to Customer → Loan initiated
```

## Pages (21)
Dashboard · Leads · Reference Check · Customers · Loans · Applications ·
Payments · M-Pesa · Accounting · Branches · Allocations · Collections ·
Assets · Groups · Reports · Performance · Notifications · Staff · Settings · Profile

## Production Deployment
See `SETUP_PRODUCTION.md`
