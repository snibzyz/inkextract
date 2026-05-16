"""cards.py — Reusable card / chip / badge primitives"""
from __future__ import annotations
import reflex as rx
from ..theme import c, shadow, RADIUS


def section_card(*children, **kwargs) -> rx.Component:
    """Standard card surface — white bg + subtle border + radius"""
    defaults = dict(
        padding="1.25rem",
        background="white",
        border=f"1px solid {c(4)}",
        border_radius=RADIUS["lg"],
        box_shadow=shadow("sm"),
    )
    defaults.update(kwargs)
    return rx.box(*children, **defaults)


def stat_chip(label: str | rx.Var, value, color: str = "gray") -> rx.Component:
    """Compact stat pill — label + bold value"""
    return rx.hstack(
        rx.text(label, size="1", color=c(10)),
        rx.text(rx.cond(isinstance(value, (str, int, float)),
                        str(value), value),
                size="2", weight="bold",
                color=rx.color(color, 11)),
        spacing="2", align="baseline",
        padding_x="10px", padding_y="6px",
        background=c(2),
        border=f"1px solid {c(4)}",
        border_radius=RADIUS["sm"],
    )


def status_dot(color: str = "green", label: str = "Active") -> rx.Component:
    return rx.hstack(
        rx.box(
            width="6px", height="6px",
            background=rx.color(color, 9),
            border_radius="50%",
        ),
        rx.text(label, size="1", weight="bold",
                color=rx.color(color, 11),
                style={"textTransform": "uppercase",
                       "letterSpacing": "0.06em"}),
        spacing="2", align="center",
    )


def avatar_icon(icon: str, color_scheme: str = "amber",
                size: int = 40, icon_size: int = 18) -> rx.Component:
    """Square rounded avatar with icon inside (folder/file/etc)"""
    return rx.box(
        rx.icon(icon, size=icon_size,
                color=rx.color(color_scheme, 11)),
        width=f"{size}px", height=f"{size}px",
        background=rx.color(color_scheme, 3),
        border=f"1px solid {rx.color(color_scheme, 6)}",
        border_radius=RADIUS["md"],
        display="flex", align_items="center",
        justify_content="center",
        flex_shrink="0",
    )


def page_header(breadcrumb: list[str], title: str,
                subtitle: str = "", action: rx.Component | None = None
                ) -> rx.Component:
    """Linear-style page header — breadcrumb + h1 + optional action"""
    crumb_items = []
    for i, label in enumerate(breadcrumb):
        if i > 0:
            crumb_items.append(rx.icon("chevron-right", size=12, color=c(8)))
        is_last = i == len(breadcrumb) - 1
        crumb_items.append(
            rx.text(label, size="2",
                    weight="medium" if is_last else "regular",
                    color=c(12) if is_last else c(10))
        )
    return rx.vstack(
        rx.hstack(*crumb_items, spacing="2", align="center"),
        rx.hstack(
            rx.heading(title, size="7", weight="bold", color=c(12)),
            rx.spacer(),
            action if action is not None else rx.fragment(),
            width="100%", align="center",
        ),
        rx.cond(
            subtitle != "",
            rx.text(subtitle, size="2", color=c(10)),
            rx.fragment(),
        ),
        align="start", spacing="2", width="100%",
        margin_bottom="1.5rem",
    )


def empty_state(icon: str, title: str, description: str,
                action: rx.Component | None = None) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.icon(icon, size=28, color=c(9)),
            width="64px", height="64px",
            background=c(3),
            border_radius="50%",
            display="flex", align_items="center",
            justify_content="center",
            margin_bottom="0.75rem",
        ),
        rx.heading(title, size="4", color=c(12), weight="medium"),
        rx.text(description, size="2", color=c(10),
                text_align="center", max_width="320px"),
        action if action is not None else rx.fragment(),
        align="center", spacing="2",
        padding="3rem 1.5rem",
        width="100%",
    )
