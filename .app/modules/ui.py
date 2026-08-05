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

# ===== ธีมสีส้ม INKEXTRACT — aligned กับ INKREALM amber (#F59E0B)
# = single source of truth ของตระกูล INK · ตาม E:\Mega Project\CLAUDE.md §4 =====
ORANGE_PRIMARY = "#F59E0B"   # amber-500 — primary brand
ORANGE_DARK = "#D97706"      # amber-600 — hover/active
ORANGE_LIGHT = "#FBBF24"     # amber-400 — accent/highlight
ORANGE_BG = "#FEF3C7"        # amber-100 — soft tint background
TEXT_DARK = "#3E2723"
GRAY_BORDER = "#E0E0E0"

APP_NAME = "INKEXTRACT"
APP_TAGLINE = "เครื่องมือจัดการนิยายแปล — ตรวจ • คัด • รวม • แยก • คำศัพท์"

_GLOBAL_CSS = f"""
<style>
/* ============================================================
* Sarabun font + Material Symbols (icons แทน emoji)
* NOTE: @import ใน <style> เป็น render-blocking — รู้ว่าช้ากว่า <link>
* แต่ใส่ <link> นอก <style> ผ่าน st.markdown แล้ว Streamlit markdown
* จะ escape `<style>` ที่ตามมา → CSS ทั้งก้อนกลายเป็น text ไม่โหลด
* (ทดสอบแล้วบั๊กจริง — revert กลับมาใช้ @import)
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
    /* ── Radius scale ── */
    --ink-radius-sm: 6px;
    --ink-radius-md: 8px;
    --ink-radius-lg: 10px;
    --ink-radius-xl: 14px;
    --ink-radius-pill: 999px;

    /* ── Font size scale (rem-based · 16px base) ── */
    --ink-text-xs: 0.85rem;   /* 13.6px · caption · hint */
    --ink-text-sm: 0.92rem;   /* 14.7px · secondary text */
    --ink-text-base: 1rem;    /* 16px · body, input, button */
    --ink-text-md: 1.05rem;   /* 16.8px · tab, emphasized */
    --ink-text-lg: 1.15rem;   /* 18.4px · sub-header */
    --ink-text-xl: 1.4rem;    /* 22.4px · section header */
    --ink-text-2xl: 1.75rem;  /* 28px · page title */
    --ink-text-3xl: 2.2rem;   /* 35.2px · hero */

    /* ── Control height scale (สม่ำเสมอทั้งระบบ) ── */
    --ink-h-sm: 36px;
    --ink-h-md: 46px;   /* default input/button */
    --ink-h-lg: 52px;   /* tab, dropdown row */

    /* ── Brand orange (both themes) ── */
    --ink-orange: {ORANGE_PRIMARY};
    --ink-orange-dark: {ORANGE_DARK};
    --ink-orange-light: {ORANGE_LIGHT};

    /* ── Accent text — สำหรับข้อความบน amber-tint surface ── */
    /* แยกจาก --ink-orange-dark เพราะ dark mode ต้องสว่างกว่าเพื่อ contrast บน tint */
    --ink-accent-strong: {ORANGE_DARK};   /* light: amber-600 — บน FFF8E1/FFF3E0 ได้ 3:1 (ตามแบรนด์เดิม) */
    /* ── Text/icon บน amber button (solid primary) — WCAG AA target ── */
    --ink-on-primary: #FFFFFF;            /* light: white (brand standard — ยอมแลก WCAG เพื่อความเข้ม) */

    /* ── Light theme (default) ── */
    --ink-surface: #FFFFFF;
    --ink-surface-2: #FAFAFA;
    --ink-surface-tint: #FFF8E1;
    --ink-surface-tint-strong: #FFF3E0;
    --ink-surface-input: #FFFFFF;

    --ink-text: #212121;
    --ink-text-strong: #3E2723;
    --ink-text-muted: #6D4C41;
    --ink-text-faint: #9E9E9E;

    --ink-border: #E0E0E0;
    --ink-border-soft: #EEEEEE;
    --ink-border-orange: #FFB74D;

    --ink-success: #2E7D32;
    --ink-success-bg: #E8F5E9;
    --ink-warn: #C62828;
    --ink-warn-bg: #FFEBEE;

    --ink-shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --ink-shadow-md: 0 2px 8px rgba(0,0,0,0.06);
    --ink-shadow-lg: 0 8px 18px rgba(245,158,11,0.18);
}}

/* ── Dark theme tokens — activate เฉพาะเมื่อ JS observer set html[data-theme="dark"] ──
 *
 * เคยใช้ @media (prefers-color-scheme: dark) แต่พังหนัก:
 *   OS=dark + user pick "Light" ใน Streamlit menu → Streamlit ทำ bg=ขาว แต่
 *   @media รัน → tokens เป็น dark → text ขาวบน bg ขาว = อ่านไม่ออก
 *
 * Solution: ตัด @media ออก ให้ JS observer (_DARK_DETECT_HTML) อ่าน bg จริง
 *   ของ .stApp แล้ว set/remove html[data-theme="dark"] = single source of truth
 *   (config.toml + native menu + OS pref → ผ่าน Streamlit → bg เปลี่ยน → JS sync)
 * ── */
html[data-theme="dark"],
html[data-theme="dark"] :root,
[data-theme="dark"] {{
    --ink-orange: #FBBF24;
    --ink-orange-dark: #F59E0B;
    --ink-orange-light: #FCD34D;
    /* accent text — สว่างขึ้นเพื่อ contrast บน amber-tint (composite บน dark surface) */
    --ink-accent-strong: #FCD34D;     /* amber-300 — ตัด tint ได้ ~6:1+ */
    /* button-text บน amber bg — dark fg ให้ contrast 9:1+ แทน white (1.67:1) */
    --ink-on-primary: #1E2129;
    --ink-surface: #1E2129;
    --ink-surface-2: #262730;
    --ink-surface-tint: rgba(251,191,36,0.10);
    --ink-surface-tint-strong: rgba(251,191,36,0.18);
    --ink-surface-input: #2A2D36;
    --ink-text: #FAFAFA;
    --ink-text-strong: #FFFFFF;
    --ink-text-muted: #D4C5BB;        /* bump จาก #C7B9B0 ให้ 5:1+ บน dark surface */
    --ink-text-faint: #B0B0B0;        /* bump จาก #8B8B8B (4.36) → #B0B0B0 (6+) */
    --ink-border: #3D434B;
    --ink-border-soft: #2E333B;
    --ink-border-orange: #FCD34D;
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
/* Primary button family — Streamlit 1.57 ใช้ data-testid ต่างกันต่อ context:
 *   stBaseButton-primary          → st.button(type="primary")
 *   stBaseButton-primaryFormSubmit → st.form_submit_button(type="primary")
 *   kind="primary" attribute       → fallback (เก่า)
 * ใช้ data-testid ครอบทั้ง 2 + universal child selector กัน Streamlit override <p> ภายใน */
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"],
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: var(--ink-orange) !important;
    color: var(--ink-on-primary) !important;  /* light=white · dark=#1E2129 */
    border: 1px solid var(--ink-orange-dark) !important;
}}
[data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-primaryFormSubmit"] *,
.stButton > button[kind="primary"] *,
.stDownloadButton > button[kind="primary"] *,
.stFormSubmitButton > button[kind="primary"] * {{
    color: var(--ink-on-primary) !important;
}}
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover,
.stButton > button[kind="primary"]:hover {{
    background: var(--ink-orange-dark) !important;
    border-color: var(--ink-orange-dark) !important;
    color: var(--ink-on-primary) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(245,124,0,0.30);
}}
.stButton > button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover {{
    border-color: var(--ink-orange) !important;
    color: var(--ink-accent-strong) !important;
}}

/* Tabs — main + sub tabs ใหญ่ขึ้น อ่านง่าย */
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: var(--ink-orange) !important;
    height: 3px !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--ink-accent-strong) !important;
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
[data-testid="stMetricValue"] {{ color: var(--ink-accent-strong); }}

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
 * Selectbox / Multiselect dropdown — แสดงครบทุก option, อ่านง่าย
 *
 * โครงสร้าง DOM จริง (Streamlit 1.51 + baseweb — verified via playwright):
 *   div[data-baseweb="popover"]                    ← outer popover wrapper
 *     div.st-gx                                    ← scrollable wrapper
 *       div.st-h3                                  ← height-auto pass-through
 *         ul                                       ← list container (NO role="listbox")
 *           div [inline height: Npx; overflow: auto; will-change: transform]
 *             div [inline height: Npx; width: 100%]  ← react-window sizer
 *               li[role="option"] [pos:absolute; top:0; height:40px]  ← virtualized items
 *
 * ปัญหา: react-window คำนวณ sizer ที่ N×40px (item count × 40). พอเราขยาย li
 * เป็น 52px ผ่าน CSS, sizer ยังเป็น 40px-base → เนื้อหาล้น & ถูก clip
 *
 * วิธีแก้: kill inline height ของทุก div ระหว่าง ul กับ li → ให้ flex stack
 * ตามจริง แล้ว apply max-height + scroll ที่ ul ตัวเดียว
 * ============================================================ */
/* Item — break virtual scroll: position:absolute → relative, height auto */
li[role="option"] {{
    position: relative !important;
    top: auto !important;
    left: auto !important;
    height: auto !important;
    min-height: 52px !important;
    padding: 0.85rem 1rem !important;
    font-size: 1rem !important;
    line-height: 1.45 !important;
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
    box-sizing: border-box !important;
}}
li[role="option"] > div,
li[role="option"] > div > div {{
    width: 100% !important;
    font-size: 1rem !important;
    line-height: 1.45 !important;
    padding: 0 !important;
}}
li[role="option"]:hover {{
    background: var(--ink-surface-tint, #fff7ed) !important;
}}
li[role="option"][aria-selected="true"] {{
    background: var(--ink-orange) !important;
    color: var(--ink-on-primary) !important;
    font-weight: 600 !important;
}}
li[role="option"][aria-selected="true"] > div,
li[role="option"][aria-selected="true"] > div > div {{
    color: var(--ink-on-primary) !important;
}}

/* Kill react-window sizer heights — let li's stack naturally
   (covers both `ul` form ปัจจุบัน และ `[role="listbox"]` form อนาคต) */
div[data-baseweb="popover"] ul > div,
div[data-baseweb="popover"] ul > div > div,
div[data-baseweb="popover"] [role="listbox"] > div,
div[data-baseweb="popover"] [role="listbox"] > div > div {{
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow: visible !important;
    will-change: auto !important;
    transform: none !important;
}}

/* List container (ul) — scroll ที่นี่ที่เดียว, padding ให้ตัว item หายใจ */
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] [role="listbox"] {{
    height: auto !important;
    max-height: 420px !important;  /* ~8 rows ของ 52px */
    overflow-y: auto !important;
    overflow-x: hidden !important;
    min-width: 320px !important;
    padding: 0.3rem 0 !important;
    scroll-behavior: smooth !important;
}}

/* Outer popover wrappers — auto height (กัน double scrollbar) */
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div {{
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
    min-width: 320px !important;
}}

/* Popover เอง — shadow + radius + theme bg ให้ดูเด่น (UX) */
div[data-baseweb="popover"] {{
    border-radius: var(--ink-radius-md) !important;
    box-shadow: var(--ink-shadow-lg, 0 8px 24px rgba(0,0,0,0.18)) !important;
    background: var(--ink-surface, white) !important;
    border: 1px solid var(--ink-border, #E0E0E0) !important;
    overflow: hidden !important;  /* clip rounded corners */
}}

/* Scrollbar ของ popover — เรียวบาง สไตล์ INKEXTRACT */
div[data-baseweb="popover"] ul::-webkit-scrollbar,
div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar {{
    width: 8px !important;
}}
div[data-baseweb="popover"] ul::-webkit-scrollbar-thumb,
div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-thumb {{
    background: var(--ink-border, #ccc) !important;
    border-radius: 4px !important;
}}
div[data-baseweb="popover"] ul::-webkit-scrollbar-thumb:hover,
div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-thumb:hover {{
    background: var(--ink-orange-light) !important;
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
    color: var(--ink-on-primary) !important;
    border: 1px solid var(--ink-orange-dark) !important;
    font-weight: 600 !important;
}}
[data-testid="stFileUploaderDropzone"] button p,
[data-testid="stFileUploaderDropzone"] button span {{
    color: var(--ink-on-primary) !important;
}}
[data-testid="stFileUploaderDropzone"] button:hover {{
    background: var(--ink-orange-dark) !important;
    color: var(--ink-on-primary) !important;
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
* INKEXTRACT app header — compact 1-row brand bar
* Psychology: F-pattern reading → logo+title top-left (first attention),
* version chip top-right (status/trust). Height ≤ 72px keeps content
* the focus, not chrome.
* ============================================================ */
.ink-header {{
    background: linear-gradient(135deg, {ORANGE_PRIMARY} 0%, {ORANGE_DARK} 100%);
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 8px rgba(245,158,11,0.20);
    color: white;
}}
.ink-header-row {{
    display: flex; align-items: center; gap: 0.85rem;
}}
.ink-header-text {{ flex: 1; min-width: 0; display: flex; align-items: center; gap: 0.6rem; }}
.ink-header h1 {{
    margin: 0; color: white; font-size: 1.3rem; letter-spacing: 0.5px;
    font-weight: 700; line-height: 1.1;
}}
.ink-header p.ink-tagline {{
    margin: 0; color: rgba(255,255,255,0.85);
    font-size: 0.85rem; font-weight: 400;
    border-left: 1px solid rgba(255,255,255,0.35);
    padding-left: 0.7rem;
}}
@media (max-width: 900px) {{ .ink-header p.ink-tagline {{ display: none; }} }}
.ink-logo {{
    width: 36px; height: 36px; flex-shrink: 0;
    border-radius: 8px;
    background: rgba(255,255,255,0.95);
    padding: 3px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.18);
}}
.ink-version-badge {{
    display: inline-block;
    padding: 2px 10px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 999px;
    font-size: 0.78rem; font-weight: 600;
    color: white;
    letter-spacing: 0.3px;
    flex-shrink: 0;
}}

/* ============================================================
* Active project bar — slim 1-line strip below header
* Single source of truth — แสดงทุก tab (ไม่ใช่ duplicate ของ Project tab section)
* ============================================================ */
.ink-active-bar {{
    background: var(--ink-surface-tint);
    border-left: 3px solid var(--ink-orange);
    border-radius: var(--ink-radius-md);
    padding: 0.45rem 0.85rem;
    margin-bottom: 0.6rem;
    color: var(--ink-text);
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 0.88rem;
    line-height: 1.4;
}}
.ink-active-bar .ink-active-label {{
    color: var(--ink-text-muted); font-size: 0.8rem;
}}
.ink-active-bar .ink-active-name {{
    font-weight: 700; color: var(--ink-accent-strong);
}}
.ink-active-bar .ink-active-tag {{
    font-size: 0.72rem; padding: 1px 7px; border-radius: 999px;
    background: var(--ink-surface-tint-strong);
    color: var(--ink-accent-strong); font-weight: 600;
}}
.ink-active-bar code {{
    margin-left: auto; font-family: 'Consolas','Courier New',monospace;
    font-size: 0.78rem; color: var(--ink-text-muted);
    background: var(--ink-surface-2); padding: 1px 6px; border-radius: 4px;
    border: 1px solid var(--ink-border-soft);
    max-width: 50%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}

/* ============================================================
* Project tab — Active project hero card + project list rows
* ============================================================ */
.ink-active-card {{
    background: linear-gradient(135deg,
        var(--ink-surface-tint) 0%,
        var(--ink-surface-tint-strong) 100%);
    border: 2px solid var(--ink-orange);
    border-radius: var(--ink-radius-lg);
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.75rem;
    box-shadow: var(--ink-shadow-md);
}}
.ink-active-card-label {{
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.4rem;
    font-size: 0.78rem;
    color: var(--ink-accent-strong);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 700;
}}
.ink-active-card-label .micon {{ font-size: 1.2em; }}
.ink-active-card-name {{
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--ink-accent-strong);
    line-height: 1.15;
    margin-bottom: 0.55rem;
}}
.ink-active-card-path {{
    display: inline-flex; align-items: center; gap: 0.45rem;
    font-family: 'Consolas','Courier New',monospace;
    font-size: 0.85rem;
    color: var(--ink-text);
    background: var(--ink-surface);
    padding: 5px 12px;
    border-radius: var(--ink-radius-md);
    border: 1px solid var(--ink-border);
    max-width: 100%;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.ink-active-card-path .micon {{
    font-size: 1em; color: var(--ink-accent-strong); flex-shrink: 0;
}}
.ink-active-card-meta {{
    margin-top: 0.45rem;
    font-size: 0.8rem;
    color: var(--ink-text-muted);
}}

/* Project list rows */
.ink-proj-row {{
    background: var(--ink-surface);
    border: 1px solid var(--ink-border);
    border-radius: var(--ink-radius-md);
    padding: 0.75rem 0.95rem;
    display: flex; align-items: center; gap: 0.7rem;
    transition: all 0.15s ease;
}}
.ink-proj-row:hover {{
    border-color: var(--ink-orange-light);
    background: var(--ink-surface-2);
}}
.ink-proj-row.active {{
    background: var(--ink-surface-tint);
    border: 2px solid var(--ink-orange);
    box-shadow: var(--ink-shadow-sm);
}}
.ink-proj-icon {{
    font-size: 1.4em;
    color: var(--ink-text-muted);
    flex-shrink: 0;
}}
.ink-proj-row.active .ink-proj-icon {{
    color: var(--ink-orange);
}}
.ink-proj-text {{ flex: 1; min-width: 0; }}
.ink-proj-name {{
    font-weight: 700;
    font-size: 1rem;
    color: var(--ink-text-strong);
    line-height: 1.2;
}}
.ink-proj-row.active .ink-proj-name {{
    color: var(--ink-accent-strong);
}}
.ink-proj-path {{
    font-family: 'Consolas','Courier New',monospace;
    font-size: 0.78rem;
    color: var(--ink-text-muted);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    margin-top: 2px;
}}
.ink-proj-sub {{
    font-size: 0.74rem;
    color: var(--ink-text-faint);
    margin-top: 2px;
}}
.ink-proj-active-badge {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.55rem 0.8rem;
    color: var(--ink-accent-strong);
    font-weight: 700;
    font-size: 0.85rem;
    background: var(--ink-surface-tint);
    border-radius: var(--ink-radius-md);
    border: 1px solid var(--ink-border-orange);
    width: 100%;
    justify-content: center;
}}
.ink-proj-active-badge .micon {{ font-size: 1.1em; }}

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
.ink-section h3 {{ margin: 0 0 0.25rem; color: var(--ink-accent-strong); font-size: 1.1rem; }}
.ink-section p.ink-desc {{ color: var(--ink-text-muted); font-size: 0.85rem; margin: 0 0 0.6rem; }}

/* ============================================================
* Chip
* ============================================================ */
.ink-chip {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    background: var(--ink-surface-tint-strong); color: var(--ink-accent-strong);
    font-size: 0.8rem; font-weight: 600; margin-right: 6px;
    border: 1px solid var(--ink-border-orange);
}}

/* ============================================================
* Section label — มาตรฐานเดียวสำหรับหัวข้อย่อยทั่วทั้งแอป
*   ใช้แทน ad-hoc <div style="font-weight:600;color:..."> ที่กระจัดกระจาย
*   3 size variant: lg (1.05rem h3-like) · md (default 0.95rem) · sm (0.85rem)
*   Hint = บรรทัดอธิบายใต้หัวข้อ
*
* Markdown #### (h4) / ### (h3) / ## (h2) → จัดให้ตรงกัน
*   Streamlit h4 default ดูเล็ก/อ่อน — บังคับ color = --ink-text-strong + weight 700
*   เพื่อให้ทุกหัวข้อในแอป (ไม่ว่าจะเขียนผ่าน markdown หรือ HTML class) อ่านง่ายเหมือนกัน
* ============================================================ */
.ink-section-label {{
    display: flex; align-items: center; gap: 0.45rem;
    margin: 0.9rem 0 0.45rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--ink-text-strong);
    line-height: 1.3;
}}
.ink-section-label.lg {{ font-size: 1.05rem; margin: 1rem 0 0.55rem; }}
.ink-section-label.sm {{ font-size: 0.85rem; font-weight: 600; margin: 0.7rem 0 0.35rem; }}
.ink-section-label .micon {{
    font-size: 1.15em;
    color: var(--ink-accent-strong);
    flex-shrink: 0;
}}
.ink-section-label .count {{
    font-weight: 500;
    color: var(--ink-text-muted);
    font-size: 0.92em;
    margin-left: 0.15rem;
}}
.ink-section-hint {{
    margin: -0.15rem 0 0.6rem;
    font-size: 0.85rem;
    color: var(--ink-text-muted);
    line-height: 1.45;
}}

/* Streamlit markdown heading override — ให้ทุก # heading ใช้สีและน้ำหนักมาตรฐาน */
[data-testid="stMarkdownContainer"] h2 {{
    color: var(--ink-text-strong) !important;
    font-weight: 700 !important;
    font-size: 1.25rem !important;
    margin: 1.1rem 0 0.55rem !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
    line-height: 1.3 !important;
}}
[data-testid="stMarkdownContainer"] h3 {{
    color: var(--ink-text-strong) !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    margin: 1rem 0 0.5rem !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
    line-height: 1.3 !important;
}}
[data-testid="stMarkdownContainer"] h4 {{
    color: var(--ink-text-strong) !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    margin: 0.9rem 0 0.45rem !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
    line-height: 1.3 !important;
}}
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6 {{
    color: var(--ink-text-strong) !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    margin: 0.75rem 0 0.4rem !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
}}
/* Bold inline text (**text**) — slight color bump */
[data-testid="stMarkdownContainer"] strong {{
    color: var(--ink-text-strong);
    font-weight: 700;
}}
</style>
"""


