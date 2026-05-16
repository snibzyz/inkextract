"""Comprehensive UI audit: screenshot all tabs + measure widget sizes
    + capture dropdown open states + identify alignment issues"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time, json

URL = "http://localhost:8501"
OUT = Path("_screenshots")
OUT.mkdir(exist_ok=True)

# Clear old
for f in OUT.glob("*.png"):
    f.unlink()

TABS = ["โปรเจกต์", "ตรวจต้นฉบับ", "คำศัพท์", "ตรวจสอบและแก้ไข", "จัดการไฟล์"]

# What to measure per tab — selectors of common widgets
MEASURE = {
    'button': '.stButton button',
    'selectbox': '.stSelectbox div[data-baseweb="select"]',
    'text_input': '.stTextInput input',
    'number_input': '.stNumberInput input',
    'tab': '[data-testid="stTab"]',
}

def measure_widgets(page):
    """Return dict of {widget_type: [{text, height, width, y}]}"""
    return page.evaluate("""
        (sel) => {
            const result = {};
            for (const [name, query] of Object.entries(sel)) {
                const els = document.querySelectorAll(query);
                result[name] = [];
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    const t = (el.textContent || el.value || '').trim().substring(0, 30);
                    result[name].push({text: t, w: Math.round(r.width), h: Math.round(r.height), y: Math.round(r.y)});
                    if (result[name].length >= 5) break;
                }
            }
            return result;
        }
    """, MEASURE)


def audit_dropdown(page):
    """Click first selectbox, measure dropdown li"""
    sb = page.locator('.stSelectbox div[data-baseweb="select"]').first
    try:
        sb.click()
        time.sleep(1.2)
    except Exception as e:
        return {'error': f'click failed: {e}'}

    info = page.evaluate("""
        () => {
            const lis = document.querySelectorAll('ul[role="listbox"] li[role="option"]');
            if (lis.length === 0) return {error: 'no options visible'};
            const arr = [];
            for (const li of lis) {
                const cs = getComputedStyle(li);
                const r = li.getBoundingClientRect();
                arr.push({
                    text: (li.textContent || '').trim().substring(0, 30),
                    cs_h: cs.height,
                    cs_min: cs.minHeight,
                    cs_pos: cs.position,
                    rect_h: Math.round(r.height),
                    rect_y: Math.round(r.y),
                    inline: (li.getAttribute('style') || '').substring(0, 100),
                });
            }
            return {count: lis.length, items: arr};
        }
    """)
    return info


def run_audit(theme_label):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = {"viewport": {"width": 1600, "height": 1000}}
        if theme_label == "dark":
            ctx["color_scheme"] = "dark"
        page = browser.new_context(**ctx).new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_selector('[data-testid="stTab"]', timeout=20000)
        time.sleep(2.5)

        report = {'theme': theme_label, 'tabs': []}

        # Overview screenshot
        page.screenshot(path=str(OUT / f"{theme_label}_00_overview.png"))

        for i, name in enumerate(TABS, 1):
            try:
                page.locator(f'button[role="tab"]:has-text("{name}")').first.click()
                time.sleep(1.8)
                ss = OUT / f"{theme_label}_{i:02d}_{name.replace(' ', '_')}.png"
                page.screenshot(path=str(ss), full_page=True)
                meas = measure_widgets(page)
                report['tabs'].append({'name': name, 'screenshot': ss.name, 'measurements': meas})
                print(f"  saved {ss.name}")
            except Exception as e:
                print(f"  FAILED {name}: {e}")
                report['tabs'].append({'name': name, 'error': str(e)})

        # Special: dropdown test
        try:
            page.locator('button[role="tab"]:has-text("ตรวจสอบและแก้ไข")').first.click()
            time.sleep(1.5)
            # Try sub-tab if exists
            try:
                page.locator('button[role="tab"]:has-text("โหมดทั่วไป")').first.click()
                time.sleep(1.5)
            except Exception:
                pass
            dd = audit_dropdown(page)
            report['dropdown'] = dd
            page.screenshot(path=str(OUT / f"{theme_label}_99_dropdown.png"))
            print(f"  dropdown: {dd}")
        except Exception as e:
            print(f"  dropdown audit failed: {e}")

        browser.close()
        return report


if __name__ == "__main__":
    print("=== LIGHT ===")
    light = run_audit("light")
    print("=== DARK ===")
    dark = run_audit("dark")

    # Save report
    (OUT / "audit_report.json").write_text(
        json.dumps({"light": light, "dark": dark}, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"\nReport: {OUT}/audit_report.json")
    print(f"Total screenshots: {len(list(OUT.glob('*.png')))}")
