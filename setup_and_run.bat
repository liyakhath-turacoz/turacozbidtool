@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Turacoz Bid Tool Setup and Launch
echo ==========================================
echo    Turacoz Bid Tool Setup: Backend + Web + Mobile
echo ==========================================

echo.
echo [1/5] Installing backend requirements...
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [-] Backend requirements install failed!
    pause
    exit /b 1
)

echo.
echo [2/5] Setting up Database...
set /p "resetDatabase=This deletes every row in the configured database. Type RESET to confirm; press Enter to keep existing data: "
if /i "%resetDatabase%"=="RESET" (
    python backend\scripts\seed_test_accounts.py --reset
) else (
    python backend\scripts\seed_test_accounts.py
)
if %errorlevel% neq 0 (
    echo.
    echo [-] Database seeding failed! Check password or ensure MariaDB/MySQL is running.
    pause
    exit /b 1
)

python backend\scripts\add_dummy_data.py
if %errorlevel% neq 0 (
    echo.
    echo [-] Seeding dummy data failed!
    pause
    exit /b 1
)

echo.
echo [3/5] Installing and building React web frontend...
cd web
call npm install
if %errorlevel% neq 0 (
    cd ..
    echo.
    echo [-] npm install failed!
    pause
    exit /b 1
)
call npm run build
if %errorlevel% neq 0 (
    cd ..
    echo.
    echo [-] React build failed!
    pause
    exit /b 1
)
cd ..

echo.
echo [4/5] Optional Flutter Android build...
set /p "rebuild=Do you want to build the Flutter Android APK? (y/N): "
if /i "%rebuild%"=="y" (
    set /p "apiBase=API URL reachable from the Android device [http://10.0.2.2:8000]: "
    if "!apiBase!"=="" set "apiBase=http://10.0.2.2:8000"
    cd mobile
    call flutter pub get
    call flutter build apk --release --dart-define=API_BASE_URL=!apiBase!
    cd ..
)

echo.
echo [5/5] Starting backend API...
echo [*] Backend: http://localhost:8000
echo [*] In another terminal, run: cd web ^&^& npm run dev
python server.py
pause
