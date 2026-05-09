"""tabs/manuscript.py — Tab 'ตรวจต้นฉบับ' (port จาก noveleditor)

UX:
- Stats: 4 การ์ดเรียงแนวนอน
- File explorer (ฝั่งซ้าย): card-list แบบเดียวกับ noveleditor
    •  checkbox = เลือกลบ
    • คลิกชื่อไฟล์ = พรีวิวเฉย ๆ (ไม่เกี่ยวกับลบ)
    • ไฟล์เล็กผิดปกติ → highlight แดง + 
- Preview (ฝั่งขวา): VS-Code style monospace + line numbers
"""
from __future__ import annotations
from pathlib import Path
import streamlit as st

from modules import paths, ui, manuscript_checker


# ============================================================
# Helpers
# ============================================================

def _sorted_entries(scan):
    """เรียงไฟล์ตามเลขตอน ASC"""
    return sorted(
        scan.files,
        key=lambda e: (
            e.number is None,
            e.number if e.number is not None else 0,
            e.filename,
        ),
    )


def _open_folder(path: str) -> None:
    """เปิดโฟลเดอร์ใน file explorer ของ OS"""
    import subprocess
    import platform
    import os
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        ui.error(f"ไม่พบโฟลเดอร์: {abs_path}")
        return
    try:
        sys_name = platform.system()
        if sys_name == 'Windows':
            subprocess.Popen(['explorer', abs_path])
        elif sys_name == 'Darwin':
            subprocess.Popen(['open', abs_path])
        else:
            subprocess.Popen(['xdg-open', abs_path])
    except Exception as e:
        ui.error(f"เปิดโฟลเดอร์ไม่ได้: {e}")


def _chk_key(filename: str) -> str:
    return f"ms_chk_{filename}"


def _set_all_checkboxes(scan, value: bool) -> None:
    """ปรับ widget-state ของ checkbox ทุกตัว — ใช้ก่อน st.rerun()"""
    for e in scan.files:
        st.session_state[_chk_key(e.filename)] = value


def _select_only(scan, filenames: set) -> None:
    """ตั้งให้ checkbox เป็น True เฉพาะรายชื่อนี้"""
    for e in scan.files:
        st.session_state[_chk_key(e.filename)] = e.filename in filenames


# ============================================================
# Sub-renderers
# ============================================================

def _render_folder_bar(folder_default: str):
    """แถวบนสุด: text input + ปุ่มสำคัญ (ในการ์ดสีขาว)"""
    st.markdown('<div class="ms-folderbar-wrap">', unsafe_allow_html=True)
    cols = st.columns([5, 1, 1, 1])
    with cols[0]:
        folder_text = st.text_input(
        "โฟลเดอร์ที่จะตรวจ",
            value=folder_default,
            help="path ของโฟลเดอร์ที่มีไฟล์ .txt — กดปุ่ม 'ตั้งค่า' เพื่อสแกน",
            key="ms_folder_input",
            label_visibility="collapsed",
            placeholder="path ของโฟลเดอร์ (เช่น input หรือ C:\\path\\to\\folder)",
        )
    with cols[1]:
        do_set = ui.primary_button("ตั้งค่า", help="สแกนไฟล์จากโฟลเดอร์นี้", key="ms_set")
    with cols[2]:
        do_open = ui.secondary_button("เปิด", help="เปิดโฟลเดอร์ในตัวจัดการไฟล์", key="ms_open")
    with cols[3]:
        do_reload = ui.secondary_button("โหลดใหม่", help="สแกนโฟลเดอร์เดิมอีกครั้ง", key="ms_reload")
    st.markdown('</div>', unsafe_allow_html=True)
    return folder_text, do_set, do_open, do_reload


