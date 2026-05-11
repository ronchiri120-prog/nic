@echo off
REM ═══════════════════════════════════════════════════════
REM  QuickLender — Windows Start Script
REM ═══════════════════════════════════════════════════════

echo.
echo  ⚡ QuickLender LMS — Starting...
echo  ════════════════════════════════
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ✗ Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Navigate to backend
cd backend

REM Install dependencies if venv missing
if not exist "venv" (
    echo  Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo  Installing dependencies...
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate.bat
)

REM Run migrations
echo  Running database migrations...
python manage.py migrate 2>nul
if errorlevel 1 (
    echo  Running initial migration...
    python manage.py migrate --run-syncdb 2>nul
)

REM Create default admin if not exists
echo  Checking admin user...
python manage.py createsuperuser_quick 2>nul

REM Start server
echo.
echo  ════════════════════════════════════════════
echo   ✓  QuickLender is running!
echo   ✓  Open: http://127.0.0.1:8000
echo   ✓  Login: admin@quicklender.co.ke
echo   ✓  Password: QuickLender@2026
echo  ════════════════════════════════════════════
echo.

python manage.py runserver 0.0.0.0:8000
pause
