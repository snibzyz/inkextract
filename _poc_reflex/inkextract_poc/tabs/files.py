"""tabs/files.py — File operations (merge/separate/generate/format/clear/convert)

POC: tab nav structure + each sub-tab = stub พร้อม CTA
ภายหลัง port logic จาก files_sub/ ทั้ง 6 ตัว
"""
from __future__ import annotations
import reflex as rx
from ..state import AppState
from ..theme import c, RADIUS
from ..components.cards import page_header, section_card, empty_state


SUBTABS = [
    ("merge", "merge", "รวมไฟล์", "เอาไฟล์ตอนเล็กๆ มาต่อกัน"),
    ("separate", "split", "แยกไฟล์", "ตัดไฟล์ใหญ่ออกเป็นตอน"),
    ("generate", "file-plus-2", "สร้างไฟล์", "สร้างไฟล์เปล่าตามรูปแบบ"),
    ("format", "ruler", "ตรวจรูปแบบ", "ตรวจ encoding/CRLF/heading"),
    ("clear", "trash-2", "ลบไฟล์", "ลบไฟล์ในโฟลเดอร์ (พร้อม backup)"),
    ("convert", "arrow-left-right", "แปลงไฟล์", "TXT ↔ MD ↔ DOCX"),
]


def sub_tab_item(sub_id: str, icon: str, label: str) -> rx.Component:
    is_active = AppState.files_subtab == sub_id
    return rx.hstack(
        rx.icon(icon, size=14,
                color=rx.cond(is_active, c(11, accent=True), c(10))),
        rx.text(label, size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, c(12), c(11))),
        padding_x="12px", padding_y="8px",
        background=rx.cond(is_active, c(3, accent=True), "white"),
        border=rx.cond(
            is_active,
            f"1px solid {c(7, accent=True)}",
            f"1px solid {c(4)}",
        ),
        border_radius="999px",
        cursor="pointer",
        spacing="2", align="center",
        transition="all 0.12s",
        on_click=lambda: AppState.switch_files_subtab(sub_id),
        _hover=rx.cond(
            is_active, {},
            {"border_color": c(6, accent=True),
             "background": c(2, accent=True)},
        ),
    )


def sub_tab_nav() -> rx.Component:
    return rx.hstack(
        *[sub_tab_item(s[0], s[1], s[2]) for s in SUBTABS],
        spacing="2",
        margin_bottom="1.5rem",
        width="100%",
        wrap="wrap",
    )


def sub_content() -> rx.Component:
    # render content per active sub
    return rx.match(
        AppState.files_subtab,
        ("merge", _stub_card("merge", "รวมไฟล์",
                             "เอาไฟล์ตอนเล็ก ๆ ในโฟลเดอร์มาต่อกัน → Chapter_0001-0005.txt",
                             ["เลือกไฟล์ต้นทาง", "ตั้งค่าวิธีรวม", "เลือกโฟลเดอร์ปลายทาง"])),
        ("separate", _stub_card("split", "แยกไฟล์",
                                "ตัดไฟล์ใหญ่ออกเป็นตอนๆ ตาม heading หรือจำนวนบรรทัด",
                                ["เลือกไฟล์ที่จะแยก", "ตั้งค่าวิธีแยก", "เลือกโฟลเดอร์ปลายทาง"])),
        ("generate", _stub_card("file-plus-2", "สร้างไฟล์",
                                "สร้างไฟล์เปล่าตามรูปแบบที่กำหนด (ใช้เป็น placeholder)",
                                ["ตั้งชื่อไฟล์", "จำนวนไฟล์", "เลขนำหน้า", "โฟลเดอร์ปลายทาง"])),
        ("format", _stub_card("ruler", "ตรวจรูปแบบไฟล์",
                              "ตรวจ encoding (UTF-8) / line ending (CRLF) / heading format",
                              ["เลือกโฟลเดอร์", "เลือกเกณฑ์ตรวจ"])),
        ("clear", _stub_card("trash-2", "ลบไฟล์",
                             "ลบไฟล์ในโฟลเดอร์ + backup ไป Temp/ ก่อนทุกครั้ง",
                             ["เลือกโฟลเดอร์ที่จะลบ", "สรุปก่อนลบ", "ยืนยัน"])),
        ("convert", _stub_card("arrow-left-right", "แปลงไฟล์",
                               "แปลง .txt ↔ .md ↔ .docx — รักษา heading / formatting",
                               ["แปลงจาก (ไฟล์ต้นทาง)", "แปลงเป็น (ไฟล์ปลายทาง)"])),
    )


def _stub_card(icon: str, title: str, desc: str, steps: list[str]) -> rx.Component:
    return section_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=24, color=c(11, accent=True)),
                    width="48px", height="48px",
                    background=c(3, accent=True),
                    border=f"1px solid {c(6, accent=True)}",
                    border_radius=RADIUS["md"],
                    display="flex", align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.heading(title, size="5", color=c(12), weight="bold"),
                    rx.text(desc, size="2", color=c(10)),
                    spacing="1", align="start", flex="1",
                ),
                spacing="3", align="center", width="100%",
            ),
            rx.divider(margin_y="0.75rem"),
            rx.text("ขั้นตอน", size="1", color=c(10), weight="medium"),
            rx.vstack(
                *[
                    rx.hstack(
                        rx.box(
                            rx.text(str(i + 1), size="1",
                                    weight="bold", color="white"),
                            width="22px", height="22px",
                            background=c(9, accent=True),
                            border_radius="50%",
                            display="flex", align_items="center",
                            justify_content="center",
                            flex_shrink="0",
                        ),
                        rx.text(step, size="2", color=c(11)),
                        spacing="2", align="center",
                    )
                    for i, step in enumerate(steps)
                ],
                spacing="2", align="start", margin_top="0.5rem", width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.icon("info", size=14, color=c(11)),
                    rx.text("POC: logic จะ port จาก files_sub/ ในเฟสต่อไป",
                            size="1", color=c(11)),
                    spacing="2", align="center",
                ),
                padding="0.6rem 0.85rem",
                background=c(2),
                border=f"1px solid {c(5)}",
                border_radius=RADIUS["sm"],
                margin_top="1rem",
            ),
            spacing="0", align="start", width="100%",
        ),
    )


def render() -> rx.Component:
    return rx.vstack(
        page_header(
            breadcrumb=["Workspace", "จัดการไฟล์"],
            title="จัดการไฟล์",
            subtitle="รวม / แยก / สร้าง / แปลง / ตรวจรูปแบบ / ลบไฟล์",
        ),
        sub_tab_nav(),
        sub_content(),
        spacing="0", width="100%",
    )
