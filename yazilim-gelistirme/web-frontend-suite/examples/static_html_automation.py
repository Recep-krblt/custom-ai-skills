from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import tempfile

# Example: Automating interaction with static HTML files using file:// URLs

file_url = Path('path/to/your/file.html').resolve().as_uri()
out_dir = tempfile.gettempdir()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # Navigate to local HTML file
    page.goto(file_url)

    # Take screenshot
    page.screenshot(path=os.path.join(out_dir, 'static_page.png'), full_page=True)

    # Interact with elements
    page.click('text=Click Me')
    page.fill('#name', 'John Doe')
    page.fill('#email', 'john@example.com')

    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)

    # Take final screenshot
    page.screenshot(path=os.path.join(out_dir, 'after_submit.png'), full_page=True)

    browser.close()

print("Static HTML automation completed!")