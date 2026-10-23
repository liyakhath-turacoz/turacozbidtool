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
echo [2/4] Database setup...
echo Ensure MariaDB/MySQL is running, the configured database exists, and the repository .env has production-safe credentials.

echo.
echo [3/4] Installing and building React web frontend...
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
echo [4/4] Optional Flutter Android build...
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
echo Starting backend API...
echo [*] Backend: http://localhost:8000
echo [*] In another terminal, run: cd web ^&^& npm run dev
python server.py
pause
