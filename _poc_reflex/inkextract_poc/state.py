"""state.py — Global Reflex state ของ INKEXTRACT POC

จับคู่ event handlers กับ business logic ใน backend.py (= ของจริง .app/modules/)
"""
from __future__ import annotations
import reflex as rx
from pathlib import Path
from typing import Optional

from .backend import (
    paths, project_manager, manuscript_checker,
)


TABS = [
    ("project", "folder-open-dot", "โปรเจกต์"),
    ("manuscript", "file-search-2", "ตรวจต้นฉบับ"),
    ("vocab", "book-marked", "คำศัพท์"),
    ("proof", "spell-check-2", "ตรวจสอบและแก้ไข"),
    ("files", "folder-tree", "จัดการไฟล์"),
]


class AppState(rx.State):
    """Single global state — Reflex sync ระหว่าง backend ↔ React"""

    # ── Tab nav ─────────────────────────────────────────────────────────────
    current_tab: str = "project"

    # ── Project tab ─────────────────────────────────────────────────────────
    projects_data: list[dict] = []
    active_project_id: str = ""
    show_create_form: bool = False
    new_project_name: str = ""
    confirm_delete_id: str = ""

    # ── Manuscript tab ──────────────────────────────────────────────────────
    ms_folder: str = ""
    ms_threshold_pct: int = 30
    ms_scan_done: bool = False
    ms_total: int = 0
    ms_small: int = 0
    ms_avg_size_bytes: int = 0
    ms_padding: int = 0
    ms_entries: list[dict] = []
    ms_selected: list[str] = []  # filenames selected for delete

    # ── Vocab tab ───────────────────────────────────────────────────────────
    vocab_loaded: bool = False
    vocab_total: int = 0
    vocab_files_count: int = 0

    # ── Proof tab ───────────────────────────────────────────────────────────
    proof_mode: str = "normal"   # 'ab' or 'normal'
    proof_check_foreign: bool = True
    proof_check_numbers: bool = False
    proof_check_english: bool = False
    proof_source_folder: str = "Clean"
    proof_chunk_lines: int = 500
    proof_analyzing: bool = False
    proof_last_run_summary: str = ""
    proof_errors_count: int = 0

    # ── Files tab ───────────────────────────────────────────────────────────
    files_subtab: str = "merge"  # merge/separate/generate/format/clear/convert

    # ────────────────────────────────────────────────────────────────────────
    # COMPUTED VARS
    # ────────────────────────────────────────────────────────────────────────
    @rx.var
    def active_project(self) -> dict:
        for p in self.projects_data:
            if p["id"] == self.active_project_id:
                return p
        return self.projects_data[0] if self.projects_data else {
            "id": "", "name": "", "path": "", "created_at": "",
            "is_default": True, "file_count": 0,
        }

    @rx.var
    def active_name(self) -> str:
        return self.active_project.get("name", "")

    @rx.var
    def active_path(self) -> str:
        return self.active_project.get("path", "")

    @rx.var
    def active_meta(self) -> str:
        p = self.active_project
        if p.get("is_default"):
            return "โปรเจกต์เริ่มต้น"
        return f"สร้างเมื่อ {p.get('created_at', '')[:10]}"

    @rx.var
    def project_count(self) -> int:
        return len(self.projects_data)

    @rx.var
    def kpi_summary(self) -> str:
        ap = self.active_project
        return (f"ต้นฉบับ {ap.get('input_count', 0)} · "
                f"แก้ไข {ap.get('fix_count', 0)} · "
                f"สะอาด {ap.get('clean_count', 0)}")

    # ────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS — Tab nav
    # ────────────────────────────────────────────────────────────────────────
    @rx.event
    def switch_tab(self, tab_id: str):
        self.current_tab = tab_id

    @rx.event
    def switch_files_subtab(self, sub: str):
        self.files_subtab = sub

    # ────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS — Project tab
    # ────────────────────────────────────────────────────────────────────────
    @rx.event
    def init_projects(self):
        """รัน 1 ครั้งตอน mount — restore active + load list"""
        try:
            project_manager.restore_active_on_startup()
        except Exception as e:
            print(f"[init_projects] restore failed: {e}")
        self._reload_projects()

    def _reload_projects(self) -> None:
        try:
            projects = project_manager.list_projects()
            active = project_manager.get_active_project()
        except Exception as e:
            print(f"[_reload_projects] {e}")
            return

        out = []
        for p in projects:
            root = p.root_path()
            stats = _count_subdir_files(root)
            out.append({
                "id": p.id,
                "name": p.name,
                "path": str(root),
                "created_at": p.created_at or "",
                "is_default": p.is_default,
                "input_count": stats["input"],
                "fix_count": stats["fix"],
                "clean_count": stats["clean"],
                "raw_count": stats["raw"],
                "file_count": stats["input"] + stats["fix"] + stats["clean"],
                "exists": root.exists(),
            })
        self.projects_data = out
        self.active_project_id = active.id

    @rx.event
    def switch_project(self, project_id: str):
        try:
            project_manager.set_active_project(project_id)
            self._reload_projects()
            yield rx.toast.success(
                f"สลับไปยัง {self._name_of(project_id)}",
                position="bottom-right",
            )
        except Exception as e:
            yield rx.toast.error(f"สลับไม่ได้: {e}", position="bottom-right")

    def _name_of(self, project_id: str) -> str:
        for p in self.projects_data:
            if p["id"] == project_id:
                return p["name"]
        return project_id

    @rx.event
    def toggle_create_form(self):
        self.show_create_form = not self.show_create_form
        if self.show_create_form:
            self.new_project_name = ""

    @rx.event
    def set_new_name(self, value: str):
        self.new_project_name = value

    @rx.event
    def create_project(self):
        name = self.new_project_name.strip()
        if not name:
            yield rx.toast.error("กรุณากรอกชื่อโปรเจกต์",
                                 position="bottom-right")
            return
        try:
            created = project_manager.create_project(name)
            self.new_project_name = ""
            self.show_create_form = False
            self._reload_projects()
            yield rx.toast.success(f"สร้าง '{created.name}' สำเร็จ",
                                   position="bottom-right")
        except ValueError as e:
            yield rx.toast.error(str(e), position="bottom-right")
        except Exception as e:
            yield rx.toast.error(f"สร้างไม่สำเร็จ: {e}",
                                 position="bottom-right")

    @rx.event
    def open_active_folder(self):
        ap = self.active_project
        if not ap:
            return
        folder = Path(ap["path"])
        if not folder.exists():
            yield rx.toast.error(f"ไม่พบโฟลเดอร์: {folder}",
                                 position="bottom-right")
            return
        try:
            import os, sys, subprocess
            if sys.platform == "win32":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            yield rx.toast.success("เปิดโฟลเดอร์แล้ว",
                                   position="bottom-right", duration=1500)
        except Exception as e:
            yield rx.toast.error(f"เปิดไม่ได้: {e}",
                                 position="bottom-right")

    @rx.event
    def request_delete(self, project_id: str):
        self.confirm_delete_id = project_id

    @rx.event
    def cancel_delete(self):
        self.confirm_delete_id = ""

    @rx.event
    def confirm_delete(self, delete_files: bool):
        pid = self.confirm_delete_id
        if not pid:
            return
        try:
            name = self._name_of(pid)
            project_manager.delete_project(pid, delete_files=delete_files)
            self._reload_projects()
            self.confirm_delete_id = ""
            yield rx.toast.success(f"ลบ '{name}' แล้ว",
                                   position="bottom-right")
        except Exception as e:
            yield rx.toast.error(f"ลบไม่สำเร็จ: {e}",
                                 position="bottom-right")

    # ────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS — Manuscript tab
    # ────────────────────────────────────────────────────────────────────────
    @rx.event
    def init_manuscript(self):
        if not self.ms_folder:
            self.ms_folder = str(paths.RAW_INPUT_DIR)

    @rx.event
    def set_ms_folder(self, value: str):
        self.ms_folder = value

    @rx.event
    def set_ms_threshold(self, value: list[int | float]):
        # slider returns list
        v = value[0] if isinstance(value, list) else value
        self.ms_threshold_pct = int(v)

    @rx.event
    def scan_manuscript(self):
        folder = Path(self.ms_folder).expanduser()
        if not folder.exists():
            yield rx.toast.error(f"ไม่พบโฟลเดอร์: {folder}",
                                 position="bottom-right")
            return
        try:
            scan = manuscript_checker.scan_directory(
                folder, threshold_ratio=self.ms_threshold_pct / 100.0)
        except Exception as e:
            yield rx.toast.error(f"สแกนล้มเหลว: {e}",
                                 position="bottom-right")
            return

        self.ms_total = scan.total_files
        self.ms_small = scan.small_files_count
        self.ms_avg_size_bytes = int(scan.average_size)
        self.ms_padding = scan.detected_padding
        self.ms_scan_done = True
        self.ms_selected = []

        entries = []
        for f in sorted(scan.files, key=lambda x: x.name):
            entries.append({
                "name": f.name,
                "size": f.size,
                "is_small": f.is_small,
                "rel_size_pct": (round(f.size / scan.average_size * 100)
                                 if scan.average_size else 0),
            })
        self.ms_entries = entries
        yield rx.toast.success(
            f"สแกนเสร็จ — พบ {scan.total_files} ไฟล์ · "
            f"เล็กผิดปกติ {scan.small_files_count}",
            position="bottom-right",
        )

    @rx.event
    def toggle_ms_select(self, name: str):
        if name in self.ms_selected:
            self.ms_selected = [x for x in self.ms_selected if x != name]
        else:
            self.ms_selected = self.ms_selected + [name]

    @rx.event
    def select_all_small(self):
        self.ms_selected = [e["name"] for e in self.ms_entries if e["is_small"]]

    @rx.event
    def clear_ms_selection(self):
        self.ms_selected = []

    # ────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS — Vocab tab
    # ────────────────────────────────────────────────────────────────────────
    @rx.event
    def init_vocab(self):
        # check vocab dir
        vd = paths.VOCAB_DIR
        if vd.exists():
            files = list(vd.glob("*.csv")) + list(vd.glob("*.tsv")) + \
                    list(vd.glob("*.txt")) + list(vd.glob("*.xlsx"))
            self.vocab_files_count = len(files)
            self.vocab_loaded = bool(files)

    # ────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS — Proof tab
    # ────────────────────────────────────────────────────────────────────────
    @rx.event
    def set_proof_mode(self, value: str):
        self.proof_mode = value

    @rx.event
    def toggle_proof_foreign(self, value: bool):
        self.proof_check_foreign = value

    @rx.event
    def toggle_proof_numbers(self, value: bool):
        self.proof_check_numbers = value

    @rx.event
    def toggle_proof_english(self, value: bool):
        self.proof_check_english = value

    @rx.event
    def set_proof_source(self, value: str):
        self.proof_source_folder = value

    @rx.event
    def set_proof_chunk(self, value):
        try:
            self.proof_chunk_lines = int(value)
        except Exception:
            pass

    @rx.event
    def run_analyze(self):
        from .backend import get_proofreader
        from pathlib import Path
        # map source dropdown → dir
        src_map = {
            "Clean": paths.CLEAN_DIR,
            "Input": paths.INPUT_DIR,
            "Fix": paths.FIX_DIR,
            "Raw": paths.RAW_INPUT_DIR,
        }
        src_dir: Path = src_map.get(self.proof_source_folder, paths.CLEAN_DIR)
        if not src_dir.exists() or not any(src_dir.glob("*.txt")):
            yield rx.toast.error(
                f"ไม่มีไฟล์ใน {self.proof_source_folder}",
                position="bottom-right",
            )
            return

        self.proof_analyzing = True
        yield rx.toast(f"กำลังวิเคราะห์ {self.proof_source_folder}…",
                       position="bottom-right", duration=1500)
        try:
            pr = get_proofreader()
            result = pr.run_normal_mode_check(
                source_dir=src_dir,
                check_foreign_languages=self.proof_check_foreign,
                check_numbers=self.proof_check_numbers,
                check_english=self.proof_check_english,
            )
            errors = result if isinstance(result, list) else pr.normal_mode_errors
            self.proof_errors_count = len(errors or [])
            self.proof_last_run_summary = (
                f"สแกน {self.proof_source_folder}/ — พบ "
                f"{self.proof_errors_count} ข้อผิดพลาด"
            )
            yield rx.toast.success(self.proof_last_run_summary,
                                   position="bottom-right")
        except Exception as e:
            yield rx.toast.error(f"วิเคราะห์ล้มเหลว: {e}",
                                 position="bottom-right")
        finally:
            self.proof_analyzing = False


# ── helpers ─────────────────────────────────────────────────────────────────

def _count_subdir_files(project_root: Path) -> dict:
    """Count .txt files in standard subdirs"""
    counts = {"input": 0, "fix": 0, "clean": 0, "raw": 0}
    if not project_root.exists():
        return counts
    for key, sub in [("input", "Input"), ("fix", "Fix"),
                     ("clean", "Clean"), ("raw", "Raw")]:
        d = project_root / sub
        if d.exists() and d.is_dir():
            try:
                counts[key] = sum(1 for _ in d.glob("*.txt"))
            except OSError:
                counts[key] = 0
    return counts
