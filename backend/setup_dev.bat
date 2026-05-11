@echo off
echo.
echo ⚡ QuickLender - Dev Setup
echo ─────────────────────────────────────────
echo.

REM Fix celery.py naming conflict (shadows celery library)
IF EXIST celery.py (
    echo   Renaming celery.py to celery.py.bak to fix naming conflict...
    ren celery.py celery.py.bak
    echo   ✓ Done. celery.py renamed to celery.py.bak
) ELSE (
    echo   ✓ No celery.py conflict
)

REM Copy .env if missing
IF NOT EXIST .env (
    IF EXIST .env.example (
        copy .env.example .env
        echo   ✓ Created .env from .env.example
        echo   ⚠ Edit .env with your database credentials before continuing
        pause
    )
)

REM Install requirements
echo.
echo   Installing requirements...
pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo   ✗ pip install failed. Try: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Run migrations
echo.
echo   Running migrations...
python manage.py migrate
IF ERRORLEVEL 1 (
    echo   ✗ migrate failed. Check your database connection in .env
    pause
    exit /b 1
)

REM Create admin user
echo.
python manage.py createsuperuser_quick

echo.
echo ─────────────────────────────────────────
echo ✅ Setup complete!
echo.
echo Start the server:
echo   python manage.py runserver
echo.
echo Login at: http://127.0.0.1:8000
echo   Email   : admin@quicklender.co.ke
echo   Password: QuickLender@2026
echo.
pause
