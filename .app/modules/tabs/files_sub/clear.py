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

    # กำหนดโฟลเดอร์และเส้นทาง (ชื่อ INKIDEA-style PascalCase)
    folders_info = {
        "Input": paths.INPUT_DIR,
        "Raw": paths.RAW_INPUT_DIR,
        "Fix": paths.FIX_DIR,
        "Clean": paths.CLEAN_DIR,
        "Merge": paths.MERGE_DIR,
        "Separate": paths.SEPARATE_DIR,
        "Import": paths.IMPORT_FIX_DIR,
    }

    # แสดงสถิติไฟล์
    def _count(folder_path):
        return len(list(folder_path.glob("*"))) if folder_path.exists() else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Input", _count(folders_info["Input"]))
        st.metric("Raw", _count(folders_info["Raw"]))
    with col2:
        st.metric("Fix", _count(folders_info["Fix"]))
        st.metric("Clean", _count(folders_info["Clean"]))
    with col3:
        st.metric("Merge", _count(folders_info["Merge"]))
        st.metric("Separate", _count(folders_info["Separate"]))
    with col4:
        st.metric("Import", _count(folders_info["Import"]))

    st.markdown("---")

    # ตัวเลือกการลบไฟล์
    st.markdown("#### เลือกโฟลเดอร์ที่ต้องการลบ")

    # ใช้ session state เพื่อจำค่าการเลือก
    _DEFAULT_CLEAR_SELECTION = {
        "Input": True,
        "Raw": False,  # ต้นฉบับล้ำค่า — ปิดไว้เป็น default
        "Fix": True,
        "Clean": True,
        "Merge": False,
        "Separate": False,
        "Import": False,
    }
    if 'clear_folders_selection' not in st.session_state:
        st.session_state.clear_folders_selection = dict(_DEFAULT_CLEAR_SELECTION)
    else:
        # เติม keys ใหม่ที่ยังไม่มีใน state เก่า (กัน KeyError ตอน upgrade)
        for k, v in _DEFAULT_CLEAR_SELECTION.items():
            st.session_state.clear_folders_selection.setdefault(k, v)
        # ลบ keys เก่า (legacy lowercase) ออก
        for legacy_key in list(st.session_state.clear_folders_selection.keys()):
            if legacy_key not in _DEFAULT_CLEAR_SELECTION:
                st.session_state.clear_folders_selection.pop(legacy_key, None)

    # แบ่งเป็น 2 columns
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("**โฟลเดอร์หลัก**")

        input_selected = st.checkbox(
            "Input (ไฟล์แปลตั้งต้น)",
            value=st.session_state.clear_folders_selection["Input"],
            help="ลบไฟล์แปลในโฟลเดอร์ Input",
        )
        st.session_state.clear_folders_selection["Input"] = input_selected

        raw_selected = st.checkbox(
            "Raw (ไฟล์ raw จีนต้นฉบับ)",
            value=st.session_state.clear_folders_selection["Raw"],
            help="ลบไฟล์ raw จีนต้นฉบับ — ระวัง ข้อมูลตั้งต้น",
        )
        st.session_state.clear_folders_selection["Raw"] = raw_selected

        fix_selected = st.checkbox(
            "Fix (ไฟล์ที่แก้ไขแล้ว)",
            value=st.session_state.clear_folders_selection["Fix"],
            help="ลบไฟล์ที่แก้ไขแล้วในโฟลเดอร์ Fix",
        )
        st.session_state.clear_folders_selection["Fix"] = fix_selected

        clean_selected = st.checkbox(
            "Clean (ไฟล์ที่ทำความสะอาด — รวม .txt/.md/.docx)",
            value=st.session_state.clear_folders_selection["Clean"],
            help="ลบไฟล์ทุกชนิดในโฟลเดอร์ Clean",
        )
        st.session_state.clear_folders_selection["Clean"] = clean_selected

    with col_right:
        st.markdown("**โฟลเดอร์ผลลัพธ์**")

        merge_selected = st.checkbox(
            "Merge (ไฟล์ที่รวมแล้ว)",
            value=st.session_state.clear_folders_selection["Merge"],
            help="ลบไฟล์ที่รวมแล้วในโฟลเดอร์ Merge",
        )
        st.session_state.clear_folders_selection["Merge"] = merge_selected

        separate_selected = st.checkbox(
            "Separate (ไฟล์ที่แยกตอนแล้ว)",
            value=st.session_state.clear_folders_selection["Separate"],
            help="ลบไฟล์ที่แยกตอนในโฟลเดอร์ Separate",
        )
        st.session_state.clear_folders_selection["Separate"] = separate_selected

        import_selected = st.checkbox(
            "Import (ไฟล์ที่ผู้ใช้แก้กลับ — สำหรับ import)",
            value=st.session_state.clear_folders_selection["Import"],
            help="ลบไฟล์ใน Import (ไฟล์ที่ผู้ใช้แก้กลับมาก่อน import)",
        )
        st.session_state.clear_folders_selection["Import"] = import_selected

    # ปุ่มรีเซ็ตการเลือก
    st.markdown("---")
    col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])

    with col_reset1:
        if st.button("รีเซ็ตเป็นค่าเริ่มต้น", width='stretch'):
            st.session_state.clear_folders_selection = dict(_DEFAULT_CLEAR_SELECTION)
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



