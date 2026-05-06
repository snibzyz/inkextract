"""tabs/files_sub/merge.py — Sub-tab 'merge' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker
from modules.preferences_manager import preferences_manager


def render(merge_processor, file_processor) -> None:
    """merge sub-tab"""
    st.markdown("####  เลือกโฟลเดอร์ต้นทาง")

    # Input folder selection
    input_mode = st.radio(
    "เลือกโฟลเดอร์ต้นทาง:",
        options=["ใช้โฟลเดอร์แนะนำ", "เลือกโฟลเดอร์เอง"],
        index=0,
        help="ใช้โฟลเดอร์แนะนำ: เลือกจากรายการ | เลือกโฟลเดอร์เอง: ระบุเส้นทางโฟลเดอร์"
    )

    if input_mode == "ใช้โฟลเดอร์แนะนำ":
        folder_options = {
        "2-clean (แนะนำ)": file_processor.clean_dir,
        "1-fix": file_processor.fix_dir,
        "output": file_processor.output_dir
        }

        selected_folder = st.selectbox(
        "เลือกโฟลเดอร์ที่ต้องการรวมไฟล์:",
            options=list(folder_options.keys()),
            index=0
        )

        selected_path = folder_options[selected_folder]
    else:
        # Custom input folder
        custom_input_path = st.text_input(
        "ระบุเส้นทางโฟลเดอร์ต้นทาง:",
            value="",
            placeholder="เช่น: C:\\Users\\Username\\Desktop\\input หรือ ./custom-input",
            help="ระบุเส้นทางโฟลเดอร์ที่ต้องการรวมไฟล์"
        )

        if custom_input_path.strip():
            try:
                selected_path = Path(custom_input_path.strip())
                if not selected_path.exists():
                    st.error(f" โฟลเดอร์ไม่พบ: `{selected_path}`")
                    selected_path = None
                else:
                    st.success(f" โฟลเดอร์ต้นทาง: `{selected_path}`")
            except Exception as e:
                st.error(f" เส้นทางไม่ถูกต้อง: {str(e)}")
                selected_path = None
        else:
            selected_path = None

    # ตรวจสอบไฟล์ (ค้นหาไฟล์ .txt ทั้งหมด)
    chapter_files = merge_processor.get_available_files(selected_path)
    total_chapters = len(chapter_files)

    if total_chapters == 0:
        st.warning(f" ไม่พบไฟล์ในโฟลเดอร์ `{selected_path}/`")
        st.info(" กรุณาเตรียมไฟล์ให้พร้อมก่อน")
    else:
        st.success(f" พบ {total_chapters} ไฟล์พร้อมใช้งาน")

        # ตัวเลือกการเลือกไฟล์
        st.markdown("####  เลือกไฟล์ที่ต้องการรวม")

        col_file1, col_file2 = st.columns([1, 1])

        with col_file1:
            merge_mode = st.radio(
            "โหมดการรวมไฟล์:",
                options=["รวมทั้งหมด", "เลือกไฟล์เฉพาะ"],
                index=0,
                help="รวมทั้งหมด: รวมไฟล์ทั้งหมดในโฟลเดอร์ | เลือกไฟล์เฉพาะ: เลือกไฟล์ที่ต้องการเท่านั้น"
            )

        with col_file2:
            # Output folder selection
            st.markdown("** โฟลเดอร์ปลายทาง**")
            output_mode = st.radio(
            "เลือกโฟลเดอร์ปลายทาง:",
                options=["ใช้โฟลเดอร์แนะนำ", "เลือกโฟลเดอร์เอง"],
                index=0,
                help="ใช้โฟลเดอร์แนะนำ: ใช้โฟลเดอร์ 3-merge | เลือกโฟลเดอร์เอง: ระบุเส้นทางโฟลเดอร์ปลายทาง"
            )

        # เลือกไฟล์เฉพาะ
        selected_files = None
        if merge_mode == "เลือกไฟล์เฉพาะ":
            st.markdown("---")
            st.markdown("####  เลือกไฟล์ที่ต้องการรวม")

            # แสดงรายการไฟล์ให้เลือก
            file_options = [f"{file.name} ({file.stat().st_size} bytes)" for file in chapter_files]
            selected_indices = st.multiselect(
            "เลือกไฟล์ที่ต้องการรวม:",
                options=range(len(chapter_files)),
                format_func=lambda x: file_options[x],
                help="เลือกไฟล์ที่ต้องการรวม (สามารถเลือกหลายไฟล์ได้)"
            )

            if selected_indices:
                selected_files = [chapter_files[i] for i in selected_indices]
                st.success(f" เลือก {len(selected_files)} ไฟล์")

                # แสดงรายการไฟล์ที่เลือก
                st.markdown("** ไฟล์ที่เลือก:**")
                for i, file_path in enumerate(selected_files, 1):
                    st.write(f"{i}. `{file_path.name}`")
            else:
                st.warning(" กรุณาเลือกไฟล์ที่ต้องการรวม")

        # เลือกโฟลเดอร์ปลายทาง
        output_folder = None
        if output_mode == "ใช้โฟลเดอร์แนะนำ":
            output_folder = merge_processor.merge_dir
            st.info(f" โฟลเดอร์ปลายทาง: `{output_folder}`")
        else:
            st.markdown("---")
            st.markdown("####  เลือกโฟลเดอร์ปลายทาง")

            # ใช้ text_input สำหรับใส่ path ของโฟลเดอร์ปลายทาง
            custom_output_path = st.text_input(
            "ระบุเส้นทางโฟลเดอร์ปลายทาง:",
                value="",
                placeholder="เช่น: C:\\Users\\Username\\Desktop\\output หรือ ./custom-output",
                help="ระบุเส้นทางโฟลเดอร์ที่ต้องการบันทึกไฟล์รวม"
            )

            if custom_output_path.strip():
                try:
                    output_folder = Path(custom_output_path.strip())
                    # สร้างโฟลเดอร์ถ้าไม่มี
                    output_folder.mkdir(parents=True, exist_ok=True)
                    st.success(f" โฟลเดอร์ปลายทาง: `{output_folder}`")
                except Exception as e:
                    st.error(f" ไม่สามารถสร้างโฟลเดอร์ได้: {str(e)}")
                    output_folder = None

        # ใช้ preferences manager แทน session state
        merge_settings = preferences_manager.get_setting("file_processing", "merge_settings", {})

        # Settings
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("** การตั้งค่า Merge**")
            chapters_per_file = st.number_input(
            "ตอนต่อไฟล์ (0 = รวมทั้งหมด)", 
                0, 50, merge_settings.get("chapters_per_file", 5),
                key="merge_chapters_per_file_input"
            )
            if chapters_per_file != merge_settings.get("chapters_per_file", 5):
                merge_settings["chapters_per_file"] = chapters_per_file

            focus_keyword = st.text_input(
            "Focus keyword", 
                value=merge_settings.get("focus_keyword", "###"),
                help="คำนำหน้าก่อนชื่อบท (ถ้าว่างจะไม่ใส่อะไร)",
                key="merge_focus_keyword_input"
            )
            if focus_keyword != merge_settings.get("focus_keyword", "###"):
                merge_settings["focus_keyword"] = focus_keyword

            st.markdown("** ชื่อไฟล์**")
            title_prefix = st.text_input(
            "คำนำหน้า (Prefix)", 
                value=merge_settings.get("title_prefix", "Chapter "),
                key="merge_title_prefix_input"
            )
            if title_prefix != merge_settings.get("title_prefix", "Chapter "):
                merge_settings["title_prefix"] = title_prefix

            title_suffix = st.text_input(
            "คำต่อท้าย (Suffix)", 
                value=merge_settings.get("title_suffix", ""),
                key="merge_title_suffix_input"
            )
            if title_suffix != merge_settings.get("title_suffix", ""):
                merge_settings["title_suffix"] = title_suffix

            st.markdown("** ข้อความปิดท้าย**")
            end_credit = st.text_input(
            "End Credit (คำลงท้ายตอน)", 
                value=merge_settings.get("end_credit", "จบตอน"),
                help="ข้อความที่จะเพิ่มต่อท้ายแต่ละตอน เช่น 'จบตอน'",
                key="merge_end_credit_input"
            )
            if end_credit != merge_settings.get("end_credit", "จบตอน"):
                merge_settings["end_credit"] = end_credit

        with col2:
            st.markdown("** การจัดรูปแบบ**")

            col_num1, col_num2 = st.columns(2)
            with col_num1:
                chapter_padding = st.number_input(
                "Padding เลขบท", 
                    1, 5, merge_settings.get("chapter_padding", 3),
                    key="merge_chapter_padding_input"
                )
                if chapter_padding != merge_settings.get("chapter_padding", 3):
                    merge_settings["chapter_padding"] = chapter_padding

            with col_num2:
                start_number = st.number_input(
                "เลขเริ่มต้น", 
                    1, 9999, merge_settings.get("start_number", 1),
                    key="merge_start_number_input"
                )
                if start_number != merge_settings.get("start_number", 1):
                    merge_settings["start_number"] = start_number

            st.markdown("** ตัวเลือกเพิ่มเติม**")
            add_chapter_heading = st.checkbox(
            " เพิ่มหัวข้อบทใหม่",
                value=merge_settings.get("add_chapter_heading", True),
                help="เพิ่มหัวข้อบทใหม่ตาม Focus keyword + Title prefix",
                key="merge_add_chapter_heading_input"
            )
            if add_chapter_heading != merge_settings.get("add_chapter_heading", True):
                merge_settings["add_chapter_heading"] = add_chapter_heading

            add_filename_separator = st.checkbox(
            " เพิ่มชื่อไฟล์เป็นหัวข้อคั่น",
                value=merge_settings.get("add_filename_separator", False),
                help="เพิ่มชื่อไฟล์เดิมเป็นหัวข้อคั่นระหว่างเนื้อหา",
                key="merge_add_filename_separator_input"
            )
            if add_filename_separator != merge_settings.get("add_filename_separator", False):
                merge_settings["add_filename_separator"] = add_filename_separator

            # แสดงตัวอย่างและสถิติ
            st.markdown("** ตัวอย่าง**")
            example_filename = f"{title_prefix}{str(start_number).zfill(chapter_padding)}{title_suffix}.txt"
            st.info(f"`{example_filename}`")

        # บันทึกการตั้งค่า merge
        preferences_manager.set_setting("file_processing", "merge_settings", merge_settings)

        # Calculate estimate
        files_to_merge = len(selected_files) if selected_files else total_chapters
        est_files = 1 if chapters_per_file == 0 else (files_to_merge + chapters_per_file - 1) // chapters_per_file
        st.info(f" คาดว่าจะได้ {est_files} ไฟล์ (จาก {files_to_merge} ไฟล์ที่เลือก)")

        # ตรวจสอบเงื่อนไขก่อนเริ่มรวมไฟล์
        can_merge = True
        if not selected_path:
            can_merge = False
            st.error(" กรุณาเลือกโฟลเดอร์ต้นทาง")
        elif merge_mode == "เลือกไฟล์เฉพาะ" and not selected_files:
            can_merge = False
            st.error(" กรุณาเลือกไฟล์ที่ต้องการรวม")
        elif output_mode == "เลือกโฟลเดอร์เอง" and not output_folder:
            can_merge = False
            st.error(" กรุณาระบุโฟลเดอร์ปลายทาง")

        if st.button(" **เริ่มรวมไฟล์**", type="primary", width='stretch', disabled=not can_merge):
            with st.spinner("กำลังรวมไฟล์..."):
                created = merge_processor.merge_output(
                    chapters_per_file=chapters_per_file,
                    end_credit=end_credit,
                    focus_keyword=focus_keyword,
                    title_prefix=title_prefix,
                    title_suffix=title_suffix,
                    chapter_number_padding=int(chapter_padding),
                    start_number=int(start_number),
                    source_path=selected_path,
                    add_filename_separator=add_filename_separator,
                    add_chapter_heading=add_chapter_heading,
                    output_folder=output_folder,
                    selected_files=selected_files
                )
            if created:
                st.success(" รวมไฟล์สำเร็จ!")
                for p in created:
                    st.write(f"`{p.name}`")
                st.toast("รวมไฟล์สำเร็จ!")

        # Separate Sub-tab

