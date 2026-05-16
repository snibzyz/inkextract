"""tabs/project.py — แท็บจัดการโปรเจกต์ (สร้าง / สลับ / ลบ).

แต่ละโปรเจกต์ = พื้นที่ทำงานแยกกัน มีโฟลเดอร์ย่อย (0-input, 1-fix, 2-clean, ...)
ของตัวเอง — เผื่อทำหลายเรื่องพร้อมกันโดยไม่ปนกัน
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths, project_manager


# Keys ที่ใช้ cache processor instances ใน session_state
# ต้อง clear ตอนสลับโปรเจกต์เพื่อให้ paths ใหม่ถูก resolve
_PROCESSOR_KEYS = (
    'proofreader', 'file_processor', 'merge_processor',
    'separate_processor', 'vocab_processor',
    'md_converter', 'docx_converter',
)


def _reset_cached_processors() -> None:
    """ล้าง processor ที่ cache ไว้ใน session_state เพื่อให้ใช้ paths ของโปรเจกต์ใหม่"""
    for k in _PROCESSOR_KEYS:
        if k in st.session_state:
            del st.session_state[k]
    try:
        from modules.config import app_config
        app_config.reload_paths()
    except Exception:
        pass


def render_active_bar() -> None:
    """แถบสลิม 1 บรรทัด แสดงโปรเจกต์ที่ใช้งานอยู่ — เหนือ tabs ตลอด

    Single source of truth: นี่คือที่เดียวที่แสดง "โปรเจกต์ปัจจุบัน" รวม path.
    ใน Project tab จะมี active card สำหรับ action (rename, change, etc.) แต่
    ไม่ซ้ำกับแถบนี้ — แถบเป็น context indicator, card เป็น control surface.
    """
    active = project_manager.get_active_project()
    actual_path = str(active.root_path())
    tag_html = (
        '<span class="ink-active-tag">เริ่มต้น</span>' if active.is_default else ''
    )
    st.markdown(
        f"""
        <div class="ink-active-bar">
            <span class="ink-active-label">โปรเจกต์ที่ใช้งาน:</span>
            <span class="ink-active-name">{active.name}</span>
            {tag_html}
            <code title="{actual_path}">{actual_path}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_install_root_section() -> None:
    """Diagnostic + UI ให้ user เปลี่ยน install root ได้

    ใช้กรณีมีหลาย INKEXTRACT install บนเครื่องเดียว และอยากบอกแอปว่าให้ใช้อันไหน
    """
    install_root = paths.ROOT
    source_root = paths.SOURCE_ROOT
    cwd = paths.STARTUP_CWD
    override_file = source_root / ".config" / "install_root.txt"
    override_active = override_file.exists()

    with st.expander(":material/folder_managed: ตำแหน่ง install (ตอนนี้รันจากที่ไหน)", expanded=False):
        # diagnostic info
        st.markdown(
            f"""
            <div style="font-family: monospace; font-size: 0.85em; line-height: 1.7;">
              <strong>กำลังใช้ ROOT:</strong> <code>{install_root}</code><br>
              <strong>โค้ดอยู่ที่:</strong> <code>{source_root}</code><br>
              <strong>CWD ตอนเปิด:</strong> <code>{cwd}</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # คำอธิบายสถานะ
        if str(install_root) == str(source_root) == str(cwd):
            st.success("ทุกตัวตรงกัน — รันจาก install เดียวกับ source code")
        elif str(install_root) == str(cwd) and str(install_root) != str(source_root):
            st.info(
                f"ROOT ตามไฟล์ที่เปิด (auto-detect จาก Start.bat) — "
                f"ไม่ใช่ที่เดียวกับ source code"
            )
        elif override_active:
            st.info("ROOT ถูก override ไปยังโฟลเดอร์ที่ผู้ใช้เลือก")
        else:
            st.warning(
                "ROOT ต่างจาก source code และ CWD — อาจรันผ่าน IDE/dev tool "
                "(ไม่กระทบการใช้งาน)"
            )

        # Override picker
        st.markdown("---")
        st.markdown("**เปลี่ยน install root (เลือกเอง)**")

        if override_active:
            current_override = override_file.read_text(encoding='utf-8').strip()
            st.caption(f"override ปัจจุบัน: `{current_override}`")
        else:
            st.caption("ยังไม่ได้ตั้ง override — ใช้ auto-detect")

        with st.form("install_root_picker_form", clear_on_submit=False):
            new_root_input = st.text_input(
                "Path ของโฟลเดอร์ INKEXTRACT (ที่มี `.app/` อยู่ข้างใน)",
                value=str(install_root),
                placeholder=r"เช่น C:\Users\Peteishere\Desktop\INKEXTRACT",
                help="วาง path ของ INKEXTRACT install ที่ต้องการใช้ — แอปจะอ่านไฟล์ตั้งค่า "
                     "และโปรเจกต์จากที่นั่นแทน หลังตั้งแล้วต้องปิด-เปิดแอปใหม่",
                key="install_root_input",
            )
            col_set, col_clear = st.columns(2)
            submit_set = col_set.form_submit_button(
                "ตั้ง override + ปิด-เปิดแอปใหม่",
                type="primary",
                width='stretch',
            )
            submit_clear = col_clear.form_submit_button(
                "ล้าง override (กลับมา auto-detect)",
                width='stretch',
                disabled=not override_active,
            )

            if submit_set:
                candidate = Path(new_root_input.strip()).expanduser()
                if not candidate.exists():
                    st.error(f"ไม่พบโฟลเดอร์: `{candidate}`")
                elif not (candidate / ".app" / "app.py").exists():
                    st.error(
                        f"`{candidate}` ไม่ใช่ INKEXTRACT install (ไม่มี `.app/app.py`)"
                    )
                else:
                    override_file.parent.mkdir(parents=True, exist_ok=True)
                    override_file.write_text(str(candidate.resolve()), encoding='utf-8')
                    st.success(
                        f"ตั้ง override → `{candidate}` แล้ว — กรุณา **ปิดหน้าต่างนี้ + "
                        f"รัน Start.bat ใหม่** เพื่อให้ผลของการเปลี่ยน"
                    )

            if submit_clear and override_active:
                try:
                    override_file.unlink()
                    st.success("ล้าง override แล้ว — กรุณาปิด-เปิดแอปใหม่ เพื่อกลับไปใช้ auto-detect")
                except OSError as e:
                    st.error(f"ลบไม่ได้: {e}")


def _open_folder_in_explorer(folder_path: Path) -> None:
    """เปิดโฟลเดอร์ใน file explorer ของ OS (Windows/macOS/Linux)"""
    import os, subprocess, sys
    if not folder_path.exists():
        st.error(f"ไม่พบโฟลเดอร์: {folder_path}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder_path)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder_path)], check=False)
    except Exception as e:
        st.error(f"เปิดโฟลเดอร์ไม่ได้: {e}")


def _render_active_project_card(active) -> None:
    """กล่องเด่นๆ บอกโปรเจกต์ที่ใช้งานอยู่ + quick actions

    Psychology: F-pattern → eye เห็นชื่อโปรเจกต์ (top-left) → path → ปุ่ม action
    การจัดวางใช้กล่องส้มทำให้เด่นจากพื้นหลัง คนรู้ทันทีว่า "อันนี้คือสิ่งที่กำลังทำอยู่"
    """
    actual_path = str(active.root_path())
    tag = ("เริ่มต้น (ลบไม่ได้)" if active.is_default
           else (f"สร้าง: {active.created_at}" if active.created_at else ""))
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg,
                        var(--ink-surface-tint) 0%,
                        var(--ink-surface-tint-strong) 100%);
                    border: 2px solid var(--ink-orange);
                    border-radius: var(--ink-radius-lg);
                    padding: 1rem 1.2rem;
                    margin-bottom: 0.75rem;
                    box-shadow: var(--ink-shadow-md);">
            <div style="display:flex; align-items:center; gap:0.6rem;
                        margin-bottom: 0.3rem;">
                <span class="micon" style="font-size:1.4em;
                      color: var(--ink-orange-dark);">folder_special</span>
                <span style="font-size:0.85rem; color: var(--ink-text-muted);
                             text-transform: uppercase; letter-spacing: 0.5px;
                             font-weight: 600;">
                    โปรเจกต์ที่ใช้งานอยู่
                </span>
            </div>
            <div style="font-size: 1.35rem; font-weight: 700;
                        color: var(--ink-orange-dark); line-height: 1.2;">
                {active.name}
            </div>
            <div style="margin-top: 0.4rem; font-family: 'Consolas',monospace;
                        font-size: 0.82rem; color: var(--ink-text-muted);
                        background: var(--ink-surface-2);
                        padding: 4px 10px; border-radius: 6px;
                        border: 1px solid var(--ink-border-soft);
                        overflow: hidden; text-overflow: ellipsis;
                        white-space: nowrap;" title="{actual_path}">
                {actual_path}
            </div>
            {f'<div style="margin-top:0.4rem; font-size:0.78rem; color: var(--ink-text-muted);">{tag}</div>' if tag else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Quick action row — open folder
    col_open, _ = st.columns([1, 2])
    with col_open:
        if st.button(
            ":material/folder_open: เปิดโฟลเดอร์",
            help="เปิดโฟลเดอร์ของโปรเจกต์นี้ใน File Explorer",
            key="btn_open_active_folder",
            width='stretch',
        ):
            _open_folder_in_explorer(Path(active.path))


def _render_project_picker(projects, active) -> None:
    """รายการโปรเจกต์ทั้งหมด + ปุ่มสลับ + ปุ่มสร้างใหม่เด่นๆ ข้างบน

    Psychology: Zeigarnik effect → primary CTA "+ สร้างโปรเจกต์ใหม่" อยู่ข้างบน
    list ทำให้ user สังเกตเห็นทันที (ไม่ต้องเลื่อนสุดหน้า). list คือ
    secondary action — มี ✓ ทาง visual ว่าอันไหน active แล้ว
    """
    # Primary CTA: สร้างใหม่ (เด่น)
    with st.expander(":material/add_circle: สร้างโปรเจกต์ใหม่",
                     expanded=(len(projects) <= 1)):
        with st.form("create_project_form", clear_on_submit=True):
            new_name = st.text_input(
                "ชื่อโปรเจกต์",
                placeholder="เช่น 'ติดหนี้สามสิบล้าน' หรือ 'นิยายของฉัน A'",
                help="รองรับภาษาไทย/จีน/อังกฤษ — โฟลเดอร์จะถูกสร้างในชื่อที่ปลอดภัย",
                key="new_project_name_input",
            )
            st.caption(
                f"จะสร้างโฟลเดอร์ใน `{paths.PROJECTS_DIR}/<ชื่อ>/` "
                "พร้อมโฟลเดอร์ย่อยทั้งหมด (Raw, Input, Fix, Clean, …)"
            )
            submitted = st.form_submit_button(
                ":material/add: สร้างและสลับไปใช้งาน",
                type="primary",
                width='stretch',
            )
            if submitted:
                if not new_name or not new_name.strip():
                    st.error("กรุณากรอกชื่อโปรเจกต์")
                else:
                    try:
                        created = project_manager.create_project(new_name)
                        _reset_cached_processors()
                        st.toast(f"สร้าง '{created.name}' สำเร็จ")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"{e}")
                    except Exception as e:
                        st.error(f"สร้างไม่สำเร็จ: {e}")

    # List of projects
    st.markdown(
        f"<div style='font-size:0.85rem; color:var(--ink-text-muted); "
        f"margin: 0.75rem 0 0.4rem;'>"
        f"โปรเจกต์ทั้งหมด ({len(projects)})</div>",
        unsafe_allow_html=True,
    )
    for proj in projects:
        is_active = (proj.id == active.id)
        exists = Path(proj.path).exists()
        exists_mark = "" if exists else (
            '<span style="color:var(--ink-warn); font-weight:600;">'
            '[ไม่พบบนดิสก์]</span>'
        )
        sub_text = (
            "โปรเจกต์เริ่มต้น (ลบไม่ได้)" if proj.is_default
            else (f"สร้างเมื่อ: {proj.created_at}" if proj.created_at else "")
        )
        if is_active:
            row_bg = "var(--ink-surface-tint-strong)"
            border = "var(--ink-orange)"
            icon = "radio_button_checked"
            icon_color = "var(--ink-orange)"
        else:
            row_bg = "var(--ink-surface)"
            border = "var(--ink-border)"
            icon = "radio_button_unchecked"
            icon_color = "var(--ink-text-muted)"

        col_info, col_action = st.columns([4, 1], vertical_alignment="center")
        with col_info:
            st.markdown(
                f"""
                <div style="background: {row_bg};
                            padding: 0.7rem 0.9rem;
                            border-radius: var(--ink-radius-md);
                            border: 1px solid {border};
                            display: flex; align-items: center; gap: 0.6rem;">
                    <span class="micon" style="font-size:1.2em;color:{icon_color};">
                        {icon}</span>
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight: 600; font-size: 0.95rem;
                                    color: var(--ink-text);">
                            {proj.name} {exists_mark}
                        </div>
                        <div style="font-family: monospace; font-size: 0.75rem;
                                    color: var(--ink-text-muted);
                                    white-space: nowrap; overflow: hidden;
                                    text-overflow: ellipsis;">
                            {proj.path}
                        </div>
                        {f'<div style="font-size:0.72rem;color:var(--ink-text-faint);margin-top:2px;">{sub_text}</div>' if sub_text else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_action:
            if is_active:
                st.markdown(
                    '<div style="text-align:center; padding: 0.6rem;'
                    'color: var(--ink-orange-dark); font-weight:600; font-size:0.85rem;">'
                    'กำลังใช้งาน</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    ":material/swap_horiz: สลับไป",
                    type="primary",
                    width='stretch',
                    key=f"btn_switch_{proj.id}",
                    disabled=not exists,
                    help=("โฟลเดอร์ของโปรเจกต์นี้ไม่พบบนดิสก์ — สลับไม่ได้"
                          if not exists else "สลับมาใช้โปรเจกต์นี้"),
                ):
                    try:
                        project_manager.set_active_project(proj.id)
                        _reset_cached_processors()
                        st.toast(f"สลับไปยัง: {proj.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"สลับไม่ได้: {e}")


def _render_active_project_settings(active) -> None:
    """กล่อง expander รวม settings ของ active project (rename, delete, subfolders)

    Psychology: Progressive disclosure — settings ไม่ใช่สิ่งที่ทำบ่อย → ซ่อนใน
    expander เพื่อลด cognitive load. กลุ่มเดียวกัน ใส่กล่องเดียวกัน
    """
    with st.expander(
        f":material/settings: ตั้งค่าโปรเจกต์ '{active.name}'",
        expanded=False,
    ):
        # Subfolders summary
        st.markdown("**โฟลเดอร์ย่อย**")
        subdirs = [
            ("Raw", "ไฟล์ raw ต้นฉบับจีน"),
            ("Input", "ไฟล์แปลตั้งต้น (`[A]`/`[B]`)"),
            ("Fix", "ไฟล์ที่แก้ไขแล้ว"),
            ("Clean", "ไฟล์ที่ทำความสะอาดแล้ว"),
            ("Finish", "ฉบับเผยแพร่ (รอบที่จบแล้ว)"),
            ("Merge", "ไฟล์ที่รวม"),
            ("Separate", "ไฟล์ที่แยกตอน"),
            ("Import", "ไฟล์ที่ผู้ใช้แก้กลับ"),
            ("Output", "ผลลัพธ์ (error_trans.txt)"),
            ("Vocab", "ไฟล์คำศัพท์"),
            ("Style", "บันทึกสำนวน"),
            ("Prompt", "prompt templates"),
            ("Temp", "archive รอบเก่า"),
            ("Error/error_trans", "ข้อความที่แยกไปแปลแก้"),
        ]
        rows = []
        for sub, desc in subdirs:
            sub_path = Path(active.path) / sub
            n = "—"
            mark = "—"
            if sub_path.exists():
                try:
                    n = len(list(sub_path.glob("*.txt")))
                    mark = "พร้อม"
                except Exception:
                    n = "?"
                    mark = "พร้อม"
            else:
                mark = "ยังไม่มี"
            rows.append({"โฟลเดอร์": sub, "สถานะ": mark, "ไฟล์ .txt": n, "หน้าที่": desc})
        try:
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
        except Exception:
            for r in rows:
                st.markdown(f"- `{r['โฟลเดอร์']}/` — {r['สถานะ']} · {r['ไฟล์ .txt']} ไฟล์ · {r['หน้าที่']}")

        if not active.is_default:
            st.markdown("---")
            # Rename
            st.markdown("**เปลี่ยนชื่อโปรเจกต์**")
            with st.form(f"rename_project_form_{active.id}", clear_on_submit=False):
                renamed = st.text_input(
                    "ชื่อใหม่",
                    value=active.name,
                    help="เปลี่ยนทั้ง display name และชื่อโฟลเดอร์บนดิสก์",
                    key=f"rename_input_{active.id}",
                )
                if st.form_submit_button(":material/edit: เปลี่ยนชื่อ", width='stretch'):
                    if not renamed.strip():
                        st.error("กรุณากรอกชื่อใหม่")
                    elif renamed.strip() == active.name:
                        st.info("ชื่อยังเหมือนเดิม — ไม่มีอะไรเปลี่ยน")
                    else:
                        try:
                            new_proj = project_manager.rename_project(
                                active.id, renamed.strip()
                            )
                            _reset_cached_processors()
                            st.toast(f"เปลี่ยนชื่อเป็น '{new_proj.name}' แล้ว")
                            st.rerun()
                        except ValueError as e:
                            st.error(f"{e}")
                        except Exception as e:
                            st.error(f"เปลี่ยนชื่อไม่สำเร็จ: {e}")

            st.markdown("---")
            # Delete
            st.markdown("**ลบโปรเจกต์**")
            st.warning(
                f"กำลังจะลบ **{active.name}** — หลังลบจะกลับไปใช้"
                "โปรเจกต์เริ่มต้นโดยอัตโนมัติ"
            )
            delete_files = st.checkbox(
                "ลบโฟลเดอร์และไฟล์ทั้งหมดของโปรเจกต์นี้ด้วย (ทำลายข้อมูลถาวร)",
                value=False,
                key=f"delete_files_{active.id}",
                help="ถ้าไม่เลือก จะลบเฉพาะออกจากรายการ — โฟลเดอร์ยังอยู่บนดิสก์",
            )
            if st.button(
                ":material/delete_forever: ยืนยันการลบโปรเจกต์",
                type="secondary",
                width='stretch',
                key=f"btn_delete_{active.id}",
            ):
                try:
                    project_manager.delete_project(
                        active.id, delete_files=delete_files,
                    )
                    _reset_cached_processors()
                    st.toast(f"ลบ '{active.name}' แล้ว")
                    st.rerun()
                except Exception as e:
                    st.error(f"ลบไม่สำเร็จ: {e}")


def render() -> None:
    """หน้าจัดการโปรเจกต์ — ออกแบบตามหลัก progressive disclosure + F-pattern

    โครงสร้างจากบนลงล่าง (ตามลำดับความสำคัญต่อ user):
      1. กล่อง active project ใหญ่ๆ (รู้ทันทีว่าทำงานอันไหนอยู่)
      2. รายการ + ปุ่มสร้างใหม่เด่นๆ (action ที่ทำบ่อย)
      3. Settings ของ active (พับ — ทำเป็นครั้งคราว)
      4. ตำแหน่ง install (พับ — diagnostic เท่านั้น)
    """
    active = project_manager.get_active_project()
    projects = project_manager.list_projects()

    # 1. Active project card — เด่น
    _render_active_project_card(active)

    # 2. รายการโปรเจกต์ + สร้างใหม่
    st.markdown(
        '<div style="margin: 0.6rem 0 0.4rem; font-size: 0.95rem; '
        'font-weight: 600; color: var(--ink-text);">'
        'เลือก / สร้างโปรเจกต์</div>',
        unsafe_allow_html=True,
    )
    _render_project_picker(projects, active)

    # 3. Settings ของ active (rename / delete / subfolders) — พับ
    _render_active_project_settings(active)

    # 4. Install root (diagnostic) — พับ
    _render_install_root_section()
