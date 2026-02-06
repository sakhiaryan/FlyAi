from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlmodel import SQLModel, create_engine, Session
from pydantic import BaseModel
from typing import List, Optional
import json
import re
import asyncio
import uuid

# .env laden
load_dotenv()

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)

# Datenbank Setup
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Services importieren
from services.airport_service import search_airports
from services.openai_service import ask_chatgpt, ask_chatgpt_with_history
from services.auswaertiges_amt_service import fetch_travel_info, format_aa_info_for_chat, get_country_slug, get_aa_direct_link, format_aa_link_for_chat
from services.skyscanner_service import search_flights_skyscanner
from services.hotel_service import search_hotels, search_destination
from services.visa_service import get_visa_info, format_visa_warning_for_chat, get_critical_countries
from services.cart_service import add_to_cart, get_cart, get_cart_summary, remove_from_cart, clear_cart, format_cart_for_chat

# Models importieren
from models.search_history import SearchHistory
from models.chat_cache import ChatCache
from models.cart import CartItem

app = FastAPI(title="FlyAI", description="KI-gestützte Flugsuche", version="1.0.0")

# Rate Limiter zur App hinzufügen
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS erlauben
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models für Request Body
class ChatMessage(BaseModel):
    role: str  # "user" oder "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    question: str
    session_id: Optional[str] = None
    passport_country: Optional[str] = "deutschland"

class CartAddRequest(BaseModel):
    session_id: str
    item_type: str  # "flight", "hotel", "activity"
    item_data: dict
    price: float
    currency: str = "EUR"

class CartRemoveRequest(BaseModel):
    session_id: str
    item_id: int

# ==================== AUTH MODELS ====================
class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    token: str
    created_at: str

# Fake User Database (In-Memory)
fake_users_db = {
    "demo@flyai.de": {
        "id": 1,
        "name": "Demo User",
        "email": "demo@flyai.de",
        "password": "demo1234",  # In real app: hashed!
        "created_at": "2025-01-01T00:00:00"
    },
    "test@example.com": {
        "id": 2,
        "name": "Test User",
        "email": "test@example.com",
        "password": "test1234",
        "created_at": "2025-01-15T00:00:00"
    }
}

def generate_token():
    """Generiert einen Fake JWT Token"""
    import secrets
    return f"flyai_{secrets.token_hex(32)}"

# ==================== AUTH ENDPOINTS ====================
@app.post("/auth/login")
def login(request: LoginRequest):
    """Fake Login - prüft User in Memory-DB"""
    email = request.email.lower()

    if email not in fake_users_db:
        return {"success": False, "error": "Benutzer nicht gefunden", "error_code": "USER_NOT_FOUND"}

    user = fake_users_db[email]

    if user["password"] != request.password:
        return {"success": False, "error": "Falsches Passwort", "error_code": "INVALID_PASSWORD"}

    token = generate_token()

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"]
        },
        "token": token,
        "message": f"Willkommen zurück, {user['name']}!"
    }

@app.post("/auth/register")
def register(request: RegisterRequest):
    """Fake Registrierung - fügt User zur Memory-DB hinzu"""
    email = request.email.lower()

    # Validierung
    if not request.name or len(request.name) < 2:
        return {"success": False, "error": "Name muss mindestens 2 Zeichen haben", "error_code": "INVALID_NAME"}

    if "@" not in email or "." not in email:
        return {"success": False, "error": "Ungültige E-Mail Adresse", "error_code": "INVALID_EMAIL"}

    if len(request.password) < 8:
        return {"success": False, "error": "Passwort muss mindestens 8 Zeichen haben", "error_code": "PASSWORD_TOO_SHORT"}

    if email in fake_users_db:
        return {"success": False, "error": "E-Mail bereits registriert", "error_code": "EMAIL_EXISTS"}

    # Neuen User erstellen
    new_id = len(fake_users_db) + 1
    from datetime import datetime

    fake_users_db[email] = {
        "id": new_id,
        "name": request.name,
        "email": email,
        "password": request.password,  # In real app: hash this!
        "created_at": datetime.now().isoformat()
    }

    token = generate_token()

    return {
        "success": True,
        "user": {
            "id": new_id,
            "name": request.name,
            "email": email,
            "created_at": fake_users_db[email]["created_at"]
        },
        "token": token,
        "message": f"Willkommen bei FlyAI, {request.name}!"
    }

