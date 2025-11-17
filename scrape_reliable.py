"""
scrape_reliable.py - Standard scraper for most footwear sites
Works perfectly for: Nike, Merrell, Wolverine, Saucony, Under Armour
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re


def scrape_website(url, use_bright_data=False, bright_data_auth=None, auto_paginate=True, max_pages=10):
    """
    Reliable scraper for standard footwear sites.

    Args:
        url: Website URL to scrape
        use_bright_data: Not implemented (for future proxy support)
        bright_data_auth: Not implemented
        auto_paginate: Whether to automatically follow pagination
        max_pages: Maximum number of pages to scrape

    Returns:
        tuple: (html_content, metadata)
    """

    # Chrome options for stability
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--js-flags=--max-old-space-size=512')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Preferences
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,  # Disable images for speed
            'javascript': 1
        }
    }
    chrome_options.add_experimental_option('prefs', prefs)

    driver = None
    all_html = []
    pages_scraped = 0
    current_url = url

    print(f"\n{'='*60}")
    print(f"STARTING SCRAPE")
    print(f"URL: {url}")
    print(f"Auto-paginate: {auto_paginate}")
    print(f"Max pages: {max_pages}")
    print(f"{'='*60}\n")

    try:
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        # Scrape pages
        for page_num in range(1, max_pages + 1):
            if not auto_paginate and page_num > 1:
                break

            try:
                print(f"{'='*60}")
                print(f"PAGE {page_num}/{max_pages}")
                print(f"{'='*60}")
                print(f"Loading: {current_url}")

                # Load page with retry logic
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        print(f"Attempt {attempt}/{max_retries}: Loading...")
                        driver.get(current_url)

                        # Wait for body to load
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        print(f"✓ Page loaded successfully")
                        break

                    except TimeoutException:
                        if attempt == max_retries:
                            print(f"⚠ Failed after {max_retries} attempts")
                            raise
                        print(f"⚠ Timeout, retrying...")
                        time.sleep(5)

                # Initial wait for content
                time.sleep(3)

                # Scroll to load lazy content
                print(f"Scrolling to load content...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                # Get page source
                page_html = driver.page_source
                all_html.append(page_html)
                pages_scraped += 1

                print(f"✓ Page {page_num} captured ({len(page_html):,} bytes)")

                # Look for next page if auto-paginate is enabled
                if auto_paginate and page_num < max_pages:
                    print(f"\nLooking for next page...")
                    time.sleep(2)

                    next_page_found = False

                    # Try different pagination selectors
                    next_selectors = [
                        "a[aria-label*='next' i]",
                        "a[title*='next' i]",
                        "button[aria-label*='next' i]",
                        "a.pagination__next",
                        ".pagination a:last-child",
                        "a[rel='next']",
                        "link[rel='next']"
                    ]

                    for selector in next_selectors:
                        try:
                            next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)

                            for btn in next_buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    # Check if it's actually a next button (not disabled)
                                    btn_class = btn.get_attribute('class') or ''
                                    btn_disabled = btn.get_attribute('aria-disabled') or ''

                                    if 'disabled' not in btn_class.lower() and btn_disabled.lower() != 'true':
                                        print(f"  ✓ Found next page button")
                                        btn.click()
                                        time.sleep(4)
                                        current_url = driver.current_url
                                        next_page_found = True
                                        break

                            if next_page_found:
                                break

                        except Exception as e:
                            continue

                    if not next_page_found:
                        print(f"  ⚠ No more pages found")
                        break

            except TimeoutException:
                print(f"⚠ Timeout on page {page_num}, stopping...")
                break

            except Exception as e:
                print(f"⚠ Error on page {page_num}: {str(e)[:100]}")
                break

        # Combine all HTML
        combined_html = '\n\n<!-- PAGE BREAK -->\n\n'.join(all_html)

        metadata = {
            'url': url,
            'pages_scraped': pages_scraped,
            'total_html_length': len(combined_html),
            'scraper_type': 'standard'
        }

        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Pages scraped: {pages_scraped}")
        print(f"Total HTML: {len(combined_html):,} bytes")
        print(f"{'='*60}\n")

        return combined_html, metadata

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        return "", {"error": str(e), "pages_scraped": pages_scraped}

    finally:
        if driver:
            driver.quit()
            print("Browser closed")


if __name__ == "__main__":
    # Quick test
    test_url = "https://www.nike.com/w/sale-3yaep"
    html, meta = scrape_website(test_url, auto_paginate=False, max_pages=1)
    print(f"\nTest complete: {len(html)} bytes captured")