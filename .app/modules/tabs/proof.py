"""tabs/proof.py — Tab ตรวจสอบและแก้ไข (AB / Normal / Multi-folder)"""
from __future__ import annotations
import inspect
import streamlit as st
import pandas as pd
from pathlib import Path

from modules import paths, ui
from modules.preferences_manager import preferences_manager


# ── Stepper component — ใช้ร่วมทั้ง AB และ Normal mode ──
# Step ที่ "active" = step ปัจจุบันที่ user อยู่ (highlight สด)
# Step ที่ "done"   = ผ่านไปแล้ว (เช็คเขียว)
# Step ที่ "todo"   = ยังไม่ถึง (เทา)
_STEP_LABELS = ["ตั้งค่า", "วิเคราะห์", "ส่งออก", "นำเข้า", "แก้ไขไฟล์"]


def _render_stepper(active_idx: int, done_until: int = -1) -> None:
    """แสดง stepper 1-2-3-4-5 แบบ horizontal — visual cue ให้ user รู้ว่าอยู่ step ไหน.

    Args:
        active_idx: index ของ step ปัจจุบัน (0-based) — highlight ส้ม
        done_until: index ของ step สุดท้ายที่ทำเสร็จแล้ว (0-based, -1 = ยังไม่เริ่ม)
    """
    pieces = []
    for i, label in enumerate(_STEP_LABELS):
        n = i + 1
        if i <= done_until:
            # ผ่านไปแล้ว — เขียว
            bg = "var(--ink-success, #16a34a)"
            color = "white"
            border = "var(--ink-success, #16a34a)"
            num_html = "&check;"
        elif i == active_idx:
            # อยู่ step นี้ — ส้ม brand
            bg = "var(--ink-orange, #f97316)"
            color = "white"
            border = "var(--ink-orange, #f97316)"
            num_html = str(n)
        else:
            # ยังไม่ถึง — เทา
            bg = "transparent"
            color = "var(--ink-text-muted, #888)"
            border = "var(--ink-border, #ddd)"
            num_html = str(n)

        circle = (
            f"<div style='width:28px;height:28px;border-radius:50%;background:{bg};"
            f"color:{color};border:2px solid {border};display:inline-flex;"
            f"align-items:center;justify-content:center;font-weight:600;font-size:13px;'>"
            f"{num_html}</div>"
        )
        text = (
            f"<span style='margin-left:0.4rem;color:{color if i == active_idx or i <= done_until else 'var(--ink-text-muted, #888)'};"
            f"font-size:13px;font-weight:{'600' if i == active_idx else '400'};'>"
            f"{label}</span>"
        )
        pieces.append(
            f"<div style='display:inline-flex;align-items:center;'>{circle}{text}</div>"
        )
        if i < len(_STEP_LABELS) - 1:
            # connector
            connector_color = (
                "var(--ink-success, #16a34a)" if i < done_until
                else "var(--ink-border, #ddd)"
            )
            pieces.append(
                f"<div style='flex:1;height:2px;background:{connector_color};"
                f"margin:0 0.6rem;min-width:20px;'></div>"
            )

    html = (
        "<div style='display:flex;align-items:center;padding:0.75rem 1rem;"
        "background:var(--ink-surface-2, #f8f8f8);border-radius:var(--ink-radius-md, 8px);"
        "margin-bottom:1rem;'>"
        + "".join(pieces)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _ab_step_state(proofreader, export_files_exist: bool) -> tuple[int, int]:
    """คำนวณ stepper state สำหรับ AB mode → (active_idx, done_until)."""
    has_errors = bool(proofreader.found_errors)
    has_corrections = any(
        e.get('corrected_content') for e in (proofreader.found_errors or [])
    )
    if has_corrections:
        return (4, 3)   # อยู่ step 5 (แก้ไขไฟล์)
    if export_files_exist:
        return (3, 2)   # อยู่ step 4 (นำเข้า)
    if has_errors:
        return (2, 1)   # อยู่ step 3 (ส่งออก)
    if proofreader.normal_mode_stats.get('files', 0) > 0 or has_errors:
        return (1, 0)
    return (1, 0)       # default: อยู่ step 2 (วิเคราะห์)


def _normal_step_state(proofreader, export_files_exist: bool) -> tuple[int, int]:
    """คำนวณ stepper state สำหรับ Normal mode."""
    errors = proofreader.normal_mode_errors or []
    has_errors = bool(errors)
    has_corrections = any(e.get('corrected_content') for e in errors)
    if has_corrections:
        return (4, 3)
    if export_files_exist:
        return (3, 2)
    if has_errors:
        return (2, 1)
    if proofreader.normal_mode_stats.get('files', 0) > 0:
        return (1, 0)
    return (1, 0)


def _ab_export_exists() -> bool:
    """เช็คว่ามีไฟล์ export ใน Import/ หรือ Output/ ของ project ปัจจุบัน"""
    for d in (paths.IMPORT_FIX_DIR, paths.OUTPUT_DIR):
        if d.exists():
            if (d / "import_errors.txt").exists() or (d / "error_trans.txt").exists():
                return True
            if any(d.glob("error_trans_*.txt")):
                return True
    return False


def _normal_export_exists() -> bool:
    """เช็คว่ามีไฟล์ normal_mode export อยู่"""
    for d in (paths.IMPORT_FIX_DIR, paths.OUTPUT_DIR):
        if d.exists():
            if (d / "normal_mode_import.txt").exists() or (d / "normal_mode_errors.txt").exists():
                return True
            if any(d.glob("normal_mode_errors_*.txt")):
                return True
    return False


def render(proofreader, file_processor) -> None:
    """แสดง proof tab ทั้งหมด — มี 3 sub-tabs"""
    tab_ab_mode, tab_normal_mode, tab_multi_folder = st.tabs([
        ":material/compare_arrows: โหมด AB",
        ":material/text_fields: โหมดทั่วไป",
        ":material/folder_copy: ตรวจหลายโฟลเดอร์",
    ])

    with tab_ab_mode:
        # Dynamic stepper — บอก step ปัจจุบันตาม state จริง
        ab_active, ab_done = _ab_step_state(proofreader, _ab_export_exists())
        _render_stepper(ab_active, ab_done)

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
            help="ถ้าไฟล์ในโฟลเดอร์ `0-input` มีเนื้อหา [B] เหมือนกันหลายไฟล์จะแจ้งเตือนใน UI",
            key="ab_check_duplicate_content",
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

        # ===== Missing translation scan (เทียบกับ raw จีนต้นฉบับ) =====
        st.markdown("####  ตรวจหาบรรทัดที่ AI ข้ามแปล")
        check_missing_translation = st.checkbox(
            " ตรวจหาบรรทัดที่ AI ข้ามแปล (เทียบกับ raw)",
            value=ab_mode_prefs.get("check_missing_translation", False),
            help="เปรียบเทียบไฟล์แปลใน `0-input` กับไฟล์ raw จีนต้นฉบับ — "
                 "หาบรรทัด raw ที่ไม่มีใน [A] block ใดๆ (smart matching ด้วย bigram similarity)",
            key="ab_check_missing_translation"
        )
        if check_missing_translation != ab_mode_prefs.get("check_missing_translation", False):
            preferences_manager.set_setting("proofreading_settings", "ab_mode",
                {**ab_mode_prefs, "check_missing_translation": check_missing_translation})
            ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

        raw_dir_path = ab_mode_prefs.get("raw_input_path", str(paths.RAW_INPUT_DIR))
        min_ratio_value = float(ab_mode_prefs.get("missing_min_ratio", 0.7) or 0.7)

        if check_missing_translation:
            raw_dir_input = st.text_input(
                "โฟลเดอร์ raw ต้นฉบับจีน:",
                value=raw_dir_path,
                help="วาง path ของโฟลเดอร์ raw — รองรับ sub folder ซ้อนกัน "
                     f"(default: `{paths.RAW_INPUT_DIR}`)",
                key="ab_raw_dir_input"
            )
            if raw_dir_input.strip() and raw_dir_input != raw_dir_path:
                preferences_manager.set_setting("proofreading_settings", "ab_mode",
                    {**ab_mode_prefs, "raw_input_path": raw_dir_input.strip()})
                ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})
                raw_dir_path = raw_dir_input.strip()
            elif not raw_dir_input.strip():
                raw_dir_path = str(paths.RAW_INPUT_DIR)

            min_ratio_value = st.slider(
                "Threshold การจับคู่ (ต่ำกว่านี้ = นับว่าหาย)",
                min_value=0.5, max_value=0.95, step=0.05,
                value=min_ratio_value,
                help="ต่ำ → จับ missing น้อยลง (ทนต่อ AI paraphrase) | สูง → จับ missing เยอะขึ้น",
                key="ab_missing_min_ratio"
            )
            if min_ratio_value != ab_mode_prefs.get("missing_min_ratio", 0.7):
                preferences_manager.set_setting("proofreading_settings", "ab_mode",
                    {**ab_mode_prefs, "missing_min_ratio": float(min_ratio_value)})
                ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

            st.caption(f"raw dir: `{raw_dir_path}` · ratio: `{min_ratio_value:.2f}`")

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
                help="ตัวอย่าง: 【, 】, , , HP, MP",
                key="ab_exclude_textarea",
            )

            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button(" **บันทึกไฟล์**", width='stretch', key="ab_exclude_save"):
                    try:
                        exclude_file.write_text(new_patterns, encoding='utf-8')
                        st.success(" บันทึก exclude.txt สำเร็จ!")
                        st.toast("บันทึก exclude.txt สำเร็จ!")
                    except Exception as e:
                        st.error(f" เกิดข้อผิดพลาด: {str(e)}")

            with col_btn2:
                if st.button("โหลดรูปแบบใหม่", width='stretch', key="ab_exclude_reload"):
                    try:
                        regex_patterns.reload_patterns()
                        st.success(f"โหลดรูปแบบใหม่สำเร็จ — ตอนนี้มี {len(regex_patterns.ignore_patterns)} รูปแบบ")
                        st.toast(f"โหลด {len(regex_patterns.ignore_patterns)} patterns สำเร็จ!")
                    except Exception as e:
                        st.error(f" เกิดข้อผิดพลาด: {str(e)}")

            with col_btn3:
                if st.button(" **คู่มือการใช้**", width='stretch', key="ab_exclude_guide"):
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

        # ── Settings panel (chunk_lines / fuzzy_threshold) — แสดงค้างไว้เสมอ
        saved_chunk_lines = int(ab_mode_prefs.get("chunk_lines", 500) or 500)
        saved_fuzzy_ratio = float(ab_mode_prefs.get("import_fuzzy_min_ratio", 0.95) or 0.95)

        with st.expander("ตั้งค่าส่งออก / นำเข้า", expanded=True):
            col_setting1, col_setting2 = st.columns(2)
            with col_setting1:
                chunk_lines = st.number_input(
                    "แบ่ง chunk โดยจำนวนบรรทัด (~ ต่อไฟล์) — 0 = ไม่ split",
                    min_value=0, max_value=5000, step=50, value=saved_chunk_lines,
                    help="เขียน master `error_trans.txt` เสมอ + ถ้าตั้ง > 0 จะแบ่งเป็น "
                         "`error_trans_001.txt`, `_002.txt`, ... โดยห้ามตัดกลาง entry และ "
                         "repeat headers ในทุก chunk · ค่า ~500 บรรทัด/file พอดี token AI",
                    key="ab_export_chunk_lines",
                )
                if int(chunk_lines) != saved_chunk_lines:
                    preferences_manager.set_setting("proofreading_settings", "ab_mode",
                        {**ab_mode_prefs, "chunk_lines": int(chunk_lines)})
                    ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

            with col_setting2:
                fuzzy_threshold = st.slider(
                    "Fuzzy threshold (import)",
                    min_value=0.85, max_value=1.00, step=0.01,
                    value=saved_fuzzy_ratio,
                    help="ความเข้มข้นของ fuzzy match ตอน import กลับ — สูง = แม่น (ลด false match), "
                         "ต่ำ = ทนต่อ AI แก้ [A] เปลี่ยนเล็กน้อย · 1.00 = exact match only · "
                         "default 0.95 (แม่นๆ)",
                    key="ab_import_fuzzy_threshold",
                )
                if abs(fuzzy_threshold - saved_fuzzy_ratio) > 1e-6:
                    preferences_manager.set_setting("proofreading_settings", "ab_mode",
                        {**ab_mode_prefs, "import_fuzzy_min_ratio": float(fuzzy_threshold)})
                    ab_mode_prefs = preferences_manager.get_setting("proofreading_settings", "ab_mode", {})

        # Main Action Buttons
        st.markdown("####  การดำเนินการหลัก")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(" **เริ่มวิเคราะห์**", type="primary", width='stretch', key="ab_btn_analyze"):
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

                if check_missing_translation:
                    raw_dir = Path(raw_dir_path).expanduser()
                    with st.spinner(f"กำลังเทียบกับ raw ที่ `{raw_dir}`..."):
                        n_missing = proofreader.scan_missing_translations(
                            raw_dir,
                            min_ratio=float(min_ratio_value),
                        )
                    if n_missing > 0:
                        st.info(f"🔎 พบบรรทัดที่ AI ข้ามแปล: **{n_missing}** บรรทัด")
                    else:
                        st.success("ไม่พบบรรทัดที่ AI ข้ามแปล")

                st.toast("วิเคราะห์เสร็จสิ้น!")

        with col2:
            export_disabled = len(proofreader.found_errors) == 0
            if st.button("**ส่งออกเพื่อแก้ไข**", disabled=export_disabled, width='stretch', key="ab_btn_export"):
                with st.spinner("กำลังส่งออก..."):
                    proofreader.export_errors(chunk_lines=int(chunk_lines))
                st.toast("ส่งออกสำเร็จ!")

        with col3:
            if st.button(" **นำเข้าการแก้ไข**", width='stretch', key="ab_btn_import"):
                # ส่ง threshold เข้าไปด้วย (ถ้าฟังก์ชันรองรับ — backward compat)
                import_signature = inspect.signature(proofreader.grab_and_import_file)
                if "fuzzy_min_ratio" in import_signature.parameters:
                    proofreader.grab_and_import_file(fuzzy_min_ratio=float(fuzzy_threshold))
                else:
                    proofreader.grab_and_import_file()

        # Fix & Clean Actions
        st.markdown("####  การประมวลผลไฟล์")
        col4, col5 = st.columns(2)

        with col4:
            if st.button(" **แก้ไขไฟล์**", width='stretch', key="ab_btn_fix"):
                file_processor.fix_files(proofreader.found_errors)

        with col5:
            if st.button(" **ทำความสะอาดไฟล์**", width='stretch', key="ab_btn_clean"):
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
        # Dynamic stepper เดียวกับ AB mode — UX consistent
        nm_active, nm_done = _normal_step_state(proofreader, _normal_export_exists())
        _render_stepper(nm_active, nm_done)

        st.markdown("""
        <div style="background: var(--ink-surface-tint); padding: 1rem 1.25rem;
                    border-radius: var(--ink-radius-lg);
                    border-left: 4px solid var(--ink-orange);
                    margin-bottom: 1rem; color: var(--ink-text);">
            <h5 style="margin: 0; color: var(--ink-orange-dark);">
                โหมดทั่วไป (สแกนทุกบรรทัด)
            </h5>
            <p style="margin: 0.4rem 0 0 0; color: var(--ink-text-muted); font-size: 0.9em;">
                สำหรับไฟล์ที่ไม่มี [A]/[B] — จับคู่กลับด้วยชื่อไฟล์ + เลขบรรทัด
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
        "Clean (แนะนำ)": paths.CLEAN_DIR,
        "Input": paths.INPUT_DIR,
        "Fix": paths.FIX_DIR
        }

        folder_options = list(preset_folders.keys()) + ["ระบุเส้นทางเอง"]
        default_index = folder_options.index("Clean (แนะนำ)") if "Clean (แนะนำ)" in folder_options else 0

        selected_folder_option = st.selectbox(
        "เลือกโฟลเดอร์ที่ต้องการตรวจสอบ:",
            options=folder_options,
            index=default_index,
            help="เลือกโฟลเดอร์ที่ต้องการสแกนหาอักขระต่างประเทศ",
            key="normal_mode_folder_selection"
        )
        # บันทึกการเลือกโฟลเดอร์
        if selected_folder_option != preferences_manager.get_setting("proofreading_settings", "normal_mode", {}).get("source_folder", "Clean"):
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
                help="รองรับทั้งเส้นทางสัมบูรณ์และสัมพัทธ์",
                key="normal_custom_path_input",
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

        # ── Settings panel (chunk_lines / destination) — แสดงค้างไว้เสมอ
        normal_prefs = preferences_manager.get_setting("proofreading_settings", "normal_mode", {})
        saved_chunk_lines = int(normal_prefs.get("chunk_lines", 500) or 500)
        saved_dest = normal_prefs.get("fix_destination", str(paths.FINISH_DIR))

        with st.expander("ตั้งค่าส่งออก / แก้ไขไฟล์", expanded=True):
            col_setting1, col_setting2 = st.columns(2)
            with col_setting1:
                chunk_lines = st.number_input(
                    "แบ่ง chunk โดยจำนวนบรรทัด (~ ต่อไฟล์) — 0 = ไม่ split",
                    min_value=0, max_value=5000, step=50, value=saved_chunk_lines,
                    help="ค่า ~500 บรรทัด/file พอดี token AI · เขียน master เสมอ + ถ้าตั้ง > 0 "
                         "จะแบ่งเป็น normal_mode_errors_001.txt, _002.txt, ...",
                    key="normal_chunk_lines",
                )
                if int(chunk_lines) != saved_chunk_lines:
                    preferences_manager.set_setting("proofreading_settings", "normal_mode",
                        {**normal_prefs, "chunk_lines": int(chunk_lines)})
                    normal_prefs = preferences_manager.get_setting("proofreading_settings", "normal_mode", {})

            with col_setting2:
                # โฟลเดอร์ปลายทาง — preset ตามสเต็ป pipeline Input → Fix → Clean → Finish
                # ห้ามทำลายไฟล์ต้นทาง — auto suggest step ถัดไปตาม source
                dest_preset_folders = {
                    "Finish": paths.FINISH_DIR,
                    "Clean": paths.CLEAN_DIR,
                    "Fix": paths.FIX_DIR,
                    "Input": paths.INPUT_DIR,
                }

                # Pipeline next-step mapping: source → suggested destination
                _PIPELINE_NEXT = {
                    "Input": "Fix",
                    "Fix": "Clean",
                    "Clean": "Finish",
                }
                suggested_dest = _PIPELINE_NEXT.get(selected_folder_option, "Finish")

                # Label เพิ่ม "(แนะนำ)" บน step ที่ pipeline แนะนำ
                dest_labels = [
                    f"{name} (แนะนำ)" if name == suggested_dest else name
                    for name in dest_preset_folders.keys()
                ]
                # mapping label → folder path
                dest_label_to_path = dict(zip(dest_labels, dest_preset_folders.values()))
                dest_options = dest_labels + ["ระบุเส้นทางเอง"]

                # default index: ใช้ saved_dest ถ้ามี + ตรงกับ preset, ไม่งั้นใช้ suggested
                saved_dest_idx = None
                for i, path in enumerate(dest_preset_folders.values()):
                    if str(path) == saved_dest:
                        saved_dest_idx = i
                        break
                if saved_dest_idx is None:
                    if saved_dest and saved_dest not in [str(p) for p in dest_preset_folders.values()]:
                        # saved = custom path
                        saved_dest_idx = len(dest_options) - 1
                    else:
                        # no saved → ใช้ suggested จาก pipeline
                        suggested_label = f"{suggested_dest} (แนะนำ)"
                        saved_dest_idx = dest_options.index(suggested_label)

                selected_dest_option = st.selectbox(
                    "โฟลเดอร์ปลายทาง (เขียนไฟล์ที่แก้แล้ว):",
                    options=dest_options,
                    index=saved_dest_idx,
                    help=f"Pipeline: Input → Fix → Clean → Finish · ต้นทาง = `{selected_folder_option}` "
                         f"→ แนะนำ `{suggested_dest}` (step ถัดไป)",
                    key="normal_fix_dest_preset",
                )

            if selected_dest_option == "ระบุเส้นทางเอง":
                dest_input = st.text_input(
                    "ระบุเส้นทางโฟลเดอร์ปลายทางเอง:",
                    value=saved_dest if saved_dest not in [str(p) for p in dest_preset_folders.values()] else "",
                    placeholder=f"เช่น {paths.FINISH_DIR}",
                    key="normal_fix_destination_custom",
                )
                if dest_input.strip() and dest_input != saved_dest:
                    preferences_manager.set_setting("proofreading_settings", "normal_mode",
                        {**normal_prefs, "fix_destination": dest_input.strip()})
                    normal_prefs = preferences_manager.get_setting("proofreading_settings", "normal_mode", {})
                destination_dir = Path(dest_input.strip()).expanduser() if dest_input.strip() else paths.FINISH_DIR
            else:
                destination_dir = dest_label_to_path[selected_dest_option]
                if str(destination_dir) != saved_dest:
                    preferences_manager.set_setting("proofreading_settings", "normal_mode",
                        {**normal_prefs, "fix_destination": str(destination_dir)})
                    normal_prefs = preferences_manager.get_setting("proofreading_settings", "normal_mode", {})

            # เตือนถ้าโฟลเดอร์ปลายทาง = โฟลเดอร์ต้นทาง (จะทับไฟล์เดิม)
            if target_path and destination_dir and Path(target_path).resolve() == Path(destination_dir).resolve():
                st.warning(
                    f"โฟลเดอร์ปลายทาง = โฟลเดอร์ต้นทาง (`{destination_dir}`) "
                    "— ไฟล์เดิมจะถูกเขียนทับ! เปลี่ยนโฟลเดอร์ปลายทางเพื่อความปลอดภัย"
                )

        # ── การดำเนินการหลัก (4 ปุ่ม — แสดงเสมอ แบบโหมด AB)
        st.markdown("####  การดำเนินการหลัก")
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)

        has_errors = bool(proofreader.normal_mode_errors)

        with col_act1:
            if st.button(
                " **วิเคราะห์โหมดทั่วไป**",
                type="primary",
                width='stretch',
                key="nm_btn_analyze",
            ):
                with st.spinner("กำลังวิเคราะห์โหมดทั่วไป..."):
                    proofreader.analyze_normal_mode(
                        target_path if target_path else proofreader.normal_mode_source,
                        normal_check_foreign,
                        normal_check_numbers,
                        normal_check_english
                    )
                st.toast("วิเคราะห์โหมดทั่วไปเสร็จสิ้น!")
                # rerun ทันทีให้ UI refresh ค่าใหม่ทั้งหมด (has_errors, stats, summary)
                # — ไม่งั้นปุ่ม "ส่งออก/แก้ไข" + status box ใช้ค่าเก่าจากก่อนกด
                st.rerun()

        with col_act2:
            if st.button(
                " **ส่งออกแก้กลับได้**",
                disabled=not has_errors,
                width='stretch',
                key="nm_btn_export",
            ):
                proofreader.export_normal_mode_errors(chunk_lines=int(chunk_lines))

        with col_act3:
            # เปิดให้กดได้เสมอ — ฟังก์ชันจะตรวจสอบ + แจ้ง user เองถ้ายังไม่ได้วิเคราะห์
            if st.button(
                " **นำเข้าการแก้ไข**",
                width='stretch',
                key="nm_btn_import",
            ):
                proofreader.import_normal_mode_corrections()
                st.rerun()

        with col_act4:
            if st.button(
                " **แก้ไขไฟล์**",
                disabled=not has_errors,
                width='stretch',
                key="nm_btn_fix",
            ):
                proofreader.fix_normal_mode_files(
                    destination_dir=destination_dir,
                    in_place=False,
                )
                st.rerun()

        st.caption(
            "โหมดทั่วไปไม่มี [A] ให้ตรวจ — ระบบจับคู่ด้วย **ชื่อไฟล์ + เลขบรรทัด** ตรงเป๊ะเท่านั้น "
            "(ห้ามแก้บรรทัด `## filename` หรือ `123|` ในไฟล์ export)"
        )

        # ── สรุปผลการสแกน — แสดงเมื่อเคยวิเคราะห์แล้ว
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

        # ── ตารางข้อผิดพลาด + ปุ่ม download CSV (แสดงเมื่อมี errors)
        if has_errors:
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

                st.download_button(
                    label=" ดาวน์โหลด CSV",
                    data=normal_df.to_csv(index=False).encode('utf-8-sig'),
                    file_name="normal_mode_errors.csv",
                    mime="text/csv",
                    width='stretch',
                    key="nm_dl_csv",
                )
            except Exception:
                st.warning(" ไม่สามารถสร้างตารางสรุปได้ โปรดดูข้อมูลดิบด้านล่าง")
                for err in proofreader.normal_mode_errors[:20]:
                    categories = ', '.join(err.get('categories', []))
                    category_text = f" [{categories}]" if categories else ""
                    st.write(f" `{err['file_name']}` บรรทัด {err['line_number']}: {err['line_content']}{category_text}")

        # ── Status box (เหมือนโหมด AB)
        if has_errors:
            st.markdown(f"""
            <div style="background: var(--ink-warn-bg); border: 1px solid var(--ink-warn);
                        padding: 1rem; border-radius: var(--ink-radius-md); margin: 1rem 0;
                        color: var(--ink-text);">
                <h5 style="margin: 0; color: var(--ink-warn);">
                    พบบรรทัดที่ต้องตรวจ {len(proofreader.normal_mode_errors)} รายการ
                </h5>
                <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                    กด <strong>ส่งออกแก้กลับได้</strong> เพื่อสร้าง
                    <code>Output/normal_mode_errors.txt</code> + <code>Import/normal_mode_import.txt</code>
                    แล้วแก้บรรทัด <code>[แก้]</code> ก่อนกด <strong>นำเข้าการแก้ไข</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif stats and stats.get('files', 0) > 0:
            st.markdown("""
            <div style="background: var(--ink-success-bg); border: 1px solid var(--ink-success);
                        padding: 1rem; border-radius: var(--ink-radius-md); margin: 1rem 0;
                        color: var(--ink-text);">
                <h5 style="margin: 0; color: var(--ink-success);">
                    ไม่พบภาษาต่างประเทศ/ตัวเลขตามเงื่อนไขที่เลือก
                </h5>
                <p style="margin: 0.5rem 0 0 0; color: var(--ink-text-muted);">
                    ไฟล์ในโฟลเดอร์ที่ตรวจดูเรียบร้อยแล้ว — เปลี่ยน flag การตรวจหรือเลือกโฟลเดอร์อื่นได้
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
                    เลือกโฟลเดอร์ต้นทาง + เงื่อนไขการตรวจ แล้วกด
                    <strong>วิเคราะห์โหมดทั่วไป</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("คำแนะนำขั้นตอน", expanded=False):
            st.markdown(
                """
                1. **วิเคราะห์โหมดทั่วไป** — ระบบบันทึก (ไฟล์, เลขบรรทัด) ลงหน่วยความจำ
                2. **ส่งออกแก้กลับได้** — เขียน `Output/normal_mode_errors.txt` + `Import/normal_mode_import.txt`
                   (รูปแบบ `[เดิม]` / `[แก้]` — ผู้ใช้แก้บรรทัด `[แก้]` เท่านั้น)
                3. แก้ในไฟล์ `Import/normal_mode_import.txt` หรือส่งให้ AI แก้แล้ววางกลับ `Import/`
                4. **นำเข้าการแก้ไข** — โปรแกรมจับคู่ด้วย (ชื่อไฟล์ + เลขบรรทัด) ตรงเป๊ะ
                5. **แก้ไขไฟล์** — เขียนบรรทัดที่แก้แล้วกลับเข้าไฟล์ต้นฉบับ (หรือเขียนไปยัง Finish/)

                **ข้อควรระวัง:** ห้ามแก้บรรทัด `## filename` หรือ `123|` ในไฟล์ export
                เพราะระบบใช้บรรทัดเหล่านี้จับคู่ — ถ้าผิด ระบบจะข้าม entry นั้นและรายงาน

                **Output ของ project ไหน — ก็ไปลงโฟลเดอร์นั้น** (project ปัจจุบันแสดงในแถบส้มบนสุด)
                """
            )

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

        analyze_multi_btn = st.button(" **วิเคราะห์หลายโฟลเดอร์**", type="primary", width='stretch', key="mf_btn_analyze")

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
            if st.button("บันทึกผลและเปลี่ยนชื่อโฟลเดอร์", type="primary", width='stretch', key="mf_btn_rename"):
                proofreader.export_multiple_folders_errors()

            st.markdown("""
            ####  คำอธิบาย
            - เมื่อกด **"บันทึกผลและเปลี่ยนชื่อโฟลเดอร์"** จะทำการ:
              - เปลี่ยนชื่อโฟลเดอร์เป็น **`w ชื่อโฟลเดอร์`** ถ้าพบ errors
              - เปลี่ยนชื่อโฟลเดอร์เป็น **`c ชื่อโฟลเดอร์`** ถ้าไม่พบ errors (clean)
              - บันทึกไฟล์ **`errors-[จำนวน].txt`** ในโฟลเดอร์ที่มี errors
              """)

        # Files Tab (รวม Merge และ Separate)

