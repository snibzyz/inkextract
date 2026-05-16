"""Open dropdown ทุก selectbox แล้ว dump DOM ancestry ของ li[role=option]
   จาก popover → ขึ้นไป — เพื่อหา div ที่ clip ความสูง"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time, json

URL = "http://localhost:8501"
OUT = Path("_screenshots")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1600, "height": 1000}, color_scheme="dark").new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_selector('[data-testid="stTab"]', timeout=20000)
    time.sleep(2.5)

    # Go to proof tab → sub-tab โหมดทั่วไป
    page.locator('button[role="tab"]:has-text("ตรวจสอบและแก้ไข")').first.click()
    time.sleep(1.5)
    try:
        page.locator('button[role="tab"]:has-text("โหมดทั่วไป")').first.click()
        time.sleep(1.5)
    except Exception:
        pass

    # Click the first selectbox
    sb = page.locator('.stSelectbox div[data-baseweb="select"]').first
    sb.click()
    time.sleep(1.5)

    # Inspect ancestry from li back up to popover
    info = page.evaluate("""
        () => {
            const lis = document.querySelectorAll('[role="listbox"] [role="option"]');
            const popover = document.querySelector('div[data-baseweb="popover"]');
            const listbox = document.querySelector('[role="listbox"]');

            const elInfo = (el) => {
                if (!el) return null;
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                return {
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    'data-baseweb': el.getAttribute('data-baseweb'),
                    cls: (el.className || '').toString().substring(0, 60),
                    inline_style: (el.getAttribute('style') || '').substring(0, 200),
                    cs_h: cs.height,
                    cs_max_h: cs.maxHeight,
                    cs_overflow_y: cs.overflowY,
                    cs_position: cs.position,
                    rect_h: Math.round(r.height),
                    rect_w: Math.round(r.width),
                    children: el.children.length,
                };
            };

            const result = {
                option_count: lis.length,
                options: [],
                popover_chain: [],
            };
            for (const li of lis) {
                result.options.push(elInfo(li));
            }
            // walk from popover down
            let node = popover;
            while (node && node !== document.body) {
                result.popover_chain.push(elInfo(node));
                // only follow first child to avoid blow-up
                node = node.children[0];
                if (result.popover_chain.length > 10) break;
            }
            return result;
        }
    """)

    print(json.dumps(info, indent=2, ensure_ascii=False))
    page.screenshot(path=str(OUT / "dropdown_inspect2.png"))
    browser.close()
