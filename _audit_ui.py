"""INKEXTRACT — UI theme audit
Capture screenshots + WCAG AA contrast check (4.5:1 normal text, 3.0:1 large text)
ครอบคลุมทุก tab × light/dark — ระบุ component ที่ contrast ไม่ผ่าน

Usage:
    .venv/Scripts/python.exe _audit_ui.py
Output:
    _screenshots/<theme>_<NN>_<tab>.png
    _screenshots/contrast_report.json   ← รายการ failure (text-bg pair)
    _screenshots/audit_summary.txt      ← human-readable
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time, json

URL = "http://localhost:8501"
OUT = Path("_screenshots")
OUT.mkdir(exist_ok=True)

# Clear old png
for f in OUT.glob("*.png"):
    f.unlink()

TABS = ["โปรเจกต์", "ตรวจต้นฉบับ", "คำศัพท์", "ตรวจสอบและแก้ไข", "จัดการไฟล์"]

# ─── WCAG contrast helpers (JS-side) ──────────────────────────────────────────
CONTRAST_JS = r"""
() => {
    // parse "rgb(r,g,b)" / "rgba(r,g,b,a)" → [r,g,b,a]  (a default 1)
    function parseColor(s) {
        if (!s) return null;
        const m = s.match(/rgba?\(([^)]+)\)/);
        if (!m) return null;
        const parts = m[1].split(',').map(p => parseFloat(p.trim()));
        return [parts[0]||0, parts[1]||0, parts[2]||0, parts.length>3 ? parts[3] : 1];
    }
    // sRGB → relative luminance (WCAG)
    function lum(rgb) {
        const [r,g,b] = rgb.slice(0,3).map(v => {
            v = v/255;
            return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
        });
        return 0.2126*r + 0.7152*g + 0.0722*b;
    }
    function contrast(c1, c2) {
        const l1 = lum(c1), l2 = lum(c2);
        const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
        return (hi + 0.05) / (lo + 0.05);
    }
    // composite rgba over base — alpha blending
    function composite(over, under) {
        const a = over[3];
        const r = over[0]*a + under[0]*(1-a);
        const g = over[1]*a + under[1]*(1-a);
        const b = over[2]*a + under[2]*(1-a);
        return [r, g, b, 1];
    }
    // หาพื้นหลัง effective (walk up + composite alpha layers)
    // ถ้าเจอ background-image (gradient/image) → skip (เราเช็คไม่ได้แม่นยำ → return null)
    function effectiveBg(el) {
        let layers = [];
        let cur = el;
        let hasGradient = false;
        while (cur && cur !== document.documentElement) {
            const cs = getComputedStyle(cur);
            const bgImg = cs.backgroundImage;
            if (bgImg && bgImg !== 'none') { hasGradient = true; break; }
            const bg = parseColor(cs.backgroundColor);
            if (bg && bg[3] > 0.001) {
                layers.unshift(bg);
                if (bg[3] >= 0.999) break;  // opaque — stop walking up
            }
            cur = cur.parentElement;
        }
        if (hasGradient) return null;  // can't compute — caller will skip
        if (!layers.length) {
            const bodyBg = parseColor(getComputedStyle(document.body).backgroundColor) || [255,255,255,1];
            layers = [bodyBg];
        }
        let acc = layers[0];
        for (let i = 1; i < layers.length; i++) acc = composite(layers[i], acc);
        return acc;
    }
    // ดู text node — เก็บเฉพาะที่ visible + ไม่ว่าง
    function isElementVisible(el) {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
        const r = el.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return false;
        return true;
    }
    const failures = [];
    const seen = new Map();  // dedupe by (selector, text)
    // เลือก element ที่มี text เป็นของตัวเอง (direct text child)
    const all = document.querySelectorAll('button, a, h1, h2, h3, h4, h5, h6, p, span, div, label, li, code, strong, em');
    for (const el of all) {
        if (!isElementVisible(el)) continue;
        // direct text content (ไม่นับ child element text)
        let directText = '';
        for (const n of el.childNodes) {
            if (n.nodeType === 3) directText += n.textContent;
        }
        directText = directText.trim();
        if (!directText || directText.length < 2) continue;
        // skip pure icon spans (Material Symbols)
        const role = el.getAttribute('role');
        const aria = el.getAttribute('aria-label') || '';
        if (role === 'img' && aria.endsWith(' icon')) continue;
        const cs = getComputedStyle(el);
        const color = parseColor(cs.color);
        if (!color) continue;
        const bg = effectiveBg(el);
        if (!bg) continue;  // gradient/image bg — skip (can't compute reliably)
        const ratio = contrast(color, bg);
        // WCAG AA: 4.5:1 normal, 3.0:1 ≥18pt or ≥14pt bold
        const fontSize = parseFloat(cs.fontSize);
        const fontWeight = parseInt(cs.fontWeight) || 400;
        const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
        const minRatio = isLarge ? 3.0 : 4.5;
        if (ratio < minRatio) {
            const tag = el.tagName.toLowerCase();
            const cls = (el.className || '').toString().split(/\s+/).filter(c => c && !c.startsWith('st-emotion-')).slice(0,3).join('.');
            const key = tag + '|' + cls + '|' + directText.substring(0,30);
            if (seen.has(key)) continue;
            seen.set(key, true);
            failures.push({
                tag,
                cls: cls || '',
                text: directText.substring(0, 60),
                color: 'rgb(' + color.slice(0,3).map(Math.round).join(',') + ')',
                bg: 'rgb(' + bg.slice(0,3).map(Math.round).join(',') + ')',
                ratio: Math.round(ratio*100)/100,
                required: minRatio,
                fontSize: Math.round(fontSize*10)/10,
                fontWeight,
                isLarge,
            });
        }
    }
    return failures.sort((a,b) => a.ratio - b.ratio);
}
"""


def audit_theme(theme_label):
    """Visit each tab, screenshot + collect contrast failures"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            color_scheme=theme_label,
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_selector('[data-testid="stApp"]', timeout=15000)
        time.sleep(3.0)  # wait JS observer install + theme apply

        # verify theme actually rendered
        actual_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        actual_dark_attr = page.evaluate("document.documentElement.getAttribute('data-theme')")
        print(f"  [{theme_label}] body.bg={actual_bg}  html[data-theme]={actual_dark_attr}")

        report = {'theme': theme_label, 'tabs': [], 'body_bg': actual_bg, 'data_theme': actual_dark_attr}

        # Overview screenshot
        page.screenshot(path=str(OUT / f"{theme_label}_00_overview.png"), full_page=True)

        # initial contrast scan (overview)
        try:
            failures = page.evaluate(CONTRAST_JS)
            report['tabs'].append({'name': 'overview', 'failures': failures, 'failure_count': len(failures)})
            print(f"  [{theme_label}] overview: {len(failures)} contrast failures")
        except Exception as e:
            print(f"  [{theme_label}] overview scan FAILED: {e}")

        for i, name in enumerate(TABS, 1):
            try:
                tab = page.locator(f'button[role="tab"]:has-text("{name}")').first
                tab.click()
                time.sleep(2.0)
                ss = OUT / f"{theme_label}_{i:02d}_{name.replace(' ', '_')}.png"
                page.screenshot(path=str(ss), full_page=True)
                failures = page.evaluate(CONTRAST_JS)
                report['tabs'].append({
                    'name': name,
                    'screenshot': ss.name,
                    'failures': failures,
                    'failure_count': len(failures),
                })
                print(f"  [{theme_label}] {name}: {len(failures)} contrast failures → {ss.name}")
            except Exception as e:
                print(f"  [{theme_label}] FAILED {name}: {e}")
                report['tabs'].append({'name': name, 'error': str(e)})

        browser.close()
        return report


