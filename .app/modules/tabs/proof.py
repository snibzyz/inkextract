"""tabs/proof.py — Tab ตรวจสอบและแก้ไข (AB / Normal / Multi-folder)"""
from __future__ import annotations
import inspect
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.preferences_manager import preferences_manager


def render(proofreader, file_processor) -> None:
    """แสดง proof tab ทั้งหมด — มี 3 sub-tabs"""
    tab_ab_mode, tab_normal_mode, tab_multi_folder = st.tabs([
        ":material/compare_arrows: โหมด AB",
        ":material/text_fields: โหมดทั่วไป",
        ":material/folder_copy: ตรวจหลายโฟลเดอร์",
    ])

    with tab_ab_mode:
        # Workflow steps — ใช้ theme-aware bg + Thai-only
        st.markdown(
        """
            <div style="background: var(--ink-surface-tint); padding: 1.25rem;
                        border-radius: var(--ink-radius-lg);
                        border-left: 4px solid var(--ink-orange);
                        margin-bottom: 1.25rem; color: var(--ink-text);">
                <div style="font-weight: 700; color: var(--ink-orange-dark);
                            font-size: 1.05em; margin-bottom: 0.75rem;">
                    ขั้นตอนการทำงาน
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">1. วิเคราะห์</span>
                    <span style="color: var(--ink-text-muted);">→</span>
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">2. ส่งออก</span>
                    <span style="color: var(--ink-text-muted);">→</span>
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">3. แก้ไขนอก</span>
                    <span style="color: var(--ink-text-muted);">→</span>
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">4. นำเข้า</span>
                    <span style="color: var(--ink-text-muted);">→</span>
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">5. แก้ไฟล์</span>
                    <span style="color: var(--ink-text-muted);">→</span>
                    <span style="background: var(--ink-orange); color: white;
                                 padding: 4px 12px; border-radius: var(--ink-radius-pill);
                                 font-size: 0.88em; font-weight: 600;">6. ทำสะอาด</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Settings Section
        with st.container():
            st.markdown("####  การตั้งค่าการตรวจสอบ")
            col1, col2 = st.columns([1, 1])

        with col1:
            check_foreign_languages = st.checkbox(
            " ตรวจสอบภาษาต่างประเทศ", 
                value=preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_foreign_languages", True),
                help="ตรวจหาอักขระที่ไม่ใช่ภาษาไทย",
                key="ab_check_foreign"
            )
            if check_foreign_languages != preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_foreign_languages", True):
                preferences_manager.set_setting("proofreading_settings", "ab_mode", 
                    {**preferences_manager.get_setting("proofreading_settings", "ab_mode", {}), 
                    "check_foreign_languages": check_foreign_languages})

        with col2:
            check_numbers = st.checkbox(
            " ตรวจสอบตัวเลข", 
                value=preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_numbers", False),
                help="ตรวจหาตัวเลขในข้อความ",
                key="ab_check_numbers"
            )
            if check_numbers != preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_numbers", False):
                preferences_manager.set_setting("proofreading_settings", "ab_mode", 
                    {**preferences_manager.get_setting("proofreading_settings", "ab_mode", {}), 
                    "check_numbers": check_numbers})

        check_english = st.checkbox(
        " ตรวจสอบภาษาอังกฤษ",
            value=preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_english", False),
            help="ตรวจหาตัวอักษรภาษาอังกฤษ",
            key="ab_check_english"
        )
        if check_english != preferences_manager.get_setting("proofreading_settings", "ab_mode", {}).get("check_english", False):
            preferences_manager.set_setting("proofreading_settings", "ab_mode", 
                {**preferences_manager.get_setting("proofreading_settings", "ab_mode", {}), 
                "check_english": check_english})

        st.markdown("####  เทียบคำแปลกับ vocab")
        ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

        check_duplicate_content = st.checkbox(
        " ตรวจเนื้อหาซ้ำระหว่างไฟล์",
            value=ab_mode_prefs.get("check_duplicate_content", True),
            help="ถ้าไฟล์ในโฟลเดอร์ `0-input` มีเนื้อหา [B] เหมือนกันหลายไฟล์จะแจ้งเตือนใน UI"
        )
        if check_duplicate_content != ab_mode_prefs.get("check_duplicate_content", True):
            preferences_manager.set_setting(
            "proofreading_settings",
            "ab_mode",
                {**ab_mode_prefs, "check_duplicate_content": check_duplicate_content}
            )
            ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

        check_translation_vocab = st.checkbox(
        " ตรวจคำแปลไทยเทียบกับ vocab",
            value=ab_mode_prefs.get("check_translation_vocab", False),
            help="ถ้าบรรทัด [A] มีศัพท์จีนตรงกับ vocab จะตรวจว่าบรรทัด [B] มีคำแปลไทยตาม vocab หรือไม่",
            key="ab_check_translation_vocab"
        )
        if check_translation_vocab != ab_mode_prefs.get("check_translation_vocab", False):
            preferences_manager.set_setting("proofreading_settings", "ab_mode",
                {**ab_mode_prefs,
                "check_translation_vocab": check_translation_vocab})
            ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

        vocab_files = proofreader.get_available_vocab_files()
        vocab_file_map = {path.name: path for path in vocab_files}
        vocab_file_names = list(vocab_file_map.keys())
        saved_vocab_file = ab_mode_prefs.get("selected_vocab_file", "")
        saved_min_vocab_cn_length = int(ab_mode_prefs.get("min_vocab_cn_length", 2) or 2)
        selected_vocab_name = ""
        selected_vocab_path = None
        min_vocab_cn_length = saved_min_vocab_cn_length

        if check_translation_vocab:
            if vocab_file_names:
                default_vocab_index = vocab_file_names.index(saved_vocab_file) if saved_vocab_file in vocab_file_names else 0
                selected_vocab_name = st.selectbox(
                "เลือกไฟล์ vocab ที่ใช้เทียบ:",
                    options=vocab_file_names,
                    index=default_vocab_index,
                    help="ใช้เทียบคำจีนใน [A] กับคำแปลไทยที่ควรพบใน [B]",
                    key="ab_selected_vocab_file"
                )
                selected_vocab_path = vocab_file_map.get(selected_vocab_name)

                if selected_vocab_name != saved_vocab_file:
                    preferences_manager.set_setting("proofreading_settings", "ab_mode",
                        {**ab_mode_prefs,
                        "selected_vocab_file": selected_vocab_name})
                    ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

                st.caption(f"ใช้ vocab: `{selected_vocab_name}`")
                min_vocab_cn_length = st.number_input(
                "นับเฉพาะ vocab ที่มีอักษรจีนอย่างน้อย:",
                    min_value=1,
                    max_value=10,
                    value=saved_min_vocab_cn_length,
                    step=1,
                    help="ใช้ลูกศรขึ้นลงเพื่อลด noise จากคำจีนที่สั้นเกินไป เช่น 2 = นับคำจีนตั้งแต่ 2 ตัวขึ้นไป",
                    key="ab_min_vocab_cn_length"
                )

                if int(min_vocab_cn_length) != saved_min_vocab_cn_length:
                    preferences_manager.set_setting("proofreading_settings", "ab_mode",
                        {**ab_mode_prefs,
                        "selected_vocab_file": selected_vocab_name,
                        "min_vocab_cn_length": int(min_vocab_cn_length)})
                    ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

                st.caption(f"ขั้นต่ำคำจีนสำหรับตรวจ vocab: `{int(min_vocab_cn_length)}` ตัว")
            else:
                st.warning(" ไม่พบไฟล์ vocab ในโฟลเดอร์ `vocab`")

        # Exclude Patterns
        with st.expander("การตั้งค่ารูปแบบยกเว้น (ไม่นับเป็นข้อผิดพลาด)", expanded=False):
            from modules.config import regex_patterns

            st.markdown("""
            ** คำแนะนำ:**
            - ระบุอักขระหรือ pattern ที่**ไม่ต้องการ**ให้นับเป็นข้อผิดพลาด
            - รองรับ Regular Expression (Regex)
            - หนึ่งบรรทัดต่อหนึ่ง pattern
            - บรรทัดที่ขึ้นต้นด้วย `#` จะถูกข้าม (comment)
            """)

            # แสดง patterns ปัจจุบัน
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.metric("รูปแบบทั้งหมด", len(regex_patterns.ignore_patterns))
            with col_info2:
                exclude_file = paths.EXCLUDE_FILE
                if exclude_file.exists():
                    user_patterns_count = len([line for line in exclude_file.read_text(encoding='utf-8').split('\n') 
                                               if line.strip() and not line.strip().startswith('#')])
                    st.metric("รูปแบบที่เพิ่มเอง", user_patterns_count)
                else:
                    st.metric("รูปแบบที่เพิ่มเอง", 0)

            st.markdown("---")

            # อ่านไฟล์ exclude.txt ปัจจุบัน
            exclude_file = paths.EXCLUDE_FILE
            if exclude_file.exists():
                current_content = exclude_file.read_text(encoding='utf-8')
            else:
                current_content = """# ไฟล์สำหรับระบุอักขระหรือ pattern ที่ต้องการยกเว้น
    # บรรทัดที่ขึ้นต้นด้วย # จะถูกข้าม
    # หนึ่งบรรทัดต่อหนึ่ง pattern (รองรับ regex)

    # เพิ่ม patterns ของคุณด้านล่างนี้:
    """

            new_patterns = st.text_area(
            "แก้ไข exclude.txt (อักขระที่ต้องการยกเว้น):",
                value=current_content,
                height=200,
                help="ตัวอย่าง: 【, 】, , , HP, MP"
            )

            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button(" **บันทึกไฟล์**", width='stretch'):
                    try:
                        exclude_file.write_text(new_patterns, encoding='utf-8')
                        st.success(" บันทึก exclude.txt สำเร็จ!")
                        st.toast("บันทึก exclude.txt สำเร็จ!")
                    except Exception as e:
                        st.error(f" เกิดข้อผิดพลาด: {str(e)}")

            with col_btn2:
                if st.button("โหลดรูปแบบใหม่", width='stretch'):
                    try:
                        regex_patterns.reload_patterns()
                        st.success(f"โหลดรูปแบบใหม่สำเร็จ — ตอนนี้มี {len(regex_patterns.ignore_patterns)} รูปแบบ")
                        st.toast(f"โหลด {len(regex_patterns.ignore_patterns)} patterns สำเร็จ!")
                    except Exception as e:
                        st.error(f" เกิดข้อผิดพลาด: {str(e)}")

            with col_btn3:
                if st.button(" **คู่มือการใช้**", width='stretch'):
                    guide_file = Path("EXCLUDE_GUIDE.md")
                    if guide_file.exists():
                        st.info(" เปิดไฟล์ `EXCLUDE_GUIDE.md` เพื่อดูคู่มือการใช้งานแบบเต็ม")
                    else:
                        st.warning(" ไม่พบไฟล์คู่มือ EXCLUDE_GUIDE.md")

            # แสดงตัวอย่าง patterns ปัจจุบัน
            st.markdown("---")
            st.markdown("**รูปแบบที่ใช้งานอยู่ (10 อันดับแรก):**")

            if hasattr(regex_patterns, 'ignore_patterns_raw'):
                patterns_preview = regex_patterns.ignore_patterns_raw[:10]
                for i, pattern in enumerate(patterns_preview, 1):
                    st.code(f"{i}. {pattern}", language="regex")

                if len(regex_patterns.ignore_patterns_raw) > 10:
                    st.caption(f"... และอีก {len(regex_patterns.ignore_patterns_raw) - 10} patterns")
            else:
                st.info(" ไม่สามารถแสดง patterns ได้")

        # Main Action Buttons
        st.markdown("####  การดำเนินการหลัก")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(" **เริ่มวิเคราะห์**", type="primary", width='stretch'):
                with st.spinner("กำลังวิเคราะห์ไฟล์..."):
                    analyze_files_signature = inspect.signature(proofreader.analyze_files)
                    analyze_files_kwargs = {
                    "check_translation_vocab": check_translation_vocab,
                    "vocab_file": selected_vocab_path,
                    "check_duplicate_content": check_duplicate_content
                    }

                    if "min_vocab_cn_length" in analyze_files_signature.parameters:
                        analyze_files_kwargs["min_vocab_cn_length"] = int(min_vocab_cn_length)

                    proofreader.analyze_files(
                        check_foreign_languages,
                        check_numbers,
                        check_english,
                        **analyze_files_kwargs
                    )
                st.toast("วิเคราะห์เสร็จสิ้น!")

        with col2:
            export_disabled = len(proofreader.found_errors) == 0

            # ใช้ session state สำหรับการยืนยัน export
            if 'export_confirm' not in st.session_state:
                st.session_state.export_confirm = False

            if not st.session_state.export_confirm:
                if st.button(" **ส่งออกเพื่อแก้ไข**", disabled=export_disabled, width='stretch'):
                    st.session_state.export_confirm = True
                    st.rerun()
            else:
                st.warning(" ต้องการส่งออกไฟล์ error_trans.txt หรือไม่?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button(" ยืนยัน", type="primary", width='stretch'):
                        with st.spinner("กำลังส่งออก..."):
                            proofreader.export_errors()
                        st.session_state.export_confirm = False
                        st.toast("ส่งออกสำเร็จ!")
                        st.rerun()
                with col_no:
                    if st.button(" ยกเลิก", width='stretch'):
                        st.session_state.export_confirm = False
                        st.rerun()

        with col3:
            if st.button(" **นำเข้าการแก้ไข**", width='stretch'):
                proofreader.grab_and_import_file()

        # Fix & Clean Actions
        st.markdown("####  การประมวลผลไฟล์")
        col4, col5 = st.columns(2)

        with col4:
            if st.button(" **แก้ไขไฟล์**", width='stretch'):
                file_processor.fix_files(proofreader.found_errors)

        with col5:
            if st.button(" **ทำความสะอาดไฟล์**", width='stretch'):
                file_processor.clean_final_files()

        # Status Display
        if proofreader.found_errors:
            remaining_errors = proofreader.check_remaining_errors(check_foreign_languages, check_numbers)

            with st.container():
                if remaining_errors > 0:
                    st.markdown(f"""
                    <div style="background: var(--ink-warn-bg); border: 1px solid var(--ink-warn);
                                padding: 1rem; border-radius: var(--ink-radius-md); margin: 1rem 0;
                                color: var(--ink-text);">
                        <h5 style="margin: 0; color: var(--ink-warn);">
                            ยังมีข้อผิดพลาดเหลืออยู่ {remaining_errors} รายการ
                        </h5>
                        <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                            กรุณาแก้ไขข้อผิดพลาดในไฟล์ <code>output/error_trans.txt</code>
                            (แก้ไขเฉพาะบรรทัด [B]) แล้วกด <strong>นำเข้าการแก้ไข</strong> อีกครั้ง
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background: var(--ink-success-bg); border: 1px solid var(--ink-success);
                                padding: 1rem; border-radius: var(--ink-radius-md); margin: 1rem 0;
                                color: var(--ink-text);">
                        <h5 style="margin: 0; color: var(--ink-success);">
                            แก้ไขข้อผิดพลาดครบแล้ว
                        </h5>
                        <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                            พร้อมใช้งานปุ่ม <strong>แก้ไขไฟล์</strong> เพื่อสร้างไฟล์ที่แก้ไขแล้ว
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: var(--ink-surface-tint); padding: 2rem;
                        border-radius: var(--ink-radius-xl); text-align: center;
                        border: 2px dashed var(--ink-border-orange); color: var(--ink-text);">
                <h4 style="margin: 0; color: var(--ink-orange-dark);">เริ่มต้นการทำงาน</h4>
                <p style="margin: 1rem 0 0 0; color: var(--ink-text-muted); font-size: 1.05rem;">
                    วางไฟล์ .txt ลงในโฟลเดอร์
                    <code style="background: var(--ink-surface-2); padding: 2px 8px;
                                 border-radius: var(--ink-radius-sm);
                                 color: var(--ink-orange-dark);">0-input</code>
                    แล้วกดปุ่ม <strong>เริ่มวิเคราะห์</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)

    with tab_normal_mode:
        st.markdown("""
        <div style="background: var(--ink-surface-tint); padding: 1.25rem;
                    border-radius: var(--ink-radius-lg);
                    border-left: 4px solid var(--ink-orange);
                    margin-bottom: 1.25rem; color: var(--ink-text);">
            <h4 style="margin: 0; color: var(--ink-orange-dark);">
                โหมดทั่วไป (สแกนทุกบรรทัด)
            </h4>
            <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                ใช้สำหรับตรวจภาษาต่างประเทศในไฟล์ที่ไม่มีโครงสร้าง [A]/[B] เช่น หลังแปลเสร็จ
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("####  การตั้งค่าโหมดทั่วไป")
        col_normal_1, col_normal_2, col_normal_3 = st.columns(3)

        with col_normal_1:
            normal_check_foreign = st.checkbox(
            " ตรวจสอบภาษาต่างประเทศ",
                value=preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_foreign_languages", True),
                help="ตรวจหาอักขระที่ไม่ใช่ภาษาไทย",
                key="normal_check_foreign"
            )
            if normal_check_foreign != preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_foreign_languages", True):
                preferences_manager.set_setting("proofreading_settings", "normal_mode", 
                    {**preferences_manager.get_setting("proofreading_settings", "normal_mode", {}), 
                    "check_foreign_languages": normal_check_foreign})

        with col_normal_2:
            normal_check_numbers = st.checkbox(
            " ตรวจสอบตัวเลข",
                value=preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_numbers", False),
                help="ตรวจหาตัวเลขในข้อความ",
                key="normal_check_numbers"
            )
            if normal_check_numbers != preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_numbers", False):
                preferences_manager.set_setting("proofreading_settings", "normal_mode", 
                    {**preferences_manager.get_setting("proofreading_settings", "normal_mode", {}), 
                    "check_numbers": normal_check_numbers})

        with col_normal_3:
            normal_check_english = st.checkbox(
            " ตรวจสอบภาษาอังกฤษ",
                value=preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_english", False),
                help="ตรวจหาตัวอักษรภาษาอังกฤษ",
                key="normal_check_english"
            )
            if normal_check_english != preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("check_english", False):
                preferences_manager.set_setting("proofreading_settings", "normal_mode", 
                    {**preferences_manager.get_setting("proofreading_settings", "normal_mode", {}), 
                    "check_english": normal_check_english})

        st.markdown("####  เลือกโฟลเดอร์ต้นทาง")

        preset_folders = {
        "2-clean (แนะนำ)": paths.CLEAN_DIR,
        "0-input": paths.INPUT_DIR,
        "1-fix": paths.FIX_DIR
        }

        folder_options = list(preset_folders.keys()) + ["ระบุเส้นทางเอง"]
        default_index = folder_options.index("2-clean (แนะนำ)") if "2-clean (แนะนำ)" in folder_options else 0

        selected_folder_option = st.selectbox(
        "เลือกโฟลเดอร์ที่ต้องการตรวจสอบ:",
            options=folder_options,
            index=default_index,
            help="เลือกโฟลเดอร์ที่ต้องการสแกนหาอักขระต่างประเทศ",
            key="normal_mode_folder_selection"
        )
        # บันทึกการเลือกโฟลเดอร์
        if selected_folder_option != preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("source_folder", "2-clean"):
            preferences_manager.set_setting("proofreading_settings", "normal_mode", 
                {**preferences_manager.get_setting("proofreading_settings", "normal_mode", {}), 
                "source_folder": selected_folder_option})

        target_path: Optional[Path] = None
        folder_status_message = None

        if selected_folder_option == "ระบุเส้นทางเอง":
            custom_path_input = st.text_input(
            "ระบุเส้นทางโฟลเดอร์เอง:",
                value=str(proofreader.normal_mode_source) if proofreader.normal_mode_source else "",
                placeholder="เช่น: C:\\Users\\Username\\Desktop\\translated หรือ ./custom-input",
                help="รองรับทั้งเส้นทางสัมบูรณ์และสัมพัทธ์"
            )

            if custom_path_input.strip():
                try:
                    target_path = Path(custom_path_input.strip())
                    if target_path.exists():
                        folder_status_message = ("success", f" โฟลเดอร์: `{target_path}`")
                    else:
                        folder_status_message = ("error", f" ไม่พบโฟลเดอร์ `{target_path}`")
                        target_path = None
                except Exception as e:
                    folder_status_message = ("error", f" เส้นทางไม่ถูกต้อง: {str(e)}")
                    target_path = None
            else:
                folder_status_message = ("info", " กรุณาระบุเส้นทางโฟลเดอร์")
                target_path = None
        else:
            target_path = preset_folders.get(selected_folder_option)
            if target_path:
                folder_status_message = ("info", f" โฟลเดอร์ที่เลือก: `{target_path}`")

        if folder_status_message:
            status_level, status_text = folder_status_message
            if status_level == "success":
                st.success(status_text)
            elif status_level == "error":
                st.error(status_text)
            else:
                st.info(status_text)

        st.markdown("---")

        analyze_btn = st.button(" **วิเคราะห์โหมดทั่วไป**", type="primary", width='stretch')

        if analyze_btn:
            with st.spinner("กำลังวิเคราะห์โหมดทั่วไป..."):
                proofreader.analyze_normal_mode(
                    target_path if target_path else proofreader.normal_mode_source,
                    normal_check_foreign,
                    normal_check_numbers,
                    normal_check_english
                )
            st.toast("วิเคราะห์โหมดทั่วไปเสร็จสิ้น!")

        stats = proofreader.normal_mode_stats
        if stats.get('files', 0) > 0:
            st.markdown("####  สรุปผลการสแกน")
            col_stat1, col_stat2, col_stat3 = st.columns(3)

            with col_stat1:
                st.metric(" ไฟล์ที่วิเคราะห์", f"{stats.get('files', 0):,}")

            with col_stat2:
                st.metric(" บรรทัดที่สแกน", f"{stats.get('lines', 0):,}")

            with col_stat3:
                st.metric(" บรรทัดที่ต้องตรวจ", f"{stats.get('errors', 0):,}")

            col_stat4, col_stat5, col_stat6 = st.columns(3)

            with col_stat4:
                st.metric(" ภาษาต่างประเทศ", f"{stats.get('foreign', 0):,}")

            with col_stat5:
                st.metric(" ภาษาอังกฤษ", f"{stats.get('english', 0):,}")

            with col_stat6:
                st.metric(" ตัวเลข", f"{stats.get('numbers', 0):,}")

        if proofreader.normal_mode_errors:
            st.markdown("####  บรรทัดที่พบภาษาต่างประเทศ / ตัวเลข")
            try:
                normal_df = pd.DataFrame(proofreader.normal_mode_errors)
                normal_df = normal_df[[
                'file_name',
                'line_number',
                'line_content',
                'categories',
                'file_path'
                ]]
                normal_df.rename(columns={
                'file_name': 'ไฟล์',
                'line_number': 'บรรทัด',
                'line_content': 'ข้อความ',
                'categories': 'ประเภท',
                'file_path': 'เส้นทางไฟล์'
                }, inplace=True)
                st.dataframe(normal_df, width='stretch')
            except Exception:
                st.warning(" ไม่สามารถสร้างตารางสรุปได้ โปรดดูข้อมูลดิบด้านล่าง")
                for err in proofreader.normal_mode_errors[:20]:
                    categories = ', '.join(err.get('categories', []))
                    category_text = f" [{categories}]" if categories else ""
                    st.write(f" `{err['file_name']}` บรรทัด {err['line_number']}: {err['line_content']}{category_text}")

            st.markdown("---")
            col_export1, col_export2 = st.columns(2)

            with col_export1:
                df_for_export = normal_df.copy()
                st.download_button(
                    label=" ดาวน์โหลดผล (CSV)",
                    data=df_for_export.to_csv(index=False).encode('utf-8-sig'),
                    file_name="normal_mode_errors.csv",
                    mime="text/csv",
                    width='stretch'
                )

            with col_export2:
                if st.button(" ส่งออก normal_mode_errors.txt", width='stretch'):
                    proofreader.export_normal_mode_errors()
        elif stats and stats.get('files', 0) > 0 and stats.get('errors', 0) == 0:
            st.success(" โหมดทั่วไป: ไม่พบภาษาต่างประเทศหรือเลขที่ตั้งใจให้ตรวจ")

    with tab_multi_folder:
        st.markdown("""
        <div style="background: var(--ink-surface-tint); padding: 1.25rem;
                    border-radius: var(--ink-radius-lg);
                    border-left: 4px solid var(--ink-orange);
                    margin-bottom: 1.25rem; color: var(--ink-text);">
            <h4 style="margin: 0; color: var(--ink-orange-dark);">
                ตรวจหลายโฟลเดอร์ (ไวขึ้น)
            </h4>
            <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                ตรวจสอบโฟลเดอร์ย่อยหลายโฟลเดอร์ใน 0-input พร้อมกัน
                แล้วเปลี่ยนชื่อโฟลเดอร์ตามผลลัพธ์
            </p>
            <p style="margin: 0.4rem 0 0 0; color: var(--ink-text); font-weight: 600;">
                รองรับโฟลเดอร์ซ้อน: นักแปล / ชื่อเรื่อง / ตอน
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### โครงสร้างที่รองรับ")
        st.info("""
        **โหมดนี้รองรับ 2 รูปแบบ:**

        **1. โครงสร้างชั้นเดียว** (โฟลเดอร์เดียว)
        ```
        0-input/
        ├── เรื่อง1/
        │   ├── ตอน001.txt
        │   └── ตอน002.txt
        └── เรื่อง2/
            └── ตอน001.txt
        ```

        **2. โครงสร้างซ้อน** (นักแปล / ชื่อเรื่อง / ตอน)
        ```
        0-input/
        ├── นักแปล1/
        │   ├── เรื่อง1/
        │   │   ├── ตอน001.txt
        │   │   └── ตอน002.txt
        │   └── เรื่อง2/
        │       └── ตอน001.txt
        └── นักแปล2/
            └── เรื่อง1/
                └── ตอน001.txt
        ```

        **โหมดนี้จะตรวจที่ระดับ "ชื่อเรื่อง" และเปลี่ยนชื่อที่ระดับนั้น**
        """)

        st.markdown("#### การตั้งค่าตรวจหลายโฟลเดอร์")
        col_multi_1, col_multi_2, col_multi_3 = st.columns(3)

        with col_multi_1:
            multi_check_foreign = st.checkbox(
            " ตรวจสอบภาษาต่างประเทศ",
                value=preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_foreign_languages", True),
                help="ตรวจหาอักขระที่ไม่ใช่ภาษาไทย",
                key="multi_check_foreign"
            )
            if multi_check_foreign != preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_foreign_languages", True):
                preferences_manager.set_setting("proofreading_settings", "multi_folder", 
                    {**preferences_manager.get_setting("proofreading_settings", "multi_folder", {}), 
                    "check_foreign_languages": multi_check_foreign})

        with col_multi_2:
            multi_check_numbers = st.checkbox(
            " ตรวจสอบตัวเลข",
                value=preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_numbers", False),
                help="ตรวจหาตัวเลขในข้อความ",
                key="multi_check_numbers"
            )
            if multi_check_numbers != preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_numbers", False):
                preferences_manager.set_setting("proofreading_settings", "multi_folder", 
                    {**preferences_manager.get_setting("proofreading_settings", "multi_folder", {}), 
                    "check_numbers": multi_check_numbers})

        with col_multi_3:
            multi_check_english = st.checkbox(
            " ตรวจสอบภาษาอังกฤษ",
                value=preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_english", False),
                help="ตรวจหาตัวอักษรภาษาอังกฤษ",
                key="multi_check_english"
            )
            if multi_check_english != preferences_manager.get_setting("proofreading_settings", "multi_folder", {}).get("check_english", False):
                preferences_manager.set_setting("proofreading_settings", "multi_folder", 
                    {**preferences_manager.get_setting("proofreading_settings", "multi_folder", {}), 
                    "check_english": multi_check_english})

        st.markdown("---")

        analyze_multi_btn = st.button(" **วิเคราะห์หลายโฟลเดอร์**", type="primary", width='stretch')

        if analyze_multi_btn:
            with st.spinner("กำลังวิเคราะห์หลายโฟลเดอร์..."):
                proofreader.analyze_multiple_folders_mode(
                    multi_check_foreign,
                    multi_check_numbers,
                    multi_check_english
                )
            st.toast("วิเคราะห์หลายโฟลเดอร์เสร็จสิ้น!")

        # แสดงผลลัพธ์
        if proofreader.multi_folder_results:
            st.markdown("####  ผลลัพธ์แยกตามโฟลเดอร์")

            # สร้างตารางสรุปผล
            summary_data = []
            for folder_name, result in proofreader.multi_folder_results.items():
                summary_data.append({
                    'โฟลเดอร์': folder_name,
                    'ไฟล์': result['files'],
                    'ข้อผิดพลาด': result['total_errors'],
                    'ภาษาต่างประเทศ': result['stats']['foreign'],
                    'อังกฤษ': result['stats']['english'],
                    'ตัวเลข': result['stats']['numbers'],
                    'สถานะ': 'สะอาด' if result['total_errors'] == 0 else f'พบ {result["total_errors"]} ข้อผิดพลาด',
                })

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, width='stretch')

            # สรุปรวม
            total_folders = len(proofreader.multi_folder_results)
            total_files = sum(r['files'] for r in proofreader.multi_folder_results.values())
            total_errors = sum(r['total_errors'] for r in proofreader.multi_folder_results.values())
            clean_folders = sum(1 for r in proofreader.multi_folder_results.values() if r['total_errors'] == 0)
            error_folders = total_folders - clean_folders

            st.markdown("####  สรุปรวม")
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(" โฟลเดอร์ทั้งหมด", f"{total_folders:,}")

            with col2:
                st.metric(" ไฟล์ทั้งหมด", f"{total_files:,}")

            with col3:
                st.metric("ข้อผิดพลาดทั้งหมด", f"{total_errors:,}")

            with col4:
                st.metric("โฟลเดอร์สะอาด", f"{clean_folders:,}")

            with col5:
                st.metric("โฟลเดอร์มีข้อผิดพลาด", f"{error_folders:,}")

            st.markdown("---")

            # ปุ่มบันทึกและเปลี่ยนชื่อ
            if st.button("บันทึกผลและเปลี่ยนชื่อโฟลเดอร์", type="primary", width='stretch'):
                proofreader.export_multiple_folders_errors()

            st.markdown("""
            ####  คำอธิบาย
            - เมื่อกด **"บันทึกผลและเปลี่ยนชื่อโฟลเดอร์"** จะทำการ:
              - เปลี่ยนชื่อโฟลเดอร์เป็น **`w ชื่อโฟลเดอร์`** ถ้าพบ errors
              - เปลี่ยนชื่อโฟลเดอร์เป็น **`c ชื่อโฟลเดอร์`** ถ้าไม่พบ errors (clean)
              - บันทึกไฟล์ **`errors-[จำนวน].txt`** ในโฟลเดอร์ที่มี errors
              """)

        # Files Tab (รวม Merge และ Separate)

