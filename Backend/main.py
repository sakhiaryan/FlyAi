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
from services.amadeus_service import search_flights_amadeus
from services.airport_service import search_airports
from services.openai_service import ask_chatgpt, ask_chatgpt_with_history
from services.auswaertiges_amt_service import fetch_travel_info, format_aa_info_for_chat, get_country_slug

# Models importieren
from models.search_history import SearchHistory
from models.chat_cache import ChatCache

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
def search_flights(request: Request, from_airport: str, to_airport: str, date: str, adults: int = 1):
    """Sucht echte Flüge über Amadeus API"""

    with Session(engine) as session:
        history = SearchHistory(from_airport=from_airport, to_airport=to_airport, date=date)
        session.add(history)
        session.commit()

    result = search_flights_amadeus(
        origin=from_airport,
        destination=to_airport,
        date=date,
        adults=adults
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

    # Prüfe ob es eine Flugsuche-Anfrage ist
    flight_keywords = ["flug", "fliegen", "flüge", "flight", "buchen", "ticket"]
    is_flight_query = any(kw in question_lower for kw in flight_keywords)

    # Prüfe auf Ziel-Anfragen wie "ich will nach X"
    destination_pattern = r"(?:nach|to|towards)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s+fliegen|\s+reisen|$)"
    destination_match = re.search(destination_pattern, question_lower)

    if is_flight_query or destination_match:
        # Extrahiere Flugdaten mit KI
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{chat_request.question}"

Antworte NUR mit JSON (keine anderen Texte):
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "date": "YYYY-MM-DD oder null"}}

Wenn keine klare Flugsuche, antworte:
{{"action": "chat"}}"""

        extract_response = ask_chatgpt(extract_prompt)

        try:
            json_match = re.search(r'\{.*\}', extract_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                if data.get("action") == "search_flight" and data.get("to"):
                    return {
                        "type": "flight_search",
                        "from": data.get("from"),
                        "to": data.get("to"),
                        "date": data.get("date"),
                        "message": f"Super! Ich suche Flüge nach {data.get('to')} für dich..."
                    }
        except:
            pass

    # Prüfe ob es eine Visa/Reise/Sicherheitsfrage ist
    travel_keywords = ["visum", "visa", "einreise", "reisewarnung", "sicherheit", "gefährlich",
                       "reisehinweis", "brauche ich", "reisepass", "impfung", "corona", "covid"]
    is_travel_query = any(kw in question_lower for kw in travel_keywords)

    # Extrahiere Land aus der Frage
    country_pattern = r"(?:nach|für|in|für)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\s+reisen|\s+fliegen|\?|$|,|\s+brauche|\s+ein)"
    country_match = re.search(country_pattern, question_lower)

    aa_context = ""

    if is_travel_query and country_match:
        country = country_match.group(1).strip()
        # Prüfe ob wir das Land kennen
        if get_country_slug(country):
            try:
                # Hole aktuelle Infos vom Auswärtigen Amt
                aa_info = await fetch_travel_info(country)
                aa_context = format_aa_info_for_chat(aa_info)
            except Exception as e:
                print(f"AA-Fetch Fehler: {e}")

    # Wenn wir AA-Kontext haben, füge ihn zur Anfrage hinzu
    if aa_context:
        enhanced_question = f"""{chat_request.question}

--- AKTUELLE INFOS VOM AUSWÄRTIGEN AMT (Stand heute) ---
{aa_context}
---
Nutze diese offiziellen Infos für deine Antwort und erwähne die Quelle (Auswärtiges Amt)."""

        messages[-1] = {"role": "user", "content": enhanced_question}

    # Normale Chat-Antwort mit History
    answer = ask_chatgpt_with_history(messages)

    return {"type": "chat", "answer": answer}

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

# Datenbank-Tabellen erstellen
create_db_and_tables()
