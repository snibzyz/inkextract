# -*- coding: utf-8 -*-
"""
Auto-Updater for INKEXTRACT
ทำงานโดยไม่ต้อง Git installed
- ตรวจสอบ version ใหม่จาก GitHub releases API
- ดาวน์โหลด ZIP ถ้ามีของใหม่
- แตกไฟล์และ merge กับ folder เดิม
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

try:
    import requests
    from packaging import version
except ImportError:
    requests = None
    version = None


# ============================================================
# CONFIG
# ============================================================
REPO_OWNER = "snibzyz"
REPO_NAME = "inkextract"
VERSION_FILE = ".app/VERSION"  # ไฟล์เก็บ version ปัจจุบัน
ROOT_DIR = Path(__file__).parent.parent  # เพิ่มไป 1 level (.app/updater.py → root)

# URL ไปยัง GitHub releases API
RELEASES_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def read_version():
    """อ่าน version ปัจจุบันจากไฟล์"""
    version_file = ROOT_DIR / VERSION_FILE
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except:
            return "0.0.0"
    return "0.0.0"


def write_version(v):
    """บันทึก version ใหม่"""
    version_file = ROOT_DIR / VERSION_FILE
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(v, encoding="utf-8")


def get_latest_release():
    """ดึง release ล่าสุดจาก GitHub API"""
    if not requests:
        return None

    try:
        resp = requests.get(RELEASES_API, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {
            "tag": data.get("tag_name", ""),
            "url": data.get("zipball_url", ""),
            "body": data.get("body", ""),
        }
    except Exception as e:
        print(f"❌ ดึง release ไม่สำเร็จ: {e}")
        return None


def download_file(url, dest_path):
    """ดาวน์โหลดไฟล์"""
    if not requests:
        return False

    try:
        print(f"📥 ดาวน์โหลด: {url}")
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        pct = (downloaded / total_size) * 100
                        print(f"  {pct:.1f}%", end="\r")

        print(f"  100% ✓")
        return True
    except Exception as e:
        print(f"❌ ดาวน์โหลดไม่สำเร็จ: {e}")
        return False


def extract_and_merge(zip_path, target_dir):
    """
    แตกไฟล์ ZIP และ merge กับ folder เดิม
    - ไฟล์เก่าใน target_dir จะเก็บไว้ (ถ้า local change)
    - ไฟล์ใหม่จะ overwrite
    """
    try:
        print(f"📦 แตกไฟล์...")
        temp_dir = target_dir.parent / f"_update_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        # GitHub zipball โครงสร้าง: owner-repo-hash/...
        # หา folder ใหม่ที่อยู่ข้างใน
        extracted_folders = list(temp_dir.glob("*"))
        if not extracted_folders:
            print("❌ ไฟล์ ZIP ว่าง")
            return False

        src_dir = extracted_folders[0]  # owner-repo-hash/

        # Copy ไฟล์ใหม่ไปยัง target (skip .git, .venv, workspace/)
        skip_dirs = {".git", ".venv", "workspace", "__pycache__"}

        def copy_tree(src, dst):
            for item in src.iterdir():
                if item.name in skip_dirs:
                    continue
                dst_item = dst / item.name
                if item.is_dir():
                    dst_item.mkdir(exist_ok=True)
                    copy_tree(item, dst_item)
                else:
                    shutil.copy2(item, dst_item)

        copy_tree(src_dir, target_dir)

        # ทำความสะอาด temp folder
        shutil.rmtree(temp_dir, ignore_errors=True)

        print("✓ แตกไฟล์สำเร็จ")
        return True
    except Exception as e:
        print(f"❌ แตกไฟล์ไม่สำเร็จ: {e}")
        return False


# ============================================================
# MAIN AUTO-UPDATE LOGIC
# ============================================================
def auto_update():
    """ตรวจสอบและ update ถ้ามีอัปเดตใหม่"""

    # ข้ามถ้าไม่มี requests library
    if not requests or not version:
        return False

    print("🔄 กำลังเช็คอัปเดต...")

    current = read_version()
    latest_release = get_latest_release()

    if not latest_release:
        print("⚠ ไม่สามารถเช็คอัปเดตได้ — ใช้ version เดิม")
        return False

    tag = latest_release["tag"]

    # เปรียบเทียบ version
    try:
        if version.parse(tag) <= version.parse(current):
            print(f"✓ โค้ดล่าสุดแล้ว (v{current})")
            return False
    except:
        pass

    print(f"📦 พบอัปเดต: {current} → {tag}")
    print(f"📝 {latest_release['body'][:200]}")

    # ดาวน์โหลด ZIP
    zip_path = ROOT_DIR / f"_update_{tag}.zip"
    if not download_file(latest_release["url"], zip_path):
        return False

    # แตก + merge
    if not extract_and_merge(zip_path, ROOT_DIR):
        return False

    # บันทึก version ใหม่
    write_version(tag)

    # ทำความสะอาด
    try:
        zip_path.unlink()
    except:
        pass

    print("✓ อัปเดตเสร็จ")
    return True


if __name__ == "__main__":
    try:
        success = auto_update()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
