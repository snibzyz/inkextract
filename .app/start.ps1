# -*- coding: utf-8 -*-
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host ""
    Write-Host "[X] ยังไม่ได้ติดตั้ง" -ForegroundColor Red
    Write-Host ""
    Write-Host "กรุณาดับเบิลคลิกไฟล์  ติดตั้ง.bat  ก่อน" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "กดปุ่ม Enter เพื่อปิด"
    exit 1
}

# ============================================================
# AUTO-UPDATE: ตรวจสอบและดาวน์โหลด update จาก GitHub releases API
# - ไม่ต้อง Git installed
# - ทำงานเงียบ ๆ — fail ก็ข้ามไปรันได้
# ============================================================
function Invoke-AutoUpdate {
    try {
        Write-Host "🔄 กำลังเช็คอัปเดต..." -ForegroundColor DarkCyan
        & ".venv\Scripts\python.exe" -m ".app.updater" 2>&1 | Out-Null
        
        # ถ้า requirements.txt มีการเปลี่ยนแปลง (หรือเพื่อความปลอดภัย)
        # → re-install package
        if ($LASTEXITCODE -eq 0) {
            Write-Host "📦 requirements.txt re-installing (to be safe)..." -ForegroundColor Cyan
            & ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet 2>&1 | Out-Null
        }
    } catch {
        # เงียบไว้ — ไม่ให้ auto-update มาขัดการเปิดโปรแกรม
    }
}

Invoke-AutoUpdate

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "        INKEXTRACT — เครื่องมือจัดการนิยายแปล" -ForegroundColor Yellow
Write-Host "============================================================"
Write-Host "กำลังเปิดโปรแกรม..."
Write-Host "รอสักครู่ เบราว์เซอร์จะเปิดอัตโนมัติ"
Write-Host ""
Write-Host "(ถ้าไม่เปิดเอง คัดลอก URL ด้านล่างไปวางในเบราว์เซอร์)" -ForegroundColor Yellow
Write-Host "ปิดโปรแกรม: กด Ctrl+C" -ForegroundColor Yellow
Write-Host "============================================================"
Write-Host ""

& ".venv\Scripts\python.exe" -m streamlit run ".app\app.py"
