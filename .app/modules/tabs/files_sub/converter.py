"""tabs/files_sub/converter.py — แปลงนามสกุลไฟล์ DOCX ↔ TXT ↔ MD

UX แบบง่าย: เลือก "แปลงจาก" → "แปลงเป็น" → preview before/after → กดแปลง
"""
from __future__ import annotations
import streamlit as st
from pathlib import Path

from modules import paths
from . import _helpers as h


# ─── Mapping ของชนิดไฟล์ที่รองรับ ──────────────────────────────────────────
_FORMATS = {
    "DOCX": ".docx",
    "TXT": ".txt",
    "MD": ".md",
}

# คู่แปลงที่รองรับ — pair (from → to)
_SUPPORTED_PAIRS = [
    ("DOCX", "TXT"),
    ("TXT", "DOCX"),
    ("MD", "DOCX"),
    ("TXT", "MD"),
    ("MD", "TXT"),
]


def render(md_converter, docx_converter, file_processor) -> None:
    """แปลงไฟล์ tab — เปลี่ยนนามสกุลระหว่าง DOCX / TXT / MD"""
    st.markdown(
        '<div style="margin-bottom:0.6rem;color:var(--ink-text-muted);font-size:0.95em;">'
        'เปลี่ยนนามสกุลไฟล์ระหว่าง <code>DOCX</code> (Word), <code>TXT</code>, '
        '<code>MD</code> (Markdown)'
        '</div>',
        unsafe_allow_html=True,
    )

    # ───────────── ขั้นที่ 1 ─────────────
    h.step_header(1, "แปลงจาก (ไฟล์ต้นทาง)")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        src_fmt = st.selectbox(
            "นามสกุลต้นทาง",
            options=list(_FORMATS.keys()),
            index=0,
            key="cv_src_fmt",
        )
    with col_b:
        src_path, _ = h.folder_select(
            "โฟลเดอร์ต้นทาง",
            key="cv_src_dir",
            presets=["Clean", "Input", "Fix", "Merge", "Separate"],
            suggested="Clean",
            help=f"โฟลเดอร์ที่มีไฟล์ .{_FORMATS[src_fmt].lstrip('.')} · ค่าเริ่มต้น = Clean",
            show_count=False,
        )

    # นับจำนวนไฟล์ต้นทาง
    src_ext = _FORMATS[src_fmt]
    src_files = []
    if src_path and src_path.exists():
        src_files = sorted(src_path.rglob(f"*{src_ext}") if src_fmt == "DOCX"
                          else src_path.glob(f"*{src_ext}"))
    total_src = len(src_files)
    if total_src > 0:
        total_size = sum(f.stat().st_size for f in src_files) / (1024 * 1024)
        st.caption(f"พบไฟล์ **{total_src:,}** ไฟล์ ({total_size:.1f} MB) ในโฟลเดอร์ `{src_path}`")
    elif src_path:
        st.warning(f"ไม่พบไฟล์ {src_ext} ในโฟลเดอร์นี้")

    # ───────────── ขั้นที่ 2 ─────────────
    h.step_header(2, "แปลงเป็น (ไฟล์ปลายทาง)")

    # หา target options ที่รองรับจาก src_fmt
    valid_targets = [t for s, t in _SUPPORTED_PAIRS if s == src_fmt]
    if not valid_targets:
        st.error(f"ยังไม่รองรับการแปลงจาก {src_fmt}")
        return

    col_c, col_d = st.columns([1, 2])
    with col_c:
        tgt_fmt = st.selectbox(
            "นามสกุลปลายทาง",
            options=valid_targets,
            index=0,
            key="cv_tgt_fmt",
        )
    with col_d:
        tgt_path, _ = h.folder_select(
            "โฟลเดอร์ปลายทาง",
            key="cv_tgt_dir",
            presets=["Clean", "Output", "Finish", "Fix"],
            suggested="Clean",
            help=f"โฟลเดอร์ที่จะเขียนไฟล์ .{_FORMATS[tgt_fmt].lstrip('.')}",
            show_count=False,
        )

    # option: in-place (เฉพาะ TXT↔MD)
    in_place = False
    if (src_fmt, tgt_fmt) in [("TXT", "MD"), ("MD", "TXT")]:
        in_place = st.checkbox(
            "แปลงในที่เดิม (เปลี่ยนนามสกุลของไฟล์ต้นทาง โดยไม่สร้างไฟล์ใหม่)",
            value=False,
            help="ติ๊กถ้าต้องการเปลี่ยนนามสกุลของไฟล์เดิม (ไม่ copy)",
            key="cv_in_place",
        )

    # option: preserve subfolder structure (เฉพาะ DOCX → TXT)
    preserve_structure = True
    if (src_fmt, tgt_fmt) == ("DOCX", "TXT"):
        preserve_structure = st.checkbox(
            "รักษาโครงสร้าง subfolder",
            value=True,
            help="ถ้าติ๊ก ผลลัพธ์จะคงโครงสร้างโฟลเดอร์ย่อย (เช่น novel1/chapter1.txt)",
            key="cv_preserve",
        )

    # ───────────── PREVIEW ─────────────
    st.markdown("---")
    if src_files:
        tgt_ext = _FORMATS[tgt_fmt]
        # สร้าง preview เปลี่ยนนามสกุล
        before_after = []
        for f in src_files[:6]:
            rel = f.name
            tgt_name = f.stem + tgt_ext
            before_after.append(f"{rel}  →  {tgt_name}")
        all_pairs = [f"{f.name}  →  {f.stem + tgt_ext}" for f in src_files]
        h.filename_preview(
            before_after,
            total=len(src_files),
            title=f"ตัวอย่างการแปลง ({src_fmt} → {tgt_fmt})",
            all_filenames=all_pairs,
        )

        # ตัวอย่างเนื้อหา (เฉพาะ TXT/MD → อ่านได้)
        if src_fmt in ("TXT", "MD") and src_files:
            try:
                first_content = src_files[0].read_text(encoding='utf-8', errors='replace')
                h.content_preview(first_content,
                                  title=f"ตัวอย่างเนื้อหาไฟล์แรก: `{src_files[0].name}`")
            except Exception:
                pass

    # ───────────── Action ─────────────
    st.markdown("---")
    can_convert = bool(src_path and tgt_path and total_src > 0)
    if st.button(f" **เริ่มแปลง {src_fmt} → {tgt_fmt}**", type="primary", width='stretch',
                 disabled=not can_convert, key="cv_btn_run"):
        with st.spinner(f"กำลังแปลง {total_src} ไฟล์..."):
            result = _do_convert(src_fmt, tgt_fmt, src_path, tgt_path,
                                 preserve_structure=preserve_structure,
                                 in_place=in_place,
                                 docx_converter=docx_converter,
                                 md_converter=md_converter)
        if result and result.get('success'):
            n = result.get('files_processed', 0)
            st.success(f"แปลงสำเร็จ {n:,} ไฟล์")
            for f in result.get('converted_files', [])[:10]:
                if isinstance(f, dict):
                    st.write(f"`{f.get('source', '')}` → `{f.get('target', '')}`")
                else:
                    st.write(f"`{f}`")
            if result.get('errors'):
                st.warning(f"มี {len(result['errors'])} ไฟล์ที่ผิดพลาด")
                for err in result['errors'][:3]:
                    st.write(f"- {err}")
            st.toast(f"แปลง {n} ไฟล์สำเร็จ")
        elif result:
            st.error(f"แปลงไม่สำเร็จ: {result.get('error', 'unknown error')}")
        else:
            st.error("แปลงไม่สำเร็จ")


