import httpx
import os
import random
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, List
from datetime import datetime, timedelta

load_dotenv()

logger = logging.getLogger("flyai.hotel")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"
BASE_URL = "https://sky-scrapper.p.rapidapi.com/api/v1"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# Bekannte Städte für Hotel-Suche (Mock-Daten)
CITIES = {
    "berlin": {"entityId": "27539525", "name": "Berlin", "country": "Deutschland"},
    "münchen": {"entityId": "27539526", "name": "München", "country": "Deutschland"},
    "munich": {"entityId": "27539526", "name": "München", "country": "Deutschland"},
    "frankfurt": {"entityId": "27539527", "name": "Frankfurt", "country": "Deutschland"},
    "hamburg": {"entityId": "27539528", "name": "Hamburg", "country": "Deutschland"},
    "köln": {"entityId": "27539529", "name": "Köln", "country": "Deutschland"},
    "düsseldorf": {"entityId": "27539530", "name": "Düsseldorf", "country": "Deutschland"},
    "stuttgart": {"entityId": "27539531", "name": "Stuttgart", "country": "Deutschland"},
    "london": {"entityId": "27544008", "name": "London", "country": "UK"},
    "paris": {"entityId": "27539733", "name": "Paris", "country": "Frankreich"},
    "amsterdam": {"entityId": "27536561", "name": "Amsterdam", "country": "Niederlande"},
    "barcelona": {"entityId": "27548283", "name": "Barcelona", "country": "Spanien"},
    "madrid": {"entityId": "27544850", "name": "Madrid", "country": "Spanien"},
    "rom": {"entityId": "27539793", "name": "Rom", "country": "Italien"},
    "rome": {"entityId": "27539793", "name": "Rom", "country": "Italien"},
    "new york": {"entityId": "27537542", "name": "New York", "country": "USA"},
    "wien": {"entityId": "27538990", "name": "Wien", "country": "Österreich"},
    "vienna": {"entityId": "27538990", "name": "Wien", "country": "Österreich"},
    "zürich": {"entityId": "27545781", "name": "Zürich", "country": "Schweiz"},
    "zurich": {"entityId": "27545781", "name": "Zürich", "country": "Schweiz"},
    "prag": {"entityId": "27546111", "name": "Prag", "country": "Tschechien"},
    "prague": {"entityId": "27546111", "name": "Prag", "country": "Tschechien"},
    "lissabon": {"entityId": "27546341", "name": "Lissabon", "country": "Portugal"},
    "lisbon": {"entityId": "27546341", "name": "Lissabon", "country": "Portugal"},
    "dubai": {"entityId": "27546551", "name": "Dubai", "country": "VAE"},
    "istanbul": {"entityId": "27546721", "name": "Istanbul", "country": "Türkei"},
    "athen": {"entityId": "27546891", "name": "Athen", "country": "Griechenland"},
    "athens": {"entityId": "27546891", "name": "Athen", "country": "Griechenland"},
    "mallorca": {"entityId": "27547061", "name": "Mallorca", "country": "Spanien"},
    "miami": {"entityId": "27547231", "name": "Miami", "country": "USA"},
    "los angeles": {"entityId": "27547401", "name": "Los Angeles", "country": "USA"},
    "tokyo": {"entityId": "27547571", "name": "Tokyo", "country": "Japan"},
    "bangkok": {"entityId": "27547741", "name": "Bangkok", "country": "Thailand"},
    "singapur": {"entityId": "27547911", "name": "Singapur", "country": "Singapur"},
    "singapore": {"entityId": "27547911", "name": "Singapur", "country": "Singapur"},
}

