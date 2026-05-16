"""ui.py — Central UI library for INKEXTRACT.

ทุก component ของ UI ผ่าน module นี้ → ปรับ theme/รูปแบบที่เดียว
หลักการ:
- semantic ก่อน decoration
- tooltip ทุกปุ่ม/input ที่ผู้ใช้กระทำได้
- description ใส่เฉพาะกรณีที่ความหมายไม่ชัดในตัวมันเอง
"""
from __future__ import annotations
import streamlit as st
from contextlib import contextmanager
from typing import Optional, Iterable

# ===== ธีมสีส้ม INKEXTRACT =====
ORANGE_PRIMARY = "#F57C00"
ORANGE_DARK = "#E65100"
ORANGE_LIGHT = "#FFB74D"
ORANGE_BG = "#FFF3E0"
TEXT_DARK = "#3E2723"
GRAY_BORDER = "#E0E0E0"

APP_NAME = "INKEXTRACT"
APP_TAGLINE = "เครื่องมือจัดการนิยายแปล — ตรวจ • คัด • รวม • แยก • คำศัพท์"

_GLOBAL_CSS = f"""
<style>
/* ============================================================
* Sarabun font + Material Symbols (icons แทน emoji)
* ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
/* Streamlit ใช้ Material Symbols Rounded เป็นหลัก — ต้อง import ก่อน Outlined */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..700,0..1,-50..200&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..700,0..1,-50..200&display=swap');

/* Sarabun for ALL text EXCEPT material icons + monospace
   Streamlit renders :material/<name>: as <span role="img" aria-label="<name> icon" ...>
   ดังนั้น :not([role="img"]) ที่ aria-label ลงท้ายด้วย " icon" → ข้าม */
html body .stApp,
html body .stApp *:not([role="img"]):not([data-testid$="Icon"]):not([data-testid*="Material"]):not([class*="material-symbols"]):not([class*="material-icons"]):not(.micon):not(pre):not(code) {{
    font-family: 'Sarabun', 'Tahoma', 'Microsoft YaHei', sans-serif !important;
}}
html body .stApp pre, html body .stApp code,
html body .stApp .ms-preview-wrap pre, html body .vc-result .file {{
    font-family: 'Consolas', 'Courier New', 'Liberation Mono', monospace !important;
}}

/* Defensive: belt-and-suspenders for Material icons.
   Streamlit: <span role="img" aria-label="<name> icon" style="font-family:'Material Symbols Rounded'">name</span>
   เราต้อง override font-family inline style → ใช้ !important + match by role/aria. */
html body .stApp span[role="img"][aria-label$=" icon"],
html body .stApp [data-testid$="Icon"],
html body .stApp [data-testid*="Material"],
html body .stApp [class*="material-symbols"],
html body .stApp [class*="material-icons"],
html body .stApp span.micon,
html body .stApp .micon {{
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
    font-weight: normal !important;
    font-style: normal !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased !important;
    font-feature-settings: 'liga' !important;
}}
html body .stApp span.micon {{
    font-size: 1.1em;
    display: inline-flex; vertical-align: middle;
    color: inherit;
    font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
}}
html body .stApp .micon.lg {{ font-size: 1.6em; }}
html body .stApp .micon.xl {{ font-size: 2.2em; }}

/* ============================================================
* Theme tokens — light defaults, dark overrides via media query
* + Streamlit's [data-theme="dark"] attribute (covers manual toggle)
* ============================================================ */
:root {{
    /* radius scale — consistent across all components */
    --ink-radius-sm: 6px;
    --ink-radius-md: 8px;
    --ink-radius-lg: 10px;
    --ink-radius-xl: 14px;
    --ink-radius-pill: 999px;
    /* brand orange — same in both themes */
    --ink-orange: {ORANGE_PRIMARY};
    --ink-orange-dark: {ORANGE_DARK};
    --ink-orange-light: {ORANGE_LIGHT};

    /* surfaces */
    --ink-surface: #FFFFFF;
    --ink-surface-2: #FAFAFA;
    --ink-surface-tint: #FFF8E1;
    --ink-surface-tint-strong: #FFF3E0;
    --ink-surface-input: #FFFFFF;

    /* text */
    --ink-text: #212121;
    --ink-text-strong: #3E2723;
    --ink-text-muted: #6D4C41;
    --ink-text-faint: #9E9E9E;

    /* borders */
    --ink-border: #E0E0E0;
    --ink-border-soft: #EEEEEE;
    --ink-border-orange: #FFB74D;

    /* status */
    --ink-success: #2E7D32;
    --ink-success-bg: #E8F5E9;
    --ink-warn: #C62828;
    --ink-warn-bg: #FFEBEE;

    /* shadows */
    --ink-shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --ink-shadow-md: 0 2px 8px rgba(0,0,0,0.06);
    --ink-shadow-lg: 0 8px 18px rgba(245,124,0,0.18);
}}

/* dark mode — auto via system preference */
@media (prefers-color-scheme: dark) {{
    :root {{
        --ink-orange: #FFA726;
        --ink-orange-dark: #FFB74D;
        --ink-orange-light: #FFD180;

        --ink-surface: #1E2129;
        --ink-surface-2: #262730;
        --ink-surface-tint: rgba(255,167,38,0.10);
        --ink-surface-tint-strong: rgba(255,167,38,0.16);
        --ink-surface-input: #2A2D36;

        --ink-text: #FAFAFA;
        --ink-text-strong: #FFFFFF;
        --ink-text-muted: #C7B9B0;
        --ink-text-faint: #8B8B8B;

        --ink-border: #3D434B;
        --ink-border-soft: #2E333B;
        --ink-border-orange: #FFB74D;

        --ink-success: #81C784;
        --ink-success-bg: rgba(46,125,50,0.20);
        --ink-warn: #EF9A9A;
        --ink-warn-bg: rgba(198,40,40,0.20);

        --ink-shadow-sm: 0 1px 3px rgba(0,0,0,0.30);
        --ink-shadow-md: 0 2px 10px rgba(0,0,0,0.35);
        --ink-shadow-lg: 0 8px 22px rgba(0,0,0,0.45);
    }}
}}

/* dark mode — Streamlit manual toggle (data-theme attribute on body/html) */
[data-theme="dark"] {{
    --ink-orange: #FFA726;
    --ink-orange-dark: #FFB74D;
    --ink-orange-light: #FFD180;

    --ink-surface: #1E2129;
    --ink-surface-2: #262730;
    --ink-surface-tint: rgba(255,167,38,0.10);
    --ink-surface-tint-strong: rgba(255,167,38,0.16);
    --ink-surface-input: #2A2D36;

    --ink-text: #FAFAFA;
    --ink-text-strong: #FFFFFF;
    --ink-text-muted: #C7B9B0;
    --ink-text-faint: #8B8B8B;

    --ink-border: #3D434B;
    --ink-border-soft: #2E333B;
    --ink-border-orange: #FFB74D;

    --ink-success: #81C784;
    --ink-success-bg: rgba(46,125,50,0.20);
    --ink-warn: #EF9A9A;
    --ink-warn-bg: rgba(198,40,40,0.20);

    --ink-shadow-sm: 0 1px 3px rgba(0,0,0,0.30);
    --ink-shadow-md: 0 2px 10px rgba(0,0,0,0.35);
    --ink-shadow-lg: 0 8px 22px rgba(0,0,0,0.45);
}}

/* ============================================================
* Buttons — uniform size + orange theme + consistent radius
* ============================================================ */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    height: 46px !important;
    min-height: 46px !important;
    padding: 10px 22px !important;
    border-radius: var(--ink-radius-md) !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    line-height: 1.3 !important;
    transition: all 0.15s !important;
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: var(--ink-orange) !important;
    color: white !important;
    border: 1px solid var(--ink-orange-dark) !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: var(--ink-orange-dark) !important;
    border-color: var(--ink-orange-dark) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(245,124,0,0.30);
}}
.stButton > button[kind="secondary"]:hover {{
    border-color: var(--ink-orange) !important;
    color: var(--ink-orange-dark) !important;
}}

/* Tabs — main + sub tabs ใหญ่ขึ้น อ่านง่าย */
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: var(--ink-orange) !important;
    height: 3px !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--ink-orange-dark) !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    padding: 0.85rem 1.4rem !important;
    height: auto !important;
    min-height: 52px !important;
}}
.stTabs [data-baseweb="tab"] p {{
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
}}
/* tab icon (Material Symbols) ใหญ่ขึ้นตามตัวอักษร */
.stTabs [data-baseweb="tab"] span[role="img"][aria-label$=" icon"] {{
    font-size: 1.25em !important;
    margin-right: 0.4rem !important;
}}
/* tab-list ระยะห่างเพิ่ม */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.25rem !important;
}}

/* Progress + metric */
.stProgress > div > div > div > div {{ background-color: var(--ink-orange); }}
[data-testid="stMetricValue"] {{ color: var(--ink-orange-dark); }}

/* st.pills + st.segmented_control — pill-shaped, orange-active */
[data-testid="stPills"] button, [data-testid="stSegmentedControl"] button {{
    border-radius: var(--ink-radius-pill) !important;
    font-weight: 600 !important;
}}

/* Inputs — uniform radius + theme bg + ขนาดใหญ่ขึ้น */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div, .stTextArea textarea {{
    border-radius: var(--ink-radius-md) !important;
    font-size: 1rem !important;
}}
.stTextInput input, .stNumberInput input {{
    min-height: 46px !important;
    padding: 10px 14px !important;
}}
/* Input labels */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stMultiSelect label, .stTextArea label, .stCheckbox label,
.stRadio label, .stSlider label, .stFileUploader label,
.stDateInput label, .stTimeInput label, .stToggle label {{
    font-size: 0.98rem !important;
    font-weight: 500 !important;
}}
/* Checkbox / Toggle text */
.stCheckbox p, .stToggle p, .stRadio p {{
    font-size: 1rem !important;
}}

/* ============================================================
 * Selectbox / Multiselect dropdown popup — รายการสูงขึ้น อ่านง่าย
 *
 * Trick: Streamlit ใช้ baseweb virtual scroll ที่ position <li> ด้วย absolute
 * + height=40px คงที่ — ทำให้แก้ขนาดยาก ถ้าใส่ min-height ตรงๆ จะ overlap
 *
 * วิธีแก้: บังคับ position:relative + auto height + override top/left
 * → ทำลาย virtual scroll แต่ stacking ตามปกติ ใส่ขนาดเท่าไหร่ก็ได้
 *   (เหมาะกับ dropdown < 50 รายการ ซึ่งแอปนี้ใช้ทั้งหมด)
 * ============================================================ */
ul[role="listbox"] {{
    height: auto !important;
    max-height: 360px !important;
    overflow-y: auto !important;
    padding: 0.3rem 0 !important;
}}
ul[role="listbox"] li[role="option"] {{
    position: relative !important;
    top: auto !important;
    left: auto !important;
    height: auto !important;
    min-height: 52px !important;
    padding: 0.75rem 1rem !important;
    font-size: 1rem !important;
    line-height: 1.45 !important;
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
}}
ul[role="listbox"] li[role="option"] > div,
ul[role="listbox"] li[role="option"] > div > div {{
    width: 100% !important;
    font-size: 1rem !important;
    line-height: 1.45 !important;
    padding: 0 !important;
}}
ul[role="listbox"] li[role="option"]:hover {{
    background: var(--ink-surface-tint, #fff7ed) !important;
}}
ul[role="listbox"] li[role="option"][aria-selected="true"] {{
    background: var(--ink-orange, #f97316) !important;
    color: white !important;
    font-weight: 600 !important;
}}
ul[role="listbox"] li[role="option"][aria-selected="true"] > div,
ul[role="listbox"] li[role="option"][aria-selected="true"] > div > div {{
    color: white !important;
}}
/* ขยายความกว้าง dropdown popup เพื่อไม่ตัดข้อความ */
div[data-baseweb="popover"] ul[role="listbox"] {{
    min-width: 320px !important;
}}
/* ขยาย container ที่ครอบ ul (baseweb ใส่ height คงที่ = items*40px) */
div[data-baseweb="popover"] > div[data-baseweb="menu"] > div {{
    height: auto !important;
    max-height: 360px !important;
}}
/* Selectbox input field — match กับ dropdown */
.stSelectbox div[data-baseweb="select"] > div {{
    min-height: 46px !important;
    font-size: 1rem !important;
}}

/* ============================================================
 * File uploader — drag-drop dropzone (สวย ๆ + ใหญ่ + drag feedback)
 * ============================================================ */
[data-testid="stFileUploaderDropzone"] {{
    background: var(--ink-surface-tint) !important;
    border: 2px dashed var(--ink-border-orange) !important;
    border-radius: var(--ink-radius-xl) !important;
    padding: 1.5rem !important;
    min-height: 120px !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stFileUploaderDropzone"]:hover {{
    background: var(--ink-surface-tint-strong) !important;
    border-color: var(--ink-orange) !important;
    transform: translateY(-1px);
    box-shadow: var(--ink-shadow-md);
}}
/* drag-over visual feedback */
[data-testid="stFileUploaderDropzone"][aria-disabled="false"]:focus-within,
[data-testid="stFileUploaderDropzone"]:active {{
    background: var(--ink-surface-tint-strong) !important;
    border-color: var(--ink-orange-dark) !important;
    box-shadow: 0 0 0 4px rgba(245,124,0,0.15);
}}
/* Browse button inside dropzone — ส้ม + uniform กับปุ่มอื่น */
[data-testid="stFileUploaderDropzone"] button {{
    background: var(--ink-orange) !important;
    color: white !important;
    border: 1px solid var(--ink-orange-dark) !important;
    font-weight: 600 !important;
}}
[data-testid="stFileUploaderDropzone"] button:hover {{
    background: var(--ink-orange-dark) !important;
}}
/* "Drag and drop file here" + "200MB per file" instructions */
[data-testid="stFileUploaderDropzoneInstructions"] {{
    color: var(--ink-text-muted) !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] span {{
    color: var(--ink-text-faint) !important;
    font-size: 0.85em !important;
}}

/* Uploaded file row */
[data-testid="stFileUploaderFile"] {{
    background: var(--ink-surface) !important;
    border: 1px solid var(--ink-border) !important;
    border-radius: var(--ink-radius-md) !important;
    padding: 8px 12px !important;
    margin-top: 8px !important;
}}

/* Checkbox + radio labels — readable in both themes */
.stCheckbox label, .stRadio label, .stMultiSelect label {{ color: var(--ink-text) !important; }}

/* ============================================================
* INKEXTRACT app header — orange gradient, white text on both themes
* ============================================================ */
.ink-header {{
    background: linear-gradient(135deg, {ORANGE_PRIMARY} 0%, {ORANGE_DARK} 100%);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 14px rgba(245,124,0,0.25);
    color: white;
}}
.ink-header h1 {{
    margin: 0; color: white; font-size: 2rem; letter-spacing: 1px;
    font-weight: 800;
}}
.ink-header p {{ margin: 0.25rem 0 0; color: #FFE0B2; font-size: 0.95rem; }}
.ink-header-row {{
    display: flex; align-items: center; gap: 1rem;
}}
.ink-header-text {{ flex: 1; min-width: 0; }}
.ink-logo {{
    width: 56px; height: 56px; flex-shrink: 0;
    border-radius: 12px;
    background: rgba(255,255,255,0.95);
    padding: 4px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}}
.ink-version-badge {{
    display: inline-block;
    margin-left: 0.6rem;
    padding: 2px 10px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 999px;
    font-size: 0.6em; font-weight: 600;
    color: white;
    vertical-align: middle;
    letter-spacing: 0.3px;
}}
.ink-install-root {{
    margin: 0.35rem 0 0; font-size: 0.7rem !important;
    color: rgba(255,255,255,0.75) !important;
    font-family: monospace;
}}
.ink-install-root code {{
    background: rgba(0,0,0,0.18);
    color: #ffe6cc;
    padding: 1px 6px; border-radius: 4px;
    font-size: 0.95em;
}}

/* ============================================================
* Section card
* ============================================================ */
.ink-section {{
    border: 1px solid var(--ink-border);
    border-left: 4px solid var(--ink-orange);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin: 0.75rem 0 1rem;
    background: var(--ink-surface);
    color: var(--ink-text);
}}
.ink-section h3 {{ margin: 0 0 0.25rem; color: var(--ink-orange-dark); font-size: 1.1rem; }}
.ink-section p.ink-desc {{ color: var(--ink-text-muted); font-size: 0.85rem; margin: 0 0 0.6rem; }}

/* ============================================================
* Chip
* ============================================================ */
.ink-chip {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    background: var(--ink-surface-tint-strong); color: var(--ink-orange-dark);
    font-size: 0.8rem; font-weight: 600; margin-right: 6px;
    border: 1px solid var(--ink-border-orange);
}}
</style>
"""