def merge_unique_failures(theme_report):
    """รวม failure ทุก tab เป็น set unique (key = color+bg+tag)"""
    seen = {}
    for tab in theme_report.get('tabs', []):
        for f in tab.get('failures', []):
            k = (f['color'], f['bg'], f['tag'], f['cls'])
            if k in seen:
                seen[k]['tabs'].add(tab['name'])
                seen[k]['examples'].add(f['text'])
            else:
                seen[k] = {**f, 'tabs': {tab['name']}, 'examples': {f['text']}}
    out = []
    for v in seen.values():
        v['tabs'] = sorted(v['tabs'])
        v['examples'] = sorted(v['examples'])[:3]
        out.append(v)
    out.sort(key=lambda x: x['ratio'])
    return out


def write_summary(reports):
    lines = ["# INKEXTRACT — Contrast Audit Summary\n"]
    for theme, rep in reports.items():
        unique = merge_unique_failures(rep)
        lines.append(f"\n## {theme.upper()}  body.bg={rep['body_bg']}  data-theme={rep['data_theme']}")
        lines.append(f"  total unique failures: {len(unique)}\n")
        if not unique:
            lines.append("  ✓ NO failures — all text meets WCAG AA")
            continue
        for f in unique[:40]:
            lines.append(
                f"  [{f['ratio']:.2f}:1 / need {f['required']:.1f}]  "
                f"{f['tag']}{('.' + f['cls']) if f['cls'] else ''}"
                f"  color={f['color']}  bg={f['bg']}  size={f['fontSize']}/w{f['fontWeight']}"
            )
            lines.append(f"      tabs={f['tabs']}  examples={f['examples']}")
        if len(unique) > 40:
            lines.append(f"  ... +{len(unique)-40} more")
    return '\n'.join(lines)


if __name__ == "__main__":
    print("=== LIGHT ===")
    light = audit_theme("light")
    print("=== DARK ===")
    dark = audit_theme("dark")
    reports = {"light": light, "dark": dark}

    (OUT / "contrast_report.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False), encoding='utf-8')
    summary = write_summary(reports)
    (OUT / "audit_summary.txt").write_text(summary, encoding='utf-8')

    print("\n" + summary)
    print(f"\nReport: {OUT}/contrast_report.json")
    print(f"Summary: {OUT}/audit_summary.txt")
    print(f"Screenshots: {len(list(OUT.glob('*.png')))}")