# JS observer — sync `<html data-theme="dark">` กับ background ที่ Streamlit render จริง
# ครอบคลุม 3 case: (1) OS dark pref, (2) manual toggle ใน Settings menu, (3) prefs change live
# Why: CSS `@media (prefers-color-scheme: dark)` คุม OS pref ได้ แต่ manual toggle
# ของ Streamlit เปลี่ยน body bg โดยไม่ trigger media query → ต้อง observe เอง
# How: st.markdown strips <script>/<img onerror> → ใช้ components.v1.html (iframe)
# แล้ว access window.parent.document เพื่อแก้ host page
_DARK_DETECT_HTML = """
<script>
(function(){
    var w = window.parent || window;
    var doc = w.document;
    if (w.__inkThemeObserverInstalled) return;
    w.__inkThemeObserverInstalled = true;

    function isDarkBg(rgb) {
        var m = rgb && rgb.match(/\\d+/g);
        if (!m || m.length < 3) return false;
        var r = +m[0], g = +m[1], b = +m[2];
        var lum = 0.2126*r + 0.7152*g + 0.0722*b;
        return lum < 128;
    }
    var lastBg = '';
    function sync() {
        var app = doc.querySelector('[data-testid="stApp"]') || doc.querySelector('.stApp');
        if (!app) return;
        var bg = doc.defaultView.getComputedStyle(app).backgroundColor;
        if (bg === lastBg) return;  // unchanged — skip work
        lastBg = bg;
        var dark = isDarkBg(bg);
        var h = doc.documentElement;
        if (dark) {
            if (h.getAttribute('data-theme') !== 'dark') h.setAttribute('data-theme','dark');
        } else {
            if (h.getAttribute('data-theme') === 'dark') h.removeAttribute('data-theme');
        }
    }
    sync();
    // MutationObserver จับการ inject <style> emotion ของ Streamlit ที่เปลี่ยน theme
    try {
        var mo = new w.MutationObserver(sync);
        mo.observe(doc.head, {childList: true, subtree: true});
        mo.observe(doc.body, {attributes: true, attributeFilter: ['style', 'class']});
    } catch(e){}
    try { w.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', sync); } catch(e){}
    // Fast poll (cheap — single getComputedStyle call)
    w.setInterval(sync, 200);
})();
</script>
"""


