from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlmodel import SQLModel, create_engine, Session
from pydantic import BaseModel, field_validator
from typing import List, Optional
from passlib.context import CryptContext
import json
import re
import asyncio
import uuid
import html
import bleach
import os
import logging
from datetime import datetime

# .env laden
load_dotenv()

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("flyai")

# ==================== ENVIRONMENT VARIABLE VALIDATION ====================
def validate_env_vars():
    """Check required environment variables at startup."""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API (chat functionality)",
    }
    optional_vars = {
        "RAPIDAPI_KEY": "RapidAPI (flight/hotel search - will use mock data if missing)",
        "AMADEUS_API_KEY": "Amadeus API (airport search - will use fallback if missing)",
        "AMADEUS_API_SECRET": "Amadeus API secret",
    }

    missing_required = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"  - {var}: {description}")

    for var, description in optional_vars.items():
        if not os.getenv(var):
            logger.warning("Optional env var %s not set: %s", var, description)

    if missing_required:
        msg = "Missing required environment variables:\n" + "\n".join(missing_required)
        logger.error(msg)
        raise RuntimeError(msg)

    logger.info("Environment variables validated successfully")

validate_env_vars()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)

# Datenbank Setup
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


# Input sanitization helper
def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return text
    text = text[:max_length]
    text = bleach.clean(text, tags=[], attributes={}, strip=True)
    return text


def validate_session_id(session_id: str) -> str:
    """Validate and sanitize session ID format"""
    if not session_id:
        return str(uuid.uuid4())
    # Session IDs should be UUID format or alphanumeric
    cleaned = re.sub(r'[^a-zA-Z0-9\-_]', '', session_id)
    if len(cleaned) < 1 or len(cleaned) > 128:
        return str(uuid.uuid4())
    return cleaned

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Services importieren
from services.airport_service import search_airports
from services.openai_service import (
    ask_chatgpt, ask_chatgpt_with_history, ask_chatgpt_structured,
    detect_intent, generate_inspiration, generate_comparison,
    generate_packing_list, generate_budget_calc, generate_suggested_replies
)
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

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS - restricted to specific origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5500,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:5500,http://127.0.0.1:8080,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Pydantic Models für Request Body
class ChatMessage(BaseModel):
    role: str  # "user" oder "assistant"
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("user", "assistant", "system"):
            raise ValueError("role must be 'user', 'assistant', or 'system'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        if len(v) > 5000:
            raise ValueError("content must be at most 5000 characters")
        return v

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    question: str
    session_id: Optional[str] = None
    passport_country: Optional[str] = "deutschland"

    @field_validator("question")
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("question must not be empty")
        if len(v) > 2000:
            raise ValueError("question must be at most 2000 characters")
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v):
        if len(v) > 50:
            raise ValueError("messages list must have at most 50 entries")
        return v

class CartAddRequest(BaseModel):
    session_id: str
    item_type: str  # "flight", "hotel", "activity"
    item_data: dict
    price: float
    currency: str = "EUR"

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, v):
        allowed = ("flight", "hotel", "activity")
        if v not in allowed:
            raise ValueError(f"item_type must be one of {allowed}")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("price must be non-negative")
        if v > 1_000_000:
            raise ValueError("price exceeds maximum allowed value")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter code (e.g. EUR)")
        return v.upper()

class CartRemoveRequest(BaseModel):
    session_id: str
    item_id: int

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, v):
        if v < 1:
            raise ValueError("item_id must be a positive integer")
        return v

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

