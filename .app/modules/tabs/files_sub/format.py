"""tabs/files_sub/format.py — Sub-tab 'format' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker


def render(file_processor) -> None:
    """format sub-tab"""
    st.markdown("#### ตรวจสอบรูปแบบบรรทัดแรก")
    st.info("ตรวจรูปแบบของบรรทัดแรกในไฟล์โฟลเดอร์ 2-clean")

    # สร้าง instance ของ FormatChecker
    if 'format_checker' not in st.session_state:
        st.session_state.format_checker = FormatChecker(file_processor.clean_dir)

    format_checker = st.session_state.format_checker

    # ปุ่มตรวจสอบ
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("ตรวจสอบรูปแบบ", type="primary", width="stretch"):
            st.session_state.format_check_triggered = True

    with col2:
        if st.button("รีเฟรช", width="stretch"):
            if 'format_check_result' in st.session_state:
                del st.session_state.format_check_result
            if 'format_check_triggered' in st.session_state:
                del st.session_state.format_check_triggered

    # ตรวจสอบเมื่อกดปุ่ม
    if st.session_state.get('format_check_triggered', False):
        with st.spinner("กำลังตรวจสอบรูปแบบ..."):
            check_result = format_checker.check_all_files()
            st.session_state.format_check_result = check_result
            st.session_state.format_check_triggered = False

    # แสดงผลลัพธ์
    if 'format_check_result' in st.session_state:
        result = st.session_state.format_check_result

        # สถิติสรุป
        st.markdown("---")
        st.markdown("####  สถิติการตรวจสอบ")

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            st.metric(" ไฟล์ทั้งหมด", result['total_files'])

        with col_stat2:
            valid_percent = (result['valid_files']/result['total_files']*100) if result['total_files'] > 0 else 0
            st.metric(" ถูกต้อง", result['valid_files'], 
                     delta=f"{valid_percent:.1f}%")

        with col_stat3:
            invalid_percent = (result['invalid_files']/result['total_files']*100) if result['total_files'] > 0 else 0
            st.metric(" ไม่ถูกต้อง", result['invalid_files'],
                     delta=f"{invalid_percent:.1f}%",
                     delta_color="inverse")

        with col_stat4:
            if result['standard_format']:
                format_desc = format_checker.get_format_description(result['standard_format'])
                # ตัดข้อความให้สั้นลงถ้ายาวเกินไป
                display_format = format_desc[:35] + "..." if len(format_desc) > 35 else format_desc
                st.metric(" รูปแบบมาตรฐาน", display_format)
            else:
                st.metric(" รูปแบบมาตรฐาน", "ไม่พบ")

        # รายการไฟล์
        st.markdown("---")
        st.markdown("####  รายการไฟล์")

        # ตัวกรอง
        show_all = st.checkbox("แสดงไฟล์ทั้งหมด", value=True)

        # กรองไฟล์
        if show_all:
            display_files = result['files']
        else:
            # แสดงเฉพาะไฟล์ที่ format ไม่ถูกต้อง
            display_files = [f for f in result['files'] 
                           if not f['is_valid'] or (result['standard_format'] and f['format'] != result['standard_format'])]

        if display_files:
            # ตาราง format — ใช้ theme tokens (รองรับสว่าง/มืด)
            st.markdown("""
            <style>
                .format-table-container {
                    width: 100%;
                    margin: 1rem 0;
                    border-radius: var(--ink-radius-lg);
                    overflow: hidden;
                    box-shadow: var(--ink-shadow-md);
                    background: var(--ink-surface);
                    border: 1px solid var(--ink-border);
                }
                .format-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.95rem;
                    background: var(--ink-surface);
                    color: var(--ink-text);
                }
                .format-table thead {
                    background: linear-gradient(135deg, var(--ink-orange) 0%, var(--ink-orange-dark) 100%);
                    color: white;
                }
                .format-table th {
                    padding: 14px 18px;
                    text-align: left;
                    font-weight: 700;
                    font-size: 0.98rem;
                    border-bottom: 2px solid rgba(255,255,255,0.2);
                    color: white;
                }
                .format-table th:first-child { width: 50%; }
                .format-table th:last-child { width: 50%; }
                .format-table td {
                    padding: 12px 18px;
                    border-bottom: 1px solid var(--ink-border-soft);
                    font-size: 0.95rem;
                    vertical-align: middle;
                    color: var(--ink-text);
                }
                .format-table tbody tr {
                    transition: background-color 0.2s ease;
                    background-color: var(--ink-surface);
                }
                .format-table tbody tr:hover {
                    background-color: var(--ink-surface-tint) !important;
                }
                .format-table tbody tr.invalid {
                    background-color: var(--ink-warn-bg) !important;
                    border-left: 4px solid var(--ink-warn);
                }
                .format-table tbody tr.invalid td {
                    color: var(--ink-warn);
                    font-weight: 600;
                }
                .filename-cell {
                    color: var(--ink-text);
                    word-break: break-word;
                }
                .format-cell {
                    font-family: 'Consolas', 'Courier New', monospace;
                    color: inherit;
                }
            </style>
            """, unsafe_allow_html=True)

            # สร้าง HTML table
            html_table = '<div class="format-table-container"><table class="format-table"><thead><tr><th>ชื่อไฟล์</th><th>รูปแบบ</th></tr></thead><tbody>'

            for file_data in display_files:
                is_invalid = not file_data['is_valid'] or (result['standard_format'] and file_data['format'] != result['standard_format'])
                row_class = 'invalid' if is_invalid else 'valid'

                format_desc = format_checker.get_format_description(file_data['format'])

                # Escape HTML เพื่อป้องกัน XSS
                filename_escaped = file_data['filename'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                format_desc_escaped = format_desc.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

                html_table += f'<tr class="{row_class}"><td class="filename-cell">{filename_escaped}</td><td class="format-cell">{format_desc_escaped}</td></tr>'

            html_table += '</tbody></table></div>'

            st.markdown(html_table, unsafe_allow_html=True)
        else:
            # แสดงตารางว่างถ้าไม่มีไฟล์ที่ต้องแสดง (เมื่อกรองแล้ว)
            st.info(" ไม่มีไฟล์ที่ต้องแสดง (กรองเฉพาะไฟล์ที่ format ไม่ถูกต้อง)")

        # ปุ่มส่งออกรายงาน
        st.markdown("---")
        st.markdown("####  ส่งออกรายงาน")

        col_export1, col_export2 = st.columns([1, 1])
        with col_export1:
            if st.button(" ส่งออกรายงานเป็นไฟล์", width="stretch"):
                report_path = file_processor.output_dir / f"format_check_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt"
                if format_checker.export_report(report_path, result):
                    st.success(f" ส่งออกรายงานสำเร็จ: `{report_path}`")
                    st.toast("ส่งออกรายงานสำเร็จ!")
                else:
                    st.error(" ไม่สามารถส่งออกรายงานได้")

        with col_export2:
            st.markdown("""
            ** คำแนะนำ:**
            - รายงานจะถูกบันทึกในโฟลเดอร์ `output`
            - ไฟล์ที่ format ไม่ถูกต้องจะถูก highlight เป็นสีเหลือง
            - รูปแบบมาตรฐานคือรูปแบบที่พบมากกว่า 70%
            """)
    else:
        st.info("กดปุ่ม 'ตรวจสอบรูปแบบ' เพื่อเริ่มการตรวจสอบ")

        # Clear Files Sub-tab

