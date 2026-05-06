"""tabs/files_sub/clear.py — Sub-tab 'clear' ของ tab จัดการไฟล์"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.format_checker import FormatChecker


def render(file_processor) -> None:
    """clear sub-tab"""
    st.markdown("####  ลบไฟล์ในโฟลเดอร์")
    st.info(" เลือกโฟลเดอร์ที่ต้องการลบไฟล์ทั้งหมด ระวัง! การลบไฟล์ไม่สามารถกู้คืนได้")

    # สถิติไฟล์ในแต่ละโฟลเดอร์
    st.markdown("####  สถิติไฟล์ในโฟลเดอร์")

    # กำหนดโฟลเดอร์และเส้นทาง (ยุบ 2-clean-docx/md เข้า 2-clean เดียวแล้ว)
    folders_info = {
        "0-input": paths.INPUT_DIR,
        "1-fix": paths.FIX_DIR,
        "2-clean": paths.CLEAN_DIR,
        "3-merge": paths.MERGE_DIR,
        "4-separate": paths.SEPARATE_DIR,
    }

    # แสดงสถิติไฟล์
    col1, col2, col3 = st.columns(3)

    with col1:
        input_count = len(list(folders_info["0-input"].glob("*"))) if folders_info["0-input"].exists() else 0
        fix_count = len(list(folders_info["1-fix"].glob("*"))) if folders_info["1-fix"].exists() else 0
        st.metric("0-input", input_count)
        st.metric("1-fix", fix_count)

    with col2:
        clean_count = len(list(folders_info["2-clean"].glob("*"))) if folders_info["2-clean"].exists() else 0
        st.metric("2-clean", clean_count)

    with col3:
        merge_count = len(list(folders_info["3-merge"].glob("*"))) if folders_info["3-merge"].exists() else 0
        separate_count = len(list(folders_info["4-separate"].glob("*"))) if folders_info["4-separate"].exists() else 0
        st.metric("3-merge", merge_count)
        st.metric("4-separate", separate_count)

    st.markdown("---")

    # ตัวเลือกการลบไฟล์
    st.markdown("#### เลือกโฟลเดอร์ที่ต้องการลบ")

    # ใช้ session state เพื่อจำค่าการเลือก
    if 'clear_folders_selection' not in st.session_state:
        st.session_state.clear_folders_selection = {
            "0-input": True,
            "1-fix": True,
            "2-clean": True,
            "3-merge": False,
            "4-separate": False,
        }

    # แบ่งเป็น 2 columns
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("**โฟลเดอร์หลัก**")

        input_selected = st.checkbox(
            "0-input (ไฟล์ต้นฉบับ)",
            value=st.session_state.clear_folders_selection["0-input"],
            help="ลบไฟล์ต้นฉบับในโฟลเดอร์ 0-input",
        )
        st.session_state.clear_folders_selection["0-input"] = input_selected

        fix_selected = st.checkbox(
            "1-fix (ไฟล์แก้ไข)",
            value=st.session_state.clear_folders_selection["1-fix"],
            help="ลบไฟล์ที่แก้ไขแล้วในโฟลเดอร์ 1-fix",
        )
        st.session_state.clear_folders_selection["1-fix"] = fix_selected

        clean_selected = st.checkbox(
            "2-clean (ไฟล์สะอาด — รวม .txt/.md/.docx)",
            value=st.session_state.clear_folders_selection["2-clean"],
            help="ลบไฟล์ทุกชนิดในโฟลเดอร์ 2-clean",
        )
        st.session_state.clear_folders_selection["2-clean"] = clean_selected

    with col_right:
        st.markdown("**โฟลเดอร์ผลลัพธ์**")

        merge_selected = st.checkbox(
            "3-merge (ไฟล์รวม)",
            value=st.session_state.clear_folders_selection["3-merge"],
            help="ลบไฟล์ที่รวมแล้วในโฟลเดอร์ 3-merge",
        )
        st.session_state.clear_folders_selection["3-merge"] = merge_selected

        separate_selected = st.checkbox(
            "4-separate (ไฟล์แยก)",
            value=st.session_state.clear_folders_selection["4-separate"],
            help="ลบไฟล์ที่แยกแล้วในโฟลเดอร์ 4-separate",
        )
        st.session_state.clear_folders_selection["4-separate"] = separate_selected

    # ปุ่มรีเซ็ตการเลือก
    st.markdown("---")
    col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])

    with col_reset1:
        if st.button("รีเซ็ตเป็นค่าเริ่มต้น", width='stretch'):
            st.session_state.clear_folders_selection = {
                "0-input": True,
                "1-fix": True,
                "2-clean": True,
                "3-merge": False,
                "4-separate": False,
            }
            st.rerun()

    with col_reset2:
        if st.button(" **เลือกทั้งหมด**", width='stretch'):
            for folder in st.session_state.clear_folders_selection:
                st.session_state.clear_folders_selection[folder] = True
            st.rerun()

    with col_reset3:
        if st.button(" **ยกเลิกทั้งหมด**", width='stretch'):
            for folder in st.session_state.clear_folders_selection:
                st.session_state.clear_folders_selection[folder] = False
            st.rerun()

    # สรุปการเลือก
    selected_folders = [folder for folder, selected in st.session_state.clear_folders_selection.items() if selected]

    if selected_folders:
        st.markdown("---")
        st.markdown("####  สรุปการเลือก")

        # แสดงโฟลเดอร์ที่เลือกพร้อมจำนวนไฟล์
        for folder in selected_folders:
            folder_path = folders_info[folder]
            if folder_path.exists():
                file_count = len(list(folder_path.glob("*")))
                if file_count > 0:
                    st.warning(f" `{folder}` - {file_count} ไฟล์")
                else:
                    st.info(f" `{folder}` - ไม่มีไฟล์")
            else:
                st.info(f" `{folder}` - โฟลเดอร์ไม่มีอยู่")

        # ปุ่มลบไฟล์
        st.markdown("---")
        st.markdown("####  การดำเนินการลบไฟล์")

        # ใช้ session state สำหรับการยืนยันการลบ
        if 'clear_confirm' not in st.session_state:
            st.session_state.clear_confirm = False

        if not st.session_state.clear_confirm:
            if st.button(" **ลบไฟล์ที่เลือก**", type="primary", width='stretch'):
                st.session_state.clear_confirm = True
                st.rerun()
        else:
            st.error(" **คำเตือน!** การลบไฟล์ไม่สามารถกู้คืนได้")
            st.markdown("**คุณแน่ใจหรือไม่ที่จะลบไฟล์ในโฟลเดอร์ต่อไปนี้:**")
            for folder in selected_folders:
                st.write(f"• `{folder}`")

            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button(" **ยืนยันการลบ**", type="primary", width='stretch'):
                    # ดำเนินการลบไฟล์
                    deleted_count = 0
                    errors = []

                    with st.spinner("กำลังลบไฟล์..."):
                        for folder in selected_folders:
                            folder_path = folders_info[folder]
                            if folder_path.exists():
                                try:
                                    # นับไฟล์ก่อนลบ
                                    files_to_delete = list(folder_path.glob("*"))
                                    file_count = len(files_to_delete)

                                    # ลบไฟล์ทั้งหมดในโฟลเดอร์
                                    for file_path in files_to_delete:
                                        if file_path.is_file():
                                            file_path.unlink()
                                        elif file_path.is_dir():
                                            import shutil
                                            shutil.rmtree(file_path)

                                    deleted_count += file_count
                                    st.success(f" ลบไฟล์ใน `{folder}` สำเร็จ ({file_count} ไฟล์)")

                                except Exception as e:
                                    errors.append(f" ไม่สามารถลบไฟล์ใน `{folder}`: {str(e)}")

                    # แสดงผลลัพธ์
                    if deleted_count > 0:
                        st.success(f" ลบไฟล์สำเร็จทั้งหมด {deleted_count} ไฟล์!")
                        st.toast(f"ลบไฟล์ {deleted_count} ไฟล์สำเร็จ!")

                    if errors:
                        st.error(" มีปัญหาบางส่วน:")
                        for error in errors:
                            st.write(f"{error}")

                    st.session_state.clear_confirm = False
                    st.rerun()

            with col_no:
                if st.button(" **ยกเลิก**", width='stretch'):
                    st.session_state.clear_confirm = False
                    st.rerun()
    else:
        st.info(" กรุณาเลือกโฟลเดอร์ที่ต้องการลบไฟล์")

    # คำแนะนำการใช้งาน
    st.markdown("---")
    st.markdown("####  คำแนะนำการใช้งาน")

    col_help1, col_help2 = st.columns([1, 1])

    with col_help1:
        st.markdown("""
        ** การใช้งาน:**
        - เลือกโฟลเดอร์ที่ต้องการลบไฟล์
        - ค่าเริ่มต้นจะเลือก input, fix, clean, clean-md
        - การลบไฟล์ไม่สามารถกู้คืนได้
        - ตรวจสอบจำนวนไฟล์ก่อนลบ
        """)

    with col_help2:
        st.markdown("""
        ** คำเตือน:**
        - การลบไฟล์เป็นแบบถาวร
        - ควรสำรองไฟล์สำคัญก่อนลบ
        - ตรวจสอบโฟลเดอร์ให้ดีก่อนกดยืนยัน
        - ใช้ปุ่มรีเซ็ตเพื่อกลับค่าเริ่มต้น
        """)



