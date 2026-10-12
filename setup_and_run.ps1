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

Write-Host "`n[2/5] Setting up MariaDB/MySQL database..." -ForegroundColor Yellow
$resetDatabase = Read-Host "This deletes every row in the configured database. Type RESET to confirm; press Enter to keep existing data"
if ($resetDatabase -ceq "RESET") {
    python backend\scripts\seed_test_accounts.py --reset
} else {
    python backend\scripts\seed_test_accounts.py
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Failed to seed database roles and test accounts." -ForegroundColor Red
    exit 1
}

python backend\scripts\add_dummy_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Failed to populate dummy marketplace data." -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/5] Installing and building React web frontend..." -ForegroundColor Yellow
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

Write-Host "`n[4/5] Optional Flutter Android build..." -ForegroundColor Yellow
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

Write-Host "`n[5/5] Starting backend API..." -ForegroundColor Yellow
Write-Host "[*] Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "[*] In another terminal, run: cd web; npm run dev" -ForegroundColor Green
python server.py
