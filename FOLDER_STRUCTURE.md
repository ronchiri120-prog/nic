# QuickLender — Folder Structure

```
quicklender/
│
├── start.bat               ← Windows: double-click to run
├── start.sh                ← Linux/Mac: bash start.sh
├── docker-compose.yml      ← Docker full-stack deployment
├── README.md               ← Setup and usage guide
├── SETUP_PRODUCTION.md     ← Production deployment guide
├── FOLDER_STRUCTURE.md     ← This file
│
├── backend/                ← Django 4.2 API server
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                ← Credentials (copy from .env.example)
│   ├── .env.example        ← Template for credentials
│   ├── schema.sql          ← PostgreSQL schema reference
│   │
│   ├── quicklender_project/
│   │   ├── settings.py          ← Entry point (loads dev or prod)
│   │   ├── settings_modules/
│   │   │   ├── base.py          ← Shared settings
│   │   │   ├── development.py   ← Dev overrides (DEBUG=True)
│   │   │   └── production.py    ← Prod overrides (DEBUG=False)
│   │   ├── urls.py         ← Root URL config + frontend serving
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── apps/               ← Django applications
│   │   ├── accounts/       ← Users, roles, JWT auth, 2FA, permissions
│   │   ├── customers/      ← Customer CRM, KYC, leads, tier system
│   │   ├── loans/          ← Loan lifecycle, products, schedules
│   │   ├── payments/       ← Payments, M-Pesa Daraja, reversals
│   │   ├── branches/       ← Regions, branches, submarkets
│   │   ├── accounting/     ← Double-entry GL, P&L, Balance Sheet
│   │   ├── reports/        ← CBK MFI reports, Excel exports
│   │   ├── notifications/  ← SMS (Africa's Talking), email, Celery
│   │   ├── groups/         ← Chama/group loans
│   │   ├── allocations/    ← Loan officer allocations & reshuffle
│   │   ├── assets/         ← Asset finance / logbook loans
│   │   └── documents/      ← Statements, agreements, demand letters
│   │
│   └── tests/              ← Unit and integration tests
│
├── frontend/               ← Vanilla HTML/CSS/JS (no build step)
│   ├── assets/
│   │   ├── css/
│   │   │   ├── variables.css    ← Design tokens & colours
│   │   │   ├── base.css         ← Layout reset, app shell
│   │   │   ├── components.css   ← Buttons, cards, tables, modals
│   │   │   ├── sidebar.css      ← Dark navy sidebar
│   │   │   └── topbar.css       ← White topbar, dropdowns
│   │   └── js/
│   │       ├── auth.js          ← JWT storage, login/logout, roles
│   │       ├── api.js           ← All API endpoint definitions
│   │       └── utils.js         ← Sidebar, modals, helpers, nav permissions
│   │
│   ├── components/
│   │   └── sidebar.html    ← (Legacy — sidebar now inlined in utils.js)
│   │
│   └── pages/              ← One folder per page (html + css + js)
│       ├── login/
│       ├── dashboard/
│       ├── leads/          ← Lead origination (BA creates, RO converts)
│       ├── reference/      ← Cross-branch duplicate check
│       ├── customers/      ← 7-tab customer profile
│       ├── loans/          ← Loan lifecycle, weekly loans
│       ├── applications/   ← Credit scoring, approve/reject
│       ├── payments/       ← Record payments, reversals, bulk upload
│       ├── mpesa/          ← M-Pesa transactions, STK, B2C, C2B
│       ├── accounting/     ← GL, P&L, Balance Sheet, Journal
│       ├── branches/       ← Regions and branches CRUD
│       ├── allocations/    ← Loan officer allocations
│       ├── collections/    ← Overdue, bulk STK/SMS, restructure
│       ├── assets/         ← Asset finance
│       ├── groups/         ← Chama/group loans
│       ├── reports/        ← Portfolio, defaulters, leads, CBK
│       ├── performance/    ← Officer targets vs actuals
│       ├── notifications/  ← SMS/email logs
│       ├── staff/          ← Staff CRUD, roles, permissions matrix
│       ├── settings/       ← Products, M-Pesa config, fiscal periods
│       └── profile/        ← Password change, 2FA, theme
│
├── deployment/             ← Production server config
│   ├── nginx/              ← Nginx config with SSL/HTTPS
│   ├── scripts/            ← Deploy, backup, rollback scripts
│   └── pgbouncer.ini       ← Connection pooling
│
└── monitoring/             ← Observability
    ├── prometheus.yml
    ├── alert_rules.yml
    └── grafana/
```

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
python -m venv venv && source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  (Windows)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser_quick
python manage.py runserver
```

Then open: **http://127.0.0.1:8000**
Login: `admin@quicklender.co.ke` / `QuickLender@2026`
