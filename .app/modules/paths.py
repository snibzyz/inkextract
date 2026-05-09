"""Multi-project workspace path resolver — INKIDEA-style folder layout.

Layout:
    <root>/
        .app/                     -> source code
        .config/                  -> shared config (settings.json, projects.json, ...)
        workspace/                -> default project (legacy, backward compat)
        projects/<slug>/          -> additional user-created projects
            Raw/                  (was 0-input-raw)  ราว ต้นฉบับจีน
            Input/                (was 0-input)      ดราฟแปลที่มี [A]/[B]
            Fix/                  (was 1-fix)        หลังแก้ error
            Clean/                (was 2-clean)      เกลา
            Finish/               (NEW)              จบรอบ — ฉบับเผยแพร่
            Merge/                (was 3-merge)
            Separate/             (was 4-separate)
            Import/               (was 5-import)     user-supplied corrections
            Output/               (was output)       error_trans.txt ฯลฯ
            Vocab/                (was vocab)
            Style/                (NEW)              สำนวน — style-notes.txt
            Prompt/               (NEW)              prompt templates (fix.md ฯลฯ)
            Temp/                 (NEW)              archive รอบ
            Error/error_trans/    (NEW)              ข้อความที่แยกไปแปลแก้

Per-project paths (INPUT_DIR, FIX_DIR, ...) resolve **dynamically** via
module-level __getattr__ — when project_manager.set_active_project_root()
is called, all subsequent attribute accesses point at the new root.

Cached path attributes (e.g. processors that did `self.input_dir = paths.INPUT_DIR`
in __init__) need to be re-created after switching project — see
project_manager.reset_session_processors() helper.

Migration: ของเดิมใช้ชื่อ lowercase numbered (0-input, 1-fix, ...) — ระบบจะ
rename → PascalCase ครั้งเดียวตอน startup ผ่าน project_manager.
"""
from pathlib import Path
from typing import List, Optional, Tuple
import os


def _is_inkextract_root(p: Path) -> bool:
    """โฟลเดอร์นี้ดูเหมือน INKEXTRACT install หรือไม่"""
    return (p / ".app" / "app.py").exists() and (p / ".app" / "VERSION").exists()


