"""tabs/proof.py — Proofreading + correction workflow

Wired to: modules.proofreader.NovelProofreader (Normal mode)
AB mode = stub สำหรับ POC
"""
from __future__ import annotations
import reflex as rx
from ..state import AppState
from ..theme import c, RADIUS
from ..components.cards import page_header, section_card, stat_chip, status_dot


STEPS = [
    ("settings", "ตั้งค่า"),
    ("file-search-2", "วิเคราะห์"),
    ("file-output", "ส่งออก"),
    ("file-input", "นำเข้า"),
    ("file-check-2", "แก้ไขไฟล์"),
]


def stepper(active_idx: int = 0) -> rx.Component:
    cells = []
    for i, (icon, label) in enumerate(STEPS):
        is_active = i == active_idx
        is_done = i < active_idx
        if is_done:
            bg = rx.color("green", 9)
            border = rx.color("green", 9)
            color = "white"
        elif is_active:
            bg = c(9, accent=True)
            border = c(9, accent=True)
            color = "white"
        else:
            bg = "white"
            border = c(5)
            color = c(10)

        cells.append(
            rx.vstack(
                rx.box(
                    rx.cond(
                        is_done,
                        rx.icon("check", size=18, color="white"),
                        rx.text(str(i + 1), size="3",
                                weight="bold", color=color),
                    ),
                    width="36px", height="36px",
                    border_radius="50%",
                    background=bg,
                    border=f"2px solid {border}",
                    display="flex", align_items="center",
                    justify_content="center",
                ),
                rx.text(label, size="1",
                        weight="bold" if is_active else "medium",
                        color=c(12) if (is_active or is_done) else c(10)),
                spacing="2", align="center", flex="1",
            ),
        )

    return rx.box(
        rx.hstack(*cells, spacing="2", align="start", width="100%"),
        padding="1rem", background="white",
        border=f"1px solid {c(4)}", border_radius=RADIUS["md"],
        margin_bottom="1.5rem",
    )


def mode_toggle() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(
            rx.hstack(
                rx.icon("git-compare-arrows", size=14),
                rx.text("โหมด AB"),
                spacing="1", align="center",
            ),
            value="ab",
        ),
        rx.segmented_control.item(
            rx.hstack(
                rx.icon("type", size=14),
                rx.text("โหมดทั่วไป"),
                spacing="1", align="center",
            ),
            value="normal",
        ),
        on_change=AppState.set_proof_mode,
        value=AppState.proof_mode,
        size="3",
        margin_bottom="1.5rem",
    )


def settings_card() -> rx.Component:
    return section_card(
        rx.vstack(
            rx.hstack(
                rx.icon("settings", size=16, color=c(10)),
                rx.text("การตั้งค่า", size="3", weight="bold", color=c(12)),
                spacing="2", align="center",
            ),
            rx.grid(
                _check("ตรวจภาษาต่างประเทศ",
                       AppState.proof_check_foreign,
                       AppState.toggle_proof_foreign),
                _check("ตรวจตัวเลข",
                       AppState.proof_check_numbers,
                       AppState.toggle_proof_numbers),
                _check("ตรวจภาษาอังกฤษ",
                       AppState.proof_check_english,
                       AppState.toggle_proof_english),
                columns="3", spacing="3", width="100%", margin_top="0.5rem",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("โฟลเดอร์ต้นทาง", size="1", color=c(10)),
                    rx.select(
                        ["Clean", "Input", "Fix", "Raw"],
                        value=AppState.proof_source_folder,
                        on_change=AppState.set_proof_source,
                        size="3", width="100%",
                    ),
                    spacing="1", align="start", flex="1",
                ),
                rx.vstack(
                    rx.text("Chunk lines (ส่งออก)", size="1", color=c(10)),
                    rx.input(
                        type="number",
                        value=AppState.proof_chunk_lines.to_string(),
                        on_change=AppState.set_proof_chunk,
                        size="3", width="100%",
                    ),
                    spacing="1", align="start", flex="1",
                ),
                spacing="3", width="100%", margin_top="0.75rem",
                align="end",
            ),
            spacing="2", width="100%",
        ),
        margin_bottom="1rem",
    )


def _check(label: str, value, on_change) -> rx.Component:
    return rx.hstack(
        rx.checkbox(checked=value, on_change=on_change,
                    color_scheme="amber", size="2"),
        rx.text(label, size="2", color=c(12)),
        spacing="2", align="center",
    )


def action_card() -> rx.Component:
    return section_card(
        rx.hstack(
            rx.vstack(
                rx.text("วิเคราะห์", size="3", weight="bold", color=c(12)),
                rx.text("สแกนหาอักขระต่างประเทศ / ตัวเลข / ภาษาอังกฤษ "
                        "ในโฟลเดอร์ต้นทาง", size="2", color=c(10)),
                spacing="1", align="start", flex="1",
            ),
            rx.button(
                rx.icon("zap", size=16),
                "วิเคราะห์ตอนนี้",
                on_click=AppState.run_analyze,
                loading=AppState.proof_analyzing,
                color_scheme="amber", size="3",
                cursor="pointer",
            ),
            spacing="3", align="center", width="100%",
        ),
        margin_bottom="1rem",
    )


def result_card() -> rx.Component:
    return rx.cond(
        AppState.proof_last_run_summary != "",
        section_card(
            rx.hstack(
                rx.icon(
                    rx.cond(AppState.proof_errors_count > 0,
                            "circle-alert", "circle-check-big"),
                    size=20,
                    color=rx.cond(AppState.proof_errors_count > 0,
                                  rx.color("amber", 11),
                                  rx.color("green", 11)),
                ),
                rx.vstack(
                    rx.text("ผลการวิเคราะห์ล่าสุด", size="1", color=c(10)),
                    rx.text(AppState.proof_last_run_summary,
                            size="3", weight="medium", color=c(12)),
                    spacing="0", align="start", flex="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("file-output", size=14), "ส่งออก",
                    variant="soft", color_scheme="amber", size="2",
                ),
                spacing="3", align="center", width="100%",
            ),
            border_left=f"3px solid {rx.color('green', 9)}",
        ),
    )


def render() -> rx.Component:
    return rx.vstack(
        page_header(
            breadcrumb=["Workspace", "ตรวจสอบและแก้ไข"],
            title="ตรวจสอบและแก้ไข",
            subtitle="หาข้อผิดพลาดในไฟล์แปล แล้วส่งออกไป AI แก้กลับ",
        ),
        mode_toggle(),
        stepper(active_idx=1),
        settings_card(),
        action_card(),
        result_card(),
        spacing="0", width="100%",
    )