def _render_action_bar(scan, selected: set):
    """ปุ่ม bulk-select + Process — ปรับ widget-state ของ checkbox โดยตรง"""
    cols = st.columns([1.5, 1.5, 1.3, 0.9, 1.6])

    with cols[0]:
        if ui.secondary_button(
        "เลือกไฟล์ขนาดเล็ก",
            help="ติ๊กเฉพาะไฟล์ที่ถูกเน้นสีแดง",
            key="ms_select_small",
        ):
            small = {e.filename for e in scan.files if e.is_small}
            _select_only(scan, small)
            st.session_state['manuscript_selected'] = small
            st.rerun()

    with cols[1]:
        all_selected = bool(selected) and len(selected) == scan.total_files
        label = "ยกเลิกทั้งหมด" if all_selected else "เลือกทั้งหมด"
        if ui.secondary_button(label, help="สลับเลือก/ยกเลิกทุกไฟล์", key="ms_select_all"):
            if all_selected:
                _set_all_checkboxes(scan, False)
                st.session_state['manuscript_selected'] = set()
            else:
                _set_all_checkboxes(scan, True)
                st.session_state['manuscript_selected'] = {e.filename for e in scan.files}
            st.rerun()

    with cols[2]:
        if ui.secondary_button("ล้างเลือก", help="เคลียร์การเลือกทั้งหมด", key="ms_clear_sel"):
            _set_all_checkboxes(scan, False)
            st.session_state['manuscript_selected'] = set()
            st.rerun()

    with cols[3]:
        st.markdown(
            f'<div style="padding-top:4px;text-align:center">'
            f'<span class="ms-count-chip">เลือกแล้ว {len(selected)}</span></div>',
            unsafe_allow_html=True,
        )

    with cols[4]:
        do_process = ui.primary_button(
            f"ประมวลผล ({len(selected)})",
            help="ลบไฟล์ที่เลือก + เรียงเลขใหม่ → workspace/output/manuscript/raw/",
            key="ms_process",
            disabled=len(selected) == 0,
        )

    return do_process


def _render_explorer(scan, sorted_entries, selected: set):
    """ฝั่งซ้าย: card-list ของไฟล์ (เหมือน noveleditor)

    UX:
    -  checkbox = เลือกลบ
    - ปุ่มชื่อไฟล์ = พรีวิวเท่านั้น (ไฟล์ที่กำลังพรีวิวจะเป็น primary สีส้ม)
    """
    preview_name = st.session_state.get('manuscript_preview')

    st.markdown(
        f'<div class="ms-pane-header">ไฟล์ทั้งหมด '
        f'<span style="opacity:0.7;font-weight:500;font-size:0.85em;margin-left:6px">'
        f'· {scan.total_files} ไฟล์</span></div>',
        unsafe_allow_html=True,
    )

    # search filter (กรองในตัวก่อน render)
    search = st.text_input(
    "ค้นหาชื่อไฟล์",
        key="ms_search",
        label_visibility="collapsed",
        placeholder="ค้นหาชื่อไฟล์...",
        help="พิมพ์เพื่อกรองชื่อไฟล์",
    )
    if search:
        s = search.lower().strip()
        list_entries = [e for e in sorted_entries if s in e.filename.lower()]
    else:
        list_entries = sorted_entries

    if not list_entries:
        ui.warning("ไม่พบไฟล์ตามคำค้น")
        return list_entries

    # scrollable list container
    with st.container(height=560, border=True):
        for e in list_entries:
            row = st.columns([0.12, 1])
            # checkbox สำหรับเลือกลบ
            with row[0]:
                st.checkbox(
                "เลือกลบ",
                    value=(e.filename in selected),
                    key=_chk_key(e.filename),
                    label_visibility="collapsed",
                    help="ติ๊ก = เลือกไฟล์นี้ไปประมวลผล (ลบ + renumber)",
                )
            # ปุ่มแสดง filename + size + small indicator
            with row[1]:
                size_str = ui.format_bytes(e.size)
                warn = '·  เล็กผิดปกติ' if e.is_small else ''
                label = f"{e.filename}  ·  {size_str}{warn}"
                is_active = (preview_name == e.filename)
                if st.button(
                    label,
                    key=f"ms_open_{e.filename}",
                    width="stretch",
                    type=("primary" if is_active else "secondary"),
                    help="คลิกเพื่อพรีวิวเนื้อหา",
                ):
                    st.session_state['manuscript_preview'] = e.filename
                    st.rerun()

    # ===== sync widget-state → selected set =====
    new_selected = {
        e.filename for e in scan.files
        if st.session_state.get(_chk_key(e.filename))
    }
    if new_selected != selected:
        st.session_state['manuscript_selected'] = new_selected
        st.rerun()

    return list_entries


