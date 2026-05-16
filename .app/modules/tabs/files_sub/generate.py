"""tabs/files_sub/generate.py — สร้างไฟล์ .txt เปล่าสำหรับเตรียมเขียน

STEP-based UX: ตั้งชื่อไฟล์ → จำนวน → เนื้อหา option → ปลายทาง → preview → กดสร้าง
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths
from modules.preferences_manager import preferences_manager
from . import _helpers as h


def render(file_processor) -> None:
    """สร้างไฟล์เปล่า tab — สร้าง template หลายๆ ไฟล์พร้อมกัน"""
    st.markdown(
        '<div style="margin-bottom:0.6rem;color:var(--ink-text-muted);font-size:0.95em;">'
        'สร้างไฟล์ .txt เปล่าหลายๆ ไฟล์พร้อมกัน เผื่อเตรียมเขียน เช่น '
        '<code>Chapter_0001.txt</code> ถึง <code>Chapter_0010.txt</code>'
        '</div>',
        unsafe_allow_html=True,
    )

    prefs = preferences_manager.get_setting("file_processing", "generate_settings", {}) or {}

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "ตั้งชื่อไฟล์")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        file_prefix = st.text_input(
            "คำนำหน้า",
            value=prefs.get("file_prefix", "Chapter "),
            help="เช่น Chapter_ → Chapter_0001.txt",
            key="gen_prefix",
        )
    with col_b:
        number_padding = st.number_input(
            "เลขนำหน้า (padding)",
            min_value=1, max_value=6,
            value=int(prefs.get("number_padding", 4)),
            help="4 = 0001, 0002, ... (ค่าแนะนำ)",
            key="gen_pad",
        )
    with col_c:
        file_suffix = st.text_input(
            "คำต่อท้าย (ไม่บังคับ)",
            value=prefs.get("file_suffix", ""),
            help="เช่น _draft → Chapter_0001_draft.txt",
            key="gen_suffix",
        )

    # ───────────── ขั้นที่ 2 ─────────────
    h.step_header(2, "จำนวนไฟล์ที่จะสร้าง")
    col_d, col_e = st.columns(2)
    with col_d:
        start_number = st.number_input(
            "เริ่มที่เลข",
            min_value=1, max_value=99999,
            value=int(prefs.get("start_number", 1)),
            help="เลขแรก เช่น 1 → Chapter_0001",
            key="gen_start",
        )
    with col_e:
        batch_size = st.number_input(
            "สร้างทั้งหมดกี่ไฟล์",
            min_value=1, max_value=500,
            value=int(prefs.get("batch_size", 10)),
            help="จำนวนไฟล์ที่จะสร้าง (สูงสุด 500 ไฟล์)",
            key="gen_batch",
        )

    end_number = start_number + batch_size - 1
    st.caption(f"จะสร้างไฟล์เลขที่ **{start_number}** ถึง **{end_number}** (รวม **{batch_size:,}** ไฟล์)")

    # ── ตัวเลือกขั้นสูง — ใส่ชื่อตอนในบรรทัดแรก
    add_chapter_title = False
    use_filename_as_title = True
    chapter_title_template = ""
    with st.expander("ตัวเลือกขั้นสูง (ใส่ชื่อตอนเป็นบรรทัดแรกในไฟล์)", expanded=False):
        add_chapter_title = st.checkbox(
            "ใส่ชื่อตอนในบรรทัดแรกของแต่ละไฟล์",
            value=bool(prefs.get("add_chapter_title", False)),
            help="ติ๊กถ้าต้องการให้ระบบใส่ชื่อตอนเป็นบรรทัดแรก เว้นบรรทัด พร้อมพิมพ์เนื้อหา · "
                 "ส่วนใหญ่ไม่ต้องใช้ ถ้าจะพิมพ์เอง",
            key="gen_add_title",
        )

        if add_chapter_title:
            title_mode = st.radio(
                "รูปแบบชื่อตอน:",
                options=["ใช้ชื่อไฟล์เป็นชื่อตอน", "กำหนดเอง"],
                index=0 if prefs.get("use_filename_as_title", True) else 1,
                horizontal=True,
                key="gen_title_mode",
            )
            use_filename_as_title = (title_mode == "ใช้ชื่อไฟล์เป็นชื่อตอน")

            if not use_filename_as_title:
                chapter_title_template = st.text_input(
                    "รูปแบบชื่อตอน (เลขจะถูกต่อท้าย)",
                    value=prefs.get("chapter_title_template", ""),
                    placeholder="เช่น 'ตอนที่ '",
                    help="เช่น 'ตอนที่ ' → ตอนที่ 0001, ตอนที่ 0002, ...",
                    key="gen_title_tpl",
                )

    # ───────────── ขั้นที่ 4 ─────────────
    h.step_header(4, "เลือกโฟลเดอร์ปลายทาง",
                  "ไฟล์ใหม่จะถูกสร้างไว้ที่นี่")
    dest_path, _ = h.folder_select(
        "โฟลเดอร์ปลายทาง:",
        key="gen_dest",
        presets=["Input", "Fix", "Clean"],
        suggested="Input",
        help="ค่าแนะนำคือ Input — โฟลเดอร์เริ่มต้นของ pipeline แปล",
        saved_value=prefs.get("dest_folder"),
        show_count=False,
    )

    # บันทึก settings
    new_settings = {
        "file_prefix": file_prefix,
        "file_suffix": file_suffix,
        "number_padding": int(number_padding),
        "start_number": int(start_number),
        "batch_size": int(batch_size),
        "add_chapter_title": add_chapter_title,
        "use_filename_as_title": use_filename_as_title,
        "chapter_title_template": chapter_title_template,
        "dest_folder": str(dest_path) if dest_path else "",
    }
    if new_settings != prefs:
        preferences_manager.set_setting("file_processing", "generate_settings", new_settings)

    # ───────────── PREVIEW ─────────────
    st.markdown("---")
    preview_names = h.gen_filenames_preview(file_prefix, int(number_padding),
                                            file_suffix, int(start_number), int(batch_size))
    h.filename_preview(preview_names, total=batch_size,
                       title=f"ชื่อไฟล์ที่จะสร้าง")

    # ตัวอย่างเนื้อหา
    if add_chapter_title:
        if use_filename_as_title:
            example_title = f"{file_prefix}{str(start_number).zfill(int(number_padding))}{file_suffix}"
        else:
            example_title = f"{chapter_title_template}{str(start_number).zfill(int(number_padding))}"
        example_content = f"{example_title}\n\n[...เขียนเนื้อหาที่นี่...]"
    else:
        example_content = "[ไฟล์ว่างเปล่า — พร้อมพิมพ์เนื้อหา]"
    h.content_preview(example_content, title="ตัวอย่างเนื้อหาในแต่ละไฟล์")

    # ───────────── Action ─────────────
    st.markdown("---")
    can_generate = bool(dest_path and file_prefix.strip())
    if st.button(" **สร้างไฟล์**", type="primary", width='stretch',
                 disabled=not can_generate, key="gen_btn_run"):
        with st.spinner(f"กำลังสร้าง {batch_size} ไฟล์..."):
            dest_path.mkdir(parents=True, exist_ok=True)
            created, skipped, errors = [], [], []
            for i in range(start_number, start_number + batch_size):
                filename = f"{file_prefix}{str(i).zfill(int(number_padding))}{file_suffix}.txt"
                file_path = dest_path / filename
                if file_path.exists():
                    skipped.append(filename)
                    continue
                try:
                    content = ""
                    if add_chapter_title:
                        if use_filename_as_title:
                            chap_title = f"{file_prefix}{str(i).zfill(int(number_padding))}{file_suffix}"
                        else:
                            chap_title = f"{chapter_title_template}{str(i).zfill(int(number_padding))}"
                        content = f"{chap_title}\n\n"
                    file_path.write_text(content, encoding='utf-8')
                    created.append(filename)
                except Exception as e:
                    errors.append((filename, str(e)))

        # ผลลัพธ์
        if created:
            st.success(f"สร้างไฟล์สำเร็จ {len(created):,} ไฟล์")
            if len(created) <= 10:
                for n in created:
                    st.write(f"`{n}`")
            else:
                st.write(f"`{created[0]}` ถึง `{created[-1]}`")
            st.toast(f"สร้าง {len(created)} ไฟล์สำเร็จ")
        if skipped:
            st.warning(f"ข้าม {len(skipped)} ไฟล์ที่มีอยู่แล้ว: {', '.join(f'`{n}`' for n in skipped[:5])}"
                       + (f" ... และอีก {len(skipped)-5}" if len(skipped) > 5 else ""))
        if errors:
            st.error(f"สร้างไม่สำเร็จ {len(errors)} ไฟล์:")
            for n, e in errors[:5]:
                st.write(f"- `{n}`: {e}")
