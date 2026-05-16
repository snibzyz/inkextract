"""tabs/files_sub/format.py — ตรวจรูปแบบบรรทัดแรกของไฟล์ในโฟลเดอร์

หาไฟล์ที่ format หัวบทผิดปกติ — เพื่อให้ปรับให้ตรงกันก่อนรวม/เผยแพร่
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths
from modules.format_checker import FormatChecker
from . import _helpers as h


def render(file_processor) -> None:
    """ตรวจรูปแบบ tab — หาไฟล์ที่ชื่อหัวบทไม่ตรงมาตรฐาน"""
    st.markdown(
        '<div style="margin-bottom:0.6rem;color:var(--ink-text-muted);font-size:0.95em;">'
        'ตรวจรูปแบบ <b>บรรทัดแรก</b>ของไฟล์ในโฟลเดอร์ — หาไฟล์ที่ชื่อหัวบทไม่ตรงรูปแบบมาตรฐาน'
        '</div>',
        unsafe_allow_html=True,
    )

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "เลือกโฟลเดอร์ที่จะตรวจ")
    src_path, _ = h.folder_select(
        "โฟลเดอร์ที่จะตรวจ",
        key="fmt_src",
        presets=["Clean", "Fix", "Input", "Finish", "Merge"],
        suggested="Clean",
        help="โฟลเดอร์ที่มีไฟล์ที่ต้องการตรวจรูปแบบหัวบท · ค่าเริ่มต้น = Clean",
    )

    # ปุ่มตรวจ
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        do_check = st.button("ตรวจสอบรูปแบบ", type="primary", width="stretch",
                              key="fmt_btn_check",
                              disabled=not (src_path and src_path.exists()))
    with col_btn2:
        do_clear = st.button("ล้างผลลัพธ์", width="stretch", key="fmt_btn_clear")

    if do_clear:
        for k in ('format_check_result', 'format_check_triggered', 'format_check_dir'):
            st.session_state.pop(k, None)
        st.rerun()

    if do_check:
        with st.spinner("กำลังตรวจสอบรูปแบบ..."):
            checker = FormatChecker(src_path)
            result = checker.check_all_files()
            st.session_state['format_check_result'] = result
            st.session_state['format_check_dir'] = str(src_path)
            st.session_state['format_checker'] = checker
        st.rerun()

    # ───────────── ผลการตรวจ ─────────────
    if 'format_check_result' not in st.session_state:
        st.info("กดปุ่ม **ตรวจสอบรูปแบบ** เพื่อเริ่ม")
        return

    result = st.session_state['format_check_result']
    checker = st.session_state.get('format_checker')

    st.markdown(f"### ผลการตรวจ — `{st.session_state.get('format_check_dir', '')}`")

    # KPI
    valid = result['valid_files']
    invalid = result['invalid_files']
    total = result['total_files']
    std_fmt_desc = checker.get_format_description(result['standard_format']) if (
        result['standard_format'] and checker) else "ไม่พบรูปแบบมาตรฐาน"

    h.stat_chips([
        ("ไฟล์ทั้งหมด", f"{total:,}"),
        ("ถูกต้อง", f"{valid:,} ({(valid/total*100 if total else 0):.1f}%)"),
        ("ผิด", f"{invalid:,} ({(invalid/total*100 if total else 0):.1f}%)"),
        ("มาตรฐาน", f'"{std_fmt_desc}"'),
    ])

    # ─── ตาราง ───
    show_only_invalid = st.checkbox(
        "แสดงเฉพาะไฟล์ที่ผิด",
        value=(invalid > 0),
        key="fmt_show_invalid",
    )

    files_to_show = result['files']
    if show_only_invalid:
        files_to_show = [
            f for f in files_to_show
            if not f['is_valid'] or (
                result['standard_format'] and f['format'] != result['standard_format']
            )
        ]

    if not files_to_show:
        st.success("ไม่มีไฟล์ที่ format ผิด")
    else:
        rows = []
        for f in files_to_show:
            is_invalid = not f['is_valid'] or (
                result['standard_format'] and f['format'] != result['standard_format']
            )
            fmt_desc = checker.get_format_description(f['format']) if checker else f['format']
            rows.append({
                "ไฟล์": f['filename'],
                "รูปแบบ": fmt_desc,
                "สถานะ": "ผิด" if is_invalid else "ถูกต้อง",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width='stretch', hide_index=True)

    # ─── ส่งออก ───
    st.markdown("---")
    col_e1, col_e2 = st.columns([1, 3])
    with col_e1:
        if st.button("ส่งออกรายงาน (.txt)", width="stretch", key="fmt_btn_export"):
            try:
                report_path = paths.OUTPUT_DIR / f"format_check_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt"
                if checker and checker.export_report(report_path, result):
                    st.success(f"ส่งออกรายงานสำเร็จ: `{report_path}`")
                    st.toast("ส่งออกรายงานสำเร็จ")
                else:
                    st.error("ส่งออกไม่สำเร็จ")
            except Exception as e:
                st.error(f"ส่งออกไม่สำเร็จ: {e}")
    with col_e2:
        st.caption(f"รายงานจะถูกบันทึกใน `{paths.OUTPUT_DIR}`")
