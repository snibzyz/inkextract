"""tabs/vocab.py — Tab 'จัดการคำศัพท์' (refresh 2026-05-06)

หลักการ:
    - ไม่มี emoji ในข้อความ — ใช้สี/ตัวเลข/ตำแหน่งบ่งบอกบริบท
    - ภาษาไทยเท่านั้น (ยกเว้นนามสกุลไฟล์/ตัวอย่างจีน)
    - ทุก div/ปุ่ม/text ใช้ token จาก ui.py (theme-aware)
    - flow: อัปโหลด → ภาพรวม → เลือกแม่แบบหรือปรับแต่ง → สร้าง
"""
from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd

from modules import paths, ui


# ============================================================
# CSS — ใช้ token จาก ui._GLOBAL_CSS
# ============================================================
_VOCAB_CSS = """
<style>
/* ===== Stats grid ===== */
.vc-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px; margin: 0.5rem 0 1.25rem; }
.vc-stat {
    background: var(--ink-surface);
    padding: 16px 18px;
    border-radius: var(--ink-radius-lg);
    border: 1px solid var(--ink-border);
    border-top: 4px solid var(--ink-orange);
    box-shadow: var(--ink-shadow-md);
    transition: transform 0.15s, box-shadow 0.15s;
    color: var(--ink-text);
}
.vc-stat:hover { transform: translateY(-2px); box-shadow: var(--ink-shadow-lg); }
.vc-stat .lbl {
    font-size: 0.78em; color: var(--ink-text-muted);
    letter-spacing: 0.3px; font-weight: 600; text-transform: uppercase;
}
.vc-stat .val {
    font-size: 1.7em; font-weight: 800;
    color: var(--ink-accent-strong); line-height: 1.05;
    margin: 6px 0 4px;
}
.vc-stat .hint { font-size: 0.78em; color: var(--ink-text-muted); line-height: 1.4; }
.vc-stat.warn { border-top-color: var(--ink-warn); }
.vc-stat.warn .val { color: var(--ink-warn); }
.vc-stat.ok { border-top-color: var(--ink-success); }
.vc-stat.ok .val { color: var(--ink-success); }
.vc-stat.muted { border-top-color: var(--ink-text-faint); }
.vc-stat.muted .val { color: var(--ink-text-faint); }

/* ===== Numbered step header ===== */
.vc-step {
    display: flex; align-items: baseline; gap: 10px;
    margin: 1.5rem 0 0.75rem; padding-bottom: 8px;
    border-bottom: 2px solid var(--ink-border-orange);
}
.vc-step .num {
    background: var(--ink-orange); color: var(--ink-on-primary);
    width: 30px; height: 30px;
    border-radius: var(--ink-radius-pill);
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1em; flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(245,124,0,0.30);
}
.vc-step .title {
    font-size: 1.18em; font-weight: 700;
    color: var(--ink-text-strong);
}
.vc-step .sub {
    font-size: 0.88em; color: var(--ink-text-muted);
    margin-left: 6px;
}

/* ===== Preset card ===== */
.vc-preset {
    background: var(--ink-surface);
    border: 1.5px solid var(--ink-border);
    border-top: 4px solid var(--ink-orange);
    border-radius: var(--ink-radius-xl);
    padding: 18px 16px; height: 100%;
    transition: all 0.18s;
    display: flex; flex-direction: column; gap: 8px;
    color: var(--ink-text);
}
.vc-preset:hover {
    transform: translateY(-3px);
    box-shadow: var(--ink-shadow-lg);
    border-color: var(--ink-orange-light);
}
.vc-preset .ptitle {
    font-weight: 700; color: var(--ink-accent-strong);
    font-size: 1.08em; line-height: 1.3;
}
.vc-preset .pdesc {
    font-size: 0.88em; color: var(--ink-text-muted);
    line-height: 1.5; flex-grow: 1;
}
.vc-preset .pcount {
    font-size: 0.84em; color: var(--ink-success);
    font-weight: 700; padding: 5px 12px;
    background: var(--ink-success-bg);
    border-radius: var(--ink-radius-pill);
    align-self: flex-start;
}
.vc-preset .pcount.empty {
    color: var(--ink-text-faint);
    background: var(--ink-surface-2);
}
.vc-preset.active {
    border-color: var(--ink-orange);
    background: var(--ink-surface-tint-strong);
    box-shadow: 0 0 0 3px rgba(245,124,0,0.20);
}
.vc-preset.active .ptitle::after { content: ' '; color: var(--ink-success); }

/* ===== Composer card section ===== */
.vc-comp-section {
    background: var(--ink-surface-2);
    border: 1px solid var(--ink-border);
    border-radius: var(--ink-radius-lg);
    padding: 16px 18px; margin-bottom: 12px;
    color: var(--ink-text);
}
.vc-subhead {
    font-weight: 700; color: var(--ink-text-strong);
    font-size: 0.95em;
    margin: 12px 0 8px; padding-bottom: 6px;
    border-bottom: 1px dashed var(--ink-border-orange);
    display: flex; align-items: center; gap: 6px;
}

/* ===== Result banner ===== */
.vc-result {
    background: var(--ink-surface-tint-strong);
    border: 1.5px solid var(--ink-border-orange);
    border-left: 5px solid var(--ink-orange);
    border-radius: var(--ink-radius-lg);
    padding: 16px 22px; margin: 14px 0 6px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px;
    box-shadow: var(--ink-shadow-md);
    color: var(--ink-text);
}
.vc-result .left { display: flex; align-items: baseline; gap: 8px; }
.vc-result .count {
    font-size: 1.1em; color: var(--ink-text);
}
.vc-result .count b {
    color: var(--ink-accent-strong);
    font-size: 1.5em; font-weight: 800; margin: 0 4px;
}
.vc-result .file {
    font-family: 'Consolas', monospace;
    background: var(--ink-surface);
    padding: 6px 12px;
    border-radius: var(--ink-radius-md);
    border: 1px solid var(--ink-border-orange);
    color: var(--ink-accent-strong);
    font-size: 0.92em; font-weight: 600;
}
.vc-result.empty {
    background: var(--ink-surface-2);
    border-color: var(--ink-border);
    border-left-color: var(--ink-text-faint);
    opacity: 0.85;
}
.vc-result.empty .count b { color: var(--ink-text-faint); }
.vc-result.empty .file { color: var(--ink-text-faint); border-color: var(--ink-border); }

/* ===== Empty state (drop zone) ===== */
.vc-empty {
    background: var(--ink-surface-tint);
    padding: 2.5rem 2rem; border-radius: var(--ink-radius-xl);
    text-align: center;
    border: 2px dashed var(--ink-border-orange);
    margin-top: 1rem;
    color: var(--ink-text);
}
.vc-empty h4 { margin: 0; color: var(--ink-accent-strong); font-size: 1.35rem; }
.vc-empty p { margin: 0.5rem 0 1.25rem; color: var(--ink-text-muted); font-size: 0.95rem; }
.vc-empty .examples {
    background: var(--ink-surface);
    border-radius: var(--ink-radius-lg);
    padding: 1rem 1.25rem;
    max-width: 540px; margin: 0 auto; text-align: left;
    font-size: 1.02rem; color: var(--ink-text); line-height: 1.95;
    border: 1px solid var(--ink-border);
}
.vc-empty .examples .head {
    font-size: 0.78rem; color: var(--ink-text-muted);
    margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700;
}
.vc-empty .examples .sep { color: var(--ink-accent-strong); font-weight: 700; }
</style>
"""