# ==================== GLOBAL EXCEPTION HANDLER ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Interner Serverfehler", "error_code": "INTERNAL_ERROR"},
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/airports")
@limiter.limit("30/minute")
def get_airports(request: Request, q: str):
    """Sucht Flughäfen - für Autocomplete"""
    if not q or not q.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "Query parameter 'q' is required"})
    if len(q) > 100:
        return JSONResponse(status_code=400, content={"success": False, "error": "Query too long (max 100 characters)"})
    try:
        results = search_airports(q)
        return {"success": True, "airports": results}
    except Exception as e:
        logger.error("Airport search failed for query '%s': %s", q, e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Flughafensuche fehlgeschlagen"})

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
    # Input validation
    if not from_airport or not from_airport.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "from_airport is required"})
    if not to_airport or not to_airport.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "to_airport is required"})
    if not date or not date.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "date is required"})

    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid date format. Use YYYY-MM-DD"})

    if return_date:
        try:
            datetime.strptime(return_date, "%Y-%m-%d")
        except ValueError:
            return JSONResponse(status_code=400, content={"success": False, "error": "Invalid return_date format. Use YYYY-MM-DD"})

    # Validate passenger counts
    if adults < 1 or adults > 9:
        return JSONResponse(status_code=400, content={"success": False, "error": "adults must be between 1 and 9"})
    if children < 0 or children > 9:
        return JSONResponse(status_code=400, content={"success": False, "error": "children must be between 0 and 9"})
    if infants < 0 or infants > 4:
        return JSONResponse(status_code=400, content={"success": False, "error": "infants must be between 0 and 4"})

    logger.info("Flight search: %s -> %s on %s (%d adults)", from_airport, to_airport, date, adults)

    try:
        with Session(engine) as session:
            history = SearchHistory(from_airport=from_airport, to_airport=to_airport, date=date)
            session.add(history)
            session.commit()
    except Exception as e:
        logger.error("Failed to save search history: %s", e)

    try:
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
    except Exception as e:
        logger.error("Flight search error: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": "Flugsuche fehlgeschlagen"})

@app.get("/search_history")
@limiter.limit("20/minute")
def get_search_history(request: Request):
    """Zeigt die letzten 20 Suchen"""
    try:
        with Session(engine) as session:
            history = session.query(SearchHistory).order_by(SearchHistory.timestamp.desc()).limit(20).all()
            return {"success": True, "history": history}
    except Exception as e:
        logger.error("Failed to fetch search history: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Suchverlauf konnte nicht geladen werden"})

