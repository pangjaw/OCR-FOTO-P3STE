import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def test_pdf_links():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        print("1. Navigating to http://localhost:5000 ...")
        page.goto("http://localhost:5000", wait_until="domcontentloaded", timeout=15000)

        print("2. Switching to Daftar Pegawai tab ...")
        page.locator(".nav-tab:has-text('Daftar Pegawai')").click()

        print("3. Waiting for data rows (not loading row) in #filePersonnelTableBody ...")
        page.wait_for_selector("#filePersonnelTableBody tr:not(:has-text('Memuat'))", timeout=20000)
        page.wait_for_timeout(1000)

        links = page.locator('#filePersonnelTableBody a[href*="/api/pdf/view-target"]').all()
        print(f"Found {len(links)} clickable PDF Target links in table!")
        assert len(links) > 0, "No PDF target links found in table!"

        first_link = links[0]
        href = first_link.get_attribute("href")
        target = first_link.get_attribute("target")
        text = first_link.inner_text()
        print(f"First link in table: href={href}, target={target}, text={text}")
        assert "/api/pdf/view-target" in href
        assert target == "_blank"

        page.screenshot(path="logs/preview_pdf_links_table.png")
        print("Saved logs/preview_pdf_links_table.png")

        print("4. Testing Single Correct Modal link ...")
        correct_btn = page.locator('#filePersonnelTableBody button:has-text("✏️ Koreksi")').first
        correct_btn.click()
        page.wait_for_selector("#modalCorrectSinglePersonnel", state="visible", timeout=5000)
        page.wait_for_timeout(500)

        modal_link = page.locator('#singleCorrectFileName a[href*="/api/pdf/view-target"]').first
        modal_href = modal_link.get_attribute("href")
        modal_text = modal_link.inner_text()
        print(f"Modal link: href={modal_href}, text={modal_text}")
        assert "/api/pdf/view-target" in modal_href

        page.screenshot(path="logs/preview_pdf_modal_link.png")
        print("Saved logs/preview_pdf_modal_link.png")

        print("5. Closing modal and checking Main Dashboard target table ...")
        page.locator("#modalCorrectSinglePersonnel button:has-text('Batal')").click()
        page.wait_for_timeout(500)

        page.locator(".nav-tab:has-text('Edit Tanggal Timemark')").click()
        page.wait_for_selector("#targetFileTable tr:not(:has-text('Memuat'))", timeout=15000)
        page.wait_for_timeout(1000)

        target_table_links = page.locator('#targetFileTable a[href*="/api/pdf/view-target"]').all()
        print(f"Found {len(target_table_links)} clickable PDF Target links in main dashboard table!")
        if len(target_table_links) > 0:
            tbl_link = target_table_links[0]
            print(f"Dashboard target table link: href={tbl_link.get_attribute('href')}, text={tbl_link.inner_text()}")

        page.screenshot(path="logs/preview_dashboard_target_links.png")
        print("Saved logs/preview_dashboard_target_links.png")

        browser.close()
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pdf_links()
