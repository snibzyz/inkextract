# -*- coding: utf-8 -*-
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot\..

function Write-Banner {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "         ติดตั้งโปรแกรมตรวจสอบคำแปลนิยาย" -ForegroundColor Cyan
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
Write-Step "1/4" "ตรวจสอบ Python..."

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
    Write-Host "   ไม่พบ Python — กำลังลองติดตั้งผ่าน winget..." -ForegroundColor Yellow
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
        # refresh path
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command "py" -ErrorAction SilentlyContinue) { $pythonCmd = "py -3" }
        elseif (Get-Command "python" -ErrorAction SilentlyContinue) { $pythonCmd = "python" }
    }
}

if (-not $pythonCmd) {
    Write-Err "ไม่พบ Python และติดตั้งอัตโนมัติไม่สำเร็จ"
    Write-Host "กรุณาทำตามนี้:" -ForegroundColor Yellow
    Write-Host "  1. ไปที่เว็บ  https://www.python.org/downloads/"
    Write-Host "  2. กดดาวน์โหลด Python (เวอร์ชัน 3.12 ขึ้นไป)"
    Write-Host "  3. ตอนติดตั้ง  ติ๊กช่อง  'Add Python to PATH'  ก่อนกด Install"
    Write-Host "  4. ติดตั้งเสร็จแล้ว กลับมาดับเบิลคลิกไฟล์ ติดตั้ง.bat อีกครั้ง"
    Write-Host ""
    Start-Process "https://www.python.org/downloads/"
    Read-Host "กดปุ่ม Enter เพื่อปิด"
    exit 1
}

Write-Host "   พบ Python: $pythonCmd" -ForegroundColor Green

# --- 2. Create venv ---
Write-Step "2/4" "เตรียมสภาพแวดล้อม..."

if (-not (Test-Path ".venv")) {
    Invoke-Expression "$pythonCmd -m venv .venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "สร้าง .venv ไม่สำเร็จ"
        Read-Host "กดปุ่ม Enter เพื่อปิด"
        exit 1
    }
}

# --- 3. Install packages ---
$streamlitOk = & ".venv\Scripts\python.exe" -c "import streamlit" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Step "3/4" "ส่วนประกอบติดตั้งแล้ว ข้าม..."
} else {
    Write-Step "3/4" "ติดตั้งส่วนประกอบ (อาจใช้เวลา 1-3 นาที)..."
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
    $pipOut = & ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet --disable-pip-version-check 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ($pipOut -match "WinError 32") {
            Write-Err "มีโปรแกรมกำลังใช้งาน .venv อยู่"
            Write-Host "กรุณาปิดโปรแกรมที่รันอยู่ (เช่น เริ่มโปรแกรม.bat) แล้วลองใหม่" -ForegroundColor Yellow
        } else {
            Write-Err "ติดตั้งส่วนประกอบไม่สำเร็จ — ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่"
            Write-Host ($pipOut | Out-String)
        }
        Read-Host "กดปุ่ม Enter เพื่อปิด"
        exit 1
    }
}

# --- 4. Ensure workspace folders ---
Write-Step "4/4" "เตรียมโฟลเดอร์..."

@("workspace\0-input","workspace\1-fix","workspace\2-clean",
  "workspace\3-merge","workspace\4-separate",
  "workspace\output","workspace\vocab") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}
if (-not (Test-Path ".config")) { New-Item -ItemType Directory -Path ".config" -Force | Out-Null }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   ติดตั้งเสร็จสิ้น!" -ForegroundColor Green
Write-Host ""
Write-Host "   ดับเบิลคลิกไฟล์  เริ่มโปรแกรม.bat  เพื่อใช้งาน" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