@app.get("/auth/me")
def get_current_user(token: str = None):
    """Gibt User-Info zurück wenn Token gültig"""
    if not token or not token.startswith("flyai_"):
        return {"success": False, "error": "Nicht authentifiziert", "error_code": "NOT_AUTHENTICATED"}

    # In real app: Token validieren und User aus DB holen
    # Hier geben wir einfach Demo-User zurück
    return {
        "success": True,
        "user": {
            "id": 1,
            "name": "Demo User",
            "email": "demo@flyai.de"
        }
    }

@app.post("/auth/logout")
def logout():
    """Fake Logout"""
    return {"success": True, "message": "Erfolgreich abgemeldet"}

@app.get("/auth/check-email")
def check_email(email: str):
    """Prüft ob E-Mail bereits registriert ist"""
    return {
        "exists": email.lower() in fake_users_db,
        "email": email
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/airports")
@limiter.limit("30/minute")
def get_airports(request: Request, q: str):
    """Sucht Flughäfen - für Autocomplete"""
    results = search_airports(q)
    return {"airports": results}

@app.get("/search_flights")
@limiter.limit("10/minute")
async def search_flights(
    request: Request,
    from_airport: str,
    to_airport: str,
    date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0
):
    """Sucht Flüge über Skyscanner API"""

    with Session(engine) as session:
        history = SearchHistory(from_airport=from_airport, to_airport=to_airport, date=date)
        session.add(history)
        session.commit()

    # Skyscanner Flugsuche
    result = await search_flights_skyscanner(
        origin=from_airport,
        destination=to_airport,
        date=date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants=infants
    )

    return result

@app.get("/search_history")
@limiter.limit("20/minute")
def get_search_history(request: Request):
    """Zeigt die letzten 20 Suchen"""
    with Session(engine) as session:
        history = session.query(SearchHistory).order_by(SearchHistory.timestamp.desc()).limit(20).all()
        return {"history": history}

@app.post("/chat")
@limiter.limit("20/minute")
async def chat_with_history(request: Request, chat_request: ChatRequest):
    """Chat MIT Konversations-History - der Bot merkt sich alles!"""

    # Konvertiere zu OpenAI Format
    messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]

    # Aktuelle Frage hinzufügen
    messages.append({"role": "user", "content": chat_request.question})

    question_lower = chat_request.question.lower()
    session_id = chat_request.session_id or str(uuid.uuid4())

    # ==================== WARENKORB ABFRAGE ====================
    cart_keywords = ["warenkorb", "cart", "einkaufswagen", "was habe ich", "meine buchungen", "übersicht"]
    is_cart_query = any(kw in question_lower for kw in cart_keywords)

    if is_cart_query:
        cart_text = format_cart_for_chat(engine, session_id)
        return {"type": "cart", "answer": cart_text, "session_id": session_id}

    # ==================== FLUGSUCHE ====================
    flight_keywords = ["flug", "fliegen", "flüge", "flight", "buchen", "ticket"]
    is_flight_query = any(kw in question_lower for kw in flight_keywords)

    # Prüfe auf Ziel-Anfragen wie "ich will nach X"
    destination_pattern = r"(?:nach|to|towards)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s+fliegen|\s+reisen|$)"
    destination_match = re.search(destination_pattern, question_lower)

    # Extrahiere Zielland für Visa-Check
    target_country = None
    if destination_match:
        target_country = destination_match.group(1).strip()

    if is_flight_query or destination_match:
        # Extrahiere Flugdaten mit KI
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{chat_request.question}"

