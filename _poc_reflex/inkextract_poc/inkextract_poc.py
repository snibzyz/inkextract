"""INKEXTRACT Reflex POC — Project tab demo

แสดง: Active project hero card · Project list (active state) · Create new form
Theme: amber (INKREALM brand #F59E0B)
"""
from __future__ import annotations
import reflex as rx
from dataclasses import dataclass


# ── Mock data — match INKEXTRACT real project shape ──────────────────────────
@dataclass
class Project:
    id: str
    name: str
    path: str
    created_at: str
    is_default: bool


INITIAL_PROJECTS = [
    Project("workspace", "Workspace (เดิม)",
            r"Z:\Mega Project\INKEXTRACT\workspace",
            "2026-05-01T00:00:00", True),
    Project("038-1-huayuan", "038 1 หยวน",
            r"Z:\Mega Project\INKEXTRACT\projects\038-1-huayuan",
            "2026-05-10T01:32:11", False),
    Project("ติดหนี้สามสิบล้าน", "ติดหนี้สามสิบล้าน",
            r"Z:\Mega Project\INKEXTRACT\projects\tid-nee-30m",
            "2026-05-12T08:15:00", False),
]


class State(rx.State):
    """App state — Reflex auto-syncs ระหว่าง backend ↔ React frontend"""
    projects: list[dict] = [
        {"id": p.id, "name": p.name, "path": p.path,
         "created_at": p.created_at, "is_default": p.is_default}
        for p in INITIAL_PROJECTS
    ]
    active_id: str = "workspace"
    show_create: bool = False
    new_project_name: str = ""
    stats_expanded: bool = False

    @rx.var
    def active_project(self) -> dict:
        for p in self.projects:
            if p["id"] == self.active_id:
                return p
        return self.projects[0] if self.projects else {}

    @rx.var
    def active_name(self) -> str:
        return self.active_project.get("name", "")

    @rx.var
    def active_path(self) -> str:
        return self.active_project.get("path", "")

    @rx.var
    def active_meta(self) -> str:
        p = self.active_project
        if p.get("is_default"):
            return "เริ่มต้น (ลบไม่ได้)"
        return f"สร้างเมื่อ: {p.get('created_at', '')}"

    @rx.event
    def switch_project(self, project_id: str):
        self.active_id = project_id
        yield rx.toast(f"สลับไปยัง: {self._name_of(project_id)}",
                       position="bottom-right")

    def _name_of(self, project_id: str) -> str:
        for p in self.projects:
            if p["id"] == project_id:
                return p["name"]
        return ""

    @rx.event
    def toggle_create(self):
        self.show_create = not self.show_create

    @rx.event
    def set_new_name(self, value: str):
        self.new_project_name = value

    @rx.event
    def create_project(self):
        name = self.new_project_name.strip()
        if not name:
            yield rx.toast("กรุณากรอกชื่อโปรเจกต์", position="bottom-right")
            return
        new_id = name.lower().replace(" ", "-")
        self.projects.append({
            "id": new_id, "name": name,
            "path": rf"Z:\Mega Project\INKEXTRACT\projects\{new_id}",
            "created_at": "2026-05-17T12:00:00", "is_default": False,
        })
        self.active_id = new_id
        self.new_project_name = ""
        self.show_create = False
        yield rx.toast(f"สร้าง '{name}' สำเร็จ", position="bottom-right")

    @rx.event
    def toggle_stats(self):
        self.stats_expanded = not self.stats_expanded


# ── Amber brand color (INKREALM) ──────────────────────────────────────────────
AMBER_50 = "#FFFBEB"
AMBER_100 = "#FEF3C7"
AMBER_200 = "#FDE68A"
AMBER_400 = "#FBBF24"
AMBER_500 = "#F59E0B"
AMBER_600 = "#D97706"
AMBER_700 = "#B45309"


# ── Components ────────────────────────────────────────────────────────────────
def top_bar() -> rx.Component:
    """แถบบนสุด — INKEXTRACT brand + version"""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("book_open", size=22, color="white"),
                rx.heading("INKEXTRACT", size="5", color="white",
                           weight="bold", letter_spacing="0.5px"),
                rx.text("·", color="rgba(255,255,255,0.5)", size="4"),
                rx.text("เครื่องมือจัดการนิยายแปล",
                        color="rgba(255,255,255,0.9)", size="2"),
                spacing="2", align="center",
            ),
            rx.spacer(),
            rx.badge("v2.0-poc", color_scheme="gray", variant="solid",
                     high_contrast=True),
            width="100%", align="center", padding_x="1.25rem",
            padding_y="0.75rem",
        ),
        background=f"linear-gradient(135deg, {AMBER_500} 0%, {AMBER_600} 100%)",
        box_shadow="0 2px 12px rgba(245,158,11,0.25)",
        border_radius="12px",
        margin_bottom="0.75rem",
    )


