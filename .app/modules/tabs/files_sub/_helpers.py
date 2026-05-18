"""Shared UI helpers สำหรับ tab จัดการไฟล์ — STEP header, folder picker, preview boxes.

ใช้ใน merge / separate / generate / converter / format / clear เพื่อให้ UI ดูคล้ายกัน
ใช้ใน proof.py ได้ด้วย (folder_select)
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import streamlit as st

from modules import paths


# ─── STEP header ───────────────────────────────────────────────────────────
def step_header(num: int, title: str, desc: Optional[str] = None) -> None:
    """แสดงหัวข้อขั้นตอน เช่น 'ขั้นที่ 1 — เลือกไฟล์ต้นทาง'"""
    desc_html = (
        f'<div style="color:var(--ink-text-muted);font-size:0.85em;margin-top:0.15rem">'
        f'{desc}</div>'
        if desc else ""
    )
    st.markdown(
        f'<div style="margin:0.9rem 0 0.4rem 0;">'
        f'  <span style="background:var(--ink-orange,#f97316);color:var(--ink-on-primary,white);'
        f'    padding:0.18rem 0.55rem;border-radius:0.35rem;font-weight:700;'
        f'    font-size:0.85em;margin-right:0.55rem;">ขั้นที่ {num}</span>'
        f'  <span style="font-weight:600;font-size:1.05rem;color:var(--ink-text);">{title}</span>'
        f'  {desc_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─── Native folder picker via tkinter ──────────────────────────────────────
def _native_folder_dialog(initial: Optional[str] = None) -> Optional[str]:
    """เปิด native folder picker (Windows Explorer / macOS Finder / Linux file dialog).

    ใช้ tkinter ใน Python stdlib — ทำงานบน server machine (= user machine สำหรับ INKEXTRACT)
    Returns: path ที่เลือก หรือ None ถ้ายกเลิก
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        folder = filedialog.askdirectory(
            parent=root,
            title="เลือกโฟลเดอร์",
            initialdir=initial or str(Path.home()),
        )
        root.destroy()
        return folder if folder else None
    except Exception as e:
        st.error(f"เปิด folder picker ไม่ได้: {e}")
        return None


# ─── Pipeline-aware folder dropdown ────────────────────────────────────────
# Pipeline ของแอป: Raw → Input → Fix → Clean → Merge / Separate → Finish
_DEFAULT_PRESETS: Dict[str, Path] = {
    "Raw": paths.RAW_INPUT_DIR,
    "Input": paths.INPUT_DIR,
    "Fix": paths.FIX_DIR,
    "Clean": paths.CLEAN_DIR,
    "Merge": paths.MERGE_DIR,
    "Separate": paths.SEPARATE_DIR,
    "Finish": paths.FINISH_DIR,
    "Output": paths.OUTPUT_DIR,
}


def folder_select(
    label: str,
    key: str,
    presets: List[str],
    suggested: Optional[str] = None,
    help: Optional[str] = None,
    show_count: bool = True,
    saved_value: Optional[str] = None,
) -> Tuple[Optional[Path], str]:
    """แสดง dropdown เลือกโฟลเดอร์ (preset + browse picker) — ใช้ทั่วแอป.

    Args:
        label: ป้ายของ selectbox
        key: streamlit key ต้องไม่ซ้ำ
        presets: list ของชื่อ preset (เช่น ['Clean', 'Input', 'Fix'])
        suggested: ชื่อ preset ที่ติด '(แนะนำ)' (default index)
        help: tooltip
        show_count: แสดงจำนวนไฟล์ .txt ที่พบใน folder
        saved_value: ค่าที่บันทึก (string path) — ถ้ามี ใช้แทน suggested

    Returns:
        (path, label) — path เป็น None ถ้า user ยังไม่เลือก/ระบุ
    """
    # ─── สร้าง dropdown labels ───
    display_labels = []
    label_to_path: Dict[str, Path] = {}
    for name in presets:
        path = _DEFAULT_PRESETS.get(name)
        if path is None:
            continue
        display = f"{name} (แนะนำ)" if name == suggested else name
        display_labels.append(display)
        label_to_path[display] = path
    display_labels.append("เลือกโฟลเดอร์อื่น (browse)")

    # ─── default index ───
    default_idx = 0
    if saved_value:
        matched = False
        for i, disp in enumerate(display_labels[:-1]):
            if str(label_to_path[disp]) == saved_value:
                default_idx = i
                matched = True
                break
        if not matched and saved_value:
            # saved = custom path → default = browse
            default_idx = len(display_labels) - 1
    elif suggested:
        for i, disp in enumerate(display_labels[:-1]):
            if disp.startswith(f"{suggested} "):
                default_idx = i
                break

    selected_label = st.selectbox(
        label,
        options=display_labels,
        index=default_idx,
        help=help,
        key=key,
    )

    # ─── ถ้าเลือก browse → ปุ่ม browse + แสดง path ที่เลือก ───
    if selected_label == "เลือกโฟลเดอร์อื่น (browse)":
        picked_key = f"{key}_picked"
        if picked_key not in st.session_state:
            # ใช้ saved_value เป็นค่าเริ่มต้น ถ้า saved เป็น custom
            preset_paths = [str(p) for p in label_to_path.values()]
            if saved_value and saved_value not in preset_paths:
                st.session_state[picked_key] = saved_value
            else:
                st.session_state[picked_key] = ""

        col_btn, col_show = st.columns([1, 3])
        with col_btn:
            if st.button("เลือกโฟลเดอร์...", key=f"{key}_browse_btn",
                         width="stretch", help="เปิดหน้าต่างเลือกโฟลเดอร์ของระบบ"):
                initial = st.session_state[picked_key] or str(paths.ROOT)
                picked = _native_folder_dialog(initial=initial)
                if picked:
                    st.session_state[picked_key] = picked
                    st.rerun()
        with col_show:
            current = st.session_state.get(picked_key, "")
            if current:
                st.code(current, language=None)
            else:
                st.caption("ยังไม่เลือกโฟลเดอร์ — กดปุ่ม **เลือกโฟลเดอร์...**")

        path = Path(st.session_state[picked_key]) if st.session_state[picked_key] else None
        result_label = "เลือกเอง"
    else:
        path = label_to_path[selected_label]
        result_label = selected_label.replace(" (แนะนำ)", "")

    # ─── แสดงจำนวนไฟล์ ───
    if show_count and path:
        if path.exists():
            n = len(list(path.glob("*.txt")))
            st.caption(f"พบไฟล์ .txt: **{n:,}** ไฟล์ในโฟลเดอร์ `{path}`")
        else:
            st.caption(f"โฟลเดอร์ `{path}` ยังไม่มี (จะถูกสร้างให้อัตโนมัติ)")

    return path, result_label