Antworte NUR mit JSON (keine anderen Texte):
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "to_country": "Land des Ziels", "date": "YYYY-MM-DD oder null"}}

Wenn keine klare Flugsuche, antworte:
{{"action": "chat"}}"""

        extract_response = ask_chatgpt(extract_prompt)

        try:
            json_match = re.search(r'\{.*\}', extract_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                if data.get("action") == "search_flight" and data.get("to"):
                    # Visa-Check für Zielland
                    visa_warning = ""
                    to_country = data.get("to_country") or target_country
                    aa_url = None

                    if to_country:
                        visa_info = get_visa_info(to_country)
                        if visa_info["visa_required"] or visa_info["has_warning"]:
                            visa_warning = format_visa_warning_for_chat(to_country)

                        # AA-Link IMMER hinzufügen!
                        aa_link = get_aa_direct_link(to_country)
                        if aa_link["success"]:
                            aa_url = aa_link["url"]

                    response_msg = f"Super! Ich suche Flüge nach {data.get('to')} für dich..."
                    if visa_warning:
                        response_msg += f"\n\n{visa_warning}"

                    # AA-Link zur Nachricht hinzufügen
                    if aa_url:
                        response_msg += f"\n\n🔗 **Offizielle Reisehinweise:** {aa_url}"

                    return {
                        "type": "flight_search",
                        "from": data.get("from"),
                        "to": data.get("to"),
                        "to_country": to_country,
                        "date": data.get("date"),
                        "message": response_msg,
                        "visa_info": get_visa_info(to_country) if to_country else None,
                        "aa_url": aa_url,
                        "session_id": session_id
                    }
        except:
            pass

    # ==================== HOTEL SUCHE ====================
    hotel_keywords = ["hotel", "unterkunft", "übernachtung", "zimmer", "übernachten"]
    is_hotel_query = any(kw in question_lower for kw in hotel_keywords)

    if is_hotel_query:
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Hoteldaten.
Anfrage: "{chat_request.question}"

Antworte NUR mit JSON:
{{"action": "search_hotel", "destination": "Stadt oder Region", "country": "Land", "checkin": "YYYY-MM-DD oder null", "checkout": "YYYY-MM-DD oder null"}}

Wenn keine Hotelsuche:
{{"action": "chat"}}"""

        extract_response = ask_chatgpt(extract_prompt)

        try:
            json_match = re.search(r'\{.*\}', extract_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                if data.get("action") == "search_hotel" and data.get("destination"):
                    # Visa-Check
                    visa_warning = ""
                    country = data.get("country")
                    aa_url = None

                    if country:
                        visa_info = get_visa_info(country)
                        if visa_info["visa_required"] or visa_info["has_warning"]:
                            visa_warning = format_visa_warning_for_chat(country)

                        # AA-Link IMMER hinzufügen!
                        aa_link = get_aa_direct_link(country)
                        if aa_link["success"]:
                            aa_url = aa_link["url"]

                    response_msg = f"Ich suche Hotels in {data.get('destination')} für dich..."
                    if visa_warning:
                        response_msg += f"\n\n{visa_warning}"

                    # AA-Link zur Nachricht hinzufügen
                    if aa_url:
                        response_msg += f"\n\n🔗 **Offizielle Reisehinweise:** {aa_url}"

                    return {
                        "type": "hotel_search",
                        "destination": data.get("destination"),
                        "country": country,
                        "checkin": data.get("checkin"),
                        "checkout": data.get("checkout"),
                        "message": response_msg,
                        "visa_info": get_visa_info(country) if country else None,
                        "aa_url": aa_url,
                        "session_id": session_id
                    }
        except:
            pass

    # ==================== VISA/REISE FRAGEN (TOKEN-OPTIMIERT) ====================
    travel_keywords = ["visum", "visa", "einreise", "reisewarnung", "sicherheit", "gefährlich",
                       "reisehinweis", "brauche ich", "reisepass", "impfung", "corona", "covid", "pass",
                       "auswärtiges amt", "reiseinfo", "reisen", "kann ich nach", "darf ich nach"]
    is_travel_query = any(kw in question_lower for kw in travel_keywords)

    # Extrahiere Land aus der Frage (verbesserte Patterns - Reihenfolge wichtig!)
    country_patterns = [
        r"(?:visum|visa)\s+(?:für|nach)\s+([A-Za-zäöüÄÖÜß]+)",  # "Visum für Thailand"
        r"(?:kann ich nach|darf ich nach)\s+([A-Za-zäöüÄÖÜß]+)",  # "Kann ich nach Syrien"
        r"(?:reise nach|fliegen nach|trip nach)\s+([A-Za-zäöüÄÖÜß]+)",  # "Reise nach Japan"
        r"nach\s+([A-Za-zäöüÄÖÜß]+)\s+(?:reisen|fliegen)",  # "nach Thailand reisen"
        r"für\s+([A-Za-zäöüÄÖÜß]+)\s+(?:visum|visa|einreise)",  # "für China Visum"
        r"in\s+([A-Za-zäöüÄÖÜß]+)\s+(?:reisen|fliegen|einreise)",  # "in Japan reisen"
        r"([A-Za-zäöüÄÖÜß]+)\s+(?:visum|visa|einreise|reisewarnung)",  # "Thailand Visum"
        r"(?:ist|wie ist)\s+([A-Za-zäöüÄÖÜß]+)\s+(?:sicher|gefährlich)",  # "Ist Syrien sicher?"
        r"nach\s+([A-Za-zäöüÄÖÜß]+)",  # Fallback: "nach X" allgemein
    ]
    country_match = None
    for pattern in country_patterns:
        match = re.search(pattern, question_lower)
        if match:
            extracted = match.group(1).strip()
            # Prüfe ob es ein bekanntes Land ist
            if get_country_slug(extracted) or get_visa_info(extracted)["visa_required"] is not None:
                country_match = match
                break

    # SCHNELLE DIREKT-ANTWORT für Reisefragen (spart Tokens!)
    if is_travel_query and country_match:
        country = country_match.group(1).strip()

        # Visa-Info (schnell, lokal)
        visa_info = get_visa_info(country)

        # AA-Link (schnell, kein Scraping!)
        aa_link = get_aa_direct_link(country)

        # Baue kurze, direkte Antwort
        response_parts = []

        # Reisewarnung zuerst (wichtig!)
        if visa_info.get("has_warning"):
            response_parts.append(f"⚠️ **{visa_info['warning_text']}**")

        # Visa-Info kurz
        if visa_info["visa_required"] is True:
            response_parts.append(f"📋 **Visum erforderlich** für {country.title()}")
            response_parts.append(f"   Typ: {visa_info['visa_type']}")
            if visa_info.get("notes"):
                response_parts.append(f"   {visa_info['notes'][:150]}")
        elif visa_info["visa_required"] is False:
            if "ESTA" in str(visa_info.get("visa_type", "")):
                response_parts.append(f"📋 **ESTA erforderlich** für {country.title()} (kein Visum)")
            else:
                response_parts.append(f"✅ **Visumfrei** für {country.title()} (deutsche Staatsbürger)")

        # AA-Link (das Wichtigste!)
        if aa_link["success"]:
            response_parts.append(f"\n🔗 **Offizielle Infos vom Auswärtigen Amt:**")
            response_parts.append(aa_link["url"])

        # Direkte Antwort ohne KI-Call (spart viele Tokens!)
        direct_answer = "\n".join(response_parts)

        return {
            "type": "travel_info",
            "answer": direct_answer,
            "country": country.title(),
            "visa_info": visa_info,
            "aa_url": aa_link.get("url"),
            "session_id": session_id
        }

    # ==================== PASS-FRAGE ====================
    pass_keywords = ["welchen pass", "was für ein pass", "reisepass", "personalausweis", "passport"]
    is_pass_query = any(kw in question_lower for kw in pass_keywords)

    if is_pass_query and not country_match:
        # Frage nach Pass-Typ wenn Zielland unklar
        return {
            "type": "ask_passport",
            "message": "Welchen Reisepass hast du? (z.B. deutscher Pass, österreichischer Pass) Und wohin möchtest du reisen?",
            "session_id": session_id
        }

    # ==================== REISEPLANUNG ====================
    planning_keywords = ["reise planen", "trip planen", "urlaub planen", "reiseplan", "komplette reise",
                         "was kann ich unternehmen", "was gibt es zu sehen", "sehenswürdigkeiten",
                         "aktivitäten", "tipps für", "empfehlungen für", "beste zeit", "wann sollte ich",
                         "wie lange", "budget", "kosten", "günstiger", "teuer", "beste reisezeit"]
    is_planning_query = any(kw in question_lower for kw in planning_keywords)

    # Budget-Anfragen erkennen
    budget_keywords = ["budget", "kosten", "preis", "wie viel", "wieviel", "günstig", "billig", "teuer"]
    is_budget_query = any(kw in question_lower for kw in budget_keywords)

    # Timing-Anfragen erkennen
    timing_keywords = ["beste zeit", "wann", "saison", "jahreszeit", "regenzeit", "trockenzeit", "monsun"]
    is_timing_query = any(kw in question_lower for kw in timing_keywords)

    if (is_planning_query or is_budget_query or is_timing_query) and country_match:
        country = country_match.group(1).strip()

        # Erstelle spezialisierten Prompt für Reiseplanung
        planning_prompt = f"""Du bist ein erfahrener Reiseberater. Gib eine hilfreiche, prägnante Antwort auf diese Frage.

Frage: "{chat_request.question}"
Land: {country}

Antworte kurz und hilfreich (max. 200 Wörter). Verwende Emoji für bessere Lesbarkeit.
Fokus:
- Wenn nach BUDGET/KOSTEN gefragt: Gib realistische Preise für Flüge, Hotels, Essen
- Wenn nach BESTE ZEIT gefragt: Nenne optimale Monate und warum
- Wenn nach AKTIVITÄTEN gefragt: Liste Top 3-5 Highlights
- Wenn nach TIPPS gefragt: Gib praktische lokale Tipps

Schließe mit: "Soll ich Flüge nach {country} suchen? 🛫" """

        planning_answer = ask_chatgpt(planning_prompt)

        # AA-Link hinzufügen
        aa_link = get_aa_direct_link(country)
        aa_url = aa_link.get("url") if aa_link["success"] else None

        if aa_url:
            planning_answer += f"\n\n🔗 **Offizielle Reisehinweise:** {aa_url}"

        return {
            "type": "travel_planning",
            "answer": planning_answer,
            "country": country.title(),
            "visa_info": get_visa_info(country),
            "aa_url": aa_url,
            "session_id": session_id
        }

    # ==================== WETTER-ANFRAGEN ====================
    weather_keywords = ["wetter", "temperatur", "klima", "regen", "sonnig", "warm", "kalt"]
    is_weather_query = any(kw in question_lower for kw in weather_keywords)

    if is_weather_query and country_match:
        country = country_match.group(1).strip()

        weather_prompt = f"""Beschreibe das typische Klima und Wetter in {country} kurz (max. 100 Wörter).
Nenne:
- Beste Reisezeit (Monate)
- Typische Temperaturen
- Regenzeit/Trockenzeit wenn relevant

Verwende Wetter-Emojis für bessere Lesbarkeit."""

        weather_answer = ask_chatgpt(weather_prompt)

        return {
            "type": "weather_info",
            "answer": weather_answer,
            "country": country.title(),
            "session_id": session_id
        }

    # ==================== NORMALE CHAT-ANTWORT MIT HISTORY ====================
    answer = ask_chatgpt_with_history(messages)

    # Prüfe ob ein Land in der Frage erwähnt wird - dann AA-Link hinzufügen!
    detected_country = None
    aa_url = None

    # Versuche Land aus der Frage zu extrahieren (auch ohne Travel-Keywords)
    for pattern in country_patterns:
        match = re.search(pattern, question_lower)
        if match:
            extracted = match.group(1).strip()
            if get_country_slug(extracted):
                detected_country = extracted
                break

    # Auch in der Antwort nach Ländern suchen (für Kontext)
    if not detected_country:
        # Bekannte Länder direkt suchen
        common_countries = ["usa", "china", "japan", "thailand", "türkei", "spanien", "italien",
                          "frankreich", "griechenland", "ägypten", "australien", "brasilien",
                          "mexiko", "indien", "vietnam", "indonesien", "marokko", "russland",
                          "syrien", "afghanistan", "iran", "ukraine", "israel"]
        for country in common_countries:
            if country in question_lower:
                detected_country = country
                break

    # Wenn Land erkannt wurde: AA-Link hinzufügen!
    if detected_country:
        aa_link = get_aa_direct_link(detected_country)
        if aa_link["success"]:
            aa_url = aa_link["url"]
            # Link zur Antwort hinzufügen
            answer += f"\n\n🔗 **Offizielle Reise- und Sicherheitshinweise:**\n{aa_url}"

    return {
        "type": "chat",
        "answer": answer,
        "session_id": session_id,
        "detected_country": detected_country,
        "aa_url": aa_url
    }

@app.get("/smart_ask")
@limiter.limit("10/minute")
def smart_ask(request: Request, question: str):
    """Einfacher Chat ohne History (Legacy-Endpoint)"""

    flight_keywords = ["flug", "fliegen", "flüge", "flight", "nach", "von", "reise", "buchen"]
    is_flight_query = any(kw in question.lower() for kw in flight_keywords)

    if is_flight_query:
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{question}"

Antworte NUR mit JSON:
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "date": "YYYY-MM-DD oder null"}}