def apply_theme() -> None:
    """ใส่ CSS theme ระดับ global — ต้องเรียกทุก rerun
    (Streamlit ลบ markdown ที่ไม่ถูก emit ในรอบ rerun ใหม่)"""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def _resolve_logo_path() -> Optional[str]:
    """หาโลโก้ inkideaex.png — ลำดับ:
      1. .app/inkideaex.png  (อยู่กับ source — กันโดนลบ)
      2. <ROOT>/inkideaex.png  (legacy fallback)
    """
    try:
        from . import paths
        # Priority 1: ติดมากับ source code ใน .app/
        app_logo = paths.APP_DIR / "inkideaex.png"
        if app_logo.exists():
            return str(app_logo)
        # Priority 2: legacy ที่ root
        root_logo = paths.ROOT / "inkideaex.png"
        if root_logo.exists():
            return str(root_logo)
    except Exception:
        pass
    return None


def _read_app_version() -> str:
    """อ่านเวอร์ชันจาก .app/VERSION (string เช่น '1.1.2'). คืน '?' ถ้าอ่านไม่ได้"""
    try:
        from . import paths
        version_file = paths.APP_DIR / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip() or '?'
    except Exception:
        pass
    return '?'


def get_install_root() -> str:
    """คืน path ของ INKEXTRACT install ที่กำลังรันอยู่ — ใช้ใน UI diagnostic
    เพื่อให้ user เห็นชัดเจนว่ารัน install ไหน (เผื่อมีหลายชุดในเครื่องเดียว)
    """
    try:
        from . import paths
        return str(paths.ROOT)
    except Exception:
        return '?'


