from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5000', wait_until='domcontentloaded')
    page.locator(".nav-tab:has-text('Daftar Pegawai')").click()
    page.wait_for_timeout(3000)
    print("Table Body HTML:")
    print(page.locator("#filePersonnelTableBody").inner_html()[:1000])
    browser.close()
