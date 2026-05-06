#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "           ติดตั้งโปรแกรมตรวจสอบคำแปลนิยาย"
echo "============================================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[X] ไม่พบ Python ในเครื่อง"
    echo
    echo "กรุณาทำตามนี้:"
    echo "  1. เว็บจะเปิดให้อัตโนมัติ → ดาวน์โหลด Python 3.12"
    echo "  2. ติดตั้งตามขั้นตอนปกติ"
    echo "  3. เสร็จแล้ว กลับมาดับเบิลคลิกไฟล์นี้อีกครั้ง"
    echo
    open "https://www.python.org/downloads/" 2>/dev/null || true
    read -n 1 -s -r -p "กดปุ่มใดก็ได้เพื่อปิดหน้าต่าง..."
    exit 1
fi

echo "[1/3] กำลังเตรียมระบบ..."
if [ ! -d ".venv" ]; then
    "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if python -c "import streamlit" 2>/dev/null; then
    echo "[2/3] ส่วนประกอบติดตั้งแล้ว ข้าม..."
else
    echo "[2/3] กำลังติดตั้งส่วนประกอบ (อาจใช้เวลาสักครู่)..."
    python -m pip install --upgrade pip --quiet
    python -m pip install -r .app/requirements.txt --quiet
fi

echo "[3/3] กำลังเตรียมโฟลเดอร์..."
mkdir -p workspace/0-input workspace/1-fix workspace/2-clean \
         workspace/2-clean-docx workspace/2-clean-md \
         workspace/3-merge workspace/4-separate \
         workspace/output workspace/vocab

# ทำให้ไฟล์เริ่มโปรแกรมรันได้
chmod +x "เริ่มโปรแกรม.command" 2>/dev/null || true

echo
echo "============================================================"
echo "  [/] ติดตั้งเสร็จสิ้น!"
echo
echo "  ดับเบิลคลิกไฟล์  เริ่มโปรแกรม.command  เพื่อใช้งาน"
echo "============================================================"
echo
read -n 1 -s -r -p "กดปุ่มใดก็ได้เพื่อปิดหน้าต่าง..."
