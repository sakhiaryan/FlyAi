import httpx
import os
import random
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, List
from datetime import datetime, timedelta

load_dotenv()

logger = logging.getLogger("flyai.skyscanner")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"
BASE_URL = "https://sky-scrapper.p.rapidapi.com/api/v1"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# Bekannte Flughäfen für Mock-Daten
AIRPORTS = {
    "stuttgart": {"code": "STR", "name": "Stuttgart", "city": "Stuttgart"},
    "str": {"code": "STR", "name": "Stuttgart", "city": "Stuttgart"},
    "berlin": {"code": "BER", "name": "Berlin Brandenburg", "city": "Berlin"},
    "ber": {"code": "BER", "name": "Berlin Brandenburg", "city": "Berlin"},
    "frankfurt": {"code": "FRA", "name": "Frankfurt am Main", "city": "Frankfurt"},
    "fra": {"code": "FRA", "name": "Frankfurt am Main", "city": "Frankfurt"},
    "münchen": {"code": "MUC", "name": "München Franz Josef Strauß", "city": "München"},
    "munich": {"code": "MUC", "name": "München Franz Josef Strauß", "city": "München"},
    "muc": {"code": "MUC", "name": "München Franz Josef Strauß", "city": "München"},
    "hamburg": {"code": "HAM", "name": "Hamburg", "city": "Hamburg"},
    "ham": {"code": "HAM", "name": "Hamburg", "city": "Hamburg"},
    "düsseldorf": {"code": "DUS", "name": "Düsseldorf", "city": "Düsseldorf"},
    "dus": {"code": "DUS", "name": "Düsseldorf", "city": "Düsseldorf"},
    "köln": {"code": "CGN", "name": "Köln/Bonn", "city": "Köln"},
    "cologne": {"code": "CGN", "name": "Köln/Bonn", "city": "Köln"},
    "london": {"code": "LHR", "name": "London Heathrow", "city": "London"},
    "lhr": {"code": "LHR", "name": "London Heathrow", "city": "London"},
    "paris": {"code": "CDG", "name": "Paris Charles de Gaulle", "city": "Paris"},
    "cdg": {"code": "CDG", "name": "Paris Charles de Gaulle", "city": "Paris"},
    "amsterdam": {"code": "AMS", "name": "Amsterdam Schiphol", "city": "Amsterdam"},
    "ams": {"code": "AMS", "name": "Amsterdam Schiphol", "city": "Amsterdam"},
    "new york": {"code": "JFK", "name": "New York JFK", "city": "New York"},
    "jfk": {"code": "JFK", "name": "New York JFK", "city": "New York"},
    "barcelona": {"code": "BCN", "name": "Barcelona El Prat", "city": "Barcelona"},
    "bcn": {"code": "BCN", "name": "Barcelona El Prat", "city": "Barcelona"},
    "madrid": {"code": "MAD", "name": "Madrid Barajas", "city": "Madrid"},
    "mad": {"code": "MAD", "name": "Madrid Barajas", "city": "Madrid"},
    "rom": {"code": "FCO", "name": "Rom Fiumicino", "city": "Rom"},
    "rome": {"code": "FCO", "name": "Rom Fiumicino", "city": "Rom"},
    "fco": {"code": "FCO", "name": "Rom Fiumicino", "city": "Rom"},
    "mailand": {"code": "MXP", "name": "Mailand Malpensa", "city": "Mailand"},
    "milan": {"code": "MXP", "name": "Mailand Malpensa", "city": "Mailand"},
    "wien": {"code": "VIE", "name": "Wien Schwechat", "city": "Wien"},
    "vienna": {"code": "VIE", "name": "Wien Schwechat", "city": "Wien"},
    "zürich": {"code": "ZRH", "name": "Zürich", "city": "Zürich"},
    "zurich": {"code": "ZRH", "name": "Zürich", "city": "Zürich"},
    "istanbul": {"code": "IST", "name": "Istanbul", "city": "Istanbul"},
    "dubai": {"code": "DXB", "name": "Dubai International", "city": "Dubai"},
    "bangkok": {"code": "BKK", "name": "Bangkok Suvarnabhumi", "city": "Bangkok"},
    "tokyo": {"code": "NRT", "name": "Tokyo Narita", "city": "Tokyo"},
    "los angeles": {"code": "LAX", "name": "Los Angeles", "city": "Los Angeles"},
    "lax": {"code": "LAX", "name": "Los Angeles", "city": "Los Angeles"},
    "mallorca": {"code": "PMI", "name": "Palma de Mallorca", "city": "Mallorca"},
    "palma": {"code": "PMI", "name": "Palma de Mallorca", "city": "Mallorca"},
    "antalya": {"code": "AYT", "name": "Antalya", "city": "Antalya"},
    "athen": {"code": "ATH", "name": "Athen", "city": "Athen"},
    "athens": {"code": "ATH", "name": "Athen", "city": "Athen"},
    "lissabon": {"code": "LIS", "name": "Lissabon", "city": "Lissabon"},
    "lisbon": {"code": "LIS", "name": "Lissabon", "city": "Lissabon"},
    "prag": {"code": "PRG", "name": "Prag", "city": "Prag"},
    "prague": {"code": "PRG", "name": "Prag", "city": "Prag"},
    "kopenhagen": {"code": "CPH", "name": "Kopenhagen", "city": "Kopenhagen"},
    "copenhagen": {"code": "CPH", "name": "Kopenhagen", "city": "Kopenhagen"},
    "brüssel": {"code": "BRU", "name": "Brüssel", "city": "Brüssel"},
    "brussels": {"code": "BRU", "name": "Brüssel", "city": "Brüssel"},
}

