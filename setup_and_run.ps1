# Setup & Run script for Turacoz Bid Tool

$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Turacoz Bid Tool Setup: Backend + Web + Mobile " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n[1/5] Installing backend requirements..." -ForegroundColor Yellow
pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Failed to install backend packages." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/4] Database setup..." -ForegroundColor Yellow
Write-Host "Ensure MariaDB/MySQL is running, the configured database exists, and the repository .env has production-safe credentials." -ForegroundColor Gray

Write-Host "`n[3/4] Installing and building React web frontend..." -ForegroundColor Yellow
Push-Location web
npm install
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "[-] npm install failed." -ForegroundColor Red
    exit 1
}
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "[-] React build failed." -ForegroundColor Red
    exit 1
}
Pop-Location

Write-Host "`n[4/4] Optional Flutter Android build..." -ForegroundColor Yellow
$rebuild = Read-Host "Do you want to build the Flutter Android APK? (y/N)"
if ($rebuild -eq 'y' -or $rebuild -eq 'Y') {
    $apiUrl = Read-Host "API URL reachable from the Android device [http://10.0.2.2:8000]"
    if ([string]::IsNullOrWhiteSpace($apiUrl)) { $apiUrl = "http://10.0.2.2:8000" }
    Push-Location mobile
    flutter pub get
    flutter build apk --release --dart-define=API_BASE_URL=$apiUrl
    Pop-Location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Flutter Android build encountered errors." -ForegroundColor Red
    }
}

Write-Host "`nStarting backend API..." -ForegroundColor Yellow
Write-Host "[*] Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "[*] In another terminal, run: cd web; npm run dev" -ForegroundColor Green
python server.py
