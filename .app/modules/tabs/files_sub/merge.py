"""tabs/files_sub/merge.py — รวมหลายตอนเป็นไฟล์เดียว/หลายไฟล์

STEP-based UX: เลือกต้นทาง → ตั้งค่า → ปลายทาง → preview → กดรวม
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths
from modules.preferences_manager import preferences_manager
from . import _helpers as h


def render(merge_processor, file_processor) -> None:
    """รวมไฟล์ tab — เอาหลายตอนมาต่อกัน"""
    st.markdown(
        '<div class="ink-section-hint">'
        'เอาไฟล์ตอนหลายไฟล์ในโฟลเดอร์มาต่อกัน → ได้ไฟล์รวม เช่น '
        '<code>001.txt</code> + <code>002.txt</code> + ... → <code>Chapter_0001-0005.txt</code>'
        '</div>',
        unsafe_allow_html=True,
    )

    # โหลด preferences
    prefs = preferences_manager.get_setting("file_processing", "merge_settings", {}) or {}

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "เลือกไฟล์ต้นทาง",
                  "โฟลเดอร์ที่มีไฟล์ตอนเล็กๆ ที่ต้องการรวม")
    source_path, source_label = h.folder_select(
        "โฟลเดอร์ต้นทาง:",
        key="merge_src",
        presets=["Clean", "Fix", "Input", "Output"],
        suggested="Clean",
        help="โฟลเดอร์ที่มีไฟล์ตอนเล็กๆ ที่จะรวม · ค่าเริ่มต้น = Clean",
        saved_value=prefs.get("source_folder"),
    )
    if source_path and str(source_path) != prefs.get("source_folder"):
        preferences_manager.set_setting("file_processing", "merge_settings",
            {**prefs, "source_folder": str(source_path)})
        prefs = preferences_manager.get_setting("file_processing", "merge_settings", {}) or {}

    # หา list ของไฟล์
    chapter_files = []
    if source_path and source_path.exists():
        chapter_files = merge_processor.get_available_files(source_path)
    total_chapters = len(chapter_files)

    # เลือกไฟล์เฉพาะ
    selected_files = None
    if total_chapters > 0:
        pick_specific = st.checkbox(
            "เลือกไฟล์เฉพาะ (ค่าเริ่มต้น: รวมทั้งหมด)",
            value=False,
            key="merge_pick_specific",
        )
        if pick_specific:
            file_options = [f"{f.name} ({f.stat().st_size:,} bytes)" for f in chapter_files]
            picked_idx = st.multiselect(
                "เลือกไฟล์ที่ต้องการรวม:",
                options=range(len(chapter_files)),
                format_func=lambda i: file_options[i],
                key="merge_picked_files",
            )
            if picked_idx:
                selected_files = [chapter_files[i] for i in picked_idx]
                st.caption(f"เลือกแล้ว **{len(selected_files):,}** ไฟล์")
            else:
                st.warning("ยังไม่ได้เลือกไฟล์ใดๆ")

    # ───────────── ขั้นที่ 2 ─────────────
    h.step_header(2, "ตั้งค่าวิธีรวม",
                  "กำหนดจำนวนตอนต่อไฟล์ + รูปแบบหัวบท + ชื่อไฟล์ปลายทาง")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        chapters_per_file = st.number_input(
            "ตอนต่อไฟล์ (0 = รวมเป็นไฟล์เดียว)",
            min_value=0, max_value=200,
            value=int(prefs.get("chapters_per_file", 0)),
            help="ค่าเริ่มต้น = 0 (รวมทุกตอนเป็นไฟล์เดียว) · ถ้าใส่ 5 → จะได้ไฟล์ละ 5 ตอน",
            key="merge_cpf",
        )
    with col_b:
        chapter_padding = st.number_input(
            "เลขนำหน้า (padding)",
            min_value=1, max_value=6,
            value=int(prefs.get("chapter_padding", 4)),
            help="จำนวนหลักของเลขตอน · 4 = 0001, 0002, ... (ค่าแนะนำ)",
            key="merge_pad",
        )
    with col_c:
        start_number = st.number_input(
            "เริ่มที่เลข",
            min_value=1, max_value=99999,
            value=int(prefs.get("start_number", 1)),
            help="เลขแรกของไฟล์รวม เช่น 1 → Chapter_0001",
            key="merge_start",
        )

    col_d, col_e = st.columns(2)
    with col_d:
        title_prefix = st.text_input(
            "คำนำหน้าชื่อไฟล์",
            value=prefs.get("title_prefix", "Chapter "),
            help="เช่น Chapter_ → Chapter_0001.txt",
            key="merge_prefix",
        )
    with col_e:
        title_suffix = st.text_input(
            "คำต่อท้ายชื่อไฟล์ (ไม่บังคับ)",
            value=prefs.get("title_suffix", ""),
            help="เช่น _v1 → Chapter_0001_v1.txt",
            key="merge_suffix",
        )

    # ── ตัวเลือกขั้นสูง (พับไว้) — ส่วนใหญ่ไม่จำเป็นต้องแก้
    with st.expander("ตัวเลือกขั้นสูง (เพิ่มหัวบทอัตโนมัติ / end credit)", expanded=False):
        col_f, col_g = st.columns(2)
        with col_f:
            add_chapter_heading = st.checkbox(
                "เพิ่มหัวบทใหม่อัตโนมัติก่อนเนื้อหาทุกตอน",
                value=bool(prefs.get("add_chapter_heading", False)),
                help="ตัวอย่าง: ถ้าติ๊ก จะมี '### Chapter 0001' ใส่บนทุกตอนในไฟล์รวม "
                     "(ใช้เครื่องหมาย + คำนำหน้าด้านล่าง) · ค่าเริ่มต้น: ไม่ติ๊ก (เพราะไฟล์เดิมมักมีหัวบทอยู่แล้ว)",
                key="merge_add_heading",
            )
            focus_keyword = st.text_input(
                "เครื่องหมายหัวบท (ใช้เมื่อติ๊กด้านบน)",
                value=prefs.get("focus_keyword", ""),
                help="เช่น '###' → ผลคือ '### Chapter 0001' บนแต่ละตอน · ปล่อยว่าง = ไม่ใส่เครื่องหมาย",
                key="merge_focus",
                disabled=not add_chapter_heading,
            )
        with col_g:
            add_filename_separator = st.checkbox(
                "ใส่ชื่อไฟล์เดิมเป็นตัวคั่นระหว่างตอน",
                value=bool(prefs.get("add_filename_separator", False)),
                help="แสดงชื่อไฟล์เดิม (เช่น <001.txt>) ก่อนเนื้อหา เพื่อรู้ว่าตอนไหนมาจากไฟล์ใด · "
                     "ส่วนใหญ่ไม่ต้องใช้",
                key="merge_add_filename",
            )
            end_credit = st.text_input(
                "ข้อความปิดท้ายแต่ละตอน",
                value=prefs.get("end_credit", ""),
                help="เช่น 'จบตอน' จะถูกใส่ท้ายทุกตอน · ปล่อยว่าง = ไม่ใส่อะไร · "
                     "ค่าเริ่มต้น: ไม่ใส่",
                key="merge_end_credit",
            )

    # บันทึก settings
    new_settings = {
        "source_folder": str(source_path) if source_path else "",
        "chapters_per_file": int(chapters_per_file),
        "chapter_padding": int(chapter_padding),
        "start_number": int(start_number),
        "title_prefix": title_prefix,
        "title_suffix": title_suffix,
        "focus_keyword": focus_keyword,
        "end_credit": end_credit,
        "add_chapter_heading": add_chapter_heading,
        "add_filename_separator": add_filename_separator,
    }
    if new_settings != prefs:
        preferences_manager.set_setting("file_processing", "merge_settings", new_settings)

    # ───────────── ขั้นที่ 3 ─────────────
    h.step_header(3, "เลือกโฟลเดอร์ปลายทาง",
                  "ไฟล์รวมจะถูกเขียนลงโฟลเดอร์นี้ — ไฟล์ต้นทางคงเดิม")
    dest_path, _ = h.folder_select(
        "โฟลเดอร์ปลายทาง:",
        key="merge_dest",
        presets=["Merge", "Finish", "Clean", "Fix"],
        suggested="Merge",
        help="ค่าแนะนำคือ Merge — โฟลเดอร์สำหรับเก็บไฟล์ที่รวมแล้ว",
        saved_value=prefs.get("dest_folder"),
        show_count=False,
    )
    if dest_path and str(dest_path) != prefs.get("dest_folder"):
        preferences_manager.set_setting("file_processing", "merge_settings",
            {**new_settings, "dest_folder": str(dest_path)})

    # เตือนทับ
    if source_path and dest_path and source_path.resolve() == dest_path.resolve():
        st.warning(f"โฟลเดอร์ปลายทาง = โฟลเดอร์ต้นทาง (`{dest_path}`) — ไฟล์เดิมจะถูกเขียนทับ!")

    # ───────────── PREVIEW ─────────────
    st.markdown("---")
    files_to_merge = len(selected_files) if selected_files else total_chapters
    if files_to_merge > 0:
        est_files = 1 if chapters_per_file == 0 else (files_to_merge + chapters_per_file - 1) // chapters_per_file

        # generate preview filenames
        preview_names = []
        if chapters_per_file == 0:
            n = start_number
            preview_names.append(f"{title_prefix}{str(n).zfill(chapter_padding)}{title_suffix}.txt")
        else:
            for i in range(min(est_files, 6)):
                n_from = start_number + i * chapters_per_file
                n_to = n_from + chapters_per_file - 1
                preview_names.append(
                    f"{title_prefix}{str(n_from).zfill(chapter_padding)}-"
                    f"{str(n_to).zfill(chapter_padding)}{title_suffix}.txt"
                )
        h.filename_preview(preview_names, total=est_files,
                           title=f"{files_to_merge:,} ไฟล์ต้นทาง → {est_files:,} ไฟล์รวม")

        # content preview — อ่าน 3 ไฟล์แรก ไฟล์ละ 3 บรรทัด
        first_files = (selected_files or chapter_files)[:3]
        preview_lines = []
        for idx, f in enumerate(first_files):
            chap_n = start_number + idx
            heading_text = f"{focus_keyword} {title_prefix}{str(chap_n).zfill(chapter_padding)}{title_suffix}".strip()
            if add_chapter_heading:
                preview_lines.append(heading_text)
            if add_filename_separator:
                preview_lines.append(f"<{f.name}>")
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                snippet = content.strip().splitlines()[:3]
                preview_lines.extend(snippet)
            except Exception:
                preview_lines.append("(อ่านไฟล์ไม่ได้)")
            if end_credit:
                preview_lines.append(end_credit)
            preview_lines.append("")
        if preview_lines:
            h.content_preview("\n".join(preview_lines),
                              title=f"ตัวอย่างเนื้อหา (จำลองจาก {len(first_files)} ตอนแรก ตอนละ 3 บรรทัด)",
                              max_lines=len(preview_lines))
    else:
        st.info("ยังไม่มีไฟล์ในโฟลเดอร์ต้นทาง — กรุณาเลือกโฟลเดอร์อื่น หรือใส่ไฟล์ในโฟลเดอร์นี้ก่อน")

    # ───────────── Action ─────────────
    st.markdown("---")
    can_merge = bool(source_path and source_path.exists() and dest_path and files_to_merge > 0)
    if st.button(" **เริ่มรวมไฟล์**", type="primary", width='stretch',
                 disabled=not can_merge, key="merge_btn_run"):
        with st.spinner("กำลังรวมไฟล์..."):
            created = merge_processor.merge_output(
                chapters_per_file=int(chapters_per_file),
                end_credit=end_credit,
                focus_keyword=focus_keyword,
                title_prefix=title_prefix,
                title_suffix=title_suffix,
                chapter_number_padding=int(chapter_padding),
                start_number=int(start_number),
                source_path=source_path,
                add_filename_separator=add_filename_separator,
                add_chapter_heading=add_chapter_heading,
                output_folder=dest_path,
                selected_files=selected_files,
            )
        if created:
            st.success(f"รวมไฟล์สำเร็จ — สร้าง {len(created)} ไฟล์")
            for p in created:
                st.write(f"`{p.name}`")
            st.toast(f"รวม {len(created)} ไฟล์สำเร็จ")
        else:
            st.error("รวมไม่สำเร็จ — กรุณาตรวจสอบ log")
