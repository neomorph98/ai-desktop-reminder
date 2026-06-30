# setup.ps1 - One-click environment setup for "AI Desktop Reminder" (incl. Lively Wallpaper)
# Usage:  ./setup.ps1   (or double-click setup.bat)
# Note: messages are in English on purpose so the script stays ASCII-only and runs
#       reliably regardless of console encoding. Chinese docs are in README.md.

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Info($m) { Write-Host "[*]  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!]  $m" -ForegroundColor Yellow }
function Err($m)  { Write-Host "[X]  $m" -ForegroundColor Red }

Write-Host "=== AI Desktop Reminder - environment setup ===" -ForegroundColor Magenta

# 1) Python
Info "Checking Python ..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Err "Python not found. Install Python 3.10+ (https://www.python.org/downloads/) and retry."
    exit 1
}
Ok ("Found " + (python --version))

# 2) Dependencies
Info "Installing Python dependencies (requirements.txt) ..."
python -m pip install -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Err "pip install failed - check your network / pip."; exit 1 }
Ok "Dependencies installed"

# 3) .env
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
    Ok ".env already exists, skipping"
} else {
    Copy-Item (Join-Path $Root '.env.example') $envFile
    Ok "Created .env from .env.example"
    Warn "Put your LLM API key into .env (e.g. MINIMAX_API_KEY / DEEPSEEK_API_KEY)"
}

# 4) Lively Wallpaper
$livelyExe = Join-Path $env:ProgramFiles 'Lively Wallpaper\livelycu.exe'
Info "Checking Lively Wallpaper ..."
if (Test-Path $livelyExe) {
    Ok "Lively already installed"
} elseif (Get-Command winget -ErrorAction SilentlyContinue) {
    Info "Installing Lively via winget (rocksdanister.LivelyWallpaper) ..."
    try {
        winget install -e --id rocksdanister.LivelyWallpaper --accept-package-agreements --accept-source-agreements
    } catch {
        Warn ("winget install error: " + $_.Exception.Message)
    }
    if (Test-Path $livelyExe) {
        Ok "Lively installed"
    } else {
        Warn "winget finished but livelycu.exe not in the default path (maybe the Store build - different path)."
    }
} else {
    Warn "winget not found. Install Lively manually:"
    Write-Host "    Microsoft Store: https://apps.microsoft.com/detail/9ntm2qc6qws7"
    Write-Host "    GitHub releases: https://github.com/rocksdanister/lively/releases"
}

# 5) Apply wallpaper (best effort: wallpaper/ contains LivelyInfo.json, so setwp --file works)
if (Test-Path $livelyExe) {
    $wp = Join-Path $Root 'wallpaper'
    Info "Applying wallpaper via Lively ..."
    try {
        & $livelyExe setwp --file "$wp"
        Ok "Wallpaper apply attempted (wallpaper/)"
    } catch {
        Warn ("Auto-apply failed: " + $_.Exception.Message)
        Write-Host "    Manual: open Lively -> Add Wallpaper -> paste http://127.0.0.1:8765/"
    }
} else {
    Warn "Skipped wallpaper apply (Lively not ready). After install, add http://127.0.0.1:8765/ in Lively."
}

# 6) Final steps
Write-Host ""
Write-Host "=== Done. 3 steps left ===" -ForegroundColor Magenta
Write-Host "  1. Open .env and fill in your LLM API key"
Write-Host "  2. Run:  python main.py"
Write-Host "  3. In Lively, enable 'mouse input' for this wallpaper so you can click 'done'"
Write-Host ""