@app.post("/chat")
@limiter.limit("20/minute")
async def chat_with_history(request: Request, chat_request: ChatRequest):
    """Chat MIT Konversations-History - der Bot merkt sich alles!
    Erweitert mit: Intent-Erkennung, Suggested Replies, Pauschalreise,
    Inspiration, Vergleich, Packliste, Budget-Kalkulation
    """

    # Konvertiere zu OpenAI Format
    messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]

    # Aktuelle Frage hinzufuegen
    messages.append({"role": "user", "content": chat_request.question})

    question_lower = chat_request.question.lower()
    session_id = chat_request.session_id or str(uuid.uuid4())

    logger.info("Chat request (session=%s): %s", session_id, chat_request.question[:100])

    # ==================== WARENKORB ABFRAGE ====================
    cart_keywords = ["warenkorb", "cart", "einkaufswagen", "was habe ich", "meine buchungen", "uebersicht", "übersicht"]
    is_cart_query = any(kw in question_lower for kw in cart_keywords)

    if is_cart_query:
        try:
            cart_text = format_cart_for_chat(engine, session_id)
            return {
                "type": "cart",
                "answer": cart_text,
                "session_id": session_id,
                "suggested_replies": generate_suggested_replies("cart")
            }
        except Exception as e:
            logger.error("Cart query failed: %s", e)
            return {
                "type": "cart",
                "answer": "Warenkorb konnte nicht geladen werden.",
                "session_id": session_id,
                "suggested_replies": ["Erneut versuchen", "Fluege suchen", "Hotels suchen"]
            }

    # ==================== INSPIRATION / "WOHIN SOLL ICH REISEN?" ====================
    inspiration_keywords = [
        "inspiriere mich", "wohin soll ich", "wohin kann ich", "reiseziel vorschlagen",
        "wo soll ich hin", "reise inspiration", "vorschlaege", "vorschläge",
        "empfehle mir", "top reiseziele", "beliebte ziele", "wohin reisen",
        "ideen", "keine ahnung wohin", "ueberrasch mich", "überrasch mich"
    ]
    is_inspiration = any(kw in question_lower for kw in inspiration_keywords)

    if is_inspiration:
        # Extrahiere Praeferenzen aus der Frage
        preferences = None
        budget = None
        season = None

        if any(kw in question_lower for kw in ["strand", "meer", "sonne", "beach"]):
            preferences = "Strandurlaub"
        elif any(kw in question_lower for kw in ["stadt", "city", "kultur", "museum"]):
            preferences = "Staedtetrip/Kultur"
        elif any(kw in question_lower for kw in ["abenteuer", "adventure", "wandern", "natur"]):
            preferences = "Abenteuer/Natur"
        elif any(kw in question_lower for kw in ["familie", "kinder", "family"]):
            preferences = "Familienreise"

        if any(kw in question_lower for kw in ["guenstig", "günstig", "billig", "budget", "wenig geld"]):
            budget = "Budget (unter 500 EUR)"
        elif any(kw in question_lower for kw in ["luxus", "luxury", "premium", "5 sterne"]):
            budget = "Luxus"

        if any(kw in question_lower for kw in ["sommer", "summer"]):
            season = "Sommer"
        elif any(kw in question_lower for kw in ["winter"]):
            season = "Winter"
        elif any(kw in question_lower for kw in ["herbst", "autumn"]):
            season = "Herbst"
        elif any(kw in question_lower for kw in ["fruehling", "frühling", "spring"]):
            season = "Fruehling"

        inspiration_answer = generate_inspiration(preferences, budget, season)

        return {
            "type": "inspiration",
            "answer": inspiration_answer,
            "session_id": session_id,
            "suggested_replies": ["Mehr Inspirationen", "Fluege suchen", "Budget berechnen", "Vergleiche zwei Ziele"]
        }

    # ==================== VERGLEICH ZWEIER ZIELE ====================
    compare_keywords = ["vergleich", "vergleiche", "oder", "vs", "versus", "besser"]
    is_compare = any(kw in question_lower for kw in compare_keywords)

    if is_compare:
        # Versuche zwei Ziele zu extrahieren
        compare_patterns = [
            r"(?:vergleiche?)\s+([A-Za-zäöüÄÖÜß\s]+?)\s+(?:und|oder|vs|versus|mit)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s*$|\s*\?)",
            r"([A-Za-zäöüÄÖÜß]+)\s+(?:oder|vs|versus)\s+([A-Za-zäöüÄÖÜß]+)",
            r"(?:lieber|besser)\s+([A-Za-zäöüÄÖÜß]+)\s+oder\s+([A-Za-zäöüÄÖÜß]+)",
        ]

        dest1, dest2 = None, None
        for pattern in compare_patterns:
            match = re.search(pattern, question_lower)
            if match:
                dest1 = match.group(1).strip()
                dest2 = match.group(2).strip()
                break

        if dest1 and dest2:
            comparison = generate_comparison(dest1, dest2)
            return {
                "type": "comparison",
                "answer": comparison,
                "destinations": [dest1.title(), dest2.title()],
                "session_id": session_id,
                "suggested_replies": [
                    f"Fluege nach {dest1.title()}",
                    f"Fluege nach {dest2.title()}",
                    f"Hotels in {dest1.title()}",
                    "Anderes Ziel vergleichen"
                ]
            }

    # ==================== PACKLISTE ====================
    packing_keywords = ["packliste", "packen", "was mitnehmen", "koffer", "was einpacken", "checkliste reise", "packing"]
    is_packing = any(kw in question_lower for kw in packing_keywords)

    if is_packing:
        # Extrahiere Ziel aus Frage oder Kontext
        destination = None
        season = None

        # Aus aktueller Frage
        dest_match = re.search(r"(?:fuer|für|nach)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s*$|\s*\?|\s+im|\s+in)", question_lower)
        if dest_match:
            destination = dest_match.group(1).strip()

        # Aus Chat-History wenn nicht in Frage
        if not destination and chat_request.messages:
            for msg in reversed(chat_request.messages):
                content_lower = msg.content.lower()
                for p in [r"nach\s+([A-Za-zäöüÄÖÜß]+)", r"in\s+([A-Za-zäöüÄÖÜß]+)", r"fuer\s+([A-Za-zäöüÄÖÜß]+)"]:
                    m = re.search(p, content_lower)
                    if m:
                        destination = m.group(1).strip()
                        break
                if destination:
                    break

        if any(kw in question_lower for kw in ["sommer", "warm", "heiss"]):
            season = "Sommer/warm"
        elif any(kw in question_lower for kw in ["winter", "kalt", "schnee"]):
            season = "Winter/kalt"

        if destination:
            packing_answer = generate_packing_list(destination, season)
            return {
                "type": "packing_list",
                "answer": packing_answer,
                "destination": destination.title(),
                "session_id": session_id,
                "suggested_replies": generate_suggested_replies("packing_list", destination.title())
            }
        else:
            return {
                "type": "ask_destination",
                "answer": "Fuer welches Reiseziel soll ich eine Packliste erstellen? Nenn mir auch gerne die Jahreszeit!",
                "session_id": session_id,
                "suggested_replies": ["Thailand", "Island", "Japan", "Spanien"]
            }

    # ==================== BUDGET-KALKULATION ====================
    budget_calc_keywords = ["budget berechnen", "was kostet", "wie teuer", "budget kalkulation",
                           "reisebudget", "budget planen", "kostenaufstellung"]
    is_budget_calc = any(kw in question_lower for kw in budget_calc_keywords)

    if is_budget_calc:
        # Extrahiere Ziel
        destination = None
        dest_match = re.search(r"(?:fuer|für|nach|in)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s*$|\s*\?|\s+fuer|\s+für)", question_lower)
        if dest_match:
            destination = dest_match.group(1).strip()

        # Aus Chat-History
        if not destination and chat_request.messages:
            for msg in reversed(chat_request.messages):
                content_lower = msg.content.lower()
                for p in [r"nach\s+([A-Za-zäöüÄÖÜß]+)", r"in\s+([A-Za-zäöüÄÖÜß]+)"]:
                    m = re.search(p, content_lower)
                    if m:
                        destination = m.group(1).strip()
                        break
                if destination:
                    break

        if destination:
            # Extrahiere optionale Parameter
            duration = None
            travelers = None
            style = None

            dur_match = re.search(r"(\d+)\s*(?:tage|wochen|naechte|nächte)", question_lower)
            if dur_match:
                duration = dur_match.group(0)

            trav_match = re.search(r"(\d+)\s*(?:personen|leute|erwachsene)", question_lower)
            if trav_match:
                travelers = trav_match.group(0)

            if any(kw in question_lower for kw in ["luxus", "luxury", "premium"]):
                style = "Luxus"
            elif any(kw in question_lower for kw in ["guenstig", "günstig", "budget", "billig", "backpacker"]):
                style = "Budget/Backpacker"

            budget_answer = generate_budget_calc(destination, duration, travelers, style)
            return {
                "type": "budget_calc",
                "answer": budget_answer,
                "destination": destination.title(),
                "session_id": session_id,
                "suggested_replies": generate_suggested_replies("budget_calc", destination.title())
            }
        else:
            return {
                "type": "ask_destination",
                "answer": "Fuer welches Reiseziel soll ich das Budget berechnen?",
                "session_id": session_id,
                "suggested_replies": ["Thailand 2 Wochen", "Japan 10 Tage", "Spanien 1 Woche", "Bali 14 Tage"]
            }

    # ==================== PAUSCHALREISE / KOMPLETT-PAKET ====================
    package_keywords = ["pauschalreise", "komplett-paket", "komplettpaket", "all inclusive",
                       "flug und hotel", "flug + hotel", "paket", "gesamtpaket", "kombination"]
    is_package = any(kw in question_lower for kw in package_keywords)

    if is_package:
        # Extrahiere Daten mit KI
        extract_prompt = f"""Analysiere diese Pauschalreise-Anfrage.
Anfrage: "{chat_request.question}"

Antworte mit JSON:
{{"action": "package_search", "destination": "Stadt oder Region", "country": "Land", "from": "Abflugort oder null", "date": "YYYY-MM-DD oder null", "return_date": "YYYY-MM-DD oder null", "travelers": "Anzahl oder null", "budget": "Budget in EUR oder null"}}

Wenn keine Paketsuche:
{{"action": "chat"}}"""

        data = ask_chatgpt_structured(extract_prompt)

        if data.get("action") == "package_search" and data.get("destination"):
            destination = data.get("destination")
            country = data.get("country")

            # Visa-Check
            visa_warning = ""
            aa_url = None
            if country:
                visa_info = get_visa_info(country)
                if visa_info["visa_required"] or visa_info["has_warning"]:
                    visa_warning = format_visa_warning_for_chat(country)
                aa_link = get_aa_direct_link(country)
                if aa_link["success"]:
                    aa_url = aa_link["url"]

            response_msg = f"Ich suche ein Komplettpaket (Flug + Hotel) nach {destination} fuer dich!"
            response_msg += f"\n\nIch starte mit der Flugsuche - passende Hotels zeige ich dir direkt danach."

            if visa_warning:
                response_msg += f"\n\n{visa_warning}"
            if aa_url:
                response_msg += f"\n\n🔗 **Offizielle Reisehinweise:** {aa_url}"

            return {
                "type": "package_search",
                "destination": destination,
                "country": country,
                "from": data.get("from"),
                "date": data.get("date"),
                "return_date": data.get("return_date"),
                "message": response_msg,
                "visa_info": get_visa_info(country) if country else None,
                "aa_url": aa_url,
                "session_id": session_id,
                "suggested_replies": ["Nur Fluege", "Nur Hotels", "Budget aendern", "Andere Daten"]
            }

    # ==================== FLUGSUCHE ====================
    flight_keywords = ["flug", "fliegen", "fluege", "flüge", "flight", "buchen", "ticket"]
    is_flight_query = any(kw in question_lower for kw in flight_keywords)

    # Pruefe auf Ziel-Anfragen wie "ich will nach X"
    destination_pattern = r"(?:nach|to|towards)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s+fliegen|\s+reisen|$)"
    destination_match = re.search(destination_pattern, question_lower)

    # Extrahiere Zielland fuer Visa-Check
    target_country = None
    if destination_match:
        target_country = destination_match.group(1).strip()

    if is_flight_query or destination_match:
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{chat_request.question}"

