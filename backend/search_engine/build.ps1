$ErrorActionPreference = "Stop"
$crate = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $crate "target\release\catalog-matcher.exe"
$destination = Join-Path $crate "bin\catalog_matcher.exe"

cargo build --manifest-path (Join-Path $crate "Cargo.toml") --release
New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
Copy-Item -LiteralPath $target -Destination $destination -Force
Write-Host "Built catalog matcher at $destination"
