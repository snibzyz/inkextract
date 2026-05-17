"""project_manager.py — Multi-project workspace registry & switcher.

Inspired by INKIDEA's workspace pattern (Electron) — adapted for Streamlit.

Key concepts:
  * "Default project" = legacy `workspace/` folder (always exists, can't be deleted)
  * "User projects" = folders under `projects/<slug>/` with same subdir layout
  * Registry stored at `.config/projects.json`
  * Active project tracked in registry — restored on app startup

Usage:
    # On app startup
    project_manager.restore_active_on_startup()

    # List projects for UI dropdown
    projects = project_manager.list_projects()

    # Switch project
    project_manager.set_active_project(project_id)
    # ... then reset processors in session_state and st.rerun()

    # Create new project
    project = project_manager.create_project("My Novel")

Migration:
  * Phase 2 รอบแรกใช้ `workspaces/` (พหูพจน์) → ตอนนี้เปลี่ยนเป็น `projects/`
  * `_migrate_legacy_workspaces_dir()` ทำงานครั้งเดียวตอน startup:
    rename folder ถ้าเก่าอยู่ + อัพเดต path ใน registry
"""
from __future__ import annotations
import json
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import paths


DEFAULT_PROJECT_ID = "__default__"
DEFAULT_PROJECT_NAME = "Workspace (เดิม)"


@dataclass
class Project:
    """One project = one folder with the standard subdir layout.

    Note: `path` is stored for display/inspection only — at runtime we always
    derive root from `paths.PROJECTS_DIR / self.id` (or DEFAULT_WORKSPACE_DIR
    for default). This makes the registry **portable** — moving the whole
    INKEXTRACT folder to another drive/location just works without editing
    `projects.json`.
    """
    id: str
    name: str
    path: str
    created_at: str = ""

    @property
    def is_default(self) -> bool:
        return self.id == DEFAULT_PROJECT_ID

    def root_path(self) -> Path:
        """Always derive from current paths config — ignore stored absolute path."""
        if self.is_default:
            return paths.DEFAULT_WORKSPACE_DIR
        return paths.PROJECTS_DIR / self.id


# ============================================================
# Slug helpers
# ============================================================

_SLUG_KEEP_RE = re.compile(r'[^\w฀-๿一-鿿-]+', re.UNICODE)
_SLUG_DASH_RE = re.compile(r'-+')


def slugify(name: str) -> str:
    """Folder-friendly slug — keeps Thai/Chinese chars, collapses others."""
    if not name:
        return 'project'
    n = unicodedata.normalize('NFKC', name)
    s = _SLUG_KEEP_RE.sub('-', n)
    s = _SLUG_DASH_RE.sub('-', s).strip('-')
    return (s or 'project')[:60]


# ============================================================
# Registry I/O
# ============================================================

def _empty_registry() -> dict:
    return {"version": 1, "active_project_id": None, "projects": []}


def _heal_paths_in_registry(data: dict) -> bool:
    """Rewrite stored `path` ของแต่ละ project ให้ชี้ที่ paths.PROJECTS_DIR ปัจจุบัน.

    ใช้กรณี:
      - User ย้ายโฟลเดอร์ INKEXTRACT ไปไดรฟ์/ที่ใหม่ → absolute path เก่าใน
        registry ไม่ตรงอีกแล้ว
      - clone repo ใหม่บนเครื่องใหม่ — registry ที่ติดมาจะมี path ของเครื่องเก่า

    Returns:
        True ถ้ามีการแก้ไข (เพื่อให้ caller รู้ว่าต้อง save)
    """
    changed = False
    expected_root = str(paths.PROJECTS_DIR)
    for proj in data.get('projects', []):
        pid = proj.get('id')
        if not pid:
            continue
        expected = str(paths.PROJECTS_DIR / pid)
        if proj.get('path') != expected:
            proj['path'] = expected
            changed = True
    return changed


