import json
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def extract_info(url: str, max_attempts: int = 3) -> dict:
    def get_card_info(card_soup: BeautifulSoup) -> tuple:
        title = card_soup.select_one('.mui-style-zix8z0').get_text()
        content = card_soup.select_one('.mui-style-1nx3dmf')
        if content is not None:
            return (title, content.get_text())

        content = card_soup.select_one('.mui-style-1pevhg6')
        if content is not None:
            return (title, [item.title() for item in content.get_text().split(', ')])

        content = card_soup.select_one('.mui-style-wpionb')
        if content is not None:
            return (title, [li.get_text() for li in content.select('.mui-style-hf84um')])

    for _ in range(max_attempts):
        try:
            with sync_playwright() as p:
                # Launch headless browser
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate and wait until network activity settles
                page.goto(url, wait_until='networkidle')
                time.sleep(1)

                # Get the fully rendered HTML
                dynamic_html = page.content()
                soup = BeautifulSoup(dynamic_html, 'html.parser')

                # Extract card info
                cards = soup.select('div.mui-style-1c9ql2d')
                cards_dict = dict(get_card_info(card) for card in cards)

                # Get itinerary if available
                itinerary_button = page.get_by_role('tab', name='ITINERARY', exact=True)
                if (
                    itinerary_button.count() > 0
                    and itinerary_button.first.is_visible()
                    and itinerary_button.first.is_enabled()
                ):
                    itinerary_button.first.click()
                    time.sleep(0.5)
                    page.wait_for_load_state('networkidle')
                    time.sleep(1)

                    dynamic_html = page.content()
                    soup = BeautifulSoup(dynamic_html, 'html.parser')

                    return {
                        **cards_dict,
                        'itinerary': soup.select_one('.mui-style-fvnyah').prettify(),
                    }

                return cards_dict

        except Exception as e:
            print(e)

    return {}


if __name__ == '__main__':
    with open('destination_research/tours.json', encoding='utf-8') as f:
        tours = json.load(f)

    info = [
        {**tour, **extract_info('https://www.chanbrothers.com' + tour['link'])} for tour in tours
    ]

    with open('destination_research/info.json', 'w') as f:
        f.write(json.dumps(info, indent=4))
