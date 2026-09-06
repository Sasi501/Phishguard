import pytest
import os
from playwright.sync_api import sync_playwright

def test_extension_load():
    with sync_playwright() as p:
        path_to_extension = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../extension"))
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/test-user-data-dir",
            headless=False,
            args=[
                f"--disable-extensions-except={path_to_extension}",
                f"--load-extension={path_to_extension}",
            ],
        )
        page = browser.new_page()
        page.goto("https://example.com")
        assert "Example Domain" in page.title()
        browser.close()

