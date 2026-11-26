import json
from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel

# Initialize the client (automatically reads OPENAI_API_KEY from environment)
client = OpenAI()


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

    # Attractions
    if 'itinerary' in tour_dict:
        itinerary_html = tour_dict['itinerary']
        attractions = extract_attractions(itinerary_html, countries)
    else:
        attractions = None

    return {
        'name': name,
        'nights': nights,
        'url': url,
        'starting_price': starting_price,
        'starting_price_per_night': starting_price_per_night,
        'countries': countries,
        'cities': classify_cities(cities, countries),
        'months': months,
        'attractions': attractions,
    }


def classify_cities(cities: list, countries: list) -> dict:
    if cities is None:
        return

    if len(countries) == 1:
        return {countries[0]: sorted(list(set(cities)))}

    class CityMatch(BaseModel):
        city: str
        country: str

    class Results(BaseModel):
        matches: list[CityMatch]

    response = client.responses.parse(
        model='gpt-6-luna',
        input=[
            {
                'role': 'system',
                'content': (
                    'Match each city to a country from the supplied list only. '
                    'Return one match for every input city, in order.'
                ),
            },
            {
                'role': 'user',
                'content': f'Cities: {cities}\nAllowed countries: {countries}',
            },
        ],
        text_format=Results,
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError('No parsed result; handle refusals or incomplete responses.')

    # Validate the model's country values against your authoritative input list.
    allowed = set(countries)
    for match in result.matches:
        if match.country is not None and match.country not in allowed:
            raise ValueError(f'Unexpected country: {match.country}')

    matches = result.model_dump()['matches']
    return {
        country: sorted(
            list(set(match['city'] for match in matches if match['country'] == country))
        )
        for country in countries
    }


def extract_attractions(itinerary_html: str, countries: list) -> dict:
    class AttractionMatch(BaseModel):
        attraction: str
        country: str

    class Results(BaseModel):
        matches: list[AttractionMatch]

    response = client.responses.parse(
        model='gpt-6-luna',
        input=[
            {
                'role': 'system',
                'content': (
                    'Extract the attractions listed in the given HTML itinerary. '
                    'Match each attraction to a country from the supplied list only. '
                    'Return one match for every input attraction, in order.'
                ),
            },
            {
                'role': 'user',
                'content': f'HTML Itinerary: {itinerary_html}\nAllowed countries: {countries}',
            },
        ],
        text_format=Results,
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError('No parsed result; handle refusals or incomplete responses.')

    # Validate the model's country values against your authoritative input list.
    allowed = set(countries)
    for match in result.matches:
        if match.country is not None and match.country not in allowed:
            raise ValueError(f'Unexpected country: {match.country}')

    matches = result.model_dump()['matches']
    return {
        country: sorted(
            list(set(match['attraction'] for match in matches if match['country'] == country))
        )
        for country in countries
    }


if __name__ == '__main__':
    with open('destination_research/info.json', encoding='utf-8') as f:
        info = json.load(f)

    data = [clean_tour_dict(tour_dict) for tour_dict in info]

    with open('destination_research/data.json', 'w') as f:
        f.write(json.dumps(data, indent=4))
