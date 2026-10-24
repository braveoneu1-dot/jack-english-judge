import sys, time
from playwright.sync_api import sync_playwright

URL = "https://jack-english-judge-by-jack.streamlit.app/"
WAKE_TEXT = "get this app back up"

def app_rendered(page):
    for f in page.frames:
        try:
            if f.locator("[data-testid='stApp'], [data-testid='stAppViewContainer']").count() > 0:
                return True
        except Exception:
            pass
    return False

def click_wake(page):
    for f in page.frames:
        try:
            b = f.locator(f"button:has-text('{WAKE_TEXT}')")
            if b.count() > 0:
                b.first.click(timeout=10000)
                return True
        except Exception:
            pass
    return False

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    page = br.new_page()
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    print("Landed on:", page.url)
    woke = False
    deadline = time.time() + 180
    while time.time() < deadline:
        if not woke and click_wake(page):
            woke = True
            print("Sleep page detected; clicked wake button")
        if app_rendered(page):
            time.sleep(5)
            print("Streamlit app rendered OK (woke=%s)" % woke)
            br.close()
            sys.exit(0)
        time.sleep(3)
    print("FAILED: app did not render. URL:", page.url)
    print(page.content()[:2000])
    br.close()
    sys.exit(1)