Antworte mit JSON:
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "to_country": "Land des Ziels", "date": "YYYY-MM-DD oder null"}}

Wenn keine klare Flugsuche, antworte:
{{"action": "chat"}}"""

        data = ask_chatgpt_structured(extract_prompt)

        try:
                if data.get("action") == "search_flight" and data.get("to"):
                    visa_warning = ""
                    to_country = data.get("to_country") or target_country
                    aa_url = None

                    if to_country:
                        visa_info = get_visa_info(to_country)
                        if visa_info["visa_required"] or visa_info["has_warning"]:
                            visa_warning = format_visa_warning_for_chat(to_country)
                        aa_link = get_aa_direct_link(to_country)
                        if aa_link["success"]:
                            aa_url = aa_link["url"]

                    response_msg = f"Super! Ich suche Fluege nach {data.get('to')} fuer dich..."
                    if visa_warning:
                        response_msg += f"\n\n{visa_warning}"
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
                        "session_id": session_id,
                        "suggested_replies": generate_suggested_replies("flight_search", data.get("to"))
                    }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse flight extraction response: %s", e)

    # ==================== HOTEL SUCHE ====================
    hotel_keywords = ["hotel", "unterkunft", "uebernachtung", "übernachtung", "zimmer", "uebernachten", "übernachten"]
    is_hotel_query = any(kw in question_lower for kw in hotel_keywords)

    if is_hotel_query:
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Hoteldaten.
Anfrage: "{chat_request.question}"

Antworte mit JSON:
{{"action": "search_hotel", "destination": "Stadt oder Region", "country": "Land", "checkin": "YYYY-MM-DD oder null", "checkout": "YYYY-MM-DD oder null"}}

Wenn keine Hotelsuche:
{{"action": "chat"}}"""

        data = ask_chatgpt_structured(extract_prompt)

        try:
                if data.get("action") == "search_hotel" and data.get("destination"):
                    visa_warning = ""
                    country = data.get("country")
                    aa_url = None

                    if country:
                        visa_info = get_visa_info(country)
                        if visa_info["visa_required"] or visa_info["has_warning"]:
                            visa_warning = format_visa_warning_for_chat(country)
                        aa_link = get_aa_direct_link(country)
                        if aa_link["success"]:
                            aa_url = aa_link["url"]

                    response_msg = f"Ich suche Hotels in {data.get('destination')} fuer dich..."
                    if visa_warning:
                        response_msg += f"\n\n{visa_warning}"
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
                        "session_id": session_id,
                        "suggested_replies": generate_suggested_replies("hotel_search", data.get("destination"))
                    }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse hotel extraction response: %s", e)

    # ==================== VISA/REISE FRAGEN (TOKEN-OPTIMIERT) ====================
    travel_keywords = ["visum", "visa", "einreise", "reisewarnung", "sicherheit", "gefaehrlich", "gefährlich",
                       "reisehinweis", "brauche ich", "reisepass", "impfung", "corona", "covid", "pass",
                       "auswaertiges amt", "auswärtiges amt", "reiseinfo", "reisen", "kann ich nach", "darf ich nach"]
    is_travel_query = any(kw in question_lower for kw in travel_keywords)

    country_patterns = [
        r"(?:visum|visa)\s+(?:für|fuer|nach)\s+([A-Za-zäöüÄÖÜß]+)",
        r"(?:kann ich nach|darf ich nach)\s+([A-Za-zäöüÄÖÜß]+)",
        r"(?:reise nach|fliegen nach|trip nach)\s+([A-Za-zäöüÄÖÜß]+)",
        r"nach\s+([A-Za-zäöüÄÖÜß]+)\s+(?:reisen|fliegen)",
        r"für\s+([A-Za-zäöüÄÖÜß]+)\s+(?:visum|visa|einreise)",
        r"in\s+([A-Za-zäöüÄÖÜß]+)\s+(?:reisen|fliegen|einreise)",
        r"([A-Za-zäöüÄÖÜß]+)\s+(?:visum|visa|einreise|reisewarnung)",
        r"(?:ist|wie ist)\s+([A-Za-zäöüÄÖÜß]+)\s+(?:sicher|gefaehrlich|gefährlich)",
        r"nach\s+([A-Za-zäöüÄÖÜß]+)",
    ]
    country_match = None
    for pattern in country_patterns:
        match = re.search(pattern, question_lower)
        if match:
            extracted = match.group(1).strip()
            if get_country_slug(extracted) or get_visa_info(extracted)["visa_required"] is not None:
                country_match = match
                break

    # SCHNELLE DIREKT-ANTWORT fuer Reisefragen (spart Tokens!)
    if is_travel_query and country_match:
        country = country_match.group(1).strip()

        visa_info = get_visa_info(country)
        aa_link = get_aa_direct_link(country)

        response_parts = []

        if visa_info.get("has_warning"):
            response_parts.append(f"⚠️ **{visa_info['warning_text']}**")

        if visa_info["visa_required"] is True:
            response_parts.append(f"📋 **Visum erforderlich** fuer {country.title()}")
            response_parts.append(f"   Typ: {visa_info['visa_type']}")
            if visa_info.get("notes"):
                response_parts.append(f"   {visa_info['notes'][:150]}")
        elif visa_info["visa_required"] is False:
            if "ESTA" in str(visa_info.get("visa_type", "")):
                response_parts.append(f"📋 **ESTA erforderlich** fuer {country.title()} (kein Visum)")
            else:
                response_parts.append(f"✅ **Visumfrei** fuer {country.title()} (deutsche Staatsbuerger)")

        if aa_link["success"]:
            response_parts.append(f"\n🔗 **Offizielle Infos vom Auswaertigen Amt:**")
            response_parts.append(aa_link["url"])

        direct_answer = "\n".join(response_parts)

        return {
            "type": "travel_info",
            "answer": direct_answer,
            "country": country.title(),
            "visa_info": visa_info,
            "aa_url": aa_link.get("url"),
            "session_id": session_id,
            "suggested_replies": generate_suggested_replies("visa_info", country.title())
        }

    # ==================== PASS-FRAGE ====================
    pass_keywords = ["welchen pass", "was fuer ein pass", "was für ein pass", "reisepass", "personalausweis", "passport"]
    is_pass_query = any(kw in question_lower for kw in pass_keywords)

    if is_pass_query and not country_match:
        return {
            "type": "ask_passport",
            "message": "Welchen Reisepass hast du? (z.B. deutscher Pass, oesterreichischer Pass) Und wohin moechtest du reisen?",
            "session_id": session_id,
            "suggested_replies": ["Deutscher Pass", "Oesterreichischer Pass", "Schweizer Pass"]
        }

    # ==================== REISEPLANUNG ====================
    planning_keywords = ["reise planen", "trip planen", "urlaub planen", "reiseplan", "komplette reise",
                         "was kann ich unternehmen", "was gibt es zu sehen", "sehenswuerdigkeiten", "sehenswürdigkeiten",
                         "aktivitaeten", "aktivitäten", "tipps fuer", "tipps für", "empfehlungen fuer", "empfehlungen für",
                         "beste zeit", "wann sollte ich", "wie lange", "budget", "kosten", "guenstiger", "günstiger",
                         "teuer", "beste reisezeit"]
    is_planning_query = any(kw in question_lower for kw in planning_keywords)

    budget_keywords = ["budget", "kosten", "preis", "wie viel", "wieviel", "guenstig", "günstig", "billig", "teuer"]
    is_budget_query = any(kw in question_lower for kw in budget_keywords)

    timing_keywords = ["beste zeit", "wann", "saison", "jahreszeit", "regenzeit", "trockenzeit", "monsun"]
    is_timing_query = any(kw in question_lower for kw in timing_keywords)

    if (is_planning_query or is_budget_query or is_timing_query) and country_match:
        country = country_match.group(1).strip()

        planning_prompt = f"""Du bist ein erfahrener Reiseberater. Gib eine hilfreiche, praegnante Antwort auf diese Frage.

Frage: "{chat_request.question}"
Land: {country}

Antworte kurz und hilfreich (max. 200 Woerter). Verwende Emoji fuer bessere Lesbarkeit.
Fokus:
- Wenn nach BUDGET/KOSTEN gefragt: Gib realistische Preise fuer Fluege, Hotels, Essen
- Wenn nach BESTE ZEIT gefragt: Nenne optimale Monate und warum
- Wenn nach AKTIVITAETEN gefragt: Liste Top 3-5 Highlights
- Wenn nach TIPPS gefragt: Gib praktische lokale Tipps

Schliesse mit: "Soll ich Fluege nach {country} suchen?" """

        planning_answer = ask_chatgpt(planning_prompt)

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
            "session_id": session_id,
            "suggested_replies": generate_suggested_replies("travel_planning", country.title())
        }

    # ==================== WETTER-ANFRAGEN ====================
    weather_keywords = ["wetter", "temperatur", "klima", "regen", "sonnig", "warm", "kalt"]
    is_weather_query = any(kw in question_lower for kw in weather_keywords)

    if is_weather_query and country_match:
        country = country_match.group(1).strip()

        weather_prompt = f"""Beschreibe das typische Klima und Wetter in {country} kurz (max. 100 Woerter).
Nenne:
- Beste Reisezeit (Monate)
- Typische Temperaturen
- Regenzeit/Trockenzeit wenn relevant

Verwende Wetter-Emojis fuer bessere Lesbarkeit."""

        weather_answer = ask_chatgpt(weather_prompt)

        return {
            "type": "weather_info",
            "answer": weather_answer,
            "country": country.title(),
            "session_id": session_id,
            "suggested_replies": generate_suggested_replies("weather_info", country.title())
        }

    # ==================== NORMALE CHAT-ANTWORT MIT HISTORY ====================
    answer = ask_chatgpt_with_history(messages)

    detected_country = None
    aa_url = None

    for pattern in country_patterns:
        match = re.search(pattern, question_lower)
        if match:
            extracted = match.group(1).strip()
            if get_country_slug(extracted):
                detected_country = extracted
                break

    if not detected_country:
        common_countries = ["usa", "china", "japan", "thailand", "tuerkei", "türkei", "spanien", "italien",
                          "frankreich", "griechenland", "aegypten", "ägypten", "australien", "brasilien",
                          "mexiko", "indien", "vietnam", "indonesien", "marokko", "russland",
                          "syrien", "afghanistan", "iran", "ukraine", "israel"]
        for country in common_countries:
            if country in question_lower:
                detected_country = country
                break

    if detected_country:
        aa_link = get_aa_direct_link(detected_country)
        if aa_link["success"]:
            aa_url = aa_link["url"]
            answer += f"\n\n🔗 **Offizielle Reise- und Sicherheitshinweise:**\n{aa_url}"

    # Generiere kontextbezogene Suggested Replies
    suggested = generate_suggested_replies("general_chat", detected_country)

    return {
        "type": "chat",
        "answer": answer,
        "session_id": session_id,
        "detected_country": detected_country,
        "aa_url": aa_url,
        "suggested_replies": suggested
    }

