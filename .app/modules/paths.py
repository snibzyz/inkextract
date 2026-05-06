"""Central path resolver.

All folders and config files in the project are derived from a single root
directory so that the app keeps working no matter where the user installs it.

Layout:
    <root>/
        .app/        -> source code (this file lives in .app/modules/)
        .config/     -> all config files (exclude.txt, settings.json, ...)
        workspace/   -> all user data (0-input, 1-fix, 2-clean, ...)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

APP_DIR = ROOT / ".app"
CONFIG_DIR = ROOT / ".config"
WORKSPACE_DIR = ROOT / "workspace"

INPUT_DIR = WORKSPACE_DIR / "0-input"
FIX_DIR = WORKSPACE_DIR / "1-fix"
CLEAN_DIR = WORKSPACE_DIR / "2-clean"
# Deprecated 2026-05-06: ยุบมาเป็น 2-clean เดียว — converters เขียนไฟล์ใน 2-clean ทันที
# (อยู่เพื่อ backward compat — ทุก path ชี้กลับมาที่ CLEAN_DIR)
CLEAN_DOCX_DIR = CLEAN_DIR
CLEAN_MD_DIR = CLEAN_DIR
MERGE_DIR = WORKSPACE_DIR / "3-merge"
SEPARATE_DIR = WORKSPACE_DIR / "4-separate"
OUTPUT_DIR = WORKSPACE_DIR / "output"
VOCAB_DIR = WORKSPACE_DIR / "vocab"

EXCLUDE_FILE = CONFIG_DIR / "exclude.txt"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
USER_PREFS_FILE = CONFIG_DIR / "user_preferences.json"
NOVEL_LIST_FILE = CONFIG_DIR / "novel_list.txt"
OCR_SETTINGS_FILE = CONFIG_DIR / "ocr_settings.json"

LOG_FILE = OUTPUT_DIR / "app.log"

ALL_DATA_DIRS = (
    INPUT_DIR, FIX_DIR, CLEAN_DIR,
    MERGE_DIR, SEPARATE_DIR, OUTPUT_DIR, VOCAB_DIR,
)


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    WORKSPACE_DIR.mkdir(exist_ok=True)
    for d in ALL_DATA_DIRS:
        d.mkdir(parents=True, exist_ok=True)
