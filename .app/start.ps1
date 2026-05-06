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
# AUTO-UPDATE: ดึง code ล่าสุดจาก git origin (ถ้าติดตั้งผ่าน git clone)
# - ทำงานเงียบ ๆ — fail ก็ข้ามไปรันได้
# - ถ้าไม่มี .git/ หรือไม่มี git ในเครื่อง → ข้ามทันที
# - ถ้ามี local change ที่ขัดแย้ง → ไม่ overwrite (warn แล้วใช้ของเดิม)
# ============================================================
function Invoke-AutoUpdate {
    if (-not (Test-Path ".git")) { return }
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { return }

    Write-Host "🔄 กำลังเช็คอัปเดตจาก GitHub..." -ForegroundColor DarkCyan
    try {
        # fetch แบบเงียบ
        & git fetch --quiet origin 2>$null
        if ($LASTEXITCODE -ne 0) { return }

        # หา branch ปัจจุบัน
        $branch = (& git rev-parse --abbrev-ref HEAD 2>$null).Trim()
        if (-not $branch -or $branch -eq "HEAD") { return }

        # เปรียบเทียบ HEAD vs origin/<branch>
        $local = (& git rev-parse "@" 2>$null).Trim()
        $remote = (& git rev-parse "@{u}" 2>$null).Trim()
        if (-not $remote -or $local -eq $remote) {
            Write-Host "✓ โค้ดล่าสุดแล้ว" -ForegroundColor Green
            return
        }

        # นับ commits ที่ตามหลัง
        $behind = (& git rev-list --count "$local..$remote" 2>$null).Trim()

        # ถ้ามีไฟล์ local ที่ค้าง (uncommitted) → ไม่ pull กัน conflict
        $dirty = & git status --porcelain 2>$null
        if ($dirty) {
            Write-Host "⚠ พบไฟล์ที่แก้ในเครื่อง (uncommitted) — ข้าม auto-update เพื่อไม่ทับของเดิม" -ForegroundColor Yellow
            Write-Host "  (มีอัปเดตใหม่ $behind commit ที่ GitHub — ดึงเองได้ด้วย: git pull)" -ForegroundColor DarkYellow
            return
        }

        # pull แบบ fast-forward เท่านั้น (กัน merge อัตโนมัติ)
        Write-Host "📦 พบอัปเดต $behind commit — กำลังดึง..." -ForegroundColor Cyan
        & git pull --ff-only --quiet origin $branch 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ อัปเดตเสร็จ — กำลังเริ่มโปรแกรม..." -ForegroundColor Green
            # ถ้า requirements.txt เปลี่ยน → install เพิ่ม
            $reqChanged = & git diff --name-only "HEAD@{1}" HEAD 2>$null | Select-String -Pattern "requirements\.txt" -Quiet
            if ($reqChanged) {
                Write-Host "📦 requirements.txt เปลี่ยน — กำลังติดตั้ง package เพิ่ม..." -ForegroundColor Cyan
                & ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet 2>&1 | Out-Null
            }
        } else {
            Write-Host "⚠ ดึงอัปเดตไม่สำเร็จ — รันด้วย code เดิม" -ForegroundColor Yellow
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
