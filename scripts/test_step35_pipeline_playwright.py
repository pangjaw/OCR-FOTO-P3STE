import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def verify_step35_buttons():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        print("1. Opening http://localhost:5000 ...")
        page.goto("http://localhost:5000", wait_until="domcontentloaded", timeout=15000)

        print("2. Checking Step 3.5 button on Tab 1 (Edit Tanggal Timemark) ...")
        btn_tab1 = page.locator("button:has-text('Step 3.5: Koreksi Personil')").first
        assert btn_tab1.is_visible(), "Step 3.5 button on Tab 1 is not visible!"
        print("Tab 1 Step 3.5 button text:", btn_tab1.inner_text())

        page.screenshot(path="logs/preview_pipeline_tab1_step35.png")
        print("Saved logs/preview_pipeline_tab1_step35.png")

        print("3. Switching to Tab 2 (Edit Jam Foto) ...")
        page.locator(".nav-tab:has-text('Edit Jam Foto')").click()
        page.wait_for_timeout(1000)

        btn_tab2 = page.locator("#timeTab button:has-text('Step 3.5: Koreksi Personil')").first
        assert btn_tab2.is_visible(), "Step 3.5 button on Tab 2 is not visible!"
        print("Tab 2 Step 3.5 button text:", btn_tab2.inner_text())

        page.screenshot(path="logs/preview_pipeline_tab2_step35.png")
        print("Saved logs/preview_pipeline_tab2_step35.png")

        browser.close()
        print("✅ Playwright verification of Step 3.5 pipeline buttons succeeded!")

if __name__ == "__main__":
    verify_step35_buttons()
