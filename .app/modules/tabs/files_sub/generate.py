"""tabs/files_sub/generate.py — Sub-tab 'generate' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker


def render(file_processor) -> None:
    """generate sub-tab"""
    st.markdown("####  สร้างไฟล์ TXT เปล่า")
    st.info(" สร้างไฟล์ .txt เปล่าสำหรับเตรียมเขียนเนื้อหา ไฟล์จะถูกสร้างในโฟลเดอร์ `0-input`")

    # Settings Section
    st.markdown("####  การตั้งค่าการสร้างไฟล์")

    # ใช้ session state เพื่อจำค่าล่าสุด
    if 'generate_file_prefix' not in st.session_state:
        st.session_state.generate_file_prefix = "Chapter "
    if 'generate_file_suffix' not in st.session_state:
        st.session_state.generate_file_suffix = ""
    if 'generate_number_padding' not in st.session_state:
        st.session_state.generate_number_padding = 3
    if 'generate_start_number' not in st.session_state:
        st.session_state.generate_start_number = 1
    if 'generate_batch_size' not in st.session_state:
        st.session_state.generate_batch_size = 10

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("** ชื่อไฟล์**")
        file_prefix = st.text_input(
        "คำนำหน้า (Prefix)",
            value=st.session_state.generate_file_prefix,
            help="คำที่ใส่หน้าหมายเลข",
            key="generate_file_prefix_input"
        )

        file_suffix = st.text_input(
        "คำต่อท้าย (Suffix) (ไม่บังคับ)",
            value=st.session_state.generate_file_suffix,
            placeholder="เช่น _draft",
            help="คำที่ใส่หลังหมายเลข",
            key="generate_file_suffix_input"
        )

        st.markdown("** การจัดรูปแบบ**")
        number_padding = st.number_input(
        "จำนวนหลักเลข",
            min_value=1,
            max_value=5,
            value=st.session_state.generate_number_padding,
            help="001 = 3 หลัก, 0001 = 4 หลัก",
            key="generate_number_padding_input"
        )

    with col_right:
        st.markdown("** จำนวนไฟล์**")

        col_num1, col_num2 = st.columns(2)
        with col_num1:
            start_number = st.number_input(
            "หมายเลขเริ่มต้น",
                min_value=1,
                max_value=9999,
                value=st.session_state.generate_start_number,
                help="หมายเลขไฟล์แรก",
                key="generate_start_number_input"
            )

        with col_num2:
            batch_size = st.number_input(
            "จำนวนไฟล์ที่จะสร้าง",
                min_value=1,
                max_value=100,
                value=st.session_state.generate_batch_size,
                help="จำนวนไฟล์ที่ต้องการสร้างในครั้งนี้",
                key="generate_batch_size_input"
            )

        # แสดงตัวอย่าง
        st.markdown("** ตัวอย่าง**")
        example_filename = f"{file_prefix}{str(start_number).zfill(number_padding)}{file_suffix}.txt"
        st.info(f"`{example_filename}`")

    # อัปเดต session state
    st.session_state.generate_file_prefix = file_prefix
    st.session_state.generate_file_suffix = file_suffix
    st.session_state.generate_number_padding = number_padding
    st.session_state.generate_start_number = start_number
    st.session_state.generate_batch_size = batch_size

    # คำนวณหมายเลขสิ้นสุด
    end_number = start_number + batch_size - 1
    st.info(f" จะสร้างไฟล์หมายเลข {start_number} ถึง {end_number}")

    # ออปชันพิเศษ
    st.markdown("---")
    st.markdown("####  ออปชันพิเศษ")

    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        # ใช้ session state เพื่อจำค่าล่าสุด
        if 'generate_add_chapter_title' not in st.session_state:
            st.session_state.generate_add_chapter_title = True
        if 'generate_chapter_title_template' not in st.session_state:
            st.session_state.generate_chapter_title_template = "ระบบเซียนหมื่นพรสวรรค์ ตอนที่ "

        add_chapter_title = st.checkbox(
        " เพิ่มชื่อตอนในบรรทัดแรก",
            value=st.session_state.generate_add_chapter_title,
            help="เพิ่มชื่อตอนในบรรทัดแรกของไฟล์",
            key="generate_chapter_title_checkbox"
        )

        # อัปเดต session state
        st.session_state.generate_add_chapter_title = add_chapter_title

        if add_chapter_title:
            use_filename_as_title = st.checkbox(
            " ใช้ชื่อไฟล์เป็นชื่อตอน",
                value=True,
                help="ใช้ชื่อไฟล์ (ไม่รวม .txt) เป็นชื่อตอน"
            )

            if not use_filename_as_title:
                chapter_title_template = st.text_input(
                "รูปแบบชื่อตอนแบบกำหนดเอง",
                    value=st.session_state.generate_chapter_title_template,
                    help="ข้อความที่จะตามด้วยหมายเลขตอน เช่น 'ระบบเซียนหมื่นพรสวรรค์ ตอนที่ 001'",
                    key="generate_chapter_title_input"
                )

                # อัปเดต session state
                st.session_state.generate_chapter_title_template = chapter_title_template
            else:
                chapter_title_template = ""
        else:
            chapter_title_template = ""
            use_filename_as_title = False

    with col_opt2:
        if add_chapter_title:
            # แสดงตัวอย่างชื่อตอน
            if use_filename_as_title:
                example_filename_for_title = f"{file_prefix}{str(start_number).zfill(number_padding)}{file_suffix}"
                st.info(f" ตัวอย่างเนื้อหาในไฟล์:\n```\n{example_filename_for_title}\n\n[เนื้อหา...]\n```")
                st.caption(" ใช้ชื่อไฟล์ (ไม่รวม .txt) เป็นชื่อตอน + บรรทัดว่าง")
            else:
                example_title = f"{chapter_title_template}{str(start_number).zfill(number_padding)}"
                st.info(f" ตัวอย่างเนื้อหาในไฟล์:\n```\n{example_title}\n\n[เนื้อหา...]\n```")
                st.caption(" ใช้รูปแบบกำหนดเอง + บรรทัดว่าง")
        else:
            st.markdown("")  # Placeholder เพื่อให้ layout สมดุล

    # Preview Section
    example_filename = f"{file_prefix}{str(start_number).zfill(number_padding)}{file_suffix}.txt"
    st.markdown("---")
    st.info(f" **ตัวอย่างชื่อไฟล์**: `{example_filename}`")

    # File list preview
    if batch_size <= 20:  # แสดงตัวอย่างถ้าไม่เยอะเกินไป
        st.markdown("** รายการไฟล์ที่จะสร้าง:**")
        preview_files = []
        for i in range(start_number, start_number + batch_size):
            filename = f"{file_prefix}{str(i).zfill(number_padding)}{file_suffix}.txt"
            preview_files.append(filename)

        # แสดงเป็น columns
        cols = st.columns(3)
        for idx, filename in enumerate(preview_files):
            with cols[idx % 3]:
                st.write(f" `{filename}`")
    else:
        st.markdown(f"** จะสร้าง {batch_size} ไฟล์** (เยอะเกินไปจึงไม่แสดงรายการ)")

    # Generate Button
    if st.button(" **สร้างไฟล์**", type="primary", width='stretch'):
        with st.spinner("กำลังสร้างไฟล์..."):
            # สร้างโฟลเดอร์ input ถ้าไม่มี
            input_dir = paths.INPUT_DIR
            input_dir.mkdir(exist_ok=True)

            created_files = []
            errors = []

            for i in range(start_number, start_number + batch_size):
                filename = f"{file_prefix}{str(i).zfill(number_padding)}{file_suffix}.txt"
                file_path = input_dir / filename

                try:
                    # ตรวจสอบว่าไฟล์มีอยู่แล้วหรือไม่
                    if file_path.exists():
                        errors.append(f" `{filename}` มีอยู่แล้ว (ข้าม)")
                    else:
                        # เตรียมเนื้อหาไฟล์
                        file_content = ""

                        # เพิ่มชื่อตอนถ้าเลือกออปชันนี้
                        if add_chapter_title:
                            if use_filename_as_title:
                                # ใช้ชื่อไฟล์ (ไม่รวม .txt) เป็นชื่อตอน
                                chapter_title = f"{file_prefix}{str(i).zfill(number_padding)}{file_suffix}"
                                file_content = f"{chapter_title}\n\n"# เพิ่มบรรทัดว่าง
                            elif chapter_title_template:
                                # ใช้รูปแบบกำหนดเอง
                                chapter_number = str(i).zfill(number_padding)
                                chapter_title = f"{chapter_title_template}{chapter_number}"
                                file_content = f"{chapter_title}\n\n"# เพิ่มบรรทัดว่าง

                        # สร้างไฟล์
                        file_path.write_text(file_content, encoding="utf-8")
                        created_files.append(filename)
                except Exception as e:
                    errors.append(f" ไม่สามารถสร้าง `{filename}`: {str(e)}")

        # แสดงผลลัพธ์
        if created_files:
            st.success(f" สร้างไฟล์สำเร็จ {len(created_files)} ไฟล์!")

            # แสดงรายการไฟล์ที่สร้างสำเร็จ (จำกัด 10 ไฟล์แรก)
            if len(created_files) <= 10:
                st.markdown("** ไฟล์ที่สร้างแล้ว:**")
                for filename in created_files:
                    st.write(f"`{filename}`")
            else:
                st.write(f"** สร้างไฟล์แล้ว:** `{created_files[0]}` ถึง `{created_files[-1]}`")

            st.toast(f"สร้าง {len(created_files)} ไฟล์สำเร็จ!")

        # แสดงข้อผิดพลาด (ถ้ามี)
        if errors:
            st.warning(" มีปัญหาบางส่วน:")
            for error in errors[:5]:  # แสดงแค่ 5 ข้อผิดพลาดแรก
                st.write(f"{error}")
            if len(errors) > 5:
                st.write(f"... และอีก {len(errors) - 5} รายการ")

        if not created_files and not errors:
            st.error(" ไม่สามารถสร้างไฟล์ได้")

        # Converter Sub-tab