def _ensure_css():
    st.markdown(_VOCAB_CSS, unsafe_allow_html=True)


# ============================================================
# Stats card helpers
# ============================================================
def _stat_card(label: str, value, hint: str = "", *, kind: str = "") -> str:
    klass = "vc-stat" + (f" {kind}" if kind else "")
    val_str = f"{value:,}" if isinstance(value, int) else str(value)
    hint_html = f'<div class="hint">{hint}</div>' if hint else ''
    return (
        f'<div class="{klass}">'
        f'<div class="lbl">{label}</div>'
        f'<div class="val">{val_str}</div>'
        f'{hint_html}'
        f'</div>'
    )


def _render_stats(stats: dict) -> None:
    cards = [
        _stat_card("บรรทัดทั้งหมด", stats['total'],
 "นับทุกบรรทัดในไฟล์ที่อัปโหลด"),
        _stat_card("คู่ไม่ซ้ำ จีน+ไทย", stats['unique_pairs'],
 "นับ จีน+ไทย ตรงกัน = 1 คู่",
                   kind="ok"),
        _stat_card("บรรทัดซ้ำเป๊ะ", stats['duplicate_entries'],
 "บรรทัดที่ซ้ำกับบรรทัดอื่น (จีน+ไทย ตรงกัน)",
                   kind="muted" if stats['duplicate_entries'] == 0 else ""),
        _stat_card("คำขัดแย้ง", f"{stats['conflict_cn_count']:,}",
                   f"จีนตรง · ไทยต่าง — กระทบ {stats['conflict_entries']:,} บรรทัด",
                   kind="warn" if stats['conflict_cn_count'] else "muted"),
    ]
    st.markdown(f'<div class="vc-stats">{"".join(cards)}</div>', unsafe_allow_html=True)