def page_setup(page_title: str = APP_NAME, page_icon: Optional[str] = None) -> None:
    """ตั้งค่า page + theme ในการเรียกครั้งเดียว.

    ถ้าไม่ระบุ page_icon จะลองโหลด `inkideaex.png` จาก root โปรเจกต์เป็น default
    """
    if page_icon is None:
        page_icon = _resolve_logo_path() or ""
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout="wide")
    apply_theme()


def header(title: str = APP_NAME, tagline: str = APP_TAGLINE) -> None:
    """หัวหน้าเพจสีส้ม — แสดงโลโก้ + เวอร์ชัน + install root"""
    logo_path = _resolve_logo_path()
    if logo_path:
        try:
            import base64
            with open(logo_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            logo_html = (
                f'<img src="data:image/png;base64,{b64}" '
                f'class="ink-logo" alt="logo" />'
            )
        except Exception:
            logo_html = ''
    else:
        logo_html = ''

    version = _read_app_version()
    install_root = get_install_root()
    version_html = (
        f'<span class="ink-version-badge" title="install ที่กำลังรัน: {install_root}">'
        f'v{version}</span>'
    )

    st.markdown(
        f"""<div class="ink-header">
            <div class="ink-header-row">
                {logo_html}
                <div class="ink-header-text">
                    <h1>{title} {version_html}</h1>
                    <p>{tagline}</p>
                    <p class="ink-install-root">install: <code>{install_root}</code></p>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


@contextmanager
def section(title: str, description: Optional[str] = None, icon: str = ""):
    """กล่องส่วนหนึ่งของหน้า — ใช้แทน st.markdown('### ...')

    Usage:
        with ui.section("ตรวจคำแปล", description="..."):
            ...
            """
    icon_part = f"{icon} " if icon else ""
    desc = f'<p class="ink-desc">{description}</p>' if description else ''
    st.markdown(
        f'<div class="ink-section"><h3>{icon_part}{title}</h3>{desc}</div>',
        unsafe_allow_html=True,
    )
    yield


def kpi_row(items: Iterable[tuple]) -> None:
    """แสดงแถว KPI / metric — รับ tuples (label, value, [help])"""
    items = list(items)
    if not items:
        return
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        if len(item) == 3:
            label, value, help_text = item
        else:
            label, value = item
            help_text = None
        with col:
            st.metric(label, value, help=help_text)


def primary_button(label: str, *, help: Optional[str] = None, key: Optional[str] = None,
                   disabled: bool = False, width: str = "stretch") -> bool:
    """ปุ่มหลัก (สีส้ม) — tooltip บังคับให้ใส่ผ่าน help"""
    return st.button(
        label, type="primary", help=help, key=key,
        disabled=disabled, width=width,
    )


def secondary_button(label: str, *, help: Optional[str] = None, key: Optional[str] = None,
                     disabled: bool = False, width: str = "stretch") -> bool:
    """ปุ่มรอง"""
    return st.button(
        label, type="secondary", help=help, key=key,
        disabled=disabled, width=width,
    )


def info(message: str) -> None:
    st.info(message)


def success(message: str) -> None:
    st.success(message)


def warning(message: str) -> None:
    st.warning(message)


def error(message: str) -> None:
    st.error(message)


def chip(label: str) -> str:
    """คืน HTML chip — ใช้ใน inline markdown"""
    return f'<span class="ink-chip">{label}</span>'


def format_bytes(n: float) -> str:
    """ฟอร์แมตขนาดไฟล์ — ตรงกับ noveleditor edition"""
    if n <= 0:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.2f} {units[i]}"


# CSS เฉพาะหน้าตรวจต้นฉบับ — ใช้ token เดียวกับ global
MANUSCRIPT_CSS = """
<style>
/* ===== Stats grid (shared with vocab tab via .vc-stats) ===== */
.ms-stats {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px; margin-bottom: 1rem;
}
.ms-stat-card {
    background: var(--ink-surface);
    padding: 16px 14px;
    border-radius: var(--ink-radius-lg);
    border: 1px solid var(--ink-border);
    border-top: 4px solid var(--ink-orange);
    text-align: center;
    box-shadow: var(--ink-shadow-md);
    transition: transform 0.15s, box-shadow 0.15s;
    color: var(--ink-text);
}
.ms-stat-card:hover { transform: translateY(-2px); box-shadow: var(--ink-shadow-lg); }
.ms-stat-card .label {
    font-size: 0.78em; color: var(--ink-text-muted);
    margin-bottom: 8px; letter-spacing: 0.3px; font-weight: 600;
    text-transform: uppercase;
}
.ms-stat-card .value {
    font-size: 1.55em; font-weight: 800;
    color: var(--ink-orange-dark); line-height: 1;
}

/* ===== Pane header ===== */
.ms-pane-header {
    padding: 12px 16px;
    background: var(--ink-surface-tint-strong);
    border: 1px solid var(--ink-border);
    border-bottom: 2px solid var(--ink-orange);
    border-radius: var(--ink-radius-lg) var(--ink-radius-lg) 0 0;
    font-weight: 700;
    color: var(--ink-orange-dark);
    font-size: 1.02em;
    display: flex; align-items: center; gap: 6px;
}

/* ===== File row (explorer) ===== */
.ms-row {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    background: var(--ink-surface);
    border: 1.5px solid var(--ink-border);
    border-radius: var(--ink-radius-md);
    margin-bottom: 6px; transition: all 0.15s; cursor: default;
    color: var(--ink-text);
}
.ms-row:hover {
    background: var(--ink-surface-tint);
    border-color: var(--ink-orange-light);
    transform: translateX(2px);
}
.ms-row.small { background: var(--ink-warn-bg); border-color: var(--ink-warn); }
.ms-row.active {
    background: var(--ink-surface-tint-strong);
    border-color: var(--ink-orange);
    box-shadow: 0 0 0 2px rgba(245,124,0,0.18);
}
.ms-row .icon { font-size: 1.1em; }
.ms-row .info { flex: 1; min-width: 0; }
.ms-row .name {
    font-weight: 600; color: var(--ink-text);
    font-size: 0.92em; word-break: break-word; line-height: 1.35;
}
.ms-row .size { font-size: 0.78em; color: var(--ink-text-muted); margin-top: 2px; }
.ms-row.small .size { color: var(--ink-warn); font-weight: 600; }

/* ===== List row buttons — compact ===== */
[data-testid="stHorizontalBlock"] .stCheckbox { margin-top: 4px; }

/* ===== Preview pane (VS-Code feel) =====
 * ความสูง 560px เท่ากับฝั่ง file list — ขอบและมุมลงล็อกกัน
 */
.ms-preview-wrap {
    border: 1px solid var(--ink-border); border-top: 0;
    border-radius: 0 0 var(--ink-radius-lg) var(--ink-radius-lg);
    background: var(--ink-surface-2);
    padding: 0; overflow: hidden;
}
.ms-preview-wrap [data-testid="stCode"] {
    border: none !important; background: transparent !important;
}
.ms-preview-wrap pre {
    font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace !important;
    font-size: 13px !important; line-height: 1.55 !important;
    color: var(--ink-text) !important;
    background: transparent !important;
    padding: 12px 16px !important; margin: 0 !important;
    white-space: pre !important; word-wrap: normal !important;
    tab-size: 4;
}
.ms-preview-wrap .react-syntax-highlighter-line-number {
    color: var(--ink-text-faint) !important;
    opacity: 0.55;
    user-select: none;
    border-right: 1px solid var(--ink-border);
    margin-right: 0.5em !important;
    padding-right: 0.75em !important;
}
.ms-preview-empty {
    background: var(--ink-surface-2);
    border: 1px dashed var(--ink-border); border-top: 0;
    border-radius: 0 0 var(--ink-radius-lg) var(--ink-radius-lg);
    height: 560px;
    display: flex; align-items: center; justify-content: center;
    text-align: center;
    color: var(--ink-text-faint);
    font-style: italic; font-size: 1.05em;
}

/* ===== Folder bar wrap ===== */
.ms-folderbar-wrap {
    background: var(--ink-surface);
    border: 1px solid var(--ink-border);
    border-radius: var(--ink-radius-lg);
    padding: 10px 14px; margin-bottom: 12px;
    box-shadow: var(--ink-shadow-sm);
}

/* ===== Selection count chip ===== */
.ms-count-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: var(--ink-radius-pill);
    background: var(--ink-surface-tint-strong);
    color: var(--ink-orange-dark);
    font-weight: 700; font-size: 0.95em;
    border: 1px solid var(--ink-border-orange);
}
</style>
"""


def apply_manuscript_css() -> None:
    """ใส่ CSS เพิ่มเฉพาะหน้าตรวจต้นฉบับ — ต้องเรียกทุก rerun
    (Streamlit ลบ markdown ที่ไม่ถูก emit ในรอบ rerun ใหม่)"""
    st.markdown(MANUSCRIPT_CSS, unsafe_allow_html=True)


def stats_cards(items: Iterable[tuple]) -> None:
    """แสดงสถิติเป็นการ์ดเรียงเป็น grid (label, value)"""
    items = list(items)
    if not items:
        return
    html_parts = ['<div class="ms-stats">']
    for label, value in items:
        html_parts.append(
            f'<div class="ms-stat-card"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>'
        )
    html_parts.append('</div>')
    st.markdown(''.join(html_parts), unsafe_allow_html=True)