def _detect_root() -> Path:
    """หา install root โดยลำดับ priority นี้:
      1. ENV `INKEXTRACT_ROOT` ถ้าตั้งและ valid (force ผ่าน environment)
      2. Override file `<source>/.config/install_root.txt` (ผู้ใช้เลือกผ่าน UI)
      3. CWD ถ้าหน้าตา "INKEXTRACT-like" — Start.bat ทำ `cd /d %~dp0` ก่อนรัน
         streamlit เลย cwd = install ที่ user เปิด Start จริง (auto-detect)
      4. Fallback: ตำแหน่งของ paths.py file — ใช้กรณีรันจาก IDE / dev tool

    ค่าที่ได้คือโฟลเดอร์ INKEXTRACT (มี `.app/`, `workspace/`, `projects/` ข้างใน)
    """
    # 1. ENV override
    env_root = os.environ.get("INKEXTRACT_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if _is_inkextract_root(candidate):
            return candidate

    # 2. Override file ที่ source — ผู้ใช้ตั้งจาก UI
    #    (ใช้ source's .config เพื่อให้ override ติดมากับ source — กันสับสน)
    source_root = Path(__file__).resolve().parents[2]
    override_file = source_root / ".config" / "install_root.txt"
    try:
        if override_file.exists():
            override_path = override_file.read_text(encoding='utf-8').strip()
            if override_path:
                candidate = Path(override_path).expanduser().resolve()
                if _is_inkextract_root(candidate):
                    return candidate
    except OSError:
        pass

    # 3. CWD auto-detect — Start.bat ตั้ง cwd ให้ก่อน
    try:
        cwd = Path.cwd().resolve()
        if _is_inkextract_root(cwd):
            return cwd
    except OSError:
        pass

    # 4. Fallback: ตำแหน่งของไฟล์ paths.py
    return source_root


ROOT = _detect_root()
# CWD ตอนเริ่ม process — เก็บไว้ให้ UI แสดง diagnostic
try:
    STARTUP_CWD = Path.cwd().resolve()
except OSError:
    STARTUP_CWD = ROOT
# __file__-based root — เก็บไว้แยกเผื่อ UI ต้องการเทียบกับ ROOT ปัจจุบัน
SOURCE_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / ".app"
CONFIG_DIR = ROOT / ".config"

# Default workspace = legacy (used when no active project set)
DEFAULT_WORKSPACE_DIR = ROOT / "workspace"
# Container for user-created projects
PROJECTS_DIR = ROOT / "projects"
# Legacy alias — เคยใช้ชื่อ workspaces/ ในรอบ Phase 2 แรก
# คงไว้เป็น backward compat สำหรับ migration เท่านั้น
LEGACY_WORKSPACES_DIR = ROOT / "workspaces"

# Active project root — None = use DEFAULT_WORKSPACE_DIR.
# Mutated by project_manager.set_active_project()
_active_root: Optional[Path] = None


def set_active_project_root(path: Optional[Path]) -> None:
    """Set or clear active project root.

    None  → fallback to DEFAULT_WORKSPACE_DIR (legacy)
    Path  → use this folder as project root
    """
    global _active_root
    _active_root = Path(path) if path is not None else None


def get_active_project_root() -> Path:
    """Return current project root (active project, or default fallback)."""
    return _active_root if _active_root is not None else DEFAULT_WORKSPACE_DIR


# ============================================================
# Shared config files — always at .config/, never per-project
# ============================================================

EXCLUDE_FILE = CONFIG_DIR / "exclude.txt"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
USER_PREFS_FILE = CONFIG_DIR / "user_preferences.json"
NOVEL_LIST_FILE = CONFIG_DIR / "novel_list.txt"
OCR_SETTINGS_FILE = CONFIG_DIR / "ocr_settings.json"
PROJECTS_FILE = CONFIG_DIR / "projects.json"

# Log file — shared across all projects (อยู่ใน .config/ ไม่ใช่ output/ ของโปรเจกต์)
LOG_FILE = CONFIG_DIR / "app.log"


# ============================================================
# Per-project subdir mapping (single source of truth)
# ============================================================

_SUBDIR_NAMES = {
    # Pipeline (was numbered) — now PascalCase
    "RAW_INPUT_DIR": "Raw",
    "INPUT_DIR": "Input",
    "FIX_DIR": "Fix",
    "CLEAN_DIR": "Clean",
    "CLEAN_DOCX_DIR": "Clean",   # legacy alias
    "CLEAN_MD_DIR": "Clean",     # legacy alias
    "FINISH_DIR": "Finish",      # NEW
    # Side resources
    "MERGE_DIR": "Merge",
    "SEPARATE_DIR": "Separate",
    "IMPORT_FIX_DIR": "Import",
    "OUTPUT_DIR": "Output",
    "VOCAB_DIR": "Vocab",
    "STYLE_DIR": "Style",        # NEW
    "TEMP_DIR": "Temp",          # NEW
    "PROMPT_DIR": "Prompt",      # NEW (singular, no library/session)
    # Nested
    "ERROR_DIR": "Error",
    "ERROR_TRANS_DIR": "Error/error_trans",     # NEW
}

# Order for ALL_DATA_DIRS — ทุกโฟลเดอร์ที่ ensure_dirs ต้องสร้าง (de-duplicated)
_DATA_DIR_KEYS_UNIQUE = [
    "RAW_INPUT_DIR", "INPUT_DIR", "FIX_DIR", "CLEAN_DIR", "FINISH_DIR",
    "MERGE_DIR", "SEPARATE_DIR", "IMPORT_FIX_DIR",
    "OUTPUT_DIR", "VOCAB_DIR", "STYLE_DIR",
    "PROMPT_DIR",
    "TEMP_DIR", "ERROR_TRANS_DIR",
]

# Mapping ของชื่อเก่า → ชื่อใหม่ — ใช้ตอน migration
LEGACY_SUBDIR_RENAME = {
    "0-input-raw": "Raw",
    "0-input": "Input",
    "1-fix": "Fix",
    "2-clean": "Clean",
    "3-merge": "Merge",
    "4-separate": "Separate",
    "5-import": "Import",
    "output": "Output",
    "vocab": "Vocab",
}


def __getattr__(name: str):
    """Module-level lazy attribute lookup — resolve subdirs against active root.

    Allows existing code `paths.INPUT_DIR` to work without changes, while still
    pointing at whichever project is currently active.
    """
    root = get_active_project_root()
    if name == "WORKSPACE_DIR":
        return root
    if name == "ALL_DATA_DIRS":
        seen = set()
        out: List[Path] = []
        for key in _DATA_DIR_KEYS_UNIQUE:
            p = root / _SUBDIR_NAMES[key]
            if p not in seen:
                seen.add(p)
                out.append(p)
        return tuple(out)
    if name in _SUBDIR_NAMES:
        return root / _SUBDIR_NAMES[name]
    raise AttributeError(f"module 'paths' has no attribute {name!r}")


def ensure_dirs() -> None:
    """Create config + active-project directory tree if missing."""
    CONFIG_DIR.mkdir(exist_ok=True)
    root = get_active_project_root()
    root.mkdir(parents=True, exist_ok=True)
    seen = set()
    for key in _DATA_DIR_KEYS_UNIQUE:
        p = root / _SUBDIR_NAMES[key]
        if p in seen:
            continue
        seen.add(p)
        p.mkdir(parents=True, exist_ok=True)
