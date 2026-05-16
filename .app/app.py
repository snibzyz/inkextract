import streamlit as st
from pathlib import Path
from typing import Optional
import inspect
import pandas as pd
from modules import paths, ui, project_manager
from modules.proofreader import NovelProofreader
from modules.file_processor import FileProcessor
from modules.merge_processor import MergeProcessor
from modules.separate_processor import SeparateProcessor
from modules.vocab_processor import VocabProcessor
from modules.md_converter import MarkdownConverter
from modules.docx_converter import DocxConverter
from modules.preferences_manager import preferences_manager
from modules.format_checker import FormatChecker
from modules import manuscript_checker
from modules.tabs import manuscript as tab_manuscript_module
from modules.tabs import project as tab_project_module
from modules import update_banner

# ตั้งค่าหน้าและธีม INKEXTRACT — ปล่อย page_icon ว่างให้ ui.page_setup
# auto-resolve โลโก้ inkideaex.png (อยู่ใน .app/) มาเป็น tab icon ของ browser
ui.page_setup(page_title=ui.APP_NAME)


def main():
    # คืนค่าโปรเจกต์ที่ใช้งานล่าสุดจาก registry (idempotent)
    project_manager.restore_active_on_startup()
    # AppConfig singleton snapshot paths ตอน import (ก่อน restore) — ต้อง re-resolve
    # ให้ point ที่โปรเจกต์ปัจจุบัน ไม่งั้น output จะลง workspace/ เสมอ
    from modules.config import app_config
    app_config.reload_paths()

    ui.header()
    update_banner.render()

    # แถบโปรเจกต์ที่ใช้งาน — แสดงเหนือ tabs ตลอด
    tab_project_module.render_active_bar()

    # สร้าง instance ของ processors (re-init ถ้า session_state ถูก clear ตอนสลับ project)
    if 'proofreader' not in st.session_state:
        st.session_state.proofreader = NovelProofreader()
    if 'file_processor' not in st.session_state:
        st.session_state.file_processor = FileProcessor()
    if 'merge_processor' not in st.session_state:
        st.session_state.merge_processor = MergeProcessor()
    if 'separate_processor' not in st.session_state:
        st.session_state.separate_processor = SeparateProcessor()
    if 'vocab_processor' not in st.session_state:
        st.session_state.vocab_processor = VocabProcessor()
    if 'md_converter' not in st.session_state:
        st.session_state.md_converter = MarkdownConverter()
    if 'docx_converter' not in st.session_state:
        st.session_state.docx_converter = DocxConverter()
    
    
    proofreader = st.session_state.proofreader
    file_processor = st.session_state.file_processor
    merge_processor = st.session_state.merge_processor
    separate_processor = st.session_state.separate_processor
    vocab_processor = st.session_state.vocab_processor
    md_converter = st.session_state.md_converter
    docx_converter = st.session_state.docx_converter
    
    # Quick Stats — collapsed by default (progressive disclosure)
    # Psychology: stats เป็น "อยากดูเมื่ออยากดู" — ไม่ควรกินพื้นที่ตลอด
    input_files = len(list(proofreader.input_dir.glob("*.txt"))) if proofreader.input_dir.exists() else 0
    fix_files = len(list(file_processor.fix_dir.glob("*.txt"))) if file_processor.fix_dir.exists() else 0
    clean_files = len(list(file_processor.clean_dir.glob("*.txt"))) if file_processor.clean_dir.exists() else 0
    error_count = len(proofreader.found_errors)

    summary = (
        f"ต้นฉบับ {input_files} · แก้ไข {fix_files} · สะอาด {clean_files} · "
        f"errors {error_count}"
    )
    with st.expander(
        f":material/dashboard: สถิติการทำงาน — {summary}",
        expanded=False,
    ):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ไฟล์ต้นฉบับ", input_files, help="ไฟล์ในโฟลเดอร์ Input")
        c2.metric("ไฟล์แก้ไข", fix_files, help="ไฟล์ในโฟลเดอร์ Fix")
        c3.metric("ไฟล์สะอาด", clean_files, help="ไฟล์ในโฟลเดอร์ Clean")
        c4.metric(
            "ข้อผิดพลาด", error_count, help="จำนวนข้อผิดพลาดที่พบ",
            delta_color=("normal" if error_count == 0 else "inverse"),
        )

    # Tabs หลัก — :material/<icon>: syntax (Streamlit 1.34+)
    tab_project, tab_manuscript, tab_vocab, tab_proof, tab_files = st.tabs([
        ":material/folder_special: โปรเจกต์",
        ":material/fact_check: ตรวจต้นฉบับ",
        ":material/menu_book: คำศัพท์",
        ":material/spellcheck: ตรวจสอบและแก้ไข",
        ":material/folder: จัดการไฟล์",
    ])

    with tab_project:
        tab_project_module.render()

    with tab_manuscript:
        tab_manuscript_module.render()


    # แท็บคำศัพท์ — auto-detect ทุก format ในไฟล์เดียวกัน
    with tab_vocab:
        from modules.tabs import vocab as tab_vocab_module
        tab_vocab_module.render(vocab_processor)
    with tab_proof:
        from modules.tabs import proof as tab_proof_module
        tab_proof_module.render(proofreader, file_processor)
    with tab_files:
        from modules.tabs import files as tab_files_module
        tab_files_module.render(file_processor, merge_processor, separate_processor, md_converter, docx_converter)
if __name__ == "__main__":
    main()
