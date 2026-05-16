"""inkextract_poc.py — Main app entry

Thin wrapper:
  1. import backend (เซ็ต sys.path + stub streamlit)
  2. compose nav_bar + tab_nav + tab content (sync กับ AppState.current_tab)
  3. configure rx.theme (amber) + global font
"""
from __future__ import annotations
import reflex as rx

# 1) ต้อง import backend ก่อนใช้ modules — มัน inject sys.path + stub
from . import backend  # noqa: F401

from .state import AppState
from .theme import c
from .components.layout import nav_bar, tab_nav
from .tabs import project, manuscript, vocab, proof, files


def _tab_content() -> rx.Component:
    """Swap content ตาม AppState.current_tab"""
    return rx.match(
        AppState.current_tab,
        ("project", project.render()),
        ("manuscript", manuscript.render()),
        ("vocab", vocab.render()),
        ("proof", proof.render()),
        ("files", files.render()),
        project.render(),  # fallback
    )


def index() -> rx.Component:
    return rx.box(
        nav_bar(),
        rx.container(
            tab_nav(),
            _tab_content(),
            size="4",
            padding_y="1.5rem",
        ),
        rx.box(on_mount=AppState.init_projects),
        min_height="100vh",
        background=c(2),
    )


app = rx.App(
    theme=rx.theme(
        accent_color="amber",
        gray_color="sand",
        radius="medium",
        scaling="100%",
        appearance="light",
    ),
    style={
        "fontFamily":
            "'Inter', 'Sarabun', 'Tahoma', 'Microsoft YaHei', sans-serif",
        "fontFeatureSettings": "'cv11', 'ss01', 'ss03'",
    },
    stylesheets=[
        "https://fonts.googleapis.com/css2?"
        "family=Inter:wght@400;500;600;700&"
        "family=Sarabun:wght@300;400;500;600;700&"
        "family=JetBrains+Mono:wght@400;500&display=swap",
    ],
)
app.add_page(index, title="INKEXTRACT — Reflex POC")
