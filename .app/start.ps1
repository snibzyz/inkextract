# ASCII-only on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI when no BOM
# is present, which corrupts non-ASCII text and breaks the parser. Keep this
# file 100% ASCII so it runs reliably on any Windows machine / locale.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ""
    Write-Host "[X] Not installed yet" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please double-click the install .bat first." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

# ============================================================
# AUTO-UPDATE: check and download updates from the GitHub releases API.
# - No Git required
# - Runs silently; on failure we just continue and launch the app
# ============================================================
function Invoke-AutoUpdate {
    try {
        Write-Host "Checking for updates..." -ForegroundColor DarkCyan
        & ".venv\Scripts\python.exe" -m ".app.updater" 2>&1 | Out-Null

        # Re-install requirements as a safety net in case they changed.
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Re-installing requirements (safety check)..." -ForegroundColor Cyan
            & ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet 2>&1 | Out-Null
        }
    } catch {
        # Stay silent - we never want auto-update to block app startup.
    }
}

Invoke-AutoUpdate

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "        INKEXTRACT - Translation Toolkit" -ForegroundColor Yellow
Write-Host "============================================================"
Write-Host "Starting app..."
Write-Host "Please wait - your browser will open automatically."
Write-Host ""
Write-Host "(If it does not open, copy the URL shown below into a browser.)" -ForegroundColor Yellow
Write-Host "To quit: press Ctrl+C" -ForegroundColor Yellow
Write-Host "============================================================"
Write-Host ""

& ".venv\Scripts\python.exe" -m streamlit run ".app\app.py"
