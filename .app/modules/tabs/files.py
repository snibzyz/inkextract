"""tabs/files.py — Tab จัดการไฟล์ (Merge/Separate/Generate/Convert/Format/Clear)"""
from __future__ import annotations
import streamlit as st

from modules import ui
from modules.tabs.files_sub import (
    merge as sub_merge,
    separate as sub_separate,
    generate as sub_generate,
    converter as sub_converter,
    format as sub_format,
    clear as sub_clear,
)


def render(file_processor, merge_processor, separate_processor,
           md_converter, docx_converter) -> None:
    """แสดง files tab — แต่ละ sub-tab อยู่ใน module แยก"""
    with ui.section("จัดการไฟล์", description="รวม / แยก / สร้าง / แปลง / ตรวจรูปแบบ / ลบไฟล์"):
        pass

    merge_tab, separate_tab, generate_tab, converter_tab, format_tab, clear_tab = st.tabs([
        ":material/merge: รวมไฟล์",
        ":material/call_split: แยกไฟล์",
        ":material/note_add: สร้างไฟล์",
        ":material/swap_horiz: แปลงไฟล์",
        ":material/rule: ตรวจรูปแบบ",
        ":material/delete: ลบไฟล์",
    ])

    with merge_tab:
        sub_merge.render(merge_processor, file_processor)
    with separate_tab:
        sub_separate.render(separate_processor, file_processor)
    with generate_tab:
        sub_generate.render(file_processor)
    with converter_tab:
        sub_converter.render(md_converter, docx_converter, file_processor)
    with format_tab:
        sub_format.render(file_processor)
    with clear_tab:
        sub_clear.render(file_processor)