# Hotel-Ketten für Mock-Daten mit echten Bildern
HOTEL_CHAINS = [
    {
        "name": "Marriott",
        "stars": 4,
        "images": [
            "https://cache.marriott.com/content/dam/marriott-renditions/BERDT/berdt-exterior-6702-hor-clsc.jpg",
            "https://cache.marriott.com/content/dam/marriott-renditions/MUNCH/munch-exterior-0001-hor-clsc.jpg",
        ]
    },
    {
        "name": "Hilton",
        "stars": 5,
        "images": [
            "https://www.hilton.com/im/en/BERHITW/16756676/hilton-berlin-exterior-night.jpg",
            "https://www.hilton.com/im/en/FRAECHT/3403252/fra-exterior.jpg",
        ]
    },
    {
        "name": "Holiday Inn",
        "stars": 3,
        "images": [
            "https://digital.ihg.com/is/image/ihg/holiday-inn-berlin-4831668498-2x1",
            "https://digital.ihg.com/is/image/ihg/holiday-inn-munich-4598053839-2x1",
        ]
    },
    {
        "name": "Ibis",
        "stars": 2,
        "images": [
            "https://www.ahstatic.com/photos/5513_ho_00_p_1024x768.jpg",
            "https://www.ahstatic.com/photos/1454_ho_00_p_1024x768.jpg",
        ]
    },
    {
        "name": "Radisson Blu",
        "stars": 4,
        "images": [
            "https://www.radissonhotels.com/en-us/destination/germany/berlin-hotels",
            "https://media.radissonhotels.net/image/radisson-blu-hotel-berlin/exteriorview/16256-113266-f63591840_3xl.jpg",
        ]
    },
    {
        "name": "InterContinental",
        "stars": 5,
        "images": [
            "https://digital.ihg.com/is/image/ihg/intercontinental-berlin-2531687447-2x1",
            "https://digital.ihg.com/is/image/ihg/intercontinental-frankfurt-5481093261-2x1",
        ]
    },
    {
        "name": "Novotel",
        "stars": 3,
        "images": [
            "https://www.ahstatic.com/photos/5343_ho_00_p_1024x768.jpg",
            "https://www.ahstatic.com/photos/2866_ho_00_p_1024x768.jpg",
        ]
    },
    {
        "name": "Hyatt",
        "stars": 5,
        "images": [
            "https://assets.hyatt.com/content/dam/hyatt/hyattdam/images/2017/08/29/1013/Grand-Hyatt-Berlin-P671-Exterior-Night.jpg",
            "https://assets.hyatt.com/content/dam/hyatt/hyattdam/images/2019/01/04/1227/Park-Hyatt-Vienna-P081-Exterior.jpg",
        ]
    },
    {
        "name": "Best Western",
        "stars": 3,
        "images": [
            "https://www.bestwestern.de/images/hotels/89149/89149_hotelbild_09.jpg",
            "https://www.bestwestern.de/images/hotels/89010/89010_hotelbild_01.jpg",
        ]
    },
    {
        "name": "NH Hotels",
        "stars": 4,
        "images": [
            "https://www.nh-hotels.com/corporate/sites/default/files/destination_images/berlin.jpg",
            "https://www.nh-hotels.com/corporate/sites/default/files/images/nh-collection-berlin-mitte-am-checkpoint-charlie-exterior.jpg",
        ]
    },
    {
        "name": "Moxy",
        "stars": 3,
        "images": [
            "https://cache.marriott.com/content/dam/marriott-renditions/BEROX/berox-exterior-5720-hor-clsc.jpg",
            "https://cache.marriott.com/content/dam/marriott-renditions/FRAOX/fraox-exterior-0079-hor-clsc.jpg",
        ]
    },
    {
        "name": "Mercure",
        "stars": 3,
        "images": [
            "https://www.ahstatic.com/photos/1765_ho_00_p_1024x768.jpg",
            "https://www.ahstatic.com/photos/5765_ho_00_p_1024x768.jpg",
        ]
    },
    {
        "name": "Sheraton",
        "stars": 4,
        "images": [
            "https://cache.marriott.com/content/dam/marriott-renditions/BERSI/bersi-exterior-0023-hor-clsc.jpg",
            "https://cache.marriott.com/content/dam/marriott-renditions/FRASI/frasi-exterior-0049-hor-clsc.jpg",
        ]
    },
    {
        "name": "Westin",
        "stars": 5,
        "images": [
            "https://cache.marriott.com/content/dam/marriott-renditions/BERWI/berwi-exterior-0130-hor-clsc.jpg",
            "https://cache.marriott.com/content/dam/marriott-renditions/FRAWI/frawi-exterior-9571-hor-clsc.jpg",
        ]
    },
    {
        "name": "Crowne Plaza",
        "stars": 4,
        "images": [
            "https://digital.ihg.com/is/image/ihg/crowne-plaza-berlin-4902049807-2x1",
            "https://digital.ihg.com/is/image/ihg/crowne-plaza-frankfurt-5099113139-2x1",
        ]
    },
]

