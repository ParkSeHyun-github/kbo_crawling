from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('http://127.0.0.1:8000/?season=2025', wait_until='networkidle', timeout=15000)
    page.screenshot(path='screenshot.png', full_page=False)
    browser.close()
    print('screenshot.png 저장 완료')
