"""Check that a walk opened from the off-route temple is visible and reversible.

Serve dist/, then run with Python Playwright and an installed Chromium browser:
    python3 tests/walking-route.py http://localhost:8000/
"""
import os
import sys

from playwright.sync_api import sync_playwright


def check_route(browser, url, width):
    context = browser.new_context(viewport={"width": width, "height": 800},
                                  reduced_motion="reduce", has_touch=width < 500)
    try:
        page = context.new_page()
        page.goto(url + "?place=baofu")
        page.locator("#loading").wait_for(state="hidden", timeout=90000)
        original = page.locator("#coords").inner_text()
        toggle = page.locator("#route")
        activate = toggle.tap if width < 500 else toggle.click
        activate()
        page.wait_for_function("""() => {
          const svg = document.querySelector('#journey');
          const legs = [...svg.querySelectorAll('path:not(.halo)')];
          const bounds = svg.getBoundingClientRect();
          return bounds.width > 0 && legs.length === 2 && legs.every(leg => {
            const box = leg.getBBox();
            return box.width > 0 && box.height > 0 && box.x >= 0 && box.y >= 0
              && box.x + box.width <= bounds.width && box.y + box.height <= bounds.height;
          });
        }""")
        assert page.locator(".map-pin:visible").count() == 3
        assert toggle.get_attribute("aria-pressed") == "true"
        activate()
        page.locator("#journey").wait_for(state="hidden")
        assert page.locator("#coords").inner_text() == original
        assert "place=baofu" in page.url
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
        for width in (1280, 390):
            check_route(browser, sys.argv[1].rstrip("/") + "/", width)
        browser.close()