# Fallback Bilder nach Sternekategorie (echte Hotel-Bilder von Unsplash)
FALLBACK_HOTEL_IMAGES = {
    2: [
        "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80",  # Budget Hotel
        "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&q=80",
    ],
    3: [
        "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800&q=80",  # Mid-range Hotel
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80",
        "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800&q=80",
    ],
    4: [
        "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&q=80",  # Upscale Hotel
        "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800&q=80",
        "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=800&q=80",
    ],
    5: [
        "https://images.unsplash.com/photo-1615460549969-36fa19521a4f?w=800&q=80",  # Luxury Hotel
        "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&q=80",
        "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800&q=80",
    ],
}

HOTEL_AMENITIES = [
    "WLAN kostenlos", "Frühstück inklusive", "Fitnesscenter", "Pool",
    "Spa", "Restaurant", "Bar", "Parkplatz", "Klimaanlage",
    "24h Rezeption", "Roomservice", "Wäscheservice"
]


def get_city_info(city: str) -> Optional[Dict]:
    """Findet Stadt-Info für Hotel-Suche"""
    city_lower = city.lower().strip()
    return CITIES.get(city_lower)


def generate_mock_hotels(destination: str, checkin: str, checkout: str, guests: int = 2) -> List[Dict]:
    """Generiert realistische Mock-Hotel-Daten"""
    city_info = get_city_info(destination) or {"name": destination.title(), "country": ""}

    # Berechne Anzahl Nächte
    try:
        checkin_date = datetime.strptime(checkin, "%Y-%m-%d")
        checkout_date = datetime.strptime(checkout, "%Y-%m-%d")
        nights = (checkout_date - checkin_date).days
    except:
        nights = 1

    hotels = []
    num_hotels = random.randint(10, 15)

    for i in range(num_hotels):
        chain = random.choice(HOTEL_CHAINS)
        base_price = {
            2: random.randint(40, 80),
            3: random.randint(70, 120),
            4: random.randint(110, 180),
            5: random.randint(160, 350)
        }.get(chain["stars"], 100)

        # Preis-Variation
        price_per_night = base_price + random.randint(-20, 40)
        total_price = price_per_night * nights

        # Bewertung basierend auf Sternen
        min_rating = {2: 6.5, 3: 7.0, 4: 7.8, 5: 8.5}.get(chain["stars"], 7.0)
        rating = round(min_rating + random.uniform(0, 1.2), 1)
        rating = min(rating, 10.0)

        # Anzahl Bewertungen
        reviews_count = random.randint(50, 2500)

        # Zufällige Amenities
        num_amenities = random.randint(4, 8)
        amenities = random.sample(HOTEL_AMENITIES, num_amenities)

        # Distanz zum Zentrum
        distance = round(random.uniform(0.3, 8.0), 1)

        # Wähle ein passendes Bild
        if chain.get("images"):
            # Verwende ein Bild von der Hotelkette
            image_url = random.choice(chain["images"])
        else:
            # Fallback nach Sternekategorie
            fallback_images = FALLBACK_HOTEL_IMAGES.get(chain["stars"], FALLBACK_HOTEL_IMAGES[3])
            image_url = random.choice(fallback_images)

        hotel = {
            "id": f"hotel_{i}_{random.randint(1000, 9999)}",
            "name": f"{chain['name']} {city_info['name']} {random.choice(['City', 'Central', 'Airport', 'Downtown', 'Plaza', 'Grand', 'Royal'])}",
            "stars": chain["stars"],
            "rating": rating,
            "reviewsCount": reviews_count,
            "pricePerNight": price_per_night,
            "totalPrice": total_price,
            "currency": "EUR",
            "nights": nights,
            "address": f"{random.choice(['Hauptstraße', 'Königsallee', 'Bahnhofstraße', 'Marktplatz', 'Ringstraße'])} {random.randint(1, 150)}, {city_info['name']}",
            "distance": f"{distance} km vom Zentrum",
            "amenities": amenities,
            "image": image_url,
            "freeCancel": random.choice([True, True, False]),
            "breakfastIncluded": "Frühstück inklusive" in amenities,
        }
        hotels.append(hotel)

    # Sortiere nach Preis
    hotels.sort(key=lambda x: x["totalPrice"])

    return hotels