# Airlines für Mock-Daten
AIRLINES = [
    {"code": "LH", "name": "Lufthansa", "logo": "https://logos.skyscnr.com/images/airlines/favicon/LH.png"},
    {"code": "EW", "name": "Eurowings", "logo": "https://logos.skyscnr.com/images/airlines/favicon/EW.png"},
    {"code": "FR", "name": "Ryanair", "logo": "https://logos.skyscnr.com/images/airlines/favicon/FR.png"},
    {"code": "U2", "name": "easyJet", "logo": "https://logos.skyscnr.com/images/airlines/favicon/U2.png"},
    {"code": "AF", "name": "Air France", "logo": "https://logos.skyscnr.com/images/airlines/favicon/AF.png"},
    {"code": "BA", "name": "British Airways", "logo": "https://logos.skyscnr.com/images/airlines/favicon/BA.png"},
    {"code": "KL", "name": "KLM", "logo": "https://logos.skyscnr.com/images/airlines/favicon/KL.png"},
    {"code": "TK", "name": "Turkish Airlines", "logo": "https://logos.skyscnr.com/images/airlines/favicon/TK.png"},
    {"code": "EK", "name": "Emirates", "logo": "https://logos.skyscnr.com/images/airlines/favicon/EK.png"},
    {"code": "OS", "name": "Austrian Airlines", "logo": "https://logos.skyscnr.com/images/airlines/favicon/OS.png"},
    {"code": "LX", "name": "Swiss", "logo": "https://logos.skyscnr.com/images/airlines/favicon/LX.png"},
    {"code": "IB", "name": "Iberia", "logo": "https://logos.skyscnr.com/images/airlines/favicon/IB.png"},
]


def get_airport_info(query: str) -> Optional[Dict]:
    """Findet Flughafen-Info aus der lokalen Datenbank"""
    query_lower = query.lower().strip()
    return AIRPORTS.get(query_lower)


def generate_mock_flights(origin: Dict, destination: Dict, date: str, adults: int = 1) -> List[Dict]:
    """Generiert realistische Mock-Flugdaten"""
    flights = []

    # Basis-Preise je nach Entfernung (vereinfacht)
    base_prices = {
        ("STR", "LHR"): 89, ("STR", "CDG"): 79, ("STR", "AMS"): 85,
        ("STR", "BCN"): 69, ("STR", "MAD"): 79, ("STR", "FCO"): 75,
        ("STR", "PMI"): 59, ("STR", "AYT"): 99, ("STR", "ATH"): 89,
        ("BER", "LHR"): 79, ("BER", "CDG"): 89, ("BER", "BCN"): 75,
        ("FRA", "JFK"): 389, ("FRA", "LAX"): 449, ("FRA", "BKK"): 529,
        ("MUC", "DXB"): 349, ("MUC", "NRT"): 589, ("MUC", "IST"): 129,
    }

    # Default Basis-Preis
    key = (origin["code"], destination["code"])
    reverse_key = (destination["code"], origin["code"])
    base_price = base_prices.get(key) or base_prices.get(reverse_key) or random.randint(49, 299)

    # Generiere 8-15 Flüge
    num_flights = random.randint(8, 15)

    for i in range(num_flights):
        airline = random.choice(AIRLINES)

        # Zufällige Abflugzeit zwischen 6:00 und 22:00
        hour = random.randint(6, 21)
        minute = random.choice([0, 15, 30, 45])
        departure_time = f"{date}T{hour:02d}:{minute:02d}:00"

        # Flugdauer (60-180 Minuten für Europa, mehr für Langstrecke)
        if destination["code"] in ["JFK", "LAX", "DXB", "BKK", "NRT"]:
            duration = random.randint(480, 720)  # 8-12 Stunden
        else:
            duration = random.randint(60, 180)  # 1-3 Stunden

        # Ankunftszeit berechnen
        dep_dt = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
        arr_dt = dep_dt + timedelta(minutes=duration)
        arrival_time = arr_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Preis variieren
        price_variation = random.uniform(0.7, 1.8)
        price = int(base_price * price_variation * adults)

        # Stops (meistens direkt, manchmal 1 Stop)
        stops = 0 if random.random() > 0.3 else 1
        if stops == 1:
            duration += random.randint(60, 120)  # Umsteigezeit

        flight = {
            "id": f"mock-{i}-{airline['code']}-{random.randint(1000, 9999)}",
            "price": {
                "total": str(price),
                "formatted": f"{price} €",
                "currency": "EUR"
            },
            "itineraries": [{
                "duration": duration,
                "segments": [{
                    "departure": {
                        "iataCode": origin["code"],
                        "at": departure_time,
                        "airport": origin["name"]
                    },
                    "arrival": {
                        "iataCode": destination["code"],
                        "at": arrival_time,
                        "airport": destination["name"]
                    },
                    "carrierCode": airline["code"],
                    "carrierName": airline["name"],
                    "carrierLogo": airline["logo"],
                    "number": f"{airline['code']}{random.randint(100, 9999)}",
                }]
            }],
            "stops": stops,
            "duration_formatted": format_duration(duration),
            "deep_link": f"https://www.skyscanner.de/transport/flights/{origin['code'].lower()}/{destination['code'].lower()}/{date.replace('-', '')}/"
        }

        flights.append(flight)

    # Nach Preis sortieren
    flights.sort(key=lambda x: int(x["price"]["total"]))

    return flights


async def search_airport(query: str) -> Optional[Dict]:
    """Sucht Flughafen/Stadt und gibt entityId zurück"""
    # Zuerst lokale Datenbank prüfen (für Mock-Fallback)
    local_airport = get_airport_info(query)

    # Versuche echte API
    try:
        url = f"{BASE_URL}/flights/searchAirport"
        params = {"query": query, "locale": "de-DE"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=HEADERS, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") and data.get("data"):
                    return data["data"][0] if data["data"] else None
            elif response.status_code == 429:
                # Rate Limit - nutze lokale Daten
                if local_airport:
                    return {
                        "skyId": local_airport["code"],
                        "entityId": f"mock-{local_airport['code']}",
                        "presentation": {
                            "suggestionTitle": f"{local_airport['name']} ({local_airport['code']})",
                            "subtitle": "Deutschland"
                        },
                        "_isMock": True
                    }
    except Exception as e:
        logger.error("Airport search API error: %s", e)

    # Fallback zu lokalen Daten
    if local_airport:
        return {
            "skyId": local_airport["code"],
            "entityId": f"mock-{local_airport['code']}",
            "presentation": {
                "suggestionTitle": f"{local_airport['name']} ({local_airport['code']})",
                "subtitle": "Deutschland"
            },
            "_isMock": True
        }

    return None


async def search_flights_skyscanner(
    origin: str,
    destination: str,
    date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy"
) -> Dict:
    """
    Sucht Flüge über Skyscanner API mit Mock-Fallback.
    """
    try:
        # Schritt 1: Flughäfen suchen
        origin_data = await search_airport(origin)
        dest_data = await search_airport(destination)

        if not origin_data:
            return {"success": False, "error": f"Flughafen '{origin}' nicht gefunden"}
        if not dest_data:
            return {"success": False, "error": f"Flughafen '{destination}' nicht gefunden"}

        origin_name = origin_data.get("presentation", {}).get("suggestionTitle", origin)
        dest_name = dest_data.get("presentation", {}).get("suggestionTitle", destination)

        # Prüfe ob Mock-Daten verwendet werden sollen
        use_mock = origin_data.get("_isMock") or dest_data.get("_isMock")

        if not use_mock:
            # Versuche echte API
            try:
                origin_id = origin_data.get("entityId") or origin_data.get("skyId")
                dest_id = dest_data.get("entityId") or dest_data.get("skyId")

                url = f"{BASE_URL}/flights/searchFlights"
                params = {
                    "originSkyId": origin_data.get("skyId", origin),
                    "destinationSkyId": dest_data.get("skyId", destination),
                    "originEntityId": origin_id,
                    "destinationEntityId": dest_id,
                    "date": date,
                    "cabinClass": cabin_class,
                    "adults": str(adults),
                    "childrens": str(children),
                    "infants": str(infants),
                    "sortBy": "best",
                    "currency": "EUR",
                    "market": "DE",
                    "countryCode": "DE"
                }

                if return_date:
                    params["returnDate"] = return_date

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=HEADERS, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") and data.get("data"):
                            flights = parse_skyscanner_response(data["data"])
                            return {
                                "success": True,
                                "flights": flights,
                                "origin": origin_name,
                                "destination": dest_name,
                                "source": "skyscanner"
                            }
                    elif response.status_code == 429:
                        use_mock = True  # Rate Limit - nutze Mock

            except Exception as e:
                logger.error("Skyscanner flights API error: %s", e)
                use_mock = True

        # Mock-Daten generieren
        if use_mock:
            origin_info = get_airport_info(origin) or {"code": origin[:3].upper(), "name": origin, "city": origin}
            dest_info = get_airport_info(destination) or {"code": destination[:3].upper(), "name": destination, "city": destination}

            mock_flights = generate_mock_flights(origin_info, dest_info, date, adults)

            return {
                "success": True,
                "flights": mock_flights,
                "origin": origin_name,
                "destination": dest_name,
                "source": "demo"  # Zeigt an, dass es Demo-Daten sind
            }

        return {"success": False, "error": "Keine Flüge gefunden", "flights": []}

    except httpx.TimeoutException:
        return {"success": False, "error": "Zeitüberschreitung bei der Flugsuche"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_skyscanner_response(data: Dict) -> List[Dict]:
    """Parst die Skyscanner Response in ein einheitliches Format"""
    flights = []

    itineraries = data.get("itineraries", [])

    for itinerary in itineraries[:20]:  # Max 20 Ergebnisse
        try:
            price_info = itinerary.get("price", {})
            price = price_info.get("formatted", "N/A")
            price_raw = price_info.get("raw", 0)

            legs = itinerary.get("legs", [])
            if not legs:
                continue

            outbound = legs[0]

            # Segment-Infos
            segments = outbound.get("segments", [])
            first_segment = segments[0] if segments else {}

            # Carrier Info
            carriers = outbound.get("carriers", {})
            marketing = carriers.get("marketing", [{}])
            carrier_info = marketing[0] if marketing else {}

            flight = {
                "id": itinerary.get("id", ""),
                "price": {
                    "total": str(price_raw),
                    "formatted": price,
                    "currency": "EUR"
                },
                "itineraries": [{
                    "duration": outbound.get("durationInMinutes", 0),
                    "segments": [{
                        "departure": {
                            "iataCode": outbound.get("origin", {}).get("displayCode", ""),
                            "at": outbound.get("departure", ""),
                            "airport": outbound.get("origin", {}).get("name", "")
                        },
                        "arrival": {
                            "iataCode": outbound.get("destination", {}).get("displayCode", ""),
                            "at": outbound.get("arrival", ""),
                            "airport": outbound.get("destination", {}).get("name", "")
                        },
                        "carrierCode": carrier_info.get("alternateId", ""),
                        "carrierName": carrier_info.get("name", ""),
                        "carrierLogo": carrier_info.get("logoUrl", ""),
                        "number": first_segment.get("flightNumber", ""),
                    }]
                }],
                "stops": outbound.get("stopCount", 0),
                "duration_formatted": format_duration(outbound.get("durationInMinutes", 0)),
                "deep_link": itinerary.get("deepLink", "")
            }

            flights.append(flight)

        except Exception as e:
            logger.warning("Failed to parse flight itinerary: %s", e)
            continue

    # Nach Preis sortieren
    flights.sort(key=lambda x: float(x["price"]["total"] or 0))

    return flights


def format_duration(minutes: int) -> str:
    """Formatiert Minuten zu 'Xh Ym'"""
    if not minutes:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"
