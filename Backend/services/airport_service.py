from amadeus import Client, ResponseError
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger("flyai.airport")

amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def search_airports(query: str):
    """Sucht echte Flughäfen über Amadeus API"""
    try:
        response = amadeus.reference_data.locations.get(
            keyword=query,
            subType='AIRPORT,CITY'
        )

        airports = []
        for location in response.data[:10]:  # Max 10 Ergebnisse
            airports.append({
                "code": location.get('iataCode', ''),
                "name": location.get('name', ''),
                "city": location.get('address', {}).get('cityName', ''),
                "country": location.get('address', {}).get('countryName', '')
            })

        logger.info("Airport search for '%s': %d results", query, len(airports))
        return airports
    except ResponseError as e:
        logger.error("Amadeus API error for query '%s': %s", query, e)
        return [
            {"code": "BER", "name": "Berlin Brandenburg", "city": "Berlin", "country": "Deutschland"},
            {"code": "JFK", "name": "John F. Kennedy", "city": "New York", "country": "USA"},
            {"code": "LHR", "name": "Heathrow", "city": "London", "country": "UK"}
        ]
    except Exception as e:
        logger.error("Airport search failed for query '%s': %s", query, e)
        return [
            {"code": "BER", "name": "Berlin Brandenburg", "city": "Berlin", "country": "Deutschland"},
            {"code": "JFK", "name": "John F. Kennedy", "city": "New York", "country": "USA"},
            {"code": "LHR", "name": "Heathrow", "city": "London", "country": "UK"}
        ]