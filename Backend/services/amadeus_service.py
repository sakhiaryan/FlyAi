from amadeus import Client, ResponseError
from dotenv import load_dotenv
import os

load_dotenv()

amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def search_flights_amadeus(origin: str, destination: str, date: str, adults: int = 1):
    """
    Sucht echte Flüge über Amadeus API
    """
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=date,
            adults=adults,
            max=10
        )
        return {"success": True, "flights": response.data}
    except ResponseError as error:
        # Zeige den ECHTEN Fehler
        return {
            "success": False, 
            "error": str(error),
            "status_code": error.response.status_code if error.response else None,
            "detail": error.response.body if error.response else None
        }
    except Exception as e:
        return {"success": False, "error": str(e), "type": type(e).__name__}