def _step_header(num: int, title: str, sub: str = "") -> None:
    sub_html = f'<span class="sub">— {sub}</span>' if sub else ''
    st.markdown(
        f'<div class="vc-step">'
        f'<span class="num">{num}</span>'
        f'<span class="title">{title}</span>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Filter chips (multi-select via st.pills)
# ============================================================
FILTER_CHIPS = [
    ("dedupe", "ตัดคำซ้ำ"),
    ("drop_note", "ลบหมายเหตุ"),
    ("only_conflicts", "เฉพาะคำขัดแย้ง"),
    ("only_dupes", "เฉพาะคำซ้ำเป๊ะ"),
    ("freq", "กรองความถี่"),
    ("len", "กรองความยาวจีน"),
    ("search", "ค้นหา"),
    ("source", "เฉพาะบางไฟล์"),
    ("limit", "จำกัดจำนวน"),
]
FILTER_LABELS = [c[1] for c in FILTER_CHIPS]
_CHIP_KEY_BY_LABEL = {c[1]: c[0] for c in FILTER_CHIPS}


# ============================================================
# Sort options (single-select via st.segmented_control)
# ============================================================
SORT_OPTIONS = [
    ("none", "ตามลำดับเดิม"),
    ("length_desc", "ยาว → สั้น"),
    ("length_asc", "สั้น → ยาว"),
    ("prefix", "อักษรหน้า"),
    ("suffix", "อักษรท้าย"),
    ("frequency_desc", "บ่อย → น้อย"),
    ("frequency_asc", "น้อย → บ่อย"),
    ("group_by_cn", "จัดกลุ่มจีน"),
    ("alpha_cn", "อักษร ก-ฮ จีน"),
    ("alpha_th", "อักษร ก-ฮ ไทย"),
]
_SORT_LABEL_BY_KEY = {k: lbl for k, lbl in SORT_OPTIONS}
_SORT_KEY_BY_LABEL = {lbl: k for k, lbl in SORT_OPTIONS}


# ============================================================
# Presets
# ============================================================
PRESETS = [
    {
 "key": "dictionary",
 "title": "พจนานุกรม (เริ่มต้น)",
 "desc": "ตัดคำซ้ำ + ลบคอลัมน์หมายเหตุ + เรียงตามลำดับเดิม — เหลือแค่ จีน[TAB]ไทย",
 "cfg": {"active_filters": ["dedupe", "drop_note"], "sort_by": "none"},
    },
    {
 "key": "conflicts",
 "title": "รีวิวคำขัดแย้ง",
 "desc": "เห็นเฉพาะ จีน ที่มีคำแปล ไทย หลายแบบ — ตัดสินใจเลือก",
 "cfg": {"active_filters": ["only_conflicts"], "sort_by": "group_by_cn"},
    },
    {
 "key": "duplicates",
 "title": "ดูคำซ้ำเป๊ะ",
 "desc": "เฉพาะคู่ จีน+ไทย ซ้ำ ≥2 ครั้ง — ใช้พิสูจน์/ตัดทิ้ง",
 "cfg": {"active_filters": ["only_dupes"], "sort_by": "frequency_desc"},
    },
    {
 "key": "frequent",
 "title": "คำที่ใช้บ่อย",
 "desc": "เก็บเฉพาะคำที่ปรากฏ 3 ครั้งขึ้นไป + ตัดซ้ำ + เรียงตามถี่",
 "cfg": {"active_filters": ["dedupe", "freq"], "min_freq": 3,
 "sort_by": "frequency_desc"},
    },
]


_DEFAULTS = {
 "vc_active_filters": ["dedupe", "drop_note"],
 "vc_min_freq": 3,
 "vc_max_freq": 100,
 "vc_min_len": 2,
 "vc_max_len": 10,
 "vc_use_max_freq": False,
 "vc_use_max_len": False,
 "vc_search": "",
 "vc_source_files": [],
 "vc_limit": 100,
 "vc_sort_by": "none",
 "vc_active_preset": None,
}


def _reset_to_defaults() -> None:
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v.copy() if isinstance(v, list) else v
    # sync widget state ของ pills + segmented_control ด้วย
    st.session_state.vc_filter_pills = [
        c[1] for c in FILTER_CHIPS if c[0] in _DEFAULTS["vc_active_filters"]
    ]
    st.session_state.vc_sort_seg = _SORT_LABEL_BY_KEY.get(
        _DEFAULTS["vc_sort_by"], SORT_OPTIONS[0][1]
    )


def _init_defaults() -> None:
    """Init non-widget session state ONLY.
    NOTE: ห้าม init `vc_filter_pills` / `vc_sort_seg` ที่นี่ — Streamlit's pills/
    segmented_control ignore pre-set session_state[key] on first render and
    instead use `default=` parameter. We pass `default=` in _render_composer.
    """
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v.copy() if isinstance(v, list) else v


def _apply_preset(preset: dict) -> None:
    _reset_to_defaults()
    cfg = preset["cfg"]
    af = list(cfg.get("active_filters", []))
    st.session_state.vc_active_filters = af
    if "min_freq" in cfg:
        st.session_state.vc_min_freq = cfg["min_freq"]
    if "max_freq" in cfg:
        st.session_state.vc_use_max_freq = True
        st.session_state.vc_max_freq = cfg["max_freq"]
    if "min_len" in cfg:
        st.session_state.vc_min_len = cfg["min_len"]
    if "search" in cfg:
        st.session_state.vc_search = cfg["search"]
    if "limit" in cfg:
        st.session_state.vc_limit = cfg["limit"]
    sort_by = cfg.get("sort_by", "length_desc")
    st.session_state.vc_sort_by = sort_by
    st.session_state.vc_active_preset = preset["key"]

    # ===== sync widget state ของ pills + segmented_control โดยตรง =====
    # (ไม่งั้น default= จะใช้แค่ตอน first render)
    st.session_state.vc_filter_pills = [
        c[1] for c in FILTER_CHIPS if c[0] in af
    ]
    st.session_state.vc_sort_seg = _SORT_LABEL_BY_KEY.get(
        sort_by, SORT_OPTIONS[0][1]
    )


def _config_matches_preset(preset: dict) -> bool:
    cfg = preset["cfg"]
    expected_filters = set(cfg.get("active_filters", []))
    if set(st.session_state.vc_active_filters) != expected_filters:
        return False
    if st.session_state.vc_sort_by != cfg.get("sort_by", "length_desc"):
        return False
    if "min_freq" in cfg and st.session_state.vc_min_freq != cfg["min_freq"]:
        return False
    return True


# ============================================================
# Preset CTA cards
# ============================================================

def _render_preset_cards(vp, all_vocab: list) -> None:
    cols = st.columns(len(PRESETS))
    for i, preset in enumerate(PRESETS):
        with cols[i]:
            preset_opts = _preset_to_opts(preset)
            try:
                count = len(vp.apply_pipeline(all_vocab, **preset_opts))
            except Exception:
                count = 0

            is_active = _config_matches_preset(preset)
            klass = "vc-preset active" if is_active else "vc-preset"
            count_klass = "pcount empty" if count == 0 else "pcount"

            st.markdown(
                f'<div class="{klass}">'
                f'<div class="ptitle">{preset["title"]}</div>'
                f'<div class="pdesc">{preset["desc"]}</div>'
                f'<div class="{count_klass}">→ {count:,} บรรทัด</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            label = "ใช้อยู่" if is_active else "เลือก"
            btn_type = "secondary" if is_active else "primary"
            if st.button(label, key=f"vc_preset_{preset['key']}",
                         width="stretch", type=btn_type,
                         disabled=is_active):
                _apply_preset(preset)
                st.rerun()


def _preset_to_opts(preset: dict) -> dict:
    cfg = preset["cfg"]
    af = set(cfg.get("active_filters", []))
    return {
 "dedupe_pairs": "dedupe" in af,
 "only_conflicts": "only_conflicts" in af,
 "only_exact_duplicates": "only_dupes" in af,
 "min_frequency": cfg.get("min_freq", 1) if "freq" in af else 1,
 "max_frequency": cfg.get("max_freq") if "freq" in af else None,
 "min_cn_length": cfg.get("min_len", 1) if "len" in af else 1,
 "max_cn_length": cfg.get("max_len") if "len" in af else None,
 "search_text": cfg.get("search", "") if "search" in af else "",
 "source_files": None,
 "limit": cfg.get("limit", 0) if "limit" in af else 0,
 "sort_by": cfg.get("sort_by", "length_desc"),
 "drop_extra_columns": "drop_note" in af,
    }


# ============================================================
# Composer (advanced)
# ============================================================

def _render_composer(all_vocab: list) -> None:
    st.markdown(
 '<div class="vc-subhead">ตัวกรอง '
 '<span style="font-weight:400;color:var(--ink-text-muted)">'
 '(เลือกได้หลายข้อ — ทำงานพร้อมกัน)</span>'
 '</div>',
        unsafe_allow_html=True,
    )

    active_keys = st.session_state.vc_active_filters
    active_labels = [c[1] for c in FILTER_CHIPS if c[0] in active_keys]

    # ส่ง default= เฉพาะรอบ first-render (ไม่งั้นจะเตือน "value set via Session State"
    # หรือไม่ก็ widget จะ ignore session_state ที่เรา pre-set ไว้)
    pills_kwargs = dict(
        options=FILTER_LABELS,
        selection_mode="multi",
        key="vc_filter_pills",
        label_visibility="collapsed",
    )
    if "vc_filter_pills" not in st.session_state:
        pills_kwargs["default"] = active_labels
    selected_labels = st.pills("ตัวกรอง", **pills_kwargs)
    new_keys = [_CHIP_KEY_BY_LABEL[lbl] for lbl in (selected_labels or [])]
    if new_keys != active_keys:
        st.session_state.vc_active_filters = new_keys
        st.session_state.vc_active_preset = None
        st.rerun()

    af = set(st.session_state.vc_active_filters)
    needs_inputs = af & {"freq", "len", "search", "source", "limit"}
    if needs_inputs:
        st.markdown(
 '<div class="vc-subhead">พารามิเตอร์</div>',
            unsafe_allow_html=True,
        )

        if "freq" in af:
            f1, f2, f3 = st.columns([1, 1, 0.5])
            with f1:
                st.number_input("ปรากฏ ≥ ครั้ง", min_value=2, max_value=999,
                                step=1, key="vc_min_freq")
            with f2:
                if st.session_state.vc_use_max_freq:
                    st.number_input("และ ≤ ครั้ง", min_value=1, max_value=999,
                                    step=1, key="vc_max_freq")
                else:
                    st.markdown("<div style='padding-top:30px;color:var(--ink-text-faint)'>"
 "<i>ไม่จำกัดสูงสุด</i></div>", unsafe_allow_html=True)
            with f3:
                st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
                st.checkbox("ใส่สูงสุด", key="vc_use_max_freq")

        if "len" in af:
            l1, l2, l3 = st.columns([1, 1, 0.5])
            with l1:
                st.number_input("จีนยาว ≥ ตัว", min_value=1, max_value=99,
                                step=1, key="vc_min_len")
            with l2:
                if st.session_state.vc_use_max_len:
                    st.number_input("และ ≤ ตัว", min_value=1, max_value=99,
                                    step=1, key="vc_max_len")
                else:
                    st.markdown("<div style='padding-top:30px;color:var(--ink-text-faint)'>"
 "<i>ไม่จำกัดสูงสุด</i></div>", unsafe_allow_html=True)
            with l3:
                st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
                st.checkbox("ใส่สูงสุด", key="vc_use_max_len")

        if "search" in af:
            st.text_input("พิมพ์คำที่ต้องการค้น (จีนหรือไทย)",
                          key="vc_search",
                          placeholder="เช่น 修炼  หรือ  อมตะ")

        if "source" in af:
            unique_sources = sorted({it.get('source_file', '')
                                     for it in all_vocab if it.get('source_file', '')})
            if len(unique_sources) > 1:
                st.multiselect(f"เลือกไฟล์ ({len(unique_sources)} ไฟล์ที่มี)",
                               options=unique_sources, key="vc_source_files")
            else:
                st.info("มีแค่ไฟล์เดียว — ไม่ต้องกรอง")

        if "limit" in af:
            st.number_input("เก็บกี่บรรทัดแรก (หลังเรียง)",
                            min_value=1, max_value=99999, step=10, key="vc_limit")

    # ===== Sort =====
    st.markdown(
 '<div class="vc-subhead">เรียงลำดับ '
 '<span style="font-weight:400;color:var(--ink-text-muted)">'
 '(เลือก 1 แบบ — ทำงานหลังกรอง)</span>'
 '</div>',
        unsafe_allow_html=True,
    )

    sort_labels = [lbl for _, lbl in SORT_OPTIONS]
    current_sort_label = _SORT_LABEL_BY_KEY.get(
        st.session_state.vc_sort_by, SORT_OPTIONS[0][1]
    )
    seg_kwargs = dict(
        options=sort_labels,
        key="vc_sort_seg",
        label_visibility="collapsed",
    )
    if "vc_sort_seg" not in st.session_state:
        seg_kwargs["default"] = current_sort_label
    selected_sort = st.segmented_control("เรียง", **seg_kwargs)
    if selected_sort:
        new_sort = _SORT_KEY_BY_LABEL[selected_sort]
        if new_sort != st.session_state.vc_sort_by:
            st.session_state.vc_sort_by = new_sort
            st.session_state.vc_active_preset = None
            st.rerun()


# ============================================================
# Build options + result banner
# ============================================================

def _collect_opts() -> dict:
    s = st.session_state
    af = set(s.vc_active_filters)
    return {
 "dedupe_pairs": "dedupe" in af,
 "only_conflicts": "only_conflicts" in af,
 "only_exact_duplicates": "only_dupes" in af,
 "min_frequency": s.vc_min_freq if "freq" in af else 1,
 "max_frequency": s.vc_max_freq if ("freq" in af and s.vc_use_max_freq) else None,
 "min_cn_length": s.vc_min_len if "len" in af else 1,
 "max_cn_length": s.vc_max_len if ("len" in af and s.vc_use_max_len) else None,
 "search_text": s.vc_search if "search" in af else "",
 "source_files": s.vc_source_files if ("source" in af and s.vc_source_files) else None,
 "limit": s.vc_limit if "limit" in af else 0,
 "sort_by": s.vc_sort_by,
 "drop_extra_columns": "drop_note" in af,
    }


def _autoname(opts: dict, preset_key: str = None) -> str:
    if preset_key:
        return f"vocab_{preset_key}.txt"
    parts = ["vocab"]
    if opts.get("only_conflicts"):
        parts.append("conflicts")
    if opts.get("only_exact_duplicates"):
        parts.append("dupes")
    if opts.get("min_cn_length", 1) > 1 or opts.get("max_cn_length"):
        lo = opts.get("min_cn_length", 1)
        hi = opts.get("max_cn_length", "")
        parts.append(f"len{lo}-{hi or 'x'}")
    if opts.get("min_frequency", 1) > 1 or opts.get("max_frequency"):
        lo = opts.get("min_frequency", 1)
        hi = opts.get("max_frequency", "")
        parts.append(f"freq{lo}-{hi or 'x'}")
    if opts.get("search_text"):
        safe = ''.join(c for c in opts['search_text'] if c.isalnum())[:8]
        if safe:
            parts.append(f"q{safe}")
    if opts.get("dedupe_pairs"):
        parts.append("unique")
    if opts.get("drop_extra_columns"):
        parts.append("nonote")
    sort_short = {
 "length_desc": "long", "length_asc": "short",
 "prefix": "prefix", "suffix": "suffix",
 "frequency_desc": "byfreq", "frequency_asc": "byfreqasc",
 "group_by_cn": "group", "alpha_cn": "alphaCN", "alpha_th": "alphaTH",
 "none": "raw",
    }.get(opts.get("sort_by", "length_desc"), "raw")
    parts.append(sort_short)
    if opts.get("limit"):
        parts.append(f"top{opts['limit']}")
    return "_".join(parts) + ".txt"


def _render_result(vp, all_vocab: list) -> None:
    opts = _collect_opts()
    preview = vp.apply_pipeline(all_vocab, **opts)
    n_out = len(preview)
    filename = _autoname(opts, st.session_state.vc_active_preset)

    banner_col, btn_col = st.columns([3, 1])
    with banner_col:
        empty = " empty" if n_out == 0 else ""
        st.markdown(
            f'<div class="vc-result{empty}">'
            f'<div class="left">'
            f'<span class="count">จะได้ <b>{n_out:,}</b> บรรทัด</span>'
            f'</div>'
            f'<div class="file">{filename}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with btn_col:
        st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
        if st.button("สร้างไฟล์", type="primary", width="stretch",
                     disabled=(n_out == 0), key="vc_generate"):
            with st.spinner("กำลังสร้างไฟล์..."):
                try:
                    output = vp.create_pipeline_output(all_vocab, filename=filename, **opts)
                    ui.success(f"สำเร็จ — `{Path(output).name}` ({n_out:,} บรรทัด)")
                    st.toast("สร้างไฟล์สำเร็จ")
                except Exception as e:
                    ui.error(f"สร้างไฟล์ไม่สำเร็จ: {e}")

    if n_out > 0:
        with st.expander("ดูตัวอย่าง 10 บรรทัดแรกของผลลัพธ์", expanded=False):
            df = pd.DataFrame(preview[:10])
            keep = [c for c in ['cn', 'th', 'source_file'] if c in df.columns]
            if keep:
                rename_map = {'cn': 'จีน', 'th': 'ไทย', 'source_file': 'จากไฟล์'}
                st.dataframe(df[keep].rename(columns=rename_map),
                             width="stretch", hide_index=True)


# ============================================================
# Main render
# ============================================================

def render(vocab_processor) -> None:
    _ensure_css()
    _init_defaults()

    with ui.section(
 "จัดการคำศัพท์",
        description=(
 "อัปโหลดไฟล์ .tsv / .csv / .txt / .xlsx — รองรับ จีน[แท็บ]ไทย, "
 "จีน | ไทย, จีน|ไทย|หมายเหตุ ผสมกันได้ในไฟล์เดียว "
 "ผลลัพธ์ออกที่ workspace/output/"
        ),
    ):
        pass

    # ===== STEP 1 =====
    _step_header(1, "อัปโหลดไฟล์", "TSV / CSV / TXT / XLSX")
    uploaded_files = st.file_uploader(
 "อัปโหลดไฟล์คำศัพท์",
        type=None,
        accept_multiple_files=True,
        key="vocab_upload",
        label_visibility="collapsed",
        help="รองรับ CSV, TSV, TXT, XLSX — ตรวจจับรูปแบบอัตโนมัติ",
    )

    if not uploaded_files:
        _empty_state()
        return

    supported = ('.csv', '.txt', '.tsv', '.xlsx')
    files = [f for f in uploaded_files if f.name.lower().endswith(supported)]
    bad = [f for f in uploaded_files if not f.name.lower().endswith(supported)]
    if bad:
        ui.warning(f"ข้ามไฟล์ที่ไม่รองรับ: {', '.join(f.name for f in bad)}")
    if not files:
        return

    ui.success(f"อัปโหลด {len(files)} ไฟล์")

    # ===== Cache + load =====
    cache_key = "_".join(f.name + str(f.size) for f in files)
    if st.session_state.get('vc_cache_key') != cache_key:
        with st.spinner("กำลังอ่านไฟล์..."):
            all_vocab = vocab_processor.read_csv_files(files)
        stats = vocab_processor.get_enhanced_statistics(all_vocab)
        st.session_state.vc_cache_key = cache_key
        st.session_state.vc_vocab = all_vocab
        st.session_state.vc_stats = stats
    else:
        all_vocab = st.session_state.vc_vocab
        stats = st.session_state.vc_stats

    if not all_vocab:
        ui.warning("ไม่พบข้อมูล — ตรวจรูปแบบ: จีน[แท็บ]ไทย หรือ จีน | ไทย")
        return

    # ===== STEP 2 =====
    _step_header(2, "ภาพรวมข้อมูล", "เห็นทันทีว่ามีคำซ้ำ/ขัดแย้งกี่ตัว")
    _render_stats(stats)

    with st.expander(f"ดูข้อมูลต้นทาง 10 บรรทัด ({stats['total']:,} บรรทัด)",
                     expanded=False):
        preview_df = vocab_processor.preview_vocab(all_vocab, 10)
        if not preview_df.empty:
            rename_map = {'cn': 'จีน', 'th': 'ไทย', 'source_file': 'จากไฟล์',
 'columns': 'คอลัมน์'}
            st.dataframe(preview_df.rename(columns=rename_map),
                         width="stretch", hide_index=True)

    # ===== STEP 3 =====
    _step_header(3, "เลือกสิ่งที่อยากได้", "กดแม่แบบ หรือปรับแต่งเอง")
    _render_preset_cards(vocab_processor, all_vocab)

    with st.expander("ปรับแต่งเอง (สำหรับงานเฉพาะ)",
                     expanded=(st.session_state.vc_active_preset is None and
                               len(st.session_state.vc_active_filters) > 0)):
        _render_composer(all_vocab)
        if st.button("รีเซ็ตทั้งหมด", key="vc_reset", width="content",
                     help="ล้างตัวกรองและกลับไปค่าเริ่มต้น"):
            _reset_to_defaults()
            st.rerun()

    # ===== STEP 4 =====
    _step_header(4, "สร้างไฟล์ผลลัพธ์", "ดูจำนวนก่อน แล้วกดสร้าง")
    _render_result(vocab_processor, all_vocab)

    if stats.get('frequency_distribution'):
        with st.expander("การแจกแจงความถี่ทั้งหมด (ตาราง)", expanded=False):
            rows = [
                {'ความถี่ (ครั้ง)': f, 'จำนวนคู่ จีน+ไทย': c, 'รวมบรรทัด': f * c}
                for f, c in sorted(stats['frequency_distribution'].items(), reverse=True)
            ]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _empty_state() -> None:
    st.markdown(
 """
        <div class="vc-empty">
            <h4>อัปโหลดไฟล์คำศัพท์เพื่อเริ่ม</h4>
            <p>รองรับ <b>TSV / CSV / TXT / XLSX</b> ผสมกันได้</p>
            <div class="examples">
                <div class="head">ตัวอย่างรูปแบบที่รับ</div>
                <div>不朽 <span class="sep">[แท็บ]</span> อมตะ</div>
                <div>修炼境界 <span class="sep">|</span> ขอบเขตการบำเพ็ญ</div>
                <div>圣者 <span class="sep">|</span> นักบุญ <span class="sep">|</span> หมายเหตุ</div>
            </div>
        </div>
 """,
        unsafe_allow_html=True,
    )