def _load_data() -> dict:
    """Read registry from disk — return empty if missing/corrupt.

    Auto-heal: ถ้า stored path ไม่ตรงกับ paths.PROJECTS_DIR ปัจจุบัน
    (เช่น ย้ายโฟลเดอร์ข้ามไดรฟ์) → rewrite ให้ตรง
    """
    pf = paths.PROJECTS_FILE
    if not pf.exists():
        return _empty_registry()
    try:
        data = json.loads(pf.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return _empty_registry()
        data.setdefault('version', 1)
        data.setdefault('active_project_id', None)
        data.setdefault('projects', [])
        # Self-heal stored absolute paths
        if _heal_paths_in_registry(data):
            try:
                _save_data(data)
            except OSError:
                pass  # ไม่ critical — runtime ยังใช้ root_path() ที่ derive ได้
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_registry()


def _save_data(data: dict) -> None:
    paths.CONFIG_DIR.mkdir(exist_ok=True)
    paths.PROJECTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


# ============================================================
# Public API
# ============================================================

def _default_project() -> Project:
    return Project(
        id=DEFAULT_PROJECT_ID,
        name=DEFAULT_PROJECT_NAME,
        path=str(paths.DEFAULT_WORKSPACE_DIR),
    )


def list_projects() -> List[Project]:
    """Return list of all known projects — default first, then user-created."""
    data = _load_data()
    out: List[Project] = [_default_project()]
    for p in data.get('projects', []):
        try:
            out.append(Project(**p))
        except TypeError:
            continue  # malformed entry
    return out


def get_active_project() -> Project:
    """Resolve current active project — fallback to default if not set."""
    data = _load_data()
    aid = data.get('active_project_id')
    if not aid or aid == DEFAULT_PROJECT_ID:
        return _default_project()
    for p in data.get('projects', []):
        if p.get('id') == aid:
            try:
                return Project(**p)
            except TypeError:
                break
    # Active id stale (project was deleted) — return default
    return _default_project()


def set_active_project(project_id: str) -> Project:
    """Switch active project. Caller is responsible for resetting cached
    processor instances + st.rerun().
    """
    data = _load_data()
    new_id: Optional[str] = (
        None if project_id == DEFAULT_PROJECT_ID else project_id
    )
    data['active_project_id'] = new_id
    _save_data(data)

    project = get_active_project()
    paths.set_active_project_root(
        None if project.is_default else project.root_path()
    )
    paths.ensure_dirs()
    return project


IMPORT_ERRORS_FILENAME = "import_errors.txt"

IMPORT_ERRORS_TEMPLATE = """# ============================================================
# import_errors.txt — ไฟล์รวมข้อผิดพลาดสำหรับ import กลับ
# ============================================================
#
# วิธีใช้:
#   1. กด Export ในหน้าตรวจสอบและแก้ไข — โปรแกรมจะคัดลอกเนื้อหา
#      ของ master `output/error_trans.txt` มาทับไฟล์นี้ให้อัตโนมัติ
#   2. แก้ไขเฉพาะบรรทัด [B] ของแต่ละ entry ตามคำแนะนำในไฟล์
#   3. กด Import — โปรแกรมจะอ่านไฟล์นี้จาก `Import/` ก่อน
#      แล้วค่อย fallback ไปที่ `Output/`
#
# ไฟล์นี้ถูกสร้างไว้ตั้งแต่ตอนสร้างโปรเจกต์ — ห้ามลบ
# (ถ้าลบจะถูกสร้างขึ้นใหม่อัตโนมัติทุกครั้งที่ Export)
# ============================================================
"""


def _scaffold_import_errors_file(project_root: Path) -> None:
    """สร้าง Import/import_errors.txt ถ้ายังไม่มี — กัน user หลงลบ"""
    import_dir = project_root / "Import"
    import_dir.mkdir(parents=True, exist_ok=True)
    target = import_dir / IMPORT_ERRORS_FILENAME
    if not target.exists():
        try:
            target.write_text(IMPORT_ERRORS_TEMPLATE, encoding='utf-8')
        except OSError:
            pass


def _actual_dirname_on_disk(parent: Path, requested_name: str) -> Optional[str]:
    """หา **on-disk name** จริงของ subdir (NTFS เก็บ case แต่ lookup ignore case).

    Returns:
        ชื่อจริงที่แสดงใน file explorer หรือ None ถ้าไม่เจอ
    """
    if not parent.exists():
        return None
    try:
        for entry in parent.iterdir():
            if entry.name.lower() == requested_name.lower() and entry.is_dir():
                return entry.name
    except OSError:
        pass
    return None


def _migrate_legacy_subdir_names(project_root: Path) -> None:
    """Rename ชื่อโฟลเดอร์เก่า (0-input, 1-fix, ฯลฯ) → ใหม่ (Input, Fix, ฯลฯ).

    Idempotent — รันซ้ำไม่มีผลข้างเคียง:
      * ถ้ามี old แต่ไม่มี new → rename
      * ถ้ามีทั้งคู่ → ย้ายเฉพาะไฟล์ที่ไม่ซ้ำจาก old → new แล้วลบ old ถ้าว่าง
      * บน NTFS (case-insensitive) เช่น `output` → `Output` ใช้ 2-step rename:
        old → temp_name → new (กัน Path.rename ที่ no-op เพราะมองเป็นชื่อเดียวกัน)
    """
    import shutil

    if not project_root.exists() or not project_root.is_dir():
        return

    for old_name, new_name in paths.LEGACY_SUBDIR_RENAME.items():
        # ดูชื่อจริงบนดิสก์ (NTFS อาจเก็บ case เก่าไว้)
        actual_old = _actual_dirname_on_disk(project_root, old_name)
        actual_new = _actual_dirname_on_disk(project_root, new_name)

        if actual_old is None:
            continue
        old_dir = project_root / actual_old

        # Case-only difference (เช่น "output" vs "Output" บน NTFS):
        # Path.exists() จะ True ทั้งคู่ แต่จริง ๆ เป็นโฟลเดอร์เดียวกัน
        # → ใช้ 2-step rename เพื่อบังคับให้ระบบไฟล์เปลี่ยน case
        if actual_new is not None and actual_new.lower() == new_name.lower() and actual_new != new_name:
            # ของเดิมมีแต่ case ไม่ตรง — บังคับเปลี่ยน case ผ่าน temp
            tmp = project_root / f"__migrate_tmp_{new_name}__"
            try:
                old_dir.rename(tmp)
                tmp.rename(project_root / new_name)
            except OSError:
                pass
            continue

        if actual_new is None or actual_new.lower() != new_name.lower():
            # ไม่มีของใหม่จริง ๆ — rename ปกติ
            new_dir = project_root / new_name
            try:
                old_dir.rename(new_dir)
            except OSError:
                try:
                    shutil.move(str(old_dir), str(new_dir))
                except Exception:
                    pass
            # ถ้า case บน disk ยังไม่ตรง บังคับด้วย 2-step
            actual_after = _actual_dirname_on_disk(project_root, new_name)
            if actual_after is not None and actual_after != new_name:
                tmp = project_root / f"__migrate_tmp_{new_name}__"
                try:
                    (project_root / actual_after).rename(tmp)
                    tmp.rename(project_root / new_name)
                except OSError:
                    pass
        else:
            # มีทั้งคู่ (ไม่ใช่ case-difference) → merge content
            new_dir = project_root / actual_new
            for child in list(old_dir.iterdir()):
                dest = new_dir / child.name
                if dest.exists():
                    continue
                try:
                    child.rename(dest)
                except OSError:
                    try:
                        shutil.move(str(child), str(dest))
                    except Exception:
                        pass
            try:
                if not any(old_dir.iterdir()):
                    old_dir.rmdir()
            except OSError:
                pass


def create_project(display_name: str) -> Project:
    """Create new project folder + subdirs + register + set as active."""
    if not display_name or not display_name.strip():
        raise ValueError("ชื่อ project ห้ามว่าง")
    display_name = display_name.strip()

    data = _load_data()
    for p in data.get('projects', []):
        if p.get('name') == display_name:
            raise ValueError(f"มี project ชื่อ '{display_name}' อยู่แล้ว")

    base_slug = slugify(display_name)
    slug = base_slug
    used_ids = {p.get('id') for p in data.get('projects', [])}
    used_ids.add(DEFAULT_PROJECT_ID)
    counter = 2
    while slug in used_ids or (paths.PROJECTS_DIR / slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    project_path = paths.PROJECTS_DIR / slug
    project_path.mkdir(parents=True, exist_ok=True)

    # Switch active to scaffold the standard subdir layout
    paths.set_active_project_root(project_path)
    paths.ensure_dirs()
    _scaffold_import_errors_file(project_path)

    project = Project(
        id=slug,
        name=display_name,
        path=str(project_path),
        created_at=datetime.now().isoformat(timespec='seconds'),
    )
    data.setdefault('projects', []).append(asdict(project))
    data['active_project_id'] = slug
    _save_data(data)
    return project


def rename_project(project_id: str, new_display_name: str) -> Project:
    """เปลี่ยนชื่อ project — เปลี่ยน display name + slug + ชื่อโฟลเดอร์บนดิสก์.

    ลบ default workspace ไม่ได้ rename ก็ไม่ได้ — ใช้ create+delete แทน
    """
    if project_id == DEFAULT_PROJECT_ID:
        raise ValueError("เปลี่ยนชื่อ default workspace ไม่ได้")

    if not new_display_name or not new_display_name.strip():
        raise ValueError("ชื่อใหม่ห้ามว่าง")
    new_display_name = new_display_name.strip()

    data = _load_data()
    target = next(
        (p for p in data.get('projects', []) if p.get('id') == project_id),
        None,
    )
    if target is None:
        raise ValueError(f"ไม่พบ project id={project_id}")

    if target.get('name') == new_display_name:
        # ไม่ต้องทำอะไร
        return Project(**target)

    # กัน duplicate name (ยกเว้นตัวเอง)
    for p in data.get('projects', []):
        if p.get('id') != project_id and p.get('name') == new_display_name:
            raise ValueError(f"มี project ชื่อ '{new_display_name}' อยู่แล้ว")

    # หา new slug ที่ไม่ซ้ำ
    base_slug = slugify(new_display_name)
    new_slug = base_slug
    used_ids = {
        p.get('id') for p in data.get('projects', [])
        if p.get('id') != project_id
    }
    used_ids.add(DEFAULT_PROJECT_ID)
    counter = 2
    while (
        new_slug in used_ids
        or (new_slug != target['id'] and (paths.PROJECTS_DIR / new_slug).exists())
    ):
        new_slug = f"{base_slug}-{counter}"
        counter += 1

    old_path = Path(target['path'])
    new_path = paths.PROJECTS_DIR / new_slug

    # Rename folder บนดิสก์ ถ้า slug เปลี่ยน
    if new_slug != target['id'] and old_path != new_path:
        if not old_path.exists():
            raise ValueError(f"ไม่พบโฟลเดอร์ {old_path}")
        if new_path.exists():
            raise ValueError(f"โฟลเดอร์ {new_path} มีอยู่แล้ว")
        try:
            old_path.rename(new_path)
        except OSError:
            import shutil
            shutil.move(str(old_path), str(new_path))

    # ปรับ registry
    target['name'] = new_display_name
    target['id'] = new_slug
    target['path'] = str(new_path)

    # ถ้าโปรเจกต์นี้ active อยู่ — sync active id + paths
    if data.get('active_project_id') == project_id:
        data['active_project_id'] = new_slug
        paths.set_active_project_root(new_path)

    _save_data(data)
    return Project(**target)


def delete_project(project_id: str, *, delete_files: bool = False) -> None:
    """Remove project from registry. delete_files=True also rmtree() the folder.

    Default project can't be deleted.
    """
    if project_id == DEFAULT_PROJECT_ID:
        raise ValueError("ลบ default workspace ไม่ได้")

    data = _load_data()
    target = next(
        (p for p in data.get('projects', []) if p.get('id') == project_id),
        None,
    )
    if target is None:
        return

    if delete_files:
        target_path = Path(target.get('path', ''))
        if target_path.exists() and target_path.is_dir():
            try:
                shutil.rmtree(target_path)
            except OSError:
                pass

    data['projects'] = [
        p for p in data.get('projects', []) if p.get('id') != project_id
    ]
    if data.get('active_project_id') == project_id:
        data['active_project_id'] = None
        paths.set_active_project_root(None)
    _save_data(data)


def _migrate_legacy_workspaces_dir() -> None:
    """Rename `workspaces/` (เก่า) → `projects/` (ใหม่) + update registry paths.

    ทำงานครั้งเดียวตอน startup. Idempotent — รันซ้ำไม่มีผลข้างเคียง:
      * ถ้ามี `workspaces/` แต่ไม่มี `projects/` → rename folder
      * อัพเดต string paths ใน registry ให้ชี้ไปที่ projects/ แทน
    """
    legacy = paths.LEGACY_WORKSPACES_DIR
    target = paths.PROJECTS_DIR

    # Step 1: rename folder ถ้าเข้าเงื่อนไข
    if legacy.exists() and legacy.is_dir():
        if not target.exists():
            try:
                legacy.rename(target)
            except OSError:
                # rename ข้าม drive ไม่ได้ → fallback move ทีละไฟล์
                import shutil
                try:
                    shutil.move(str(legacy), str(target))
                except Exception:
                    pass
        else:
            # มีทั้ง projects/ และ workspaces/ → ย้ายเฉพาะที่ไม่ซ้ำ
            for child in legacy.iterdir():
                dest = target / child.name
                if not dest.exists():
                    try:
                        child.rename(dest)
                    except OSError:
                        import shutil
                        try:
                            shutil.move(str(child), str(dest))
                        except Exception:
                            pass
            # ลบ workspaces/ ทิ้งถ้าว่างแล้ว
            try:
                if not any(legacy.iterdir()):
                    legacy.rmdir()
            except OSError:
                pass

    # Step 2: อัพเดต path strings ใน registry
    data = _load_data()
    changed = False
    legacy_str = str(legacy)
    target_str = str(target)
    for proj in data.get('projects', []):
        old_path = proj.get('path', '')
        if not old_path:
            continue
        # ทดแทน substring แบบ tolerant กับ separator
        if legacy_str in old_path:
            proj['path'] = old_path.replace(legacy_str, target_str)
            changed = True
        elif old_path.replace('\\', '/').find('/workspaces/') != -1:
            # cover edge case: legacy path เก็บแบบ posix
            proj['path'] = old_path.replace('/workspaces/', '/projects/').replace('\\workspaces\\', '\\projects\\')
            changed = True
    if changed:
        _save_data(data)


_MIGRATION_FLAG_NAME = ".migration_v1_done"


def restore_active_on_startup() -> Project:
    """Call once at app startup — restores active project from registry.

    Migrations executed (idempotent + flagged):
      1. Folder `workspaces/` → `projects/` (Phase 2 รอบแรกเคยใช้ชื่อนั้น)
      2. Subdir lowercase numbered (0-input, 1-fix, ...) → PascalCase (Input, Fix, ...)
         รันสำหรับทุกโปรเจกต์ที่ลงทะเบียนไว้ + default workspace

    Perf: หลัง migration สำเร็จ เขียน flag `.config/.migration_v1_done`
    ครั้งถัดไปข้าม migration walk ทั้งชุด — ประหยัด O(N_projects × N_subdirs) iterdir ต่อ startup
    """
    flag_file = paths.CONFIG_DIR / _MIGRATION_FLAG_NAME
    if not flag_file.exists():
        _migrate_legacy_workspaces_dir()
        _migrate_legacy_subdir_names(paths.DEFAULT_WORKSPACE_DIR)
        for proj in list_projects():
            if proj.is_default:
                continue
            _migrate_legacy_subdir_names(proj.root_path())
        # mark done — กัน startup ครั้งหน้าวิ่ง iterdir อีก
        try:
            flag_file.parent.mkdir(parents=True, exist_ok=True)
            flag_file.write_text("v1", encoding="utf-8")
        except Exception:
            pass  # best-effort — ถ้าเขียนไม่ได้ ครั้งหน้าก็จะ re-run migration (idempotent)

    project = get_active_project()
    paths.set_active_project_root(
        None if project.is_default else project.root_path()
    )
    paths.ensure_dirs()
    # Scaffold import_errors.txt ใน Import/ ของโปรเจกต์ที่ active
    # — กัน user หลงลบ + รองรับ project เก่าที่ยังไม่มีไฟล์นี้
    _scaffold_import_errors_file(project.root_path())
    return project
