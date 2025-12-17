from amadeus import Client, ResponseError
from dotenv import load_dotenv
import os

load_dotenv()

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
        
        return airports
    except:
        # Fallback falls API nicht funktioniert
        return [
            {"code": "BER", "name": "Berlin Brandenburg", "city": "Berlin", "country": "Deutschland"},
            {"code": "JFK", "name": "John F. Kennedy", "city": "New York", "country": "USA"},
            {"code": "LHR", "name": "Heathrow", "city": "London", "country": "UK"}
        ]