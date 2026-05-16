"""Screenshot the Reflex POC for visual comparison"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

OUT = Path("_screenshots")
OUT.mkdir(exist_ok=True)
URL = "http://localhost:3500"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for label, scheme in [("light", "light"), ("dark", "dark")]:
        page = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            color_scheme=scheme,
        ).new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_selector("h1, .rt-Heading", timeout=20000)
            time.sleep(6)  # allow React hydration + Lucide icons SVG mount
            page.screenshot(path=str(OUT / f"reflex_{label}_project.png"),
                            full_page=True)
            print(f"saved reflex_{label}_project.png")

            # also capture: click "สลับไป" on second project to show toast
            try:
                page.locator('button:has-text("สลับไป")').first.click()
                time.sleep(1.5)
                page.screenshot(
                    path=str(OUT / f"reflex_{label}_after_switch.png"),
                    full_page=True,
                )
                print(f"saved reflex_{label}_after_switch.png")
            except Exception as e:
                print(f"  switch click failed: {e}")

            # capture: click + open create form
            try:
                page.locator('button:has-text("สร้างโปรเจกต์ใหม่")').first.click()
                time.sleep(1)
                page.screenshot(
                    path=str(OUT / f"reflex_{label}_create_form.png"),
                    full_page=True,
                )
                print(f"saved reflex_{label}_create_form.png")
            except Exception as e:
                print(f"  create form click failed: {e}")

        except Exception as e:
            print(f"FAILED {label}: {e}")
    browser.close()
print("done")