Wenn keine Flugsuche:
{{"action": "chat"}}"""

        response = ask_chatgpt(extract_prompt)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                if data.get("action") == "search_flight" and data.get("to"):
                    return {
                        "type": "flight_search",
                        "from": data.get("from"),
                        "to": data.get("to"),
                        "date": data.get("date"),
                        "message": f"Ich suche Flüge von {data.get('from')} nach {data.get('to')}..."
                    }
        except:
            pass

    answer = ask_chatgpt(question)
    return {"type": "chat", "answer": answer}

# ==================== HOTEL ENDPOINTS ====================

@app.get("/search_hotels")
@limiter.limit("10/minute")
async def search_hotels_endpoint(
    request: Request,
    destination: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    children: int = 0
):
    """Sucht Hotels über Sky-Scrapper API"""
    result = await search_hotels(
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        rooms=rooms,
        children=children
    )
    return result


@app.get("/search_destination")
@limiter.limit("30/minute")
async def search_destination_endpoint(request: Request, q: str):
    """Sucht Reiseziele für Hotel-Autocomplete"""
    result = await search_destination(q)
    return result


# ==================== WARENKORB ENDPOINTS ====================

@app.post("/cart/add")
@limiter.limit("30/minute")
def add_cart_item(request: Request, cart_request: CartAddRequest):
    """Fügt Item zum Warenkorb hinzu"""
    item = add_to_cart(
        engine=engine,
        session_id=cart_request.session_id,
        item_type=cart_request.item_type,
        item_data=cart_request.item_data,
        price=cart_request.price,
        currency=cart_request.currency
    )
    return {
        "success": True,
        "message": f"{cart_request.item_type.title()} zum Warenkorb hinzugefügt!",
        "item_id": item.id,
        "cart": get_cart_summary(engine, cart_request.session_id)
    }


@app.get("/cart/{session_id}")
@limiter.limit("30/minute")
def get_cart_items(request: Request, session_id: str):
    """Holt alle Items aus dem Warenkorb"""
    return get_cart_summary(engine, session_id)


@app.delete("/cart/remove")
@limiter.limit("30/minute")
def remove_cart_item(request: Request, cart_request: CartRemoveRequest):
    """Entfernt Item aus dem Warenkorb"""
    success = remove_from_cart(engine, cart_request.session_id, cart_request.item_id)
    if success:
        return {
            "success": True,
            "message": "Item entfernt",
            "cart": get_cart_summary(engine, cart_request.session_id)
        }
    return {"success": False, "message": "Item nicht gefunden"}


@app.delete("/cart/clear/{session_id}")
@limiter.limit("10/minute")
def clear_cart_items(request: Request, session_id: str):
    """Leert den gesamten Warenkorb"""
    count = clear_cart(engine, session_id)
    return {
        "success": True,
        "message": f"{count} Items entfernt",
        "cart": get_cart_summary(engine, session_id)
    }


# ==================== VISA ENDPOINTS ====================

@app.get("/visa/{country}")
@limiter.limit("30/minute")
def get_visa_information(request: Request, country: str):
    """Gibt Visa-Informationen für ein Land zurück"""
    info = get_visa_info(country)
    return {
        "success": True,
        "visa_info": info,
        "formatted": format_visa_warning_for_chat(country)
    }


@app.get("/visa/critical/list")
@limiter.limit("10/minute")
def get_critical_countries_list(request: Request):
    """Liste aller Länder mit Reisewarnungen"""
    return {
        "success": True,
        "countries": get_critical_countries()
    }


# ==================== AUSWÄRTIGES AMT ENDPOINTS ====================

@app.get("/aa/{country}")
@limiter.limit("30/minute")
def get_aa_link(request: Request, country: str):
    """Gibt direkten Link zum Auswärtigen Amt zurück - Token-sparend!"""
    result = get_aa_direct_link(country)
    return {
        "success": result["success"],
        "country": result["country"],
        "url": result["url"],
        "formatted": format_aa_link_for_chat(country)
    }


@app.get("/travel-info/{country}")
@limiter.limit("10/minute")
async def get_travel_info_quick(request: Request, country: str):
    """
    Schnelle Reiseinfo: Visa + AA-Link kombiniert
    Spart Tokens durch direkte Links statt langer Texte
    """
    # Visa-Info
    visa_info = get_visa_info(country)

    # AA-Link (schnell, kein Scraping)
    aa_link = get_aa_direct_link(country)

    # Kurze formatierte Antwort
    response_parts = []

    # Visa-Kurzinfo
    if visa_info["visa_required"] is True:
        response_parts.append(f"📋 **Visum erforderlich** - {visa_info['visa_type']}")
    elif visa_info["visa_required"] is False:
        if "ESTA" in str(visa_info.get("visa_type", "")):
            response_parts.append(f"📋 **ESTA erforderlich** (kein Visum)")
        else:
            response_parts.append(f"✅ **Visumfrei** für deutsche Staatsbürger")

    # Reisewarnung
    if visa_info.get("has_warning"):
        response_parts.append(f"⚠️ **{visa_info['warning_text']}**")

    # AA-Link
    if aa_link["success"]:
        response_parts.append(f"\n🔗 **Offizielle Infos:** {aa_link['url']}")

    return {
        "success": True,
        "country": country.title(),
        "visa_required": visa_info["visa_required"],
        "visa_type": visa_info["visa_type"],
        "has_warning": visa_info.get("has_warning", False),
        "aa_url": aa_link.get("url"),
        "formatted": "\n".join(response_parts),
        "short_response": True  # Flag für Token-sparende Antwort
    }


# Datenbank-Tabellen erstellen
create_db_and_tables()
