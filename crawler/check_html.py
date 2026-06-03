import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx', wait_until='networkidle', timeout=30000)

    sel = page.query_selector('select#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
    options = sel.query_selector_all('option')
    for o in options:
        print(f'value={o.get_attribute("value")!r}  text={o.inner_text().strip()!r}')

    browser.close()