async def search_destination(query: str) -> Dict:
    """Sucht nach Reisezielen für Hotels"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/hotels/searchDestinationOrHotel",
                headers=HEADERS,
                params={"query": query}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") and data.get("data"):
                    return {"success": True, "destinations": data["data"]}

            # Fallback auf Mock-Daten
            city_info = get_city_info(query)
            if city_info:
                return {
                    "success": True,
                    "destinations": [{
                        "entityId": city_info["entityId"],
                        "name": city_info["name"],
                        "country": city_info["country"],
                        "type": "CITY"
                    }],
                    "source": "mock"
                }

            return {"success": False, "error": "Keine Ergebnisse gefunden"}

        except Exception as e:
            # Fallback auf Mock
            city_info = get_city_info(query)
            if city_info:
                return {
                    "success": True,
                    "destinations": [{
                        "entityId": city_info["entityId"],
                        "name": city_info["name"],
                        "country": city_info["country"],
                        "type": "CITY"
                    }],
                    "source": "mock"
                }
            return {"success": False, "error": str(e)}


async def search_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    children: int = 0
) -> Dict:
    """Sucht Hotels über Sky-Scrapper API"""

    # Erst Destination suchen
    dest_result = await search_destination(destination)

    entity_id = None
    if dest_result.get("success") and dest_result.get("destinations"):
        # Nimm die erste Stadt
        for dest in dest_result["destinations"]:
            if dest.get("type") in ["CITY", "PLACE", "HOTEL"]:
                entity_id = dest.get("entityId")
                break

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if entity_id:
                response = await client.get(
                    f"{BASE_URL}/hotels/searchHotels",
                    headers=HEADERS,
                    params={
                        "entityId": entity_id,
                        "checkin": checkin,
                        "checkout": checkout,
                        "adults": adults,
                        "rooms": rooms,
                        "limit": 20,
                        "sorting": "-relevance",
                        "currency": "EUR",
                        "market": "de-DE",
                        "countryCode": "DE"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") and data.get("data", {}).get("hotels"):
                        # Transformiere API-Daten in unser Format
                        hotels = transform_api_hotels(data["data"]["hotels"], checkin, checkout)
                        return {
                            "success": True,
                            "hotels": hotels,
                            "destination": destination,
                            "checkin": checkin,
                            "checkout": checkout,
                            "source": "api"
                        }

                # Bei Rate Limit oder Fehler -> Mock-Daten
                if response.status_code == 429:
                    logger.warning("Hotel API rate limit - falling back to mock data")

            # Fallback auf Mock-Daten
            hotels = generate_mock_hotels(destination, checkin, checkout, adults)
            return {
                "success": True,
                "hotels": hotels,
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout,
                "source": "mock"
            }

        except Exception as e:
            logger.error("Hotel API error: %s", e)
            # Fallback auf Mock
            hotels = generate_mock_hotels(destination, checkin, checkout, adults)
            return {
                "success": True,
                "hotels": hotels,
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout,
                "source": "mock",
                "error": str(e)
            }


def transform_api_hotels(api_hotels: List, checkin: str, checkout: str) -> List[Dict]:
    """Transformiert API-Hotels in unser Format"""
    try:
        checkin_date = datetime.strptime(checkin, "%Y-%m-%d")
        checkout_date = datetime.strptime(checkout, "%Y-%m-%d")
        nights = (checkout_date - checkin_date).days
    except:
        nights = 1

    hotels = []
    for hotel in api_hotels[:20]:  # Max 20 Hotels
        try:
            price_info = hotel.get("price", {})
            total_price = price_info.get("amount", 0)
            price_per_night = round(total_price / nights) if nights > 0 else total_price
            stars = hotel.get("stars", 3)

            # Bild-URL mit Fallback
            image_url = hotel.get("heroImage") or hotel.get("image") or hotel.get("imageUrl")

            # Wenn kein Bild vorhanden, nutze Fallback nach Sternen
            if not image_url or image_url == "":
                fallback_images = FALLBACK_HOTEL_IMAGES.get(stars, FALLBACK_HOTEL_IMAGES[3])
                image_url = random.choice(fallback_images)

            transformed = {
                "id": hotel.get("hotelId", ""),
                "name": hotel.get("name", "Hotel"),
                "stars": stars,
                "rating": hotel.get("reviewScore", 0),
                "reviewsCount": hotel.get("reviewCount", 0),
                "pricePerNight": price_per_night,
                "totalPrice": total_price,
                "currency": price_info.get("currency", "EUR"),
                "nights": nights,
                "address": hotel.get("address", ""),
                "distance": hotel.get("distance", ""),
                "amenities": hotel.get("amenities", [])[:6],
                "image": image_url,
                "freeCancel": hotel.get("freeCancellation", False),
                "breakfastIncluded": hotel.get("breakfastIncluded", False),
            }
            hotels.append(transformed)
        except Exception as e:
            continue

    return hotels