def _render_preview(scan, sorted_entries):
    """ฝั่งขวา: preview content แบบ VS-Code (st.code + line numbers)"""
    preview_name = st.session_state.get('manuscript_preview')

    current_idx = None
    if preview_name:
        for i, e in enumerate(sorted_entries):
            if e.filename == preview_name:
                current_idx = i
                break

    small_indices = [i for i, e in enumerate(sorted_entries) if e.is_small]

    def _prev_small(cur):
        if not small_indices:
            return None
        cur = cur if cur is not None else len(sorted_entries)
        for i in reversed(small_indices):
            if i < cur:
                return i
        return small_indices[-1]

    def _next_small(cur):
        if not small_indices:
            return None
        cur = cur if cur is not None else -1
        for i in small_indices:
            if i > cur:
                return i
        return small_indices[0]

    head = st.columns([6, 1, 1])
    title = preview_name or "เลือกไฟล์เพื่อดูเนื้อหา"
    with head[0]:
        st.markdown(
            f'<div class="ms-pane-header">{title}</div>',
            unsafe_allow_html=True,
        )
    with head[1]:
        if st.button(
        "▲", key="ms_prev_small",
            help="กระโดดไปไฟล์ขนาดเล็กก่อนหน้า",
            disabled=not small_indices,
            width="stretch",
        ):
            idx = _prev_small(current_idx)
            if idx is not None:
                st.session_state['manuscript_preview'] = sorted_entries[idx].filename
                st.rerun()
    with head[2]:
        if st.button(
        "▼", key="ms_next_small",
            help="กระโดดไปไฟล์ขนาดเล็กถัดไป",
            disabled=not small_indices,
            width="stretch",
        ):
            idx = _next_small(current_idx)
            if idx is not None:
                st.session_state['manuscript_preview'] = sorted_entries[idx].filename
                st.rerun()

    if preview_name:
        try:
            entry = next(e for e in scan.files if e.filename == preview_name)
            content = entry.path.read_text(encoding='utf-8', errors='replace')
            CAP = 200_000
            truncated = False
            if len(content) > CAP:
                content = content[:CAP]
                truncated = True

            # ความสูงเท่ากับฝั่งซ้าย (560) เพื่อ alignment แบบ VS-Code
            st.markdown('<div class="ms-preview-wrap">', unsafe_allow_html=True)
            st.code(content, language=None, line_numbers=True, height=560)
            st.markdown('</div>', unsafe_allow_html=True)
            if truncated:
                st.caption(f"ตัดที่ {CAP:,} ตัวอักษร — ไฟล์ใหญ่กว่านี้")
        except Exception as exc:
            ui.error(f"อ่านไฟล์ไม่ได้: {exc}")
    else:
        st.markdown(
        '<div class="ms-preview-empty">'
        'คลิกชื่อไฟล์ทางซ้ายเพื่อดูเนื้อหา<br/>'
        '<span style="font-size:0.85em;opacity:0.8">'
        '(ติ๊กช่องสี่เหลี่ยม = เลือกลบ — แยกจากการพรีวิว)</span>'
        '</div>',
            unsafe_allow_html=True,
        )