@app.get("/smart_ask")
@limiter.limit("10/minute")
def smart_ask(request: Request, question: str):
    """Einfacher Chat ohne History (Legacy-Endpoint)"""
    if not question or not question.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "question is required"})
    if len(question) > 2000:
        return JSONResponse(status_code=400, content={"success": False, "error": "question too long (max 2000 characters)"})

    logger.info("Smart ask: %s", question[:100])

    flight_keywords = ["flug", "fliegen", "flüge", "flight", "nach", "von", "reise", "buchen"]
    is_flight_query = any(kw in question.lower() for kw in flight_keywords)

    if is_flight_query:
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{question}"

Antworte NUR mit JSON:
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "date": "YYYY-MM-DD oder null"}}

Wenn keine Flugsuche:
{{"action": "chat"}}"""

        try:
            response = ask_chatgpt(extract_prompt)
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
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse smart_ask flight extraction: %s", e)
        except Exception as e:
            logger.error("OpenAI call failed in smart_ask: %s", e)

    try:
        answer = ask_chatgpt(question)
        return {"type": "chat", "answer": answer}
    except Exception as e:
        logger.error("smart_ask chat failed: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Chat-Antwort fehlgeschlagen"})

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
    if not destination or not destination.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "destination is required"})

    # Validate date formats
    for label, val in [("checkin", checkin), ("checkout", checkout)]:
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except (ValueError, TypeError):
            return JSONResponse(status_code=400, content={"success": False, "error": f"Invalid {label} format. Use YYYY-MM-DD"})

    if adults < 1 or adults > 9:
        return JSONResponse(status_code=400, content={"success": False, "error": "adults must be between 1 and 9"})
    if rooms < 1 or rooms > 9:
        return JSONResponse(status_code=400, content={"success": False, "error": "rooms must be between 1 and 9"})

    logger.info("Hotel search: %s, %s to %s (%d adults, %d rooms)", destination, checkin, checkout, adults, rooms)

    try:
        result = await search_hotels(
            destination=destination,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            rooms=rooms,
            children=children
        )
        return result
    except Exception as e:
        logger.error("Hotel search error: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": "Hotelsuche fehlgeschlagen"})


@app.get("/search_destination")
@limiter.limit("30/minute")
async def search_destination_endpoint(request: Request, q: str):
    """Sucht Reiseziele für Hotel-Autocomplete"""
    if not q or not q.strip():
        return JSONResponse(status_code=400, content={"success": False, "error": "Query parameter 'q' is required"})
    if len(q) > 100:
        return JSONResponse(status_code=400, content={"success": False, "error": "Query too long (max 100 characters)"})
    try:
        result = await search_destination(q)
        return result
    except Exception as e:
        logger.error("Destination search error for '%s': %s", q, e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Reisezielsuche fehlgeschlagen"})


# ==================== WARENKORB ENDPOINTS ====================

@app.post("/cart/add")
@limiter.limit("30/minute")
def add_cart_item(request: Request, cart_request: CartAddRequest):
    """Fügt Item zum Warenkorb hinzu"""
    try:
        item = add_to_cart(
            engine=engine,
            session_id=cart_request.session_id,
            item_type=cart_request.item_type,
            item_data=cart_request.item_data,
            price=cart_request.price,
            currency=cart_request.currency
        )
        logger.info("Cart item added: type=%s, price=%.2f, session=%s", cart_request.item_type, cart_request.price, cart_request.session_id)
        return {
            "success": True,
            "message": f"{cart_request.item_type.title()} zum Warenkorb hinzugefügt!",
            "item_id": item.id,
            "cart": get_cart_summary(engine, cart_request.session_id)
        }
    except Exception as e:
        logger.error("Failed to add cart item: %s", e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Item konnte nicht hinzugefügt werden"})


@app.get("/cart/{session_id}")
@limiter.limit("30/minute")
def get_cart_items(request: Request, session_id: str):
    """Holt alle Items aus dem Warenkorb"""
    try:
        return get_cart_summary(engine, session_id)
    except Exception as e:
        logger.error("Failed to get cart for session %s: %s", session_id, e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Warenkorb konnte nicht geladen werden"})


@app.delete("/cart/remove")
@limiter.limit("30/minute")
def remove_cart_item(request: Request, cart_request: CartRemoveRequest):
    """Entfernt Item aus dem Warenkorb"""
    try:
        success = remove_from_cart(engine, cart_request.session_id, cart_request.item_id)
        if success:
            logger.info("Cart item removed: id=%d, session=%s", cart_request.item_id, cart_request.session_id)
            return {
                "success": True,
                "message": "Item entfernt",
                "cart": get_cart_summary(engine, cart_request.session_id)
            }
        return JSONResponse(status_code=404, content={"success": False, "error": "Item nicht gefunden"})
    except Exception as e:
        logger.error("Failed to remove cart item %d: %s", cart_request.item_id, e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Item konnte nicht entfernt werden"})


@app.delete("/cart/clear/{session_id}")
@limiter.limit("10/minute")
def clear_cart_items(request: Request, session_id: str):
    """Leert den gesamten Warenkorb"""
    try:
        count = clear_cart(engine, session_id)
        logger.info("Cart cleared: %d items removed, session=%s", count, session_id)
        return {
            "success": True,
            "message": f"{count} Items entfernt",
            "cart": get_cart_summary(engine, session_id)
        }
    except Exception as e:
        logger.error("Failed to clear cart for session %s: %s", session_id, e)
        return JSONResponse(status_code=500, content={"success": False, "error": "Warenkorb konnte nicht geleert werden"})


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
logger.info("FlyAI backend started successfully. Database tables created.")
