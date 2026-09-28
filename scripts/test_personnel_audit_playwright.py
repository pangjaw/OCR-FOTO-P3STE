import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def test_audit():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 950})

        print("1. Navigating to http://localhost:5000 ...")
        page.goto("http://localhost:5000", wait_until="domcontentloaded", timeout=15000)

        print("2. Switching to Daftar Pegawai tab ...")
        page.locator(".nav-tab:has-text('Daftar Pegawai')").click()
        page.wait_for_timeout(2000)

        print("3. Checking personnel table and audit status ...")
        page.wait_for_selector("#filePersonnelTable tbody tr", timeout=15000)
        
        # Click button to open audit card
        print("4. Clicking '🔍 Audit Aturan Personil' button ...")
        page.locator("#btnTogglePersonnelAudit").click()
        page.wait_for_timeout(3000)

        # Wait for audit metric values (4 cards)
        total_text = page.locator("#auditMetricTotal").inner_text()
        critical_text = page.locator("#auditMetricCritical").inner_text()
        warning_text = page.locator("#auditMetricWarning").inner_text()
        ok_text = page.locator("#auditMetricOk").inner_text()
        print(f"Metrics: Total={total_text}, Temuan Utama={critical_text}, Temuan Biasa={warning_text}, Sesuai={ok_text}")

        # Capture screenshot of audit card & table
        screenshot_audit = logs_dir / "preview_personnel_audit.png"
        page.screenshot(path=str(screenshot_audit), full_page=False)
        print(f"Audit screenshot saved to: {screenshot_audit}")

        # Filter by Temuan Utama (Critical)
        print("5. Clicking '🚨 Temuan Utama' quick filter ...")
        page.locator("#btnAuditFilterCritical").click()
        page.wait_for_timeout(1000)
        
        count_critical = page.locator("#filePersCount").inner_text()
        print(f"Count text after filter Temuan Utama: {count_critical}")
        assert "64" in count_critical, f"Expected 64 files in Temuan Utama, got: {count_critical}"

        # Filter by Temuan Biasa (Warning)
        print("5b. Clicking 'ℹ️ Temuan Biasa' quick filter ...")
        page.locator("#btnAuditFilterWarning").click()
        page.wait_for_timeout(1000)
        count_warning = page.locator("#filePersCount").inner_text()
        print(f"Count text after filter Temuan Biasa: {count_warning}")
        assert "180" in count_warning, f"Expected 180 files in Temuan Biasa, got: {count_warning}"

        # Switch back to Temuan Utama to test Koreksi button
        page.locator("#btnAuditFilterCritical").click()
        page.wait_for_timeout(500)

        # Click Koreksi button on first critical row
        print("6. Clicking '✏️ Koreksi' button on first Temuan Utama row ...")
        first_koreksi_btn = page.locator("#filePersonnelTableBody tr:first-child button:has-text('✏️ Koreksi')")
        first_koreksi_btn.click()
        page.wait_for_timeout(1000)

        # Verify modal opened
        modal = page.locator("#modalCorrectSinglePersonnel")
        assert modal.is_visible(), "Modal should be visible"
        modal_file = page.locator("#singleCorrectFileName").inner_text()
        print(f"Modal opened for file: {modal_file}")

        # Check dropdowns
        kaur_val = page.locator("#selCorrectKaur").input_value()
        pnc1_val = page.locator("#selCorrectPnc1").input_value()
        pnc2_val = page.locator("#selCorrectPnc2").input_value()
        print(f"Selected in modal: KAUR={kaur_val}, PNC1={pnc1_val}, PNC2={pnc2_val}")

        # Capture modal screenshot
        screenshot_modal = logs_dir / "preview_personnel_modal.png"
        page.screenshot(path=str(screenshot_modal), full_page=False)
        print(f"Modal screenshot saved to: {screenshot_modal}")

        # Close modal
        print("7. Closing modal ...")
        page.locator("#modalCorrectSinglePersonnel button:has-text('✕ Tutup')").click()
        page.wait_for_timeout(500)
        assert not modal.is_visible(), "Modal should be closed"

        # Switch to Mode 2: Folder Luar / Kustom
        print("8. Testing Mode 2: Folder Luar / Kustom ...")
        page.locator("#auditModeCustom").check()
        page.wait_for_timeout(500)
        custom_box = page.locator("#auditCustomPathBox")
        assert custom_box.is_visible(), "Custom path input should be visible in Mode 2"
        print("Mode 2 custom input visible successfully.")

        # Switch back to Mode 1
        page.locator("#auditModePipeline").check()
        page.wait_for_timeout(500)

        print("All UI and audit tests passed successfully!")
        browser.close()

if __name__ == "__main__":
    test_audit()