def _process_and_report(scan, selected):
    """ดำเนินการ rename + แสดงผล"""
    out_dir = paths.OUTPUT_DIR / "manuscript"
    report = manuscript_checker.process(scan, selected, out_dir)

    ui.success(
        f"สำเร็จ — เรียงเลขใหม่ **{len(report.renamed)}** ไฟล์ • ลบ **{report.deleted}** ไฟล์\n\n"
        f"ไฟล์ที่เรียงเลขใหม่: `{report.raw_dir}`\n\n"
        f"ต้นฉบับสำรอง: `{report.old_dir}`"
    )
    if report.errors:
        ui.error(f"พบข้อผิดพลาด {len(report.errors)} รายการ")
        for line in report.errors[:10]:
            st.caption(line)
    with st.expander(f"รายการเปลี่ยนชื่อ {len(report.renamed)} ไฟล์", expanded=False):
        for old, new in report.renamed[:200]:
            st.write(f"`{old}` → `{new}`")
        if len(report.renamed) > 200:
            st.caption(f"... และอีก {len(report.renamed) - 200} ไฟล์")


# ============================================================
# Main entry point
# ============================================================

def render() -> None:
    """แสดง tab ตรวจต้นฉบับทั้งหมด"""
    ui.apply_manuscript_css()

    with ui.section(
    "ตรวจต้นฉบับ",
        description=(
        "สแกนไฟล์ .txt — ไฟล์เล็กผิดปกติจะถูกเน้นสีแดง "
        "ติ๊กช่องสี่เหลี่ยม = เลือกลบ • คลิกชื่อ = พรีวิว • "
        "ค่าตั้งต้นชี้ที่โฟลเดอร์ `Raw/` (ไฟล์ raw จีนต้นฉบับ) • "
        "ผลลัพธ์ออกที่ `Output/manuscript/raw/`"
        ),
    ):
        pass

    folder_default = st.session_state.get('manuscript_dir', str(paths.RAW_INPUT_DIR))
    folder_text, do_set, do_open, do_reload = _render_folder_bar(folder_default)

    if do_open:
        _open_folder(folder_text)

    threshold_pct = st.slider(
    "ไฟล์เล็กกว่า ___ % ของขนาดเฉลี่ย → ถือว่า 'เล็กผิดปกติ'",
        min_value=5, max_value=80,
        value=int(st.session_state.get('manuscript_threshold', 0.30) * 100),
        step=5, format="%d%%",
        help="เช่น 30% = ไฟล์ขนาดน้อยกว่า 30% ของค่าเฉลี่ยจะถูก highlight แดง",
        key="ms_threshold",
    )
    threshold = threshold_pct / 100

    if do_set or do_reload or 'manuscript_scan' not in st.session_state:
        scan = manuscript_checker.scan_directory(Path(folder_text), threshold_ratio=threshold)
        st.session_state['manuscript_scan'] = scan
        st.session_state['manuscript_dir'] = folder_text
        st.session_state['manuscript_threshold'] = threshold
        if do_set or do_reload:
            # rescan: clear all checkbox widget states
            for k in list(st.session_state.keys()):
                if k.startswith('ms_chk_'):
                    del st.session_state[k]
            st.session_state['manuscript_selected'] = set()
            st.session_state.pop('manuscript_preview', None)

    scan = st.session_state['manuscript_scan']

    if scan.total_files == 0:
        ui.warning("ไม่พบไฟล์ .txt ในโฟลเดอร์นี้")
        return

    # ===== Stats: HORIZONTAL row of cards =====
    ui.stats_cards([
        ("จำนวนไฟล์ทั้งหมด", scan.total_files),
        ("เลขนำหน้า", f"{scan.detected_padding} หลัก"),
        ("ขนาดเฉลี่ย", ui.format_bytes(scan.average_size)),
        ("ไฟล์ขนาดเล็ก", scan.small_files_count),
    ])

    selected = st.session_state.get('manuscript_selected', set())
    sorted_entries = _sorted_entries(scan)
    do_process = _render_action_bar(scan, selected)

    # Two-pane layout — explorer | preview
    left, right = st.columns([1, 1.5])
    with left:
        _render_explorer(scan, sorted_entries, selected)
    with right:
        _render_preview(scan, sorted_entries)

    if do_process:
        _process_and_report(scan, selected)
