"""tabs/project.py — Project management — wired to real project_manager.py"""
from __future__ import annotations
import reflex as rx
from ..state import AppState
from ..theme import c, shadow, RADIUS
from ..components.cards import (
    section_card, stat_chip, status_dot, avatar_icon, page_header,
)


def active_project_card() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Avatar
            rx.box(
                rx.icon("folder-open", size=24, color=c(11, accent=True)),
                width="56px", height="56px",
                background=f"linear-gradient(135deg, {c(4, accent=True)} 0%, {c(5, accent=True)} 100%)",
                border=f"1px solid {c(6, accent=True)}",
                border_radius="14px",
                display="flex", align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            # Main info
            rx.vstack(
                status_dot("green", "กำลังใช้งาน"),
                rx.heading(AppState.active_name, size="7", weight="bold",
                           color=c(12), margin_top="2px", line_height="1.15"),
                rx.hstack(
                    rx.icon("folder", size=12, color=c(10)),
                    rx.code(AppState.active_path, size="1",
                            background="transparent", color=c(11)),
                    spacing="2", align="center", margin_top="6px",
                ),
                rx.hstack(
                    stat_chip("ต้นฉบับ", AppState.active_project["input_count"], "amber"),
                    stat_chip("แก้ไข", AppState.active_project["fix_count"], "gray"),
                    stat_chip("สะอาด", AppState.active_project["clean_count"], "green"),
                    stat_chip("ทำงานล่าสุด", AppState.active_meta, "gray"),
                    spacing="2", margin_top="14px", wrap="wrap",
                ),
                spacing="0", align="start", flex="1", min_width="0",
            ),
            rx.spacer(),
            # Actions
            rx.vstack(
                rx.button(
                    rx.icon("folder-open", size=14),
                    "เปิดในระบบ",
                    on_click=AppState.open_active_folder,
                    color_scheme="amber", variant="solid", size="2",
                    cursor="pointer", width="160px",
                ),
                rx.button(
                    rx.icon("settings", size=14),
                    "ตั้งค่า",
                    variant="soft", color_scheme="gray", size="2",
                    cursor="pointer", width="160px",
                ),
                spacing="2", align="end",
            ),
            spacing="4", align="start", width="100%",
        ),
        padding="1.5rem",
        background="white",
        border=f"1px solid {c(4)}",
        border_left=f"3px solid {c(9, accent=True)}",
        border_radius=RADIUS["lg"],
        box_shadow=shadow("amber"),
        margin_bottom="1.5rem",
    )


def create_project_form() -> rx.Component:
    return rx.cond(
        AppState.show_create_form,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("circle-plus", size=18, color=c(11, accent=True)),
                    rx.text("สร้างโปรเจกต์ใหม่", size="3",
                            weight="bold", color=c(12)),
                    spacing="2", align="center",
                ),
                rx.text(
                    "ตั้งชื่อโปรเจกต์ — ระบบจะสร้างโฟลเดอร์ย่อย "
                    "(Raw, Input, Fix, Clean, …) ให้อัตโนมัติ",
                    size="1", color=c(10),
                ),
                rx.input(
                    placeholder="เช่น  ติดหนี้สามสิบล้าน",
                    value=AppState.new_project_name,
                    on_change=AppState.set_new_name,
                    size="3", width="100%", margin_top="6px",
                    auto_focus=True,
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("check", size=14),
                        "สร้างและสลับไปใช้งาน",
                        on_click=AppState.create_project,
                        color_scheme="amber", size="2",
                        cursor="pointer",
                    ),
                    rx.button(
                        "ยกเลิก", variant="ghost", color_scheme="gray",
                        size="2", on_click=AppState.toggle_create_form,
                        cursor="pointer",
                    ),
                    spacing="2",
                ),
                spacing="2", align="start", width="100%",
            ),
            padding="1.25rem",
            background=c(2, accent=True),
            border=f"1px dashed {c(7, accent=True)}",
            border_radius=RADIUS["lg"],
            margin_bottom="1rem",
        ),
    )


def delete_confirm_dialog() -> rx.Component:
    """แสดงเมื่อ confirm_delete_id ไม่ว่าง"""
    return rx.cond(
        AppState.confirm_delete_id != "",
        rx.box(
            # backdrop
            rx.box(
                position="fixed", top="0", left="0",
                width="100vw", height="100vh",
                background="rgba(0,0,0,0.4)",
                z_index="100",
                on_click=AppState.cancel_delete,
            ),
            # dialog
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("triangle-alert", size=20,
                                color=rx.color("red", 11)),
                        rx.text("ยืนยันการลบโปรเจกต์", size="4",
                                weight="bold", color=c(12)),
                        spacing="2", align="center",
                    ),
                    rx.text(
                        "การลบเอาออกจากรายการเท่านั้น — โฟลเดอร์ยังอยู่บนดิสก์ "
                        "เว้นแต่จะเลือกลบไฟล์ด้วย",
                        size="2", color=c(11),
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("trash-2", size=14),
                            "ลบออกจากรายการ",
                            variant="soft", color_scheme="gray",
                            size="2",
                            on_click=lambda: AppState.confirm_delete(False),
                        ),
                        rx.button(
                            rx.icon("flame", size=14),
                            "ลบไฟล์ทั้งหมดด้วย",
                            color_scheme="red", size="2",
                            on_click=lambda: AppState.confirm_delete(True),
                        ),
                        rx.spacer(),
                        rx.button("ยกเลิก", variant="ghost",
                                  color_scheme="gray", size="2",
                                  on_click=AppState.cancel_delete),
                        spacing="2", width="100%",
                    ),
                    spacing="3", width="100%",
                ),
                position="fixed",
                top="50%", left="50%",
                transform="translate(-50%, -50%)",
                width="min(480px, 90vw)",
                padding="1.5rem",
                background="white",
                border=f"1px solid {c(5)}",
                border_radius=RADIUS["lg"],
                box_shadow=shadow("lg"),
                z_index="101",
            ),
        ),
    )


