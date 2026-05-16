"""theme.py — design tokens + shortcuts

อ้างอิง Radix UI amber scale + sand gray
"""
from __future__ import annotations
import reflex as rx


# Brand
ACCENT = "amber"
GRAY = "gray"

# Layout grid (4/8/12/16/24)
SPACE = {
    "xs": "4px", "sm": "8px", "md": "12px",
    "lg": "16px", "xl": "24px", "2xl": "32px",
}

# Radius
RADIUS = {"sm": "6px", "md": "8px", "lg": "12px", "xl": "16px"}


# ── color helpers ───────────────────────────────────────────────────────────
def c(scale: int, accent: bool = False, alpha: bool = False) -> str:
    """Shorthand — rx.color('gray', 11) → c(11)  /  c(9, accent=True) for amber"""
    return rx.color(ACCENT if accent else GRAY, scale, alpha=alpha)


def shadow(level: str = "md") -> str:
    """Tailwind-ish elevation"""
    return {
        "sm": f"0 1px 2px {c(5, alpha=True)}",
        "md": f"0 1px 3px {c(4, alpha=True)}, 0 4px 8px -4px {c(6, alpha=True)}",
        "lg": f"0 4px 12px {c(5, alpha=True)}, 0 12px 32px -8px {c(7, alpha=True)}",
        "amber": f"0 1px 3px {rx.color(ACCENT, 6, alpha=True)}, 0 8px 24px -8px {rx.color(ACCENT, 7, alpha=True)}",
    }[level]
