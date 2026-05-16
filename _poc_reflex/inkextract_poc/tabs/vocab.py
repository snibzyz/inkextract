"""tabs/vocab.py — Vocabulary file management — POC stub

(Full vocab CSV/TSV/XLSX processing = port ภายหลัง — เน้น UI structure ก่อน)
"""
from __future__ import annotations
import reflex as rx
from ..state import AppState
from ..theme import c, RADIUS
from ..components.cards import page_header, section_card, empty_state, stat_chip


def render() -> rx.Component:
    return rx.vstack(
        page_header(
            breadcrumb=["Workspace", "คำศัพท์"],
            title="จัดการคำศัพท์",
            subtitle=("อัปโหลดไฟล์ .tsv / .csv / .txt / .xlsx — "
                      "รองรับ จีน[แท็บ]ไทย, จีน | ไทย ผสมกันได้"),
        ),
        rx.box(on_mount=AppState.init_vocab),

        # Status row
        rx.cond(
            AppState.vocab_loaded,
            rx.grid(
                section_card(
                    rx.text("ไฟล์ใน Vocab/", size="1", color=c(10)),
                    rx.heading(AppState.vocab_files_count.to_string(),
                               size="7", color=c(11, accent=True),
                               margin_top="4px"),
                    padding="1rem",
                ),
                section_card(
                    rx.text("คำศัพท์ทั้งหมด", size="1", color=c(10)),
                    rx.heading(AppState.vocab_total.to_string(),
                               size="7", color=c(12), margin_top="4px"),
                    padding="1rem",
                ),
                columns="2", spacing="3", width="100%",
                margin_bottom="1.5rem",
            ),
            rx.fragment(),
        ),

        # Upload zone
        rx.box(
            rx.vstack(
                rx.icon("upload-cloud", size=40, color=c(9, accent=True)),
                rx.heading("ลากไฟล์มาวาง หรือคลิกเพื่อเลือก",
                           size="4", weight="medium", color=c(12)),
                rx.text("รองรับ CSV / TSV / TXT / XLSX",
                        size="2", color=c(10)),
                rx.button(
                    rx.icon("file-plus-2", size=14),
                    "เลือกไฟล์",
                    color_scheme="amber", size="2",
                    cursor="pointer", margin_top="0.5rem",
                ),
                spacing="2", align="center",
            ),
            padding="3rem 1.5rem",
            background=c(2, accent=True),
            border=f"2px dashed {c(7, accent=True)}",
            border_radius=RADIUS["lg"],
            text_align="center",
            transition="all 0.15s",
            _hover={"background": c(3, accent=True),
                    "border_color": c(8, accent=True)},
            cursor="pointer",
        ),

        # Note
        rx.box(
            rx.hstack(
                rx.icon("info", size=16, color=c(11)),
                rx.text(
                    "POC: upload + parsing logic จะต่อจาก vocab_processor.py "
                    "ในเฟส port ต่อไป",
                    size="2", color=c(11),
                ),
                spacing="2", align="center",
            ),
            padding="0.75rem 1rem",
            background=c(2),
            border=f"1px solid {c(5)}",
            border_radius=RADIUS["md"],
            margin_top="1rem",
        ),

        spacing="0", width="100%",
    )
