"""tabs/files_sub/clear.py — ลบไฟล์ในโฟลเดอร์ที่เลือก

เลือกโฟลเดอร์ → ดูสรุป → ยืนยัน → ลบ
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path
import shutil

from modules import paths
from . import _helpers as h


# โฟลเดอร์ที่อนุญาตให้ลบได้ + คำอธิบาย
_FOLDERS = {
    "Input":    (paths.INPUT_DIR,        "ไฟล์แปลตั้งต้น"),
    "Raw":      (paths.RAW_INPUT_DIR,    "ไฟล์ raw จีนต้นฉบับ — ห้ามลบถ้ายังไม่สำรอง"),
    "Fix":      (paths.FIX_DIR,          "ไฟล์ที่แก้ไขแล้ว"),
    "Clean":    (paths.CLEAN_DIR,        "ไฟล์ที่ทำความสะอาดแล้ว"),
    "Merge":    (paths.MERGE_DIR,        "ไฟล์ที่รวมแล้ว"),
    "Separate": (paths.SEPARATE_DIR,     "ไฟล์ที่แยกแล้ว"),
    "Import":   (paths.IMPORT_FIX_DIR,   "ไฟล์ที่ผู้ใช้แก้กลับ"),
    "Output":   (paths.OUTPUT_DIR,       "error_trans / รายงาน ฯลฯ"),
}

# default selection — ปลอดภัย (ไม่ติ๊ก Raw)
_DEFAULT_SELECTION = {
    "Input": False,
    "Raw": False,
    "Fix": False,
    "Clean": False,
    "Merge": False,
    "Separate": False,
    "Import": False,
    "Output": False,
}


def _count(folder: Path) -> int:
    return len(list(folder.glob("*"))) if folder.exists() else 0


def render(file_processor) -> None:
    """ลบไฟล์ tab — ลบไฟล์ในโฟลเดอร์ที่เลือก"""
    st.markdown(
        '<div style="background:var(--ink-warn-bg,#fff7ed);padding:0.6rem 0.9rem;'
        'border-left:3px solid var(--ink-warn,#c2410c);border-radius:0.4rem;'
        'margin-bottom:0.7rem;color:var(--ink-warn,#c2410c);font-weight:600;font-size:0.92em;">'
        'การลบไฟล์เป็นแบบถาวร กู้คืนไม่ได้ — กรุณาตรวจสอบก่อนกดยืนยัน'
        '</div>',
        unsafe_allow_html=True,
    )

    # init session state
    if 'clear_selection' not in st.session_state:
        st.session_state.clear_selection = dict(_DEFAULT_SELECTION)
    else:
        # เติม keys ใหม่ (กัน upgrade)
        for k, v in _DEFAULT_SELECTION.items():
            st.session_state.clear_selection.setdefault(k, v)
    if 'clear_confirm' not in st.session_state:
        st.session_state.clear_confirm = False

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "เลือกโฟลเดอร์ที่ต้องการลบ")

    # เลือกทั้งหมด / ยกเลิก / คืน default
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("เลือกทั้งหมด", width='stretch', key="clr_all"):
            for k in st.session_state.clear_selection:
                st.session_state.clear_selection[k] = True
            st.rerun()
    with col_btn2:
        if st.button("ยกเลิกทั้งหมด", width='stretch', key="clr_none"):
            for k in st.session_state.clear_selection:
                st.session_state.clear_selection[k] = False
            st.rerun()
    with col_btn3:
        if st.button("คืนค่า default", width='stretch', key="clr_reset"):
            st.session_state.clear_selection = dict(_DEFAULT_SELECTION)
            st.session_state.clear_confirm = False
            st.rerun()

    st.markdown("")

    # checkbox list — ใช้ container แบบ 2 columns
    col_left, col_right = st.columns(2)
    keys = list(_FOLDERS.keys())
    half = (len(keys) + 1) // 2
    left_keys = keys[:half]
    right_keys = keys[half:]

    def _render_folder_row(name: str):
        folder, desc = _FOLDERS[name]
        n_files = _count(folder)
        col_chk, col_view = st.columns([5, 2])
        with col_chk:
            checked = st.checkbox(
                f"**{name}** — {desc}",
                value=st.session_state.clear_selection.get(name, False),
                key=f"clr_chk_{name}",
            )
            st.session_state.clear_selection[name] = checked
            st.caption(f"`{folder}` · พบ {n_files:,} รายการ")
        with col_view:
            if n_files > 0:
                with st.expander(f"ดูรายการ ({n_files})", expanded=False):
                    files = list(folder.glob("*"))[:50]
                    for f in files:
                        st.caption(f"`{f.name}`")
                    if n_files > 50:
                        st.caption(f"... และอีก {n_files - 50:,} รายการ")

    with col_left:
        for n in left_keys:
            _render_folder_row(n)
    with col_right:
        for n in right_keys:
            _render_folder_row(n)

    # ───────────── ขั้นที่ 2 — สรุป + ลบ ─────────────
    st.markdown("---")
    selected = [n for n, sel in st.session_state.clear_selection.items() if sel]

    if not selected:
        st.info("ยังไม่ได้เลือกโฟลเดอร์ — ติ๊กโฟลเดอร์ด้านบนเพื่อเลือกลบ")
        return

    h.step_header(2, "สรุปก่อนลบ + ยืนยัน")
    total_files = 0
    summary_lines = []
    for n in selected:
        folder, _ = _FOLDERS[n]
        cnt = _count(folder)
        total_files += cnt
        summary_lines.append(f"**{n}** ({cnt:,} ไฟล์) — `{folder}`")

    st.markdown(
        f'<div style="background:var(--ink-surface-tint);padding:0.7rem 1rem;'
        f'border-left:3px solid var(--ink-orange,#f97316);border-radius:0.4rem;'
        f'margin:0.5rem 0;">'
        f'จะลบทั้งหมด <b>{total_files:,}</b> รายการ จาก <b>{len(selected)}</b> โฟลเดอร์:'
        f'</div>',
        unsafe_allow_html=True,
    )
    for line in summary_lines:
        st.markdown(f"- {line}")

    # ปุ่มลบ + ยืนยัน
    if not st.session_state.clear_confirm:
        if st.button(f" **ลบ {total_files:,} รายการ**", type="primary", width='stretch',
                     key="clr_btn_delete", disabled=(total_files == 0)):
            st.session_state.clear_confirm = True
            st.rerun()
    else:
        st.error(f"**ยืนยันการลบ {total_files:,} รายการ?** — กู้คืนไม่ได้!")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button(" **ยืนยันลบเลย**", type="primary", width='stretch',
                         key="clr_btn_yes"):
                deleted = 0
                errors = []
                with st.spinner("กำลังลบ..."):
                    for n in selected:
                        folder, _ = _FOLDERS[n]
                        if not folder.exists():
                            continue
                        try:
                            for item in folder.glob("*"):
                                if item.is_file():
                                    item.unlink()
                                    deleted += 1
                                elif item.is_dir():
                                    shutil.rmtree(item)
                                    deleted += 1
                        except Exception as e:
                            errors.append(f"`{n}`: {e}")
                st.session_state.clear_confirm = False
                if deleted:
                    st.success(f"ลบสำเร็จ {deleted:,} รายการ")
                    st.toast(f"ลบ {deleted} รายการสำเร็จ")
                if errors:
                    st.error("บางส่วนลบไม่สำเร็จ:")
                    for e in errors[:5]:
                        st.write(f"- {e}")
                st.rerun()
        with col_no:
            if st.button("ยกเลิก", width='stretch', key="clr_btn_no"):
                st.session_state.clear_confirm = False
                st.rerun()
