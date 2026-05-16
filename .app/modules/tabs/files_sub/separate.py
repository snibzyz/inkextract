"""tabs/files_sub/separate.py — แยกไฟล์ใหญ่ที่รวมหลายตอน เป็นไฟล์ตอนละไฟล์

STEP-based UX: เลือกไฟล์ → กำหนดจุดแยก → ตั้งชื่อไฟล์ → ปลายทาง → preview → กดแยก
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths
from modules.preferences_manager import preferences_manager
from . import _helpers as h


def render(separate_processor, file_processor) -> None:
    """แยกไฟล์ tab — แยกไฟล์ใหญ่ที่รวมหลายตอนเป็นไฟล์ตอนละไฟล์"""
    st.markdown(
        '<div style="margin-bottom:0.6rem;color:var(--ink-text-muted);font-size:0.95em;">'
        'แยกไฟล์ใหญ่ที่มีหลายตอนรวมกัน → ได้ไฟล์ตอนละไฟล์ เช่น '
        '<code>Chapter_001-100.txt</code> → <code>0001.txt</code>, <code>0002.txt</code>, ...'
        '</div>',
        unsafe_allow_html=True,
    )

    prefs = preferences_manager.get_setting("file_processing", "separate_settings", {}) or {}

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "เลือกไฟล์ที่จะแยก", "อัปโหลดไฟล์ใหญ่ที่รวมหลายตอน")
    uploaded_files = st.file_uploader(
        "เลือกไฟล์ .txt (เลือกได้หลายไฟล์)",
        type=['txt'],
        accept_multiple_files=True,
        key="sep_upload",
        help="ลากไฟล์มาวาง หรือกด Browse เพื่อเลือกไฟล์จากเครื่อง",
    )
    if uploaded_files:
        st.caption(f"อัปโหลดแล้ว **{len(uploaded_files)}** ไฟล์ — "
                   f"รวม {sum(f.size for f in uploaded_files):,} bytes")

    # ───────────── ขั้นที่ 2 ─────────────
    h.step_header(2, "บอกระบบว่า 'จุดเริ่มตอนใหม่' คือบรรทัดแบบไหน",
                  "ระบบจะตัดไฟล์ทุกครั้งที่เจอบรรทัดขึ้นต้นด้วยตัวอักษรนี้")

    use_focus = st.checkbox(
        "ใช้เครื่องหมายแยกตอน",
        value=bool(prefs.get("focus_keyword", "").strip()),
        help="ติ๊กเมื่อต้องการให้ระบบแยกตอนตามเครื่องหมายที่กำหนด · ค่าเริ่มต้น: ไม่ติ๊ก (ต้องเปิดเองก่อนใช้)",
        key="sep_use_focus",
    )

    if use_focus:
        col_a, col_b = st.columns([2, 3])
        with col_a:
            focus_keyword = st.text_input(
                "เครื่องหมายขึ้นตอนใหม่",
                value=prefs.get("focus_keyword", "") or "###",
                help="เช่น '###' หมายถึงบรรทัดที่ขึ้นต้นด้วย ### = จุดเริ่มตอนใหม่",
                key="sep_focus",
            )
        with col_b:
            st.markdown(
                '<div style="background:var(--ink-surface-tint);padding:0.55rem 0.8rem;'
                'border-radius:0.4rem;font-size:0.85em;color:var(--ink-text-muted);'
                'margin-top:1.5rem;">'
                f'<b>ตัวอย่าง:</b> ถ้าใส่ <code>{focus_keyword or "###"}</code> ระบบจะแยกตรงบรรทัดเช่น '
                f'<code>{focus_keyword or "###"} ตอนที่ 1</code>, <code>{focus_keyword or "###"} ตอนที่ 2</code>'
                '</div>',
                unsafe_allow_html=True,
            )
    else:
        focus_keyword = ""
        st.caption("ติ๊กข้างบนเพื่อเปิดใช้เครื่องหมายแยกตอน — ไม่งั้นกดเริ่มไม่ได้")

    # ── ตัวเลือกขั้นสูง — ลบข้อความปิดท้ายตอน
    with st.expander("ตัวเลือกขั้นสูง (ลบ end credit เช่น 'จบตอน')", expanded=False):
        strip_end_credit = st.checkbox(
            "ลบข้อความปิดท้ายตอนออกจากแต่ละตอน",
            value=bool(prefs.get("strip_end_credit", False)),
            help="ติ๊กถ้าต้องการให้ระบบลบบรรทัดเช่น 'จบตอน' ที่อยู่ท้ายตอน · "
                 "ส่วนใหญ่ไม่ต้องใช้ ถ้าไฟล์ไม่มี end credit",
            key="sep_strip",
        )
        end_credit_text = st.text_input(
            "ข้อความที่จะลบ (เช่น จบตอน)",
            value=prefs.get("end_credit_text", ""),
            disabled=not strip_end_credit,
            help="ระบุข้อความที่อยู่ท้ายแต่ละตอนที่ต้องการลบออก",
            key="sep_end_credit",
        )

    # ───────────── ขั้นที่ 3 ─────────────
    h.step_header(3, "ตั้งชื่อไฟล์ตอนใหม่")
    col_e, col_f, col_g = st.columns(3)
    with col_e:
        title_prefix = st.text_input(
            "คำนำหน้า",
            value=prefs.get("title_prefix", "Chapter "),
            help="เช่น Chapter_ → Chapter_0001.txt",
            key="sep_prefix",
        )
    with col_f:
        chapter_padding = st.number_input(
            "เลขนำหน้า (padding)",
            min_value=1, max_value=6,
            value=int(prefs.get("chapter_padding", 4)),
            help="4 = 0001, 0002, ... (ค่าแนะนำ)",
            key="sep_pad",
        )
    with col_g:
        start_number = st.number_input(
            "เริ่มที่เลข",
            min_value=1, max_value=99999,
            value=int(prefs.get("start_number", 1)),
            help="เลขแรกของไฟล์ใหม่ เช่น 1 → Chapter_0001",
            key="sep_start",
        )

    title_suffix = st.text_input(
        "คำต่อท้าย (ไม่บังคับ)",
        value=prefs.get("title_suffix", ""),
        help="เช่น _v1 → Chapter_0001_v1.txt",
        key="sep_suffix",
    )

    # บันทึก settings
    new_settings = {
        "focus_keyword": focus_keyword,
        "strip_end_credit": strip_end_credit,
        "end_credit_text": end_credit_text,
        "title_prefix": title_prefix,
        "chapter_padding": int(chapter_padding),
        "start_number": int(start_number),
        "title_suffix": title_suffix,
    }
    if new_settings != prefs:
        preferences_manager.set_setting("file_processing", "separate_settings",
            {**prefs, **new_settings})

    # ───────────── ขั้นที่ 4 ─────────────
    h.step_header(4, "เลือกโฟลเดอร์ปลายทาง",
                  "ไฟล์ตอนใหม่จะถูกสร้างไว้ที่นี่")
    dest_path, _ = h.folder_select(
        "โฟลเดอร์ปลายทาง:",
        key="sep_dest",
        presets=["Separate", "Input", "Fix", "Clean"],
        suggested="Separate",
        help="ค่าแนะนำคือ Separate — โฟลเดอร์สำหรับเก็บไฟล์ที่แยกแล้ว",
        saved_value=prefs.get("dest_folder"),
        show_count=False,
    )
    if dest_path and str(dest_path) != prefs.get("dest_folder"):
        preferences_manager.set_setting("file_processing", "separate_settings",
            {**prefs, **new_settings, "dest_folder": str(dest_path)})

    # ───────────── PREVIEW ─────────────
    st.markdown("---")
    if uploaded_files:
        # อ่าน upload + ตัด section ตาม focus_keyword
        total_sections = 0
        all_sections: list = []   # list of section bodies (string)
        for uf in uploaded_files:
            try:
                pos = uf.tell()
                content = uf.read().decode('utf-8', errors='replace')
                uf.seek(pos)

                # ตัดเป็น sections ตาม focus_keyword
                if focus_keyword:
                    cur_section = []
                    for line in content.splitlines():
                        if line.lstrip().startswith(focus_keyword):
                            if cur_section:
                                all_sections.append("\n".join(cur_section))
                                cur_section = []
                        cur_section.append(line)
                    if cur_section:
                        all_sections.append("\n".join(cur_section))
                else:
                    all_sections.append(content)
            except Exception:
                continue

        total_sections = len(all_sections) if all_sections else 1

        # preview filenames (6 ตัวแรก + expander ทั้งหมด)
        preview_names = []
        all_names = []
        for i in range(total_sections):
            n = start_number + i
            name = f"{title_prefix}{str(n).zfill(chapter_padding)}{title_suffix}.txt"
            all_names.append(name)
            if i < 6:
                preview_names.append(name)
        h.filename_preview(preview_names, total=total_sections,
                           title=f"คาดว่าจะสร้าง {total_sections:,} ไฟล์ตอน",
                           all_filenames=all_names)

        # preview content — 3 ไฟล์แรก ไฟล์ละ 3 บรรทัด
        preview_lines = []
        for idx, section in enumerate(all_sections[:3]):
            chap_n = start_number + idx
            fname = f"{title_prefix}{str(chap_n).zfill(chapter_padding)}{title_suffix}.txt"
            preview_lines.append(f"━━━ {fname} ━━━")
            lines = section.splitlines()[:3]
            if strip_end_credit and end_credit_text and lines and lines[-1].strip() == end_credit_text.strip():
                lines = lines[:-1]
            preview_lines.extend(lines)
            preview_lines.append("")

        if preview_lines:
            h.content_preview("\n".join(preview_lines),
                              title=f"ตัวอย่างเนื้อหา (3 ไฟล์แรก ไฟล์ละ 3 บรรทัด)",
                              max_lines=len(preview_lines))
    else:
        st.info("ยังไม่ได้อัปโหลดไฟล์ — กลับไปขั้นที่ 1 เพื่อเลือกไฟล์")

    # ───────────── Action ─────────────
    st.markdown("---")
    can_separate = bool(uploaded_files and dest_path and focus_keyword.strip())
    if st.button(" **เริ่มแยกไฟล์**", type="primary", width='stretch',
                 disabled=not can_separate, key="sep_btn_run"):
        with st.spinner("กำลังแยกไฟล์..."):
            # ส่ง dest_path เข้าไปผ่าน processor (TODO: อาจต้องเพิ่ม param ใน separate_processor)
            # ตอนนี้ separate_files ไม่รับ output folder → ใช้ค่า default (Separate)
            # ถ้า dest_path != Separate ให้ย้ายไฟล์หลังจาก separate เสร็จ
            results = separate_processor.separate_files(
                uploaded_files=uploaded_files,
                focus_keyword=focus_keyword,
                title_prefix=title_prefix,
                title_suffix=title_suffix,
                chapter_number_padding=int(chapter_padding),
                start_number=int(start_number),
                strip_end_credit=strip_end_credit,
                end_credit_text=end_credit_text,
            )

            # ย้ายไฟล์ไป dest_path ถ้าไม่ใช่ Separate default
            from pathlib import Path as _P
            default_dest = paths.SEPARATE_DIR
            if dest_path and _P(dest_path).resolve() != default_dest.resolve():
                dest_path.mkdir(parents=True, exist_ok=True)
                for res in results:
                    for src_file in res.get('created_files', []):
                        try:
                            target = dest_path / _P(src_file).name
                            _P(src_file).replace(target)
                        except Exception as e:
                            st.warning(f"ย้าย `{_P(src_file).name}` ไม่ได้: {e}")

        if results:
            total_created = sum(r.get('sections', 0) for r in results)
            st.success(f"แยกไฟล์สำเร็จ — สร้าง {total_created:,} ไฟล์ตอน "
                       f"จาก {len(results)} ไฟล์ต้นทาง")
            for r in results[:5]:
                st.write(f"`{r['filename']}` → {r['sections']} ตอน")
            st.toast(f"แยก {total_created} ไฟล์สำเร็จ")
        else:
            st.error("แยกไม่สำเร็จ — กรุณาตรวจสอบเครื่องหมายหัวบท")
