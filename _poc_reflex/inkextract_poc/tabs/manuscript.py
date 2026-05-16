"""tabs/manuscript.py — Scan raw files + flag abnormally small files

Wired to: modules.manuscript_checker.scan_directory()
"""
from __future__ import annotations
import reflex as rx
from ..state import AppState
from ..theme import c, shadow, RADIUS
from ..components.cards import (
    page_header, section_card, stat_chip, empty_state,
)


def folder_input_bar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("โฟลเดอร์ที่จะตรวจ", size="1", weight="medium",
                    color=c(11)),
            rx.hstack(
                rx.input(
                    value=AppState.ms_folder,
                    on_change=AppState.set_ms_folder,
                    placeholder=r"Z:\... \Raw",
                    size="3", flex="1",
                ),
                rx.button(
                    rx.icon("search", size=14), "สแกน",
                    on_click=AppState.scan_manuscript,
                    color_scheme="amber", size="3",
                    cursor="pointer",
                ),
                spacing="2", width="100%",
            ),
            spacing="1", align="start", width="100%",
        ),
        padding="1rem",
        background="white",
        border=f"1px solid {c(4)}",
        border_radius=RADIUS["md"],
        margin_bottom="1rem",
    )


def threshold_slider() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text("เกณฑ์: ไฟล์เล็กกว่า", size="2", color=c(11)),
                rx.badge(
                    rx.text(AppState.ms_threshold_pct.to_string() + "%"),
                    color_scheme="amber", variant="soft", size="2",
                ),
                rx.text("ของขนาดเฉลี่ย = ผิดปกติ", size="2", color=c(11)),
                spacing="2", align="center",
            ),
            rx.slider(
                value=[AppState.ms_threshold_pct],
                on_change=AppState.set_ms_threshold,
                min=5, max=80, step=5,
                color_scheme="amber",
                width="100%",
            ),
            spacing="2", align="start", width="100%",
        ),
        padding="1rem",
        background="white",
        border=f"1px solid {c(4)}",
        border_radius=RADIUS["md"],
        margin_bottom="1rem",
    )


def stats_summary() -> rx.Component:
    return rx.grid(
        section_card(
            rx.text("ไฟล์ทั้งหมด", size="1", color=c(10)),
            rx.heading(AppState.ms_total.to_string(), size="7",
                       color=c(11, accent=True), margin_top="4px"),
            padding="1rem",
        ),
        section_card(
            rx.text("เลขนำหน้า", size="1", color=c(10)),
            rx.heading(AppState.ms_padding.to_string() + " หลัก", size="7",
                       color=c(12), margin_top="4px"),
            padding="1rem",
        ),
        section_card(
            rx.text("ขนาดเฉลี่ย", size="1", color=c(10)),
            rx.heading(_fmt_size_var(AppState.ms_avg_size_bytes), size="7",
                       color=c(12), margin_top="4px"),
            padding="1rem",
        ),
        section_card(
            rx.text("ไฟล์เล็กผิดปกติ", size="1", color=c(10)),
            rx.heading(AppState.ms_small.to_string(), size="7",
                       color=rx.cond(AppState.ms_small > 0,
                                     rx.color("red", 11), c(11)),
                       margin_top="4px"),
            padding="1rem",
        ),
        columns="4", spacing="3", width="100%",
        margin_bottom="1.5rem",
    )


def _fmt_size_var(bytes_var) -> rx.Var:
    """Format bytes → KB/MB string (Reflex var-friendly)"""
    return rx.cond(
        bytes_var < 1024,
        bytes_var.to_string() + " B",
        rx.cond(
            bytes_var < 1024 * 1024,
            (bytes_var / 1024).to_string() + " KB",
            (bytes_var / 1024 / 1024).to_string() + " MB",
        ),
    )


def file_row(entry: dict) -> rx.Component:
    is_small = entry["is_small"]
    is_selected = AppState.ms_selected.contains(entry["name"])
    return rx.hstack(
        rx.checkbox(
            checked=is_selected,
            on_change=lambda _: AppState.toggle_ms_select(entry["name"]),
            color_scheme="amber",
        ),
        rx.icon(
            rx.cond(is_small, "file-warning", "file-text"),
            size=16,
            color=rx.cond(is_small, rx.color("red", 11), c(11)),
        ),
        rx.text(entry["name"], size="2",
                color=rx.cond(is_small, rx.color("red", 11), c(12)),
                weight=rx.cond(is_small, "bold", "medium"),
                style={"fontFamily": "'JetBrains Mono','Consolas',monospace"}),
        rx.spacer(),
        rx.text(entry["rel_size_pct"].to_string() + "%",
                size="1", color=c(10)),
        stat_chip("ขนาด", _fmt_size_var(entry["size"]),
                  "red" if False else "gray"),
        padding="0.6rem 0.85rem",
        background=rx.cond(is_small, rx.color("red", 2), "white"),
        border=rx.cond(
            is_small,
            f"1px solid {rx.color('red', 6)}",
            f"1px solid {c(4)}",
        ),
        border_radius=RADIUS["sm"],
        spacing="3", align="center", width="100%",
        transition="background 0.12s",
        _hover={"background": c(2)},
    )


def file_list() -> rx.Component:
    return rx.cond(
        AppState.ms_scan_done,
        rx.vstack(
            rx.hstack(
                rx.text(f"รายการไฟล์", size="2", weight="medium",
                        color=c(11)),
                rx.spacer(),
                rx.button(
                    rx.icon("check-check", size=14),
                    "เลือกไฟล์เล็กทั้งหมด",
                    variant="soft", color_scheme="amber", size="1",
                    on_click=AppState.select_all_small,
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("x", size=14), "ล้างการเลือก",
                    variant="ghost", color_scheme="gray", size="1",
                    on_click=AppState.clear_ms_selection,
                    cursor="pointer",
                ),
                spacing="2", width="100%", align="center",
                margin_bottom="0.5rem",
            ),
            rx.foreach(AppState.ms_entries, file_row),
            spacing="2", width="100%",
        ),
        rx.fragment(),
    )


def render() -> rx.Component:
    return rx.vstack(
        page_header(
            breadcrumb=["Workspace", "ตรวจต้นฉบับ"],
            title="ตรวจต้นฉบับ",
            subtitle=("สแกนไฟล์ .txt — ไฟล์ที่เล็กผิดปกติเทียบกับขนาดเฉลี่ย "
                      "จะถูก highlight สีแดง"),
        ),
        rx.box(on_mount=AppState.init_manuscript),
        folder_input_bar(),
        threshold_slider(),
        rx.cond(
            AppState.ms_scan_done,
            rx.vstack(
                stats_summary(),
                file_list(),
                spacing="0", width="100%",
            ),
            empty_state(
                "search", "ยังไม่ได้สแกน",
                "ระบุโฟลเดอร์ที่ต้องการตรวจแล้วกดปุ่ม สแกน",
            ),
        ),
        spacing="0", width="100%",
    )
