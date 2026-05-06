"""tabs/files_sub/separate.py — Sub-tab 'separate' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker


def render(separate_processor, file_processor) -> None:
    """separate sub-tab"""
    st.markdown("####  อัปโหลดไฟล์เพื่อแยก")

    uploaded_files = st.file_uploader(
    "เลือกไฟล์ที่ต้องการแยก",
        type=['txt'],
        accept_multiple_files=True,
        key="separate_upload"
    )

    # Settings Section - แสดงเสมอ
    st.markdown("####  การตั้งค่าการแยกไฟล์")

    # ใช้ session state เพื่อจำค่าล่าสุด
    if 'separate_focus_keyword' not in st.session_state:
        st.session_state.separate_focus_keyword = "###"
    if 'separate_title_prefix' not in st.session_state:
        st.session_state.separate_title_prefix = "Chapter "
    if 'separate_title_suffix' not in st.session_state:
        st.session_state.separate_title_suffix = ""
    if 'separate_chapter_padding' not in st.session_state:
        st.session_state.separate_chapter_padding = 3
    if 'separate_start_number' not in st.session_state:
        st.session_state.separate_start_number = 1
    if 'separate_strip_end_credit' not in st.session_state:
        st.session_state.separate_strip_end_credit = True
    if 'separate_end_credit_text' not in st.session_state:
        st.session_state.separate_end_credit_text = "จบตอน"

    # แบ่งเป็น 2 columns หลัก
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("** จุดแยกไฟล์**")
        focus_keyword = st.text_input(
        "ตัวแยกระหว่างบท",
            value=st.session_state.separate_focus_keyword,
            help="เครื่องหมายที่ใช้แยกบท เช่น ###, Chapter",
            key="separate_focus_keyword_input"
        )

        st.markdown("** ชื่อไฟล์**")
        title_prefix = st.text_input(
        "คำนำหน้า (Prefix)",
            value=st.session_state.separate_title_prefix,
            help="คำที่ใส่หน้าหมายเลขบท",
            key="separate_title_prefix_input"
        )

        title_suffix = st.text_input(
        "คำต่อท้าย (Suffix) (ไม่บังคับ)",
            value=st.session_state.separate_title_suffix,
            placeholder="เช่น _final",
            help="คำที่ใส่หลังหมายเลขบท",
            key="separate_title_suffix_input"
        )

        st.markdown("** ข้อความปิดท้าย**")
        strip_end_credit = st.checkbox(
        "ลบ End Credit อัตโนมัติ",
            value=st.session_state.separate_strip_end_credit,
            help="ลบข้อความปิดท้ายออกจากไฟล์",
            key="separate_strip_end_credit_input"
        )

        end_credit_text = st.text_input(
        "End Credit (คำลงท้ายตอน)",
            value=st.session_state.separate_end_credit_text,
            help="ข้อความที่จะเพิ่มต่อท้ายแต่ละตอน เช่น 'จบตอน'",
            key="separate_end_credit_text_input"
        )

    with col_right:
        st.markdown("** การจัดรูปแบบ**")

        col_num1, col_num2 = st.columns(2)
        with col_num1:
            chapter_padding = st.number_input(
            "จำนวนหลักเลข",
                min_value=1,
                max_value=5,
                value=st.session_state.separate_chapter_padding,
                help="001 = 3 หลัก, 0001 = 4 หลัก",
                key="separate_chapter_padding_input"
            )

        with col_num2:
            start_number = st.number_input(
            "เลขเริ่มต้น",
                min_value=1,
                max_value=9999,
                value=st.session_state.separate_start_number,
                help="หมายเลขบทแรก",
                key="separate_start_number_input"
            )

        # เพิ่มพื้นที่ว่างเพื่อให้ columns เท่ากัน
        st.markdown("** ตัวอย่าง**")
        example_filename = f"{title_prefix}{str(start_number).zfill(chapter_padding)}{title_suffix}.txt"
        st.info(f"`{example_filename}`")

        if strip_end_credit:
            st.success(" จะลบ End Credit อัตโนมัติ")
        else:
            st.info(" จะเก็บ End Credit ไว้")

        # อัปเดต session state
        st.session_state.separate_focus_keyword = focus_keyword
        st.session_state.separate_title_prefix = title_prefix
        st.session_state.separate_title_suffix = title_suffix
        st.session_state.separate_chapter_padding = chapter_padding
        st.session_state.separate_start_number = start_number
        st.session_state.separate_strip_end_credit = strip_end_credit
        st.session_state.separate_end_credit_text = end_credit_text

    # แสดงสถานะไฟล์ที่อัปโหลด
    if uploaded_files:
        st.success(f" อัปโหลด {len(uploaded_files)} ไฟล์")

    # ปุ่มแยกไฟล์ - เปิดใช้งานได้เมื่อมีไฟล์อัปโหลด
    if uploaded_files:
        if st.button(" **เริ่มแยกไฟล์**", type="primary", width='stretch'):
            with st.spinner("กำลังแยกไฟล์..."):
                results = separate_processor.separate_files(
                    uploaded_files=uploaded_files,
                    focus_keyword=focus_keyword,
                    title_prefix=title_prefix,
                    title_suffix=title_suffix,
                    chapter_number_padding=int(chapter_padding),
                    start_number=int(start_number),
                    strip_end_credit=strip_end_credit,
                    end_credit_text=end_credit_text
                )

            if results:
                st.success(" แยกไฟล์สำเร็จ!")
                for file_info in results:
                    st.write(f"`{file_info['filename']}` ({file_info['sections']} ส่วน)")
                st.toast("แยกไฟล์สำเร็จ!")

        # Generate Sub-tab