# ─── Preview: filename list ────────────────────────────────────────────────
def filename_preview(filenames: List[str], total: Optional[int] = None,
                     max_show: int = 6, title: str = "ชื่อไฟล์ที่จะสร้าง",
                     all_filenames: Optional[List[str]] = None) -> None:
    """แสดงรายการชื่อไฟล์แบบกล่อง — show max_show ตัวแรก + ขยายดูทั้งหมดได้.

    Args:
        filenames: list ของ filenames ที่จะแสดงในกล่อง (max_show ตัวแรก)
        total: จำนวนรวมจริง (ถ้าต่างจาก len(filenames))
        max_show: แสดงสูงสุดกี่ตัวในกล่องหลัก
        title: หัวเรื่อง
        all_filenames: list ของ filenames ทั้งหมด (ถ้ามี → เปิด expander "ดูทั้งหมด")
    """
    if not filenames:
        st.info("ยังไม่มีไฟล์ที่จะสร้าง — ตั้งค่าให้ครบก่อน")
        return

    total = total if total is not None else len(filenames)
    shown = filenames[:max_show]
    list_html = ""
    for name in shown:
        list_html += (
            f'<div style="font-family:monospace;font-size:0.88em;color:var(--ink-text);'
            f'padding:0.18rem 0;">{name}</div>'
        )
    extra = total - len(shown)
    if extra > 0:
        list_html += (
            f'<div style="color:var(--ink-text-muted);font-size:0.85em;'
            f'padding:0.35rem 0 0 0;font-style:italic;">'
            f'... และอีก {extra:,} ไฟล์</div>'
        )

    st.markdown(
        f'<div style="background:var(--ink-surface-tint,#fff7ed);'
        f'border-left:3px solid var(--ink-orange,#f97316);padding:0.65rem 0.95rem;'
        f'border-radius:0.45rem;margin:0.5rem 0;">'
        f'<div style="font-weight:600;color:var(--ink-accent-strong,#c2410c);'
        f'font-size:0.92em;margin-bottom:0.45rem;">'
        f'{title} ({total:,} ไฟล์)</div>'
        f'{list_html}</div>',
        unsafe_allow_html=True,
    )

    # expander ดูชื่อทั้งหมด
    if all_filenames and len(all_filenames) > max_show:
        with st.expander(f"ดูชื่อไฟล์ทั้งหมด ({len(all_filenames):,} รายการ)", expanded=False):
            st.code("\n".join(all_filenames), language=None)


def content_preview(text: str, title: str = "ตัวอย่างเนื้อหา (10 บรรทัดแรก)",
                    max_lines: int = 10) -> None:
    """แสดงตัวอย่างเนื้อหาในกล่อง code"""
    if not text or not text.strip():
        st.caption(f"{title}: (ว่าง)")
        return
    lines = text.splitlines()
    preview = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        preview += f"\n... ({len(lines) - max_lines:,} บรรทัดที่เหลือ)"
    st.markdown(f"**{title}**")
    st.code(preview, language="text", line_numbers=False)


def stat_chips(items: List[Tuple[str, str]]) -> None:
    """แสดง chip horizontal เช่น [('พบ', '12 ไฟล์'), ('ขนาด', '1.2 MB')]"""
    if not items:
        return
    chips_html = ""
    for label, value in items:
        chips_html += (
            f'<span style="display:inline-flex;align-items:baseline;'
            f'background:var(--ink-surface,#f8f8f8);border:1px solid var(--ink-border,#ddd);'
            f'padding:0.25rem 0.7rem;border-radius:1rem;margin:0.15rem 0.3rem 0.15rem 0;'
            f'font-size:0.88em;">'
            f'<span style="color:var(--ink-text-muted);margin-right:0.4rem;">{label}</span>'
            f'<span style="font-weight:700;color:var(--ink-text);">{value}</span>'
            f'</span>'
        )
    st.markdown(f'<div style="margin:0.4rem 0;">{chips_html}</div>',
                unsafe_allow_html=True)


def gen_filenames_preview(prefix: str, padding: int, suffix: str,
                          start: int, count: int) -> List[str]:
    """สร้างรายการชื่อไฟล์ตาม pattern เช่น Chapter_0001.txt"""
    return [
        f"{prefix}{str(i).zfill(padding)}{suffix}.txt"
        for i in range(start, start + count)
    ]
