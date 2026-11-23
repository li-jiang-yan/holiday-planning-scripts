import json
from datetime import datetime


def clean_tour_dict(tour_dict: dict) -> dict:
    name = tour_dict['name']
    nights = tour_dict['nights']
    url = 'https://www.chanbrothers.com' + tour_dict['link']
    starting_price = tour_dict['starting_price']
    starting_price_per_night = round(starting_price / nights, 2) if nights is not None else None

    # Countries
    country_count = tour_dict['countries']
    countries = (
        tour_dict[f'{country_count} Countries'].split(', ')
        if country_count is not None
        else [tour_dict['link'].split('/')[3].replace('-', ' ').title()]
    )

    # Cities
    city_count = tour_dict['cities']
    if city_count is not None:
        cities = tour_dict[f'{city_count} Cities']
        if isinstance(cities, str):
            cities = cities.split(', ')
        cities = list(dict.fromkeys(cities))
    else:
        cities = None

    # Season
    date_range = tour_dict['Season']
    start_str, end_str = date_range.split(' - ')

    start = datetime.strptime(start_str, '%B %Y')
    end = datetime.strptime(end_str, '%B %Y')

    months = []
    year, month = start.year, start.month

    while (year, month) <= (end.year, end.month):
        months.append(f'{year}-{month:02d}')
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

    return {
        'name': name,
        'nights': nights,
        'url': url,
        'starting_price': starting_price,
        'starting_price_per_night': starting_price_per_night,
        'countries': countries,
        'cities': cities,
        'months': months,
    }


if __name__ == '__main__':
    with open('destination_research/info.json', encoding='utf-8') as f:
        info = json.load(f)

    data = [clean_tour_dict(tour_dict) for tour_dict in info]

    with open('destination_research/data.json', 'w') as f:
        f.write(json.dumps(data, indent=4))
