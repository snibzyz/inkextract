# ASCII-only on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI when no BOM
# is present, which corrupts non-ASCII text and breaks the parser. Keep this
# file 100% ASCII so it runs reliably on any Windows machine / locale.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot\..

function Write-Banner {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "        INKEXTRACT - Installer" -ForegroundColor Cyan
    Write-Host "============================================================"
    Write-Host ""
}

function Write-Step($n, $msg) {
    Write-Host "[$n] $msg" -ForegroundColor Green
}

function Write-Err($msg) {
    Write-Host ""
    Write-Host "[X] $msg" -ForegroundColor Red
    Write-Host ""
}

Write-Banner

# --- 1. Find Python ---
Write-Step "1/4" "Checking Python..."

$pythonCmd = $null

if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $v = & py -3 --version 2>&1
    if ($LASTEXITCODE -eq 0) { $pythonCmd = "py -3" }
}
if (-not $pythonCmd -and (Get-Command "python" -ErrorAction SilentlyContinue)) {
    $v = & python --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $v -match "Python 3") { $pythonCmd = "python" }
}
if (-not $pythonCmd -and (Get-Command "python3" -ErrorAction SilentlyContinue)) {
    $pythonCmd = "python3"
}

if (-not $pythonCmd) {
    Write-Host "   Python not found - trying winget..." -ForegroundColor Yellow
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
        # refresh path
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command "py" -ErrorAction SilentlyContinue) { $pythonCmd = "py -3" }
        elseif (Get-Command "python" -ErrorAction SilentlyContinue) { $pythonCmd = "python" }
    }
}

if (-not $pythonCmd) {
    Write-Err "Python not found and auto-install failed."
    Write-Host "Please follow these steps:" -ForegroundColor Yellow
    Write-Host "  1. Open https://www.python.org/downloads/"
    Write-Host "  2. Download Python (version 3.12 or newer)"
    Write-Host "  3. During install, CHECK the box 'Add Python to PATH' before clicking Install"
    Write-Host "  4. After install finishes, double-click the install .bat again"
    Write-Host ""
    Start-Process "https://www.python.org/downloads/"
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "   Found Python: $pythonCmd" -ForegroundColor Green

# --- 2. Create venv ---
Write-Step "2/4" "Preparing environment..."

if (-not (Test-Path ".venv")) {
    Invoke-Expression "$pythonCmd -m venv .venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create .venv"
        Read-Host "Press Enter to close"
        exit 1
    }
}

# --- 3. Install packages ---
$streamlitOk = & ".venv\Scripts\python.exe" -c "import streamlit" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Step "3/4" "Components already installed, skipping..."
} else {
    Write-Step "3/4" "Installing components (may take 1-3 minutes)..."
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
    $pipOut = & ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet --disable-pip-version-check 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ($pipOut -match "WinError 32") {
            Write-Err "A program is currently using .venv"
            Write-Host "Please close any running app (e.g. the start .bat) and try again." -ForegroundColor Yellow
        } else {
            Write-Err "Failed to install components - check your internet connection and try again."
            Write-Host ($pipOut | Out-String)
        }
        Read-Host "Press Enter to close"
        exit 1
    }
}

# --- 4. Ensure workspace folders ---
Write-Step "4/4" "Preparing folders..."

@("workspace\0-input","workspace\1-fix","workspace\2-clean",
  "workspace\3-merge","workspace\4-separate",
  "workspace\output","workspace\vocab") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}
if (-not (Test-Path ".config")) { New-Item -ItemType Directory -Path ".config" -Force | Out-Null }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Install complete!" -ForegroundColor Green
Write-Host ""
Write-Host "   Double-click the start .bat to launch the app." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