def active_bar() -> rx.Component:
    """แถบสลิม 1 บรรทัด แสดงโปรเจกต์ที่ใช้งาน"""
    return rx.hstack(
        rx.icon("folder_open", size=16, color=AMBER_600),
        rx.text("โปรเจกต์ที่ใช้งาน:", size="2",
                color=rx.color("gray", 11)),
        rx.text(State.active_name, size="2", weight="bold",
                color=AMBER_700),
        rx.spacer(),
        rx.code(State.active_path, size="1",
                color=rx.color("gray", 11)),
        background=AMBER_50,
        border_left=f"3px solid {AMBER_500}",
        border_radius="8px",
        padding="0.5rem 0.85rem", spacing="2", align="center",
        margin_bottom="0.6rem",
    )


def stats_card() -> rx.Component:
    """KPI dashboard — collapsible"""
    return rx.card(
        rx.hstack(
            rx.icon("bar_chart_3", size=18, color=AMBER_600),
            rx.text("สถิติการทำงาน", size="2", weight="medium"),
            rx.text("— ต้นฉบับ 2 · แก้ไข 0 · สะอาด 0 · errors 0",
                    size="2", color=rx.color("gray", 11)),
            rx.spacer(),
            rx.icon(
                rx.cond(State.stats_expanded, "chevron_up", "chevron_down"),
                size=16, color=rx.color("gray", 11),
            ),
            cursor="pointer", on_click=State.toggle_stats,
            align="center", spacing="2", width="100%",
        ),
        rx.cond(
            State.stats_expanded,
            rx.grid(
                stat_box("ไฟล์ต้นฉบับ", "2"),
                stat_box("ไฟล์แก้ไข", "0"),
                stat_box("ไฟล์สะอาด", "0"),
                stat_box("ข้อผิดพลาด", "0"),
                columns="4", spacing="3", margin_top="0.75rem",
            ),
        ),
        size="2", margin_bottom="0.75rem",
    )


def stat_box(label: str, value: str) -> rx.Component:
    return rx.box(
        rx.text(label, size="1", color=rx.color("gray", 11)),
        rx.heading(value, size="6", color=AMBER_600, margin_top="0.2rem"),
        padding="0.85rem", border_radius="8px",
        background=rx.color("gray", 2),
        border=f"1px solid {rx.color('gray', 5)}",
    )


def tab_nav() -> rx.Component:
    """Tabs row"""
    tabs = [
        ("folder_open", "โปรเจกต์", True),
        ("file_check_2", "ตรวจต้นฉบับ", False),
        ("book", "คำศัพท์", False),
        ("spell_check", "ตรวจสอบและแก้ไข", False),
        ("folder", "จัดการไฟล์", False),
    ]
    return rx.hstack(
        *[tab_item(i, l, a) for i, l, a in tabs],
        spacing="1",
        padding_bottom="0px",
        border_bottom=f"1px solid {rx.color('gray', 5)}",
        margin_bottom="1rem",
    )


def tab_item(icon: str, label: str, active: bool) -> rx.Component:
    return rx.hstack(
        rx.icon(icon, size=16,
                color=AMBER_600 if active else rx.color("gray", 11)),
        rx.text(label, size="2", weight="bold" if active else "medium",
                color=AMBER_700 if active else rx.color("gray", 11)),
        padding="0.7rem 1rem",
        border_bottom=f"3px solid {AMBER_500 if active else 'transparent'}",
        cursor="pointer",
        spacing="2", align="center",
        _hover={"background": rx.color("gray", 3)} if not active else {},
    )


