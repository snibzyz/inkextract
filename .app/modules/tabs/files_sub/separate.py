"""tabs/files_sub/separate.py — แยกไฟล์ใหญ่ที่รวมหลายตอน เป็นไฟล์ตอนละไฟล์

STEP-based UX: เลือกไฟล์ → กำหนดจุดแยก → ตั้งชื่อไฟล์ → ปลายทาง → preview → กดแยก
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths
from modules.preferences_manager import preferences_manager
from . import _helpers as h


class _LocalFileShim:
    """Wrapper รอบ Path ให้มี interface เหมือน UploadedFile ของ Streamlit
    (.name, .size, .read(), .tell(), .seek())

    ใช้ตอนที่ user เลือก "เลือกจากโฟลเดอร์" — แทนที่จะ upload ผ่าน file_uploader
    เราหยิบ Path มาห่อให้ใช้กับ separate_processor.separate_files() ได้เลย
    """
    __slots__ = ('_path', 'name', 'size', '_pos')

    def __init__(self, path: Path):
        self._path = path
        self.name = path.name
        try:
            self.size = path.stat().st_size
        except OSError:
            self.size = 0
        self._pos = 0

    def read(self) -> bytes:
        with open(self._path, 'rb') as f:
            f.seek(self._pos)
            data = f.read()
        return data

    def tell(self) -> int:
        return self._pos

    def seek(self, p: int) -> None:
        self._pos = p


def render(separate_processor, file_processor) -> None:
    """แยกไฟล์ tab — แยกไฟล์ใหญ่ที่รวมหลายตอนเป็นไฟล์ตอนละไฟล์"""
    st.markdown(
        '<div class="ink-section-hint">'
        'แยกไฟล์ใหญ่ที่มีหลายตอนรวมกัน → ได้ไฟล์ตอนละไฟล์ เช่น '
        '<code>Chapter_001-100.txt</code> → <code>0001.txt</code>, <code>0002.txt</code>, ...'
        '</div>',
        unsafe_allow_html=True,
    )

    prefs = preferences_manager.get_setting("file_processing", "separate_settings", {}) or {}

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "เลือกไฟล์ที่จะแยก",
                  "อัปโหลดจากเครื่อง หรือเลือกโฟลเดอร์ที่มีไฟล์อยู่แล้ว")

    # Source mode: upload vs folder — ยืดหยุ่นเลือกได้ทั้ง 2 ทาง
    saved_src_mode = prefs.get("source_mode", "upload")
    src_mode = st.radio(
        "ที่มาของไฟล์",
        options=["upload", "folder"],
        format_func=lambda x: "อัปโหลดไฟล์" if x == "upload" else "เลือกจากโฟลเดอร์",
        index=0 if saved_src_mode == "upload" else 1,
        horizontal=True,
        key="sep_src_mode",
        label_visibility="collapsed",
    )
    if src_mode != saved_src_mode:
        preferences_manager.set_setting("file_processing", "separate_settings",
            {**prefs, "source_mode": src_mode})

    uploaded_files: list = []
    if src_mode == "upload":
        uploaded_files = st.file_uploader(
            "เลือกไฟล์ .txt (เลือกได้หลายไฟล์)",
            type=['txt'],
            accept_multiple_files=True,
            key="sep_upload",
            help="ลากไฟล์มาวาง หรือกด Browse เพื่อเลือกไฟล์จากเครื่อง · จะเรียงตามชื่อไฟล์อัตโนมัติ",
        ) or []
    else:
        src_folder_path, _ = h.folder_select(
            "เลือกโฟลเดอร์ที่มีไฟล์ .txt:",
            key="sep_src_folder",
            presets=["Raw", "Input", "Merge", "Separate"],
            suggested="Raw",
            help="ระบบจะหยิบไฟล์ .txt ทั้งหมดในโฟลเดอร์ (เรียงตามชื่อ) · ไฟล์ใน sub-folder ไม่ถูกเลือก",
            saved_value=prefs.get("source_folder"),
            show_count=True,
        )
        if src_folder_path:
            if str(src_folder_path) != prefs.get("source_folder"):
                preferences_manager.set_setting("file_processing", "separate_settings",
                    {**prefs, "source_folder": str(src_folder_path)})
            txt_paths = sorted(Path(src_folder_path).glob("*.txt"), key=lambda p: p.name)
            uploaded_files = [_LocalFileShim(p) for p in txt_paths]

    if uploaded_files:
        total_bytes = sum(getattr(f, 'size', 0) for f in uploaded_files)
        st.caption(f"เจอ **{len(uploaded_files)}** ไฟล์ — "
                   f"รวม {total_bytes:,} bytes · เรียงตามชื่อไฟล์แล้ว")

    # ───────────── ขั้นที่ 2 ─────────────
    h.step_header(2, "ระบุเครื่องหมายแยกตอน",
                  "ระบบจะตัดไฟล์ทุกครั้งที่เจอบรรทัดขึ้นต้นด้วยตัวอักษรนี้")
    col_a, col_b = st.columns([2, 3])
    with col_a:
        focus_keyword = st.text_input(
            "เครื่องหมายขึ้นตอนใหม่",
            value=prefs.get("focus_keyword", "") or "###",
            help="เช่น '###' = บรรทัดที่ขึ้นต้นด้วย ### คือจุดเริ่มตอนใหม่",
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

    # ── ตัวเลือก: บรรทัดหัวตอน (ตัวแยก) จะเก็บไว้ในไฟล์ตอนหรือไม่
    _HEADER_MODES = ["keep", "drop_line", "strip_marker"]
    _HEADER_LABELS = {
        "keep": "เก็บบรรทัดหัวตอนไว้ตามเดิม",
        "drop_line": "ลบทั้งบรรทัดหัวตอนออก",
        "strip_marker": f"ลบเฉพาะเครื่องหมาย ({focus_keyword or '###'}) — เก็บชื่อตอนไว้",
    }
    saved_header_mode = prefs.get("header_mode", "keep")
    if saved_header_mode not in _HEADER_MODES:
        saved_header_mode = "keep"
    header_mode = st.selectbox(
        "บรรทัดหัวตอน (ตัวแยก) ในไฟล์ตอนที่แยกออกมา",
        options=_HEADER_MODES,
        format_func=lambda m: _HEADER_LABELS[m],
        index=_HEADER_MODES.index(saved_header_mode),
        help="เลือกว่าจะให้บรรทัดที่ขึ้นต้นด้วยเครื่องหมายแยกตอน (เช่น '### ตอนที่ 1') "
             "ติดไปในไฟล์ตอนหรือไม่ — 'ลบทั้งบรรทัด' = ไฟล์เริ่มด้วยเนื้อหาเลย · "
             "'ลบเฉพาะเครื่องหมาย' = เหลือ 'ตอนที่ 1'",
        key="sep_header_mode",
    )

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
        "header_mode": header_mode,
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
        # รวมทุกไฟล์ (เรียงตามชื่อ) เป็น stream เดียวก่อน — preview ต้องตรงกับผลจริง
        # ที่ทำแบบ merge-then-split (ดู separate_processor.separate_files)
        sorted_uploaded = sorted(uploaded_files, key=lambda f: f.name)
        merged_parts: list = []
        for uf in sorted_uploaded:
            try:
                pos = uf.tell()
                content = uf.read().decode('utf-8', errors='replace')
                uf.seek(pos)
                merged_parts.append(content.rstrip('\n'))
            except Exception:
                continue
        merged_content = "\n".join(merged_parts)

        # ตัดเป็น sections ตาม focus_keyword จาก stream ที่รวมแล้ว
        # จัดการบรรทัดหัวตอนตาม header_mode ให้ตรงกับตอนแยกจริง
        all_sections: list = []   # list of section bodies (string)
        if focus_keyword:
            cur_section: list = []
            section_started = False
            for line in merged_content.splitlines():
                if line.lstrip().startswith(focus_keyword):
                    if section_started or cur_section:
                        all_sections.append("\n".join(cur_section))
                        cur_section = []
                    section_started = True
                    head = separate_processor._transform_header(line, focus_keyword, header_mode)
                    if head is not None:
                        cur_section.append(head)
                else:
                    cur_section.append(line)
            if section_started or cur_section:
                all_sections.append("\n".join(cur_section))
        elif merged_content:
            all_sections.append(merged_content)

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
        with st.spinner("กำลังรวมไฟล์ + แยกตอน..."):
            # รวมทุกไฟล์เป็นชุดเดียวก่อนหั่น — ตอนที่คร่อมขอบไฟล์จะไม่ขาด
            # separate_files ไม่รับ output folder → เขียนลง Separate ก่อน แล้วย้ายทีหลัง
            result = separate_processor.separate_files(
                uploaded_files=uploaded_files,
                focus_keyword=focus_keyword,
                title_prefix=title_prefix,
                title_suffix=title_suffix,
                chapter_number_padding=int(chapter_padding),
                start_number=int(start_number),
                strip_end_credit=strip_end_credit,
                end_credit_text=end_credit_text,
                header_mode=header_mode,
            )
            created_files = result.get('created_files', [])

            # ย้ายไฟล์ไป dest_path ถ้าไม่ใช่ Separate default
            from pathlib import Path as _P
            default_dest = paths.SEPARATE_DIR
            if dest_path and created_files and _P(dest_path).resolve() != default_dest.resolve():
                dest_path.mkdir(parents=True, exist_ok=True)
                moved = []
                for src_file in created_files:
                    try:
                        target = dest_path / _P(src_file).name
                        _P(src_file).replace(target)
                        moved.append(target)
                    except Exception as e:
                        st.warning(f"ย้าย `{_P(src_file).name}` ไม่ได้: {e}")
                created_files = moved

        if created_files:
            total_created = len(created_files)
            src_count = len(result.get('source_files', []))
            st.success(
                f"แยกไฟล์สำเร็จ — รวม {src_count:,} ไฟล์ต้นทางเป็นชุดเดียว "
                f"แล้วหั่นได้ {total_created:,} ไฟล์ตอน"
            )
            st.info(f":material/folder: บันทึกไฟล์ตอนทั้งหมดไว้ที่: `{dest_path}`")
            st.toast(f"แยก {total_created} ไฟล์ตอนสำเร็จ", icon=":material/task_alt:")
        else:
            st.error("แยกไม่สำเร็จ — กรุณาตรวจสอบเครื่องหมายหัวบท")