def apply_theme() -> None:
    """ใส่ CSS theme ระดับ global — ต้องเรียกทุก rerun
    (Streamlit ลบ markdown ที่ไม่ถูก emit ในรอบ rerun ใหม่)
    JS observer ใส่ผ่าน st.iframe → iframe ที่ access window.parent.document ได้
    (เดิมใช้ components.v1.html — deprecated หลัง 2026-06-01 → ย้าย st.iframe)
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    # height=0 → iframe มองไม่เห็น แต่ JS ทำงาน + access parent doc ได้
    try:
        st.iframe(_DARK_DETECT_HTML, height=0)
    except AttributeError:
        # Streamlit < 1.55 — fallback ใช้ components.v1.html
        try:
            from streamlit.components.v1 import html as _components_html
            _components_html(_DARK_DETECT_HTML, height=0)
        except Exception:
            pass
    except Exception:
        pass


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
    """หัวหน้าเพจสีส้ม — แถบเดียวบาง ๆ มีโลโก้ + ชื่อ + tagline + version chip

    Psychology: F-pattern → eye lands top-left first. โลโก้+ชื่อต้องอยู่ที่นั่น
    Cognitive load: install path = diagnostic → ย้ายไปแสดงใน tooltip ของ version chip
    เพื่อลด noise. ตำแหน่ง install ของจริงอยู่ใน Project tab → "ตำแหน่ง install" expander
    """
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
                    <h1>{title}</h1>
                    <p class="ink-tagline">{tagline}</p>
                </div>
                {version_html}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def step_header(step_num: int, total: int, title: str, description: Optional[str] = None) -> None:
    """แสดง header ของขั้น (STEP N/M) — ใช้ทุก tab เพื่อ workflow consistency

    Psychology: เลขลำดับลด cognitive load — user รู้ว่าอยู่ตรงไหน + เหลืออีกกี่ขั้น
    """
    desc_html = (
        f'<div style="margin-top:0.25rem;font-size:0.88rem;color:var(--ink-text-muted);">{description}</div>'
        if description else ''
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0.7rem;margin:1.25rem 0 0.6rem;">
            <div style="display:inline-flex;width:32px;height:32px;border-radius:50%;
                        background:var(--ink-orange);color:var(--ink-on-primary);
                        align-items:center;justify-content:center;
                        font-weight:700;font-size:14px;flex-shrink:0;
                        box-shadow:var(--ink-shadow-sm);">
                {step_num}
            </div>
            <div style="flex:1;min-width:0;">
                <div style="font-size:1.05rem;font-weight:700;color:var(--ink-text);
                            line-height:1.2;">
                    {title}
                    <span style="font-size:0.78rem;color:var(--ink-text-muted);
                                 font-weight:400;margin-left:0.4rem;">
                        ขั้นที่ {step_num} จาก {total}
                    </span>
                </div>
                {desc_html}
            </div>
        </div>
        """,
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
    color: var(--ink-accent-strong); line-height: 1;
}

/* ===== Pane header ===== */
.ms-pane-header {
    padding: 12px 16px;
    background: var(--ink-surface-tint-strong);
    border: 1px solid var(--ink-border);
    border-bottom: 2px solid var(--ink-orange);
    border-radius: var(--ink-radius-lg) var(--ink-radius-lg) 0 0;
    font-weight: 700;
    color: var(--ink-accent-strong);
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
    color: var(--ink-accent-strong);
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