def active_project_card() -> rx.Component:
    """Hero card — active project (gradient amber + big name)"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("folder_open", size=18, color=AMBER_600),
                rx.text("โปรเจกต์ที่ใช้งานอยู่", size="1",
                        color=AMBER_700, weight="bold",
                        letter_spacing="0.8px",
                        style={"textTransform": "uppercase"}),
                spacing="2", align="center",
            ),
            rx.heading(State.active_name, size="8",
                       color=AMBER_700, weight="bold",
                       margin_top="0.3rem"),
            rx.hstack(
                rx.icon("folder", size=14, color=AMBER_600),
                rx.code(State.active_path, size="2",
                        color=rx.color("gray", 12)),
                background="white",
                border=f"1px solid {rx.color('gray', 5)}",
                border_radius="8px",
                padding="6px 12px", spacing="2", align="center",
                width="fit-content",
                margin_top="0.4rem",
            ),
            rx.text(State.active_meta, size="1",
                    color=rx.color("gray", 11), margin_top="0.4rem"),
            rx.hstack(
                rx.button(
                    rx.icon("folder_open", size=14),
                    "เปิดโฟลเดอร์ในระบบ",
                    variant="soft", color_scheme="amber",
                    size="2", margin_top="0.6rem",
                    on_click=lambda: rx.toast("เปิดโฟลเดอร์ใน File Explorer",
                                              position="bottom-right"),
                ),
                rx.button(
                    rx.icon("settings_2", size=14),
                    "ตั้งค่า", variant="ghost", color_scheme="gray",
                    size="2", margin_top="0.6rem",
                ),
                spacing="2",
            ),
            align="start", spacing="1",
        ),
        background=f"linear-gradient(135deg, {AMBER_50} 0%, {AMBER_100} 100%)",
        border=f"2px solid {AMBER_500}",
        size="3", margin_bottom="1rem",
    )


def create_project_form() -> rx.Component:
    return rx.cond(
        State.show_create,
        rx.card(
            rx.vstack(
                rx.text("ชื่อโปรเจกต์ใหม่", size="2", weight="medium"),
                rx.input(
                    placeholder="เช่น 'ติดหนี้สามสิบล้าน' หรือ 'นิยายของฉัน A'",
                    value=State.new_project_name,
                    on_change=State.set_new_name,
                    size="3", width="100%",
                ),
                rx.text(
                    "โฟลเดอร์ย่อย (Raw, Input, Fix, Clean, …) จะถูกสร้างให้ทันที",
                    size="1", color=rx.color("gray", 11),
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("plus", size=14),
                        "สร้างและสลับไปใช้งาน",
                        on_click=State.create_project,
                        color_scheme="amber", size="2",
                    ),
                    rx.button(
                        "ยกเลิก", variant="soft", color_scheme="gray",
                        size="2", on_click=State.toggle_create,
                    ),
                    spacing="2",
                ),
                spacing="2", align="start", width="100%",
            ),
            margin_bottom="0.75rem",
        ),
        rx.button(
            rx.icon("circle_plus", size=16),
            "สร้างโปรเจกต์ใหม่",
            on_click=State.toggle_create,
            color_scheme="amber", variant="outline",
            size="3", width="100%", margin_bottom="0.75rem",
        ),
    )


def project_row(p: dict) -> rx.Component:
    """แถวรายการโปรเจกต์ — active state พื้นหลังส้ม + border ส้มเด่น"""
    is_active = p["id"] == State.active_id
    return rx.hstack(
        rx.icon(
            rx.cond(is_active, "circle_dot", "circle"),
            size=20,
            color=rx.cond(is_active, AMBER_500, rx.color("gray", 9)),
        ),
        rx.vstack(
            rx.hstack(
                rx.text(p["name"], size="3",
                        weight="bold",
                        color=rx.cond(is_active, AMBER_700,
                                      rx.color("gray", 12))),
                rx.cond(p["is_default"],
                        rx.badge("เริ่มต้น", color_scheme="amber",
                                 variant="soft", size="1"),
                        rx.fragment()),
                spacing="2", align="center",
            ),
            rx.code(p["path"], size="1", color=rx.color("gray", 11)),
            spacing="1", align="start", flex="1", min_width="0",
        ),
        rx.spacer(),
        rx.cond(
            is_active,
            rx.hstack(
                rx.icon("circle_check_big", size=14, color=AMBER_600),
                rx.text("กำลังใช้งาน", size="2", weight="bold",
                        color=AMBER_700),
                spacing="1", align="center",
                padding="0.5rem 0.85rem",
                background="white",
                border=f"1px solid {AMBER_200}",
                border_radius="999px",
            ),
            rx.button(
                rx.icon("arrow_right_left", size=14),
                "สลับไป", size="2", color_scheme="amber",
                on_click=lambda: State.switch_project(p["id"]),
            ),
        ),
        padding="0.85rem 1rem", border_radius="10px",
        background=rx.cond(is_active, AMBER_50, "white"),
        border=rx.cond(is_active,
                       f"2px solid {AMBER_500}",
                       f"1px solid {rx.color('gray', 5)}"),
        align="center", spacing="3", width="100%",
        transition="all 0.15s ease",
        _hover=rx.cond(
            is_active,
            {},
            {"border_color": AMBER_200, "background": rx.color("gray", 2)},
        ),
    )


def project_list() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("โปรเจกต์ทั้งหมด", size="2",
                    color=rx.color("gray", 11)),
            rx.badge(rx.text(State.projects.length()),
                     color_scheme="gray", variant="soft"),
            spacing="2", align="center", margin_bottom="0.4rem",
        ),
        rx.foreach(State.projects, project_row),
        spacing="2", width="100%",
    )


def project_tab_content() -> rx.Component:
    return rx.vstack(
        active_project_card(),
        rx.text("เลือก / สร้างโปรเจกต์", size="3",
                weight="bold", margin_top="0.5rem",
                margin_bottom="0.3rem"),
        create_project_form(),
        project_list(),
        spacing="2", width="100%",
    )


def index() -> rx.Component:
    return rx.box(
        rx.container(
            top_bar(),
            active_bar(),
            stats_card(),
            tab_nav(),
            project_tab_content(),
            size="4",
            padding_y="1rem",
        ),
        min_height="100vh",
        background=rx.color("gray", 1),
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
        "fontFamily": "'Sarabun', 'Tahoma', 'Microsoft YaHei', sans-serif",
    },
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap",
    ],
)
app.add_page(index, title="INKEXTRACT — POC Reflex")
