"""Screenshot Reflex POC v2 — all 5 tabs"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

OUT = Path("_screenshots")
OUT.mkdir(exist_ok=True)
URL = "http://localhost:4500"

TAB_LABELS = ["โปรเจกต์", "ตรวจต้นฉบับ", "คำศัพท์", "ตรวจสอบและแก้ไข", "จัดการไฟล์"]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1440, "height": 1100}).new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(6)

    page.screenshot(path=str(OUT / "reflex2_01_project.png"), full_page=True)
    print("saved reflex2_01_project.png")

    for i, label in enumerate(TAB_LABELS[1:], start=2):
        try:
            page.locator(f'text="{label}"').first.click()
            time.sleep(2.5)
            slug = label.replace(" ", "_")
            out_name = f"reflex2_{i:02d}_{slug}.png"
            page.screenshot(path=str(OUT / out_name), full_page=True)
            print(f"saved {out_name}")
        except Exception as e:
            print(f"FAILED {label}: {e}")

    browser.close()
print("done")
