"""layout.py — Page-level chrome (nav bar, tab nav, container)"""
from __future__ import annotations
import reflex as rx
from ..state import AppState, TABS
from ..theme import c


def nav_bar() -> rx.Component:
    """Top sticky nav bar — brand + utility actions"""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.box(
                    rx.icon("book-open-text", size=18, color="white"),
                    width="32px", height="32px",
                    background=c(9, accent=True),
                    border_radius="8px",
                    display="flex", align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.text("INKEXTRACT", size="3", weight="bold",
                            color=c(12), line_height="1"),
                    rx.text("เครื่องมือจัดการนิยายแปล", size="1",
                            color=c(10), line_height="1",
                            margin_top="2px"),
                    spacing="0", align="start",
                ),
                spacing="3", align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("circle-help", size=14),
                    "ช่วยเหลือ",
                    variant="ghost", color_scheme="gray", size="2",
                ),
                rx.box(width="1px", height="20px",
                       background=c(5)),
                rx.badge("POC", color_scheme="amber",
                         variant="soft", size="1"),
                spacing="2", align="center",
            ),
            width="100%", align="center", padding_x="1.5rem",
            padding_y="0.8rem",
        ),
        background="white",
        border_bottom=f"1px solid {c(4)}",
        position="sticky", top="0", z_index="50",
    )


def tab_item(tab_id: str, icon: str, label: str) -> rx.Component:
    is_active = AppState.current_tab == tab_id
    return rx.hstack(
        rx.icon(icon, size=16,
                color=rx.cond(is_active, c(11, accent=True), c(10))),
        rx.text(label, size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, c(12), c(11))),
        padding_x="14px", padding_y="10px",
        border_bottom=rx.cond(
            is_active,
            f"2px solid {c(9, accent=True)}",
            "2px solid transparent",
        ),
        cursor="pointer",
        spacing="2", align="center",
        margin_bottom="-1px",
        transition="all 0.12s",
        on_click=lambda: AppState.switch_tab(tab_id),
        _hover=rx.cond(
            is_active,
            {},
            {"color": c(12), "background": c(2)},
        ),
    )


def tab_nav() -> rx.Component:
    return rx.hstack(
        *[tab_item(*t) for t in TABS],
        spacing="0",
        border_bottom=f"1px solid {c(4)}",
        margin_bottom="1.5rem",
        width="100%",
        overflow_x="auto",
    )


def page_container(*children) -> rx.Component:
    return rx.container(
        tab_nav(),
        *children,
        size="3",
        padding_y="1.5rem",
    )
