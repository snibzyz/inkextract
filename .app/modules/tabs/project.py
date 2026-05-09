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
    """แถบบอกโปรเจกต์ที่ใช้งานอยู่ — แสดงเหนือ tabs ตลอดเวลา"""
    active = project_manager.get_active_project()
    label = "(เริ่มต้น)" if active.is_default else ""
    st.markdown(
        f"""
        <div style="background: var(--ink-surface-tint, #fff7ed); padding: 0.6rem 1rem;
                    border-left: 4px solid var(--ink-orange, #f97316);
                    border-radius: var(--ink-radius-md, 8px);
                    margin-bottom: 0.75rem; color: var(--ink-text, #111);">
            <span style="font-size: 0.85em; color: var(--ink-text-muted, #666);">
                โปรเจกต์ที่ใช้งาน:
            </span>
            <strong style="font-size: 1.05em;">{active.name}</strong>
            <span style="font-size: 0.8em; color: var(--ink-text-muted, #666);
                         margin-left: 0.5rem;">{label}</span>
            <span style="font-size: 0.8em; color: var(--ink-text-muted, #666);
                         margin-left: 0.75rem;">
                <code>{active.path}</code>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """หน้าจัดการโปรเจกต์เต็มรูปแบบ"""
    st.markdown(
        """
        <div style="background: var(--ink-surface-tint, #fff7ed); padding: 1.25rem;
                    border-radius: var(--ink-radius-lg, 12px);
                    border-left: 4px solid var(--ink-orange, #f97316);
                    margin-bottom: 1.25rem; color: var(--ink-text, #111);">
            <h4 style="margin: 0; color: var(--ink-orange-dark, #c2410c);">
                จัดการโปรเจกต์
            </h4>
            <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted, #666);">
                แต่ละโปรเจกต์เก็บไฟล์ของตัวเองแยกกัน — ใช้สำหรับทำหลายเรื่องพร้อมกัน
                โฟลเดอร์ย่อย (0-input, 1-fix, 2-clean, …) ของแต่ละโปรเจกต์ไม่ปนกัน
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    active = project_manager.get_active_project()
    projects = project_manager.list_projects()

    # ---------- โปรเจกต์ที่ใช้งานอยู่ ----------
    st.markdown("#### โปรเจกต์ที่ใช้งานอยู่")

    col_info, col_open = st.columns([3, 1], vertical_alignment="center")
    with col_info:
        st.markdown(
            f"""
            **{active.name}**
            `{active.path}`
            """
        )
    with col_open:
        if st.button(
            "เปิดโฟลเดอร์",
            help="เปิดโฟลเดอร์ของโปรเจกต์นี้ใน File Explorer",
            key="btn_open_active_folder",
            width='stretch',
        ):
            try:
                import os, subprocess, sys
                folder = Path(active.path)
                if not folder.exists():
                    st.error(f"ไม่พบโฟลเดอร์: {folder}")
                elif sys.platform == "win32":
                    os.startfile(str(folder))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(folder)], check=False)
                else:
                    subprocess.run(["xdg-open", str(folder)], check=False)
            except Exception as e:
                st.error(f"เปิดโฟลเดอร์ไม่ได้: {e}")

    # แสดงโฟลเดอร์ย่อยของโปรเจกต์ (INKIDEA-style PascalCase layout)
    with st.expander("โฟลเดอร์ย่อยของโปรเจกต์", expanded=False):
        subdirs = [
            ("Raw", "ไฟล์ raw ต้นฉบับจีน"),
            ("Input", "ไฟล์แปลตั้งต้น (`[A]`/`[B]`)"),
            ("Fix", "ไฟล์ที่แก้ไขแล้ว"),
            ("Clean", "ไฟล์ที่ทำความสะอาดแล้ว"),
            ("Finish", "ฉบับเผยแพร่ (รอบที่จบแล้ว)"),
            ("Merge", "ไฟล์ที่รวม"),
            ("Separate", "ไฟล์ที่แยกตอน"),
            ("Import", "ไฟล์ที่ผู้ใช้แก้กลับ (สำหรับ import)"),
            ("Output", "ผลลัพธ์ (error_trans.txt, ฯลฯ)"),
            ("Vocab", "ไฟล์คำศัพท์"),
            ("Style", "บันทึกสำนวน (style-notes.txt)"),
            ("Prompt", "prompt templates (fix.md ฯลฯ)"),
            ("Temp", "archive รอบเก่า"),
            ("Error/error_trans", "ข้อความที่แยกไปแปลแก้"),
        ]
        for sub, desc in subdirs:
            sub_path = Path(active.path) / sub
            mark = "[มี]" if sub_path.exists() else "[ไม่มี]"
            n_files = "?"
            if sub_path.exists():
                try:
                    n_files = str(len(list(sub_path.glob("*.txt"))))
                except Exception:
                    n_files = "?"
            st.markdown(f"- {mark} `{sub}/` — {desc} _({n_files} ไฟล์ .txt)_")

    st.markdown("---")

    # ---------- รายการโปรเจกต์ทั้งหมด ----------
    st.markdown(f"#### รายการโปรเจกต์ทั้งหมด ({len(projects)} โปรเจกต์)")

    for proj in projects:
        is_active = (proj.id == active.id)
        exists_mark = "[มี]" if Path(proj.path).exists() else "[ไม่พบ]"
        badge = " &middot; <span style='color: var(--ink-orange, #f97316);'>กำลังใช้งาน</span>" if is_active else ""
        row_bg = "var(--ink-surface-tint, #fff7ed)" if is_active else "transparent"
        border_color = "var(--ink-orange, #f97316)" if is_active else "rgba(0,0,0,0.08)"

        sub_text = ""
        if proj.is_default:
            sub_text = "โปรเจกต์เริ่มต้น (ลบไม่ได้)"
        elif proj.created_at:
            sub_text = f"สร้างเมื่อ: {proj.created_at}"

        col_info, col_action = st.columns([4, 1], vertical_alignment="center")
        with col_info:
            st.markdown(
                f"""
                <div style="background: {row_bg}; padding: 0.6rem 0.8rem;
                            border-radius: var(--ink-radius-md, 8px);
                            border-left: 3px solid {border_color};">
                    <div style="font-weight: 600; font-size: 1rem; color: var(--ink-text, #111);">
                        {proj.name}{badge}
                    </div>
                    <div style="font-size: 0.78em; color: var(--ink-text-muted, #666);
                                margin-top: 0.15rem;">
                        {sub_text}
                    </div>
                    <div style="font-family: monospace; font-size: 0.78em;
                                color: var(--ink-text-muted, #888); margin-top: 0.2rem;
                                white-space: nowrap; overflow: hidden;
                                text-overflow: ellipsis;">
                        {exists_mark} {proj.path}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_action:
            if is_active:
                st.button(
                    "ใช้งานอยู่",
                    disabled=True,
                    width='stretch',
                    key=f"btn_using_{proj.id}",
                )
            else:
                if st.button(
                    "สลับไป",
                    type="primary",
                    width='stretch',
                    key=f"btn_switch_{proj.id}",
                ):
                    try:
                        project_manager.set_active_project(proj.id)
                        _reset_cached_processors()
                        st.toast(f"สลับไปยัง: {proj.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"สลับไม่ได้: {e}")

    st.markdown("---")

    # ---------- สร้างโปรเจกต์ใหม่ ----------
    st.markdown("#### สร้างโปรเจกต์ใหม่")
    with st.form("create_project_form", clear_on_submit=True):
        new_name = st.text_input(
            "ชื่อโปรเจกต์",
            placeholder="เช่น 'ติดหนี้สามสิบล้าน' หรือ 'นิยายของฉัน A'",
            help="รองรับภาษาไทย/จีน/อังกฤษ — โฟลเดอร์จะถูกสร้างในชื่อที่ปลอดภัย",
            key="new_project_name_input",
        )
        st.caption(
            f"จะสร้างโฟลเดอร์ใน `{paths.PROJECTS_DIR}/<ชื่อ>/` "
            "พร้อมโฟลเดอร์ย่อยทั้งหมด (0-input, 1-fix, …)"
        )
        submitted = st.form_submit_button(
            "สร้างและสลับไปใช้งาน",
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

    # ---------- เปลี่ยนชื่อโปรเจกต์ที่ใช้งานอยู่ ----------
    if not active.is_default:
        st.markdown("---")
        st.markdown("#### เปลี่ยนชื่อโปรเจกต์ที่ใช้งานอยู่")
        with st.form(f"rename_project_form_{active.id}", clear_on_submit=False):
            renamed = st.text_input(
                "ชื่อใหม่",
                value=active.name,
                help="เปลี่ยนทั้ง display name และชื่อโฟลเดอร์บนดิสก์ — ไฟล์ทุกตัวข้างในจะตามไปด้วย",
                key=f"rename_input_{active.id}",
            )
            submitted_rename = st.form_submit_button(
                "เปลี่ยนชื่อ",
                width='stretch',
            )
            if submitted_rename:
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

    # ---------- ลบโปรเจกต์ที่ใช้งานอยู่ ----------
    if not active.is_default:
        st.markdown("---")
        st.markdown("#### ลบโปรเจกต์ที่ใช้งานอยู่")
        st.warning(
            f"กำลังจะลบ **{active.name}** — หลังลบจะกลับไปใช้โปรเจกต์เริ่มต้นโดยอัตโนมัติ"
        )
        delete_files = st.checkbox(
            "ลบโฟลเดอร์และไฟล์ทั้งหมดของโปรเจกต์นี้ด้วย (ทำลายข้อมูลถาวร)",
            value=False,
            key=f"delete_files_{active.id}",
            help="ถ้าไม่เลือก จะลบเฉพาะออกจากรายการ — โฟลเดอร์ยังอยู่ในดิสก์",
        )
        if st.button(
            "ยืนยันการลบโปรเจกต์",
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
