import itertools
import json
import re
import time
from typing import Any

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def goto_with_retries(url: str, max_attempts: int = 3) -> list[BeautifulSoup]:
    for _ in range(max_attempts):
        try:
            with sync_playwright() as p:
                results = []

                # Launch headless browser
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate and wait until network activity settles
                page.goto(url, wait_until='networkidle')
                time.sleep(1)

                # Get the fully rendered HTML
                dynamic_html = page.content()
                results.append(BeautifulSoup(dynamic_html, 'html.parser'))

                # Click next button until disabled
                next_button = page.get_by_role('button', name='next-page')
                page.locator('.om-popup-close-x').click()

                while next_button.is_enabled():
                    next_button.click()
                    time.sleep(0.5)
                    page.wait_for_load_state('networkidle')
                    time.sleep(1)
                    dynamic_html = page.content()
                    results.append(BeautifulSoup(dynamic_html, 'html.parser'))

                browser.close()

            return results

        except Exception as e:
            print(e)

    return results


def extract_tours(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [extract_tour(tour_soup) for tour_soup in soup.select('.mui-style-15hbzfg')]


def extract_tour(soup: BeautifulSoup) -> dict[str, Any]:
    def get_count(label: str) -> int:
        for count in soup.select('.mui-style-7y7di4'):
            match = re.search(rf'\b(\d+)\s+{label}\b', count.get_text(), re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    title = soup.select_one('.mui-style-10nejqd')
    price_text = soup.select_one('.mui-style-5s2zzh').get_text()
    price_match = re.search(
        r'\bS\$\s*([\d,]+)',
        price_text,
        re.IGNORECASE,
    )
    starting_price = int(price_match.group(1).replace(',', '')) if price_match else None

    return {
        'name': title.get_text().strip(),
        'nights': get_count('nights?'),
        'countries': get_count('countries?'),
        'cities': get_count('cities?'),
        'link': title.select_one('a').get('href'),
        'starting_price': starting_price,
    }


if __name__ == '__main__':
    soups = goto_with_retries('https://www.chanbrothers.com/destinations/europe')
    tours = list(itertools.chain.from_iterable(extract_tours(soup) for soup in soups))
    with open('destination_research/tours.json', 'w') as f:
        f.write(json.dumps(tours, indent=4))
