"""tabs/files_sub/converter.py — Sub-tab 'converter' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker


def render(md_converter, docx_converter, file_processor) -> None:
    """converter sub-tab"""
    st.markdown("####  แปลงและเปลี่ยนนามสกุลไฟล์")

    # เลือกโหมดการแปลง
    conversion_mode = st.radio(
    "เลือกโหมดการแปลง:",
        options=[" DOCX → TXT", " TXT ↔ MD", " TXT/MD → DOCX"],
        index=0,
        help="DOCX → TXT: แปลง Word เป็น Text | TXT ↔ MD: เปลี่ยนนามสกุลใน-place ที่ 2-clean | TXT/MD → DOCX: แปลงเป็น Word",
        horizontal=True
    )

    st.markdown("---")

    if conversion_mode == " DOCX → TXT":
        # DOCX to TXT Mode
        st.markdown("####  แปลงไฟล์ DOCX เป็น TXT")
        st.info(" แปลงไฟล์ Word (.docx) เป็น Text (.txt) จากโฟลเดอร์ `Input` พร้อมรักษาโครงสร้าง subfolder")

        # สถิติไฟล์
        docx_stats = docx_converter.get_file_stats()
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(" ไฟล์ DOCX", docx_stats['docx_files'], help="ไฟล์ในโฟลเดอร์ 0-input (รวม subfolder)")

        with col2:
            st.metric(" ไฟล์ TXT", docx_stats['txt_files'], help="ไฟล์ในโฟลเดอร์ 0-input (รวม subfolder)")

        with col3:
            docx_size_mb = docx_stats['docx_size'] / (1024 * 1024)
            st.metric(" ขนาด DOCX", f"{docx_size_mb:.1f} MB")

        with col4:
            st.metric(" โฟลเดอร์ย่อย", docx_stats['subfolders'])

        st.markdown("---")

        # การตั้งค่า
        st.markdown("####  การตั้งค่า")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("** โฟลเดอร์ต้นทาง**")
            st.info(" ต้นทาง: `Input`")
            st.caption("ค้นหาไฟล์ .docx ทั้งหมด (รวม subfolder)")

            # แสดงจำนวนไฟล์
            if docx_stats['docx_files'] > 0:
                st.success(f" พบ {docx_stats['docx_files']} ไฟล์ DOCX พร้อมแปลง")
            else:
                st.warning(" ไม่พบไฟล์ .docx ในโฟลเดอร์ 0-input")

        with col_right:
            st.markdown("** โฟลเดอร์ปลายทาง**")
            st.info(" ปลายทาง: `output`")
            st.caption("บันทึกเป็น .txt พร้อมรักษาโครงสร้าง subfolder")

            # ตัวเลือกรักษาโครงสร้าง
            preserve_structure = st.checkbox(
            " รักษาโครงสร้าง subfolder",
                value=True,
                help="ถ้าเลือก: output/subfolder/file.txt | ถ้าไม่เลือก: output/file.txt"
            )

        # Preview Section
        if docx_stats['docx_files'] > 0:
            st.markdown("---")
            st.markdown("####  ตัวอย่างไฟล์")

            preview_data = docx_converter.preview_docx_files(docx_converter.input_dir, 3)
            if 'error' not in preview_data and preview_data['files']:
                st.info(f" **โฟลเดอร์**: `{preview_data['directory']}` ({preview_data['total_files']} ไฟล์)")

                for file_info in preview_data['files'][:2]:
                    if 'error' in file_info:
                        st.error(f" {file_info['name']}: {file_info['error']}")
                    else:
                        folder_info = f" ( {file_info['folder']})" if file_info['folder'] != 'root' else ""
                        with st.expander(f" {file_info['name']}{folder_info} ({file_info['total_paragraphs']} paragraphs)"):
                            st.code(file_info['preview'], language="text")
            else:
                st.warning(" ไม่สามารถแสดงตัวอย่างได้")

        st.markdown("---")

        # ปุ่มแปลงไฟล์
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button(" **เริ่มแปลง DOCX → TXT**", type="primary", width='stretch', disabled=docx_stats['docx_files'] == 0):
                with st.spinner("กำลังแปลงไฟล์ DOCX เป็น TXT..."):
                    result = docx_converter.convert_docx_to_txt(
                        preserve_structure=preserve_structure
                    )

                if result['success']:
                    st.success(f" แปลงสำเร็จ! ประมวลผล {result['files_processed']} ไฟล์")

                    # แสดงรายการไฟล์ที่แปลง
                    if result['converted_files']:
                        st.markdown("** ไฟล์ที่แปลงแล้ว:**")
                        for file_info in result['converted_files'][:10]:
                            st.write(f"`{file_info['source']}` → `{file_info['target']}` ({file_info['paragraphs']} paragraphs, {file_info['characters']} chars)")
                        if len(result['converted_files']) > 10:
                            st.write(f"... และอีก {len(result['converted_files']) - 10} ไฟล์")

                    # แสดงข้อผิดพลาด (ถ้ามี)
                    if result['errors']:
                        st.warning(" มีปัญหาบางส่วน:")
                        for error in result['errors'][:3]:
                            st.write(f"{error}")
                        if len(result['errors']) > 3:
                            st.write(f"... และอีก {len(result['errors']) - 3} รายการ")

                    st.toast(f"แปลง {result['files_processed']} ไฟล์สำเร็จ!")
                else:
                    st.error(f" {result['error']}")

        with col_btn2:
            if st.button(" **รีเฟรชสถิติ**", width='stretch'):
                st.rerun()

        # คำแนะนำการใช้งาน
        st.markdown("---")
        st.markdown("####  คำแนะนำการใช้งาน")

        col_help1, col_help2 = st.columns([1, 1])

        with col_help1:
            st.markdown("""
            ** การใช้งาน:**
            - วางไฟล์ .docx ในโฟลเดอร์ `Input`
            - รองรับ subfolder (เช่น 0-input/novel1/chapter1.docx)
            - แปลงเป็น text ธรรมดา (เหมือน copy-paste)
            - รักษาโครงสร้างโฟลเดอร์เดิม
            """)

        with col_help2:
            st.markdown("""
            ** ตัวเลือก:**
            - **รักษาโครงสร้าง**: บันทึก output ตามโครงสร้างเดิม
            - **ไม่รักษาโครงสร้าง**: บันทึกทุกไฟล์ที่ root ของ output
            - แปลงทีละหลายไฟล์พร้อมกัน
            """)

        # ข้อมูลเพิ่มเติม
        st.markdown("---")
        with st.expander(" ข้อมูลเพิ่มเติม"):
            st.markdown("""
            ** วัตถุประสงค์:**
            - แปลงไฟล์ Word เป็น Text ธรรมดา
            - เหมาะสำหรับการประมวลผลข้อความต่อ
            - รักษาโครงสร้าง subfolder

            ** โครงสร้างโฟลเดอร์:**
            ```
            0-input/
            ├── file1.docx → output/file1.txt
            └── subfolder/
                └── file2.docx → output/subfolder/file2.txt
            ```

            ** ฟีเจอร์:**
            - แยก paragraph อัตโนมัติ
            - รองรับ subfolder ไม่จำกัดระดับ
            - แสดง progress bar
            - สถิติไฟล์แบบ real-time
            """)

    elif conversion_mode == " TXT/MD → DOCX":
        # TXT/MD to DOCX Mode
        st.markdown("####  แปลงไฟล์ TXT/MD เป็น DOCX")
        st.info("แปลงไฟล์ .txt หรือ .md จากโฟลเดอร์ `Clean` เป็น Word (.docx) — บันทึก in-place ใน `Clean` เดิม")

        # สถิติไฟล์
        txt_md_stats = docx_converter.get_txt_md_stats()
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(" ไฟล์ TXT", txt_md_stats['txt_files'], help="ไฟล์ในโฟลเดอร์ 2-clean")

        with col2:
            st.metric(" ไฟล์ MD", txt_md_stats['md_files'], help="ไฟล์ในโฟลเดอร์ 2-clean")

        with col3:
            total_size_mb = txt_md_stats['total_size'] / (1024 * 1024)
            st.metric(" ขนาดรวม", f"{total_size_mb:.1f} MB")

        st.markdown("---")

        # การตั้งค่า
        st.markdown("####  การตั้งค่า")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("** โฟลเดอร์ต้นทาง**")
            st.info(" ต้นทาง: `Clean`")
            st.caption("ค้นหาไฟล์ .txt และ .md ทั้งหมด")

            # แสดงจำนวนไฟล์
            if txt_md_stats['total_files'] > 0:
                st.success(f" พบ {txt_md_stats['total_files']} ไฟล์พร้อมแปลง ({txt_md_stats['txt_files']} TXT + {txt_md_stats['md_files']} MD)")
            else:
                st.warning(" ไม่พบไฟล์ .txt หรือ .md ในโฟลเดอร์ 2-clean")

        with col_right:
            st.markdown("**โฟลเดอร์ปลายทาง**")
            st.info("ปลายทาง: `Clean` (in-place)")
            st.caption("บันทึก .docx ลงในโฟลเดอร์เดียวกับ source")

        st.markdown("---")

        # ปุ่มแปลงไฟล์
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button(" **เริ่มแปลง TXT/MD → DOCX**", type="primary", width='stretch', disabled=txt_md_stats['total_files'] == 0):
                with st.spinner("กำลังแปลงไฟล์ TXT/MD เป็น DOCX..."):
                    result = docx_converter.convert_txt_to_docx()

                if result['success']:
                    st.success(f" แปลงสำเร็จ! ประมวลผล {result['files_processed']} ไฟล์")

                    # แสดงรายการไฟล์ที่แปลง
                    if result['converted_files']:
                        st.markdown("** ไฟล์ที่แปลงแล้ว:**")
                        for file_info in result['converted_files'][:10]:
                            st.write(f"`{file_info['source']}` → `{file_info['target']}` ({file_info['lines']} บรรทัด, {file_info['characters']} ตัวอักษร)")
                        if len(result['converted_files']) > 10:
                            st.write(f"... และอีก {len(result['converted_files']) - 10} ไฟล์")

                    # แสดงข้อผิดพลาด (ถ้ามี)
                    if result['errors']:
                        st.warning(" มีปัญหาบางส่วน:")
                        for error in result['errors'][:3]:
                            st.write(f"{error}")
                        if len(result['errors']) > 3:
                            st.write(f"... และอีก {len(result['errors']) - 3} รายการ")

                    st.toast(f"แปลง {result['files_processed']} ไฟล์สำเร็จ!")
                else:
                    st.error(f" {result['error']}")

        with col_btn2:
            if st.button(" **รีเฟรชสถิติ**", width='stretch'):
                st.rerun()

        # คำแนะนำการใช้งาน
        st.markdown("---")
        st.markdown("####  คำแนะนำการใช้งาน")

        col_help1, col_help2 = st.columns([1, 1])

        with col_help1:
            st.markdown("""
            **การใช้งาน:**
            - แปลงไฟล์ .txt หรือ .md จากโฟลเดอร์ `Clean`
            - บันทึกเป็น .docx ในโฟลเดอร์ `Clean` เดียวกัน (in-place)
            - รองรับทั้งไฟล์ TXT และ MD
            - แปลงทีละหลายไฟล์พร้อมกัน
            """)

        with col_help2:
            st.markdown("""
            ** ฟีเจอร์:**
            - แปลงแต่ละบรรทัดเป็น paragraph แยกกัน
            - รักษาบรรทัดว่าง
            - แสดง progress bar
            - สถิติไฟล์แบบ real-time
            """)

        # ข้อมูลเพิ่มเติม
        st.markdown("---")
        with st.expander(" ข้อมูลเพิ่มเติม"):
            st.markdown("""
            ** วัตถุประสงค์:**
            - แปลงไฟล์ Text/Markdown เป็น Word document
            - เหมาะสำหรับการส่งหรือเปิดด้วย Microsoft Word
            - รักษาโครงสร้างบรรทัดเดิม

            **โครงสร้างโฟลเดอร์:**
            ```
            2-clean/
            ├── file1.txt → 2-clean/file1.docx (in-place)
            └── file2.md → 2-clean/file2.docx (in-place)
            ```

            ** ฟีเจอร์:**
            - รองรับทั้ง .txt และ .md
            - แปลงแต่ละบรรทัดเป็น paragraph
            - รักษาบรรทัดว่าง
            - แสดง progress bar
            - สถิติไฟล์แบบ real-time
            """)

    else:
        # TXT ↔ MD Mode (existing code)
        st.markdown("####  เปลี่ยนนามสกุลไฟล์ TXT ↔ MD")
        st.info(" เปลี่ยนนามสกุลไฟล์ระหว่าง .txt และ .md ใน-place ที่โฟลเดอร์ `Clean` (แปลงไฟล์โดยตรง ไม่คัดลอก)")

        # สถิติไฟล์
        stats = md_converter.get_file_stats()
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(" ไฟล์ TXT", stats['clean_files'], help="ไฟล์ในโฟลเดอร์ 2-clean")

        with col2:
            st.metric(" ไฟล์ MD", stats['md_files'], help="ไฟล์ .md ในโฟลเดอร์ 2-clean")

        with col3:
            clean_size_mb = stats['clean_size'] / (1024 * 1024)
            st.metric(" ขนาด TXT", f"{clean_size_mb:.1f} MB")

        with col4:
            md_size_mb = stats['md_size'] / (1024 * 1024)
            st.metric(" ขนาด MD", f"{md_size_mb:.1f} MB")

        st.markdown("---")

        # การตั้งค่า
        st.markdown("####  การตั้งค่า")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("** ประเภทไฟล์ที่ต้องการแปลง**")
            source_folder = st.selectbox(
            "เลือกประเภทไฟล์:",
                options=["Clean (TXT)", "Clean (MD)"],
                index=0,
                help="เลือกไฟล์ในโฟลเดอร์ 2-clean ที่ต้องการแปลง (แปลงใน-place)"
            )

            if source_folder == "Clean (TXT)":
                source_path = md_converter.clean_dir
                target_path = md_converter.clean_dir  # in-place conversion
                conversion_type = "TXT → MD"
                button_text = " **เปลี่ยนเป็น .md**"
                button_color = "primary"
            else:
                source_path = md_converter.clean_dir  # in-place conversion - ทั้งหมดอยู่ใน 2-clean
                target_path = md_converter.clean_dir
                conversion_type = "MD → TXT"
                button_text = " **เปลี่ยนกลับเป็น .txt**"
                button_color = "secondary"

        with col_right:
            st.markdown("** การแปลง**")
            if source_folder == "Clean (TXT)":
                st.info(" แปลงใน-place ที่ `Clean`")
                st.caption("เปลี่ยนนามสกุล .txt → .md โดยตรงในโฟลเดอร์เดิม")
            else:
                st.info(" แปลงใน-place ที่ `Clean`")
                st.caption("เปลี่ยนนามสกุล .md → .txt โดยตรงในโฟลเดอร์เดิม")

            # แสดงจำนวนไฟล์ในโฟลเดอร์ต้นทาง
            if source_path.exists():
                files_count = len(list(source_path.glob("*.txt" if source_folder == "Clean (TXT)" else "*.md")))
                if files_count > 0:
                    st.success(f" พบ {files_count} ไฟล์พร้อมแปลง")
                else:
                    st.warning(f" ไม่พบไฟล์ในโฟลเดอร์ {source_path}")
            else:
                st.error(f" โฟลเดอร์ {source_path} ไม่มีอยู่")

        # Preview Section
        if source_path.exists():
            st.markdown("---")
            st.markdown("####  ตัวอย่างไฟล์")

            # กำหนด extension ที่ต้องการดู
            file_ext = "txt" if source_folder == "Clean (TXT)" else "md"
            preview_data = md_converter.preview_conversion(source_path, 5, file_ext)
            if 'error' not in preview_data and preview_data['files']:
                st.info(f" **โฟลเดอร์**: `{preview_data['directory']}` ({preview_data['total_files']} ไฟล์)")

                for file_info in preview_data['files'][:2]:  # แสดงแค่ 2 ไฟล์แรก
                    with st.expander(f" {file_info['name']} ({file_info['size']} bytes)"):
                        st.code(file_info['preview'], language="markdown" if file_info['type'] in ["MD", "Markdown"] else "text")
            else:
                st.warning(" ไม่สามารถแสดงตัวอย่างได้")

        st.markdown("---")

        # ปุ่มแปลงไฟล์
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button(button_text, type=button_color, width='stretch'):
                if source_folder == "Clean (TXT)":
                    # เปลี่ยนนามสกุล TXT เป็น MD (in-place)
                    with st.spinner("กำลังเปลี่ยนนามสกุล TXT เป็น MD ใน-place..."):
                        result = md_converter.convert_txt_to_md(in_place=True)
                else:
                    # เปลี่ยนนามสกุล MD เป็น TXT (in-place)
                    with st.spinner("กำลังเปลี่ยนนามสกุล MD เป็น TXT ใน-place..."):
                        result = md_converter.convert_md_to_txt(in_place=True)

                if result['success']:
                    st.success(f" เปลี่ยนนามสกุลสำเร็จ! ประมวลผล {result['files_processed']} ไฟล์")

                    # แสดงรายการไฟล์ที่แปลง
                    if result['converted_files']:
                        st.markdown("** ไฟล์ที่แปลงแล้ว:**")
                        for filename in result['converted_files'][:10]:  # แสดงแค่ 10 ไฟล์แรก
                            st.write(f"`{filename}`")
                        if len(result['converted_files']) > 10:
                            st.write(f"... และอีก {len(result['converted_files']) - 10} ไฟล์")

                    # แสดงข้อผิดพลาด (ถ้ามี)
                    if result['errors']:
                        st.warning(" มีปัญหาบางส่วน:")
                        for error in result['errors'][:3]:
                            st.write(f"{error}")
                        if len(result['errors']) > 3:
                            st.write(f"... และอีก {len(result['errors']) - 3} รายการ")

                    st.toast(f"เปลี่ยนนามสกุล {result['files_processed']} ไฟล์สำเร็จ!")
                else:
                    st.error(f" {result['error']}")

        with col_btn2:
            if st.button(" **รีเฟรชสถิติ**", width='stretch'):
                st.rerun()

        # คำแนะนำการใช้งาน
        st.markdown("---")
        st.markdown("####  คำแนะนำการใช้งาน")

        col_help1, col_help2 = st.columns([1, 1])

        with col_help1:
            st.markdown("""
            ** TXT → MD:**
            - เปลี่ยนนามสกุลไฟล์จาก .txt เป็น .md
            - แปลงใน-place ที่โฟลเดอร์ `Clean`
            - แก้ปัญหาบรรทัดติดกันในไฟล์
            - เหมาะสำหรับการอ่านบนหน้าจอ
            """)

        with col_help2:
            st.markdown("""
            ** MD → TXT:**
            - เปลี่ยนนามสกุลไฟล์จาก .md กลับเป็น .txt
            - แปลงใน-place ที่โฟลเดอร์ `Clean`
            - แก้ปัญหาบรรทัดติดกันในไฟล์
            - เหมาะสำหรับการประมวลผลต่อ
            """)

        # ข้อมูลเพิ่มเติม
        st.markdown("---")
        with st.expander(" ข้อมูลเพิ่มเติม"):
            st.markdown("""
            ** วัตถุประสงค์:**
            - แก้ปัญหาการอ่านไฟล์ .txt ที่ล้นจอ
            - เปลี่ยนนามสกุลไฟล์เพื่อให้อ่านง่ายขึ้น
            - แก้ปัญหาบรรทัดติดกันในไฟล์

            ** โฟลเดอร์ที่เกี่ยวข้อง:**
            - `2-clean/` - ไฟล์ที่แปลง (เปลี่ยนนามสกุลโดยตรงในโฟลเดอร์นี้)

            ** ฟีเจอร์:**
            - แปลงใน-place (เปลี่ยนไฟล์โดยตรง ไม่คัดลอก)
            - เปลี่ยนนามสกุลแบบ batch (หลายไฟล์พร้อมกัน)
            - แก้ปัญหาบรรทัดติดกันอัตโนมัติ
            - แสดงตัวอย่างก่อนเปลี่ยน
            - สถิติไฟล์แบบ real-time
            """)

        # Format Check Sub-tab

