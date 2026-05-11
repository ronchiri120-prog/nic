"""
QuickLender — Development Setup Script
Run this once before starting the server:
    python setup_dev.py
"""
import os, sys, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))

def check(label, ok, fix=''):
    sym = '✓' if ok else '✗'
    print(f'  {sym} {label}')
    if not ok and fix:
        print(f'    → {fix}')
    return ok

def run(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd or BASE,
                          capture_output=True, text=True)

print('\n⚡ QuickLender — Dev Setup\n' + '─'*40)

# ── 1. Fix celery.py naming conflict ────────────────────────────────────────
conflict = os.path.join(BASE, 'celery.py')
if os.path.exists(conflict):
    backup = conflict + '.bak'
    shutil.move(conflict, backup)
    print(f'  ✓ Renamed celery.py → celery.py.bak (naming conflict fixed)')
    print(f'    (It shadowed the celery library — now moved out of the way)')
else:
    print(f'  ✓ No celery.py conflict')

# ── 2. Check Python version ─────────────────────────────────────────────────
import platform
ver = platform.python_version()
ok  = tuple(int(x) for x in ver.split('.')[:2]) >= (3, 10)
check(f'Python {ver}', ok, 'Use Python 3.10 or newer')

# ── 3. Check .env file ──────────────────────────────────────────────────────
env_path    = os.path.join(BASE, '.env')
env_ex_path = os.path.join(BASE, '.env.example')
if not os.path.exists(env_path) and os.path.exists(env_ex_path):
    shutil.copy(env_ex_path, env_path)
    print(f'  ✓ Created .env from .env.example')
check('.env file exists', os.path.exists(env_path),
      'Copy .env.example to .env and fill in your database credentials')

# ── 4. Check critical imports ────────────────────────────────────────────────
for pkg, import_name in [
    ('Django',     'django'),
    ('DRF',        'rest_framework'),
    ('celery',     'celery'),
    ('psycopg2',   'psycopg2'),
    ('decouple',   'decouple'),
    ('jwt',        'rest_framework_simplejwt'),
]:
    try:
        __import__(import_name)
        check(f'{pkg} installed', True)
    except ImportError:
        check(f'{pkg} installed', False, f'pip install -r requirements.txt')

# ── 5. Run migrations ───────────────────────────────────────────────────────
print('\n  Running migrations…')
result = run(f'python manage.py migrate --run-syncdb 2>&1')
if result.returncode == 0:
    print('  ✓ Migrations applied')
else:
    print(f'  ✗ Migration failed:\n{result.stdout[-500:]}\n{result.stderr[-500:]}')
    sys.exit(1)

# ── 6. Create admin user ─────────────────────────────────────────────────────
print('\n  Creating admin user…')
result = run('python manage.py createsuperuser_quick 2>&1')
print(f'  {result.stdout.strip()}')

print('\n' + '─'*40)
print('✅ Setup complete!')
print('\nStart the server:')
print('  python manage.py runserver')
print('\nLogin at:  http://127.0.0.1:8000')
print('  Email   : admin@quicklender.co.ke')
print('  Password: QuickLender@2026')
