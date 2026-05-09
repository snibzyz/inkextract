import streamlit as st
from pathlib import Path
from typing import Optional
import inspect
import pandas as pd
from modules import paths, ui
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
from modules import update_banner

# ตั้งค่าหน้าและ theme INKEXTRACT
ui.page_setup(page_title=ui.APP_NAME, page_icon="🟠")



def main():
    ui.header()
    update_banner.render()
    
    # สร้าง instance ของ processors
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
    
    # Quick Stats Dashboard
    st.markdown("### :material/dashboard: สถิติการทำงาน")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        input_files = len(list(proofreader.input_dir.glob("*.txt"))) if proofreader.input_dir.exists() else 0
        st.metric("ไฟล์ต้นฉบับ", input_files, help="ไฟล์ในโฟลเดอร์ 0-input")

    with col2:
        fix_files = len(list(file_processor.fix_dir.glob("*.txt"))) if file_processor.fix_dir.exists() else 0
        st.metric("ไฟล์แก้ไข", fix_files, help="ไฟล์ในโฟลเดอร์ 1-fix")

    with col3:
        clean_files = len(list(file_processor.clean_dir.glob("*.txt"))) if file_processor.clean_dir.exists() else 0
        st.metric("ไฟล์สะอาด", clean_files, help="ไฟล์ในโฟลเดอร์ 2-clean")

    with col4:
        error_count = len(proofreader.found_errors)
        delta_color = "normal" if error_count == 0 else "inverse"
        st.metric("ข้อผิดพลาด", error_count, help="จำนวนข้อผิดพลาดที่พบ", delta_color=delta_color)

    st.markdown("---")

    # Tabs หลัก — :material/<icon>: syntax (Streamlit 1.34+)
    tab_manuscript, tab_vocab, tab_proof, tab_files = st.tabs([
        ":material/fact_check: ตรวจต้นฉบับ",
        ":material/menu_book: คำศัพท์",
        ":material/spellcheck: ตรวจสอบและแก้ไข",
        ":material/folder: จัดการไฟล์",
    ])

    with tab_manuscript:
        tab_manuscript_module.render()
    
    
    # Vocab Tab — ใช้ unified parser แล้ว (auto-detect ทุก format ในไฟล์เดียวกัน)
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