def project_row(p: dict) -> rx.Component:
    is_active = p["id"] == AppState.active_project_id
    return rx.box(
        rx.hstack(
            avatar_icon(
                rx.cond(is_active, "folder-open", "folder").to_string(),
                "amber" if False else "gray",
            ) if False else rx.box(
                rx.icon(
                    rx.cond(is_active, "folder-open", "folder"),
                    size=18,
                    color=rx.cond(is_active, c(11, accent=True), c(10)),
                ),
                width="40px", height="40px",
                background=rx.cond(is_active, c(3, accent=True), c(3)),
                border=rx.cond(
                    is_active,
                    f"1px solid {c(6, accent=True)}",
                    f"1px solid {c(5)}",
                ),
                border_radius=RADIUS["md"],
                display="flex", align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(p["name"], size="3", weight="bold", color=c(12)),
                    rx.cond(
                        p["is_default"],
                        rx.badge("เริ่มต้น", color_scheme="amber",
                                 variant="soft", size="1"),
                        rx.fragment(),
                    ),
                    rx.cond(
                        ~p["exists"],
                        rx.badge("ไม่พบบนดิสก์", color_scheme="red",
                                 variant="soft", size="1"),
                        rx.fragment(),
                    ),
                    rx.cond(
                        is_active,
                        status_dot("green", "กำลังใช้งาน"),
                        rx.fragment(),
                    ),
                    spacing="2", align="center", wrap="wrap",
                ),
                rx.hstack(
                    rx.icon("folder", size=10, color=c(9)),
                    rx.text(
                        p["path"], size="1", color=c(10),
                        style={
                            "fontFamily":
                                "'JetBrains Mono','Consolas',monospace",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    spacing="1", align="center",
                ),
                rx.hstack(
                    stat_chip("ต้นฉบับ", p["input_count"], "amber"),
                    stat_chip("ไฟล์รวม", p["file_count"], "gray"),
                    rx.cond(
                        p["created_at"] != "",
                        rx.text(f"· สร้างเมื่อ {p['created_at'][:10]}",
                                size="1", color=c(10)),
                        rx.fragment(),
                    ),
                    spacing="2", align="center", margin_top="4px",
                ),
                spacing="1", align="start", flex="1", min_width="0",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    is_active,
                    rx.button(rx.icon("check", size=14), "เลือกอยู่",
                              variant="soft", color_scheme="amber",
                              size="2", disabled=True),
                    rx.button(
                        "สลับไป",
                        rx.icon("arrow-right", size=14),
                        on_click=lambda: AppState.switch_project(p["id"]),
                        variant="outline", color_scheme="amber", size="2",
                        cursor="pointer", disabled=~p["exists"],
                    ),
                ),
                rx.cond(
                    ~p["is_default"],
                    rx.icon_button(
                        rx.icon("trash-2", size=14),
                        on_click=lambda: AppState.request_delete(p["id"]),
                        variant="ghost", color_scheme="gray", size="2",
                        cursor="pointer",
                    ),
                    rx.fragment(),
                ),
                spacing="1", align="center",
            ),
            spacing="3", align="center", width="100%",
        ),
        padding="1rem",
        background=rx.cond(is_active, c(2, accent=True), "white"),
        border=rx.cond(
            is_active,
            f"1px solid {c(7, accent=True)}",
            f"1px solid {c(4)}",
        ),
        border_radius=RADIUS["md"],
        transition="all 0.15s ease",
        _hover=rx.cond(
            is_active, {},
            {"border_color": c(6, accent=True),
             "background": c(1, accent=True),
             "transform": "translateY(-1px)",
             "box_shadow": f"0 2px 8px {c(5, alpha=True)}"},
        ),
    )


def project_list() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("list", size=14, color=c(10)),
            rx.text("โปรเจกต์ทั้งหมด", size="2",
                    weight="medium", color=c(11)),
            rx.badge(rx.text(AppState.project_count.to_string()),
                     color_scheme="gray", variant="soft", size="1"),
            rx.spacer(),
            spacing="2", align="center", margin_bottom="0.6rem",
            width="100%",
        ),
        rx.foreach(AppState.projects_data, project_row),
        spacing="2", width="100%",
    )


def render() -> rx.Component:
    return rx.vstack(
        page_header(
            breadcrumb=["Workspace", "โปรเจกต์"],
            title="จัดการโปรเจกต์",
            subtitle=("แต่ละโปรเจกต์เก็บไฟล์แยกกัน — เลือกโปรเจกต์ที่จะ"
                      "ทำงาน หรือสร้างใหม่ได้"),
            action=rx.button(
                rx.icon("plus", size=14),
                "สร้างโปรเจกต์ใหม่",
                on_click=AppState.toggle_create_form,
                color_scheme="amber", size="3",
                cursor="pointer",
            ),
        ),
        active_project_card(),
        create_project_form(),
        project_list(),
        delete_confirm_dialog(),
        spacing="0", width="100%",
    )