def _do_convert(src_fmt: str, tgt_fmt: str, src_path: Path, tgt_path: Path,
                *, preserve_structure: bool, in_place: bool,
                docx_converter, md_converter) -> dict:
    """เรียก converter ที่เหมาะกับคู่แปลง"""
    pair = (src_fmt, tgt_fmt)
    if pair == ("DOCX", "TXT"):
        # patch source/target dirs ให้ docx_converter
        docx_converter.input_dir = src_path
        docx_converter.output_dir = tgt_path
        return docx_converter.convert_docx_to_txt(
            source_dir=src_path, target_dir=tgt_path,
            preserve_structure=preserve_structure,
        )
    elif pair in [("TXT", "DOCX"), ("MD", "DOCX")]:
        docx_converter.clean_dir = src_path
        return docx_converter.convert_txt_to_docx(source_dir=src_path, target_dir=tgt_path)
    elif pair == ("TXT", "MD"):
        md_converter.clean_dir = src_path
        return md_converter.convert_txt_to_md(source_dir=src_path, target_dir=tgt_path,
                                               in_place=in_place)
    elif pair == ("MD", "TXT"):
        md_converter.clean_dir = src_path
        return md_converter.convert_md_to_txt(source_dir=src_path, target_dir=tgt_path,
                                               in_place=in_place)
    return {'success': False, 'error': f'ไม่รองรับการแปลง {src_fmt} → {tgt_fmt}'}
