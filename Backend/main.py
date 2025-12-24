from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlmodel import SQLModel, create_engine, Session
import json
import re

# .env laden
load_dotenv()

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)

# Datenbank Setup
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Services importieren
from services.amadeus_service import search_flights_amadeus
from services.airport_service import search_airports
from services.openai_service import ask_chatgpt

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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/airports")
@limiter.limit("30/minute")  # Max 30 Anfragen pro Minute
def get_airports(request: Request, q: str):
    """Sucht Flughäfen - für Autocomplete"""
    results = search_airports(q)
    return {"airports": results}

@app.get("/search_flights")
@limiter.limit("10/minute")  # Max 10 Flugsuchen pro Minute
def search_flights(request: Request, from_airport: str, to_airport: str, date: str, adults: int = 1):
    """Sucht echte Flüge über Amadeus API und speichert in Historie"""
    
    # Suche in Historie speichern
    with Session(engine) as session:
        history = SearchHistory(from_airport=from_airport, to_airport=to_airport, date=date)
        session.add(history)
        session.commit()
    
    # Flüge suchen
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

@app.get("/ask")
@limiter.limit("5/minute")  # Max 5 KI-Anfragen pro Minute
def ask(request: Request, question: str):
    """Stellt eine Frage an ChatGPT"""
    answer = ask_chatgpt(question)
    return {"answer": answer}

@app.get("/smart_ask")
@limiter.limit("5/minute")
def smart_ask(request: Request, question: str):
    """Intelligenter Chat – erkennt Flugsuche-Anfragen"""
    
    # Prüfe ob es eine Flugsuche-Anfrage ist
    flight_keywords = ["flug", "fliegen", "flüge", "flight", "nach", "von", "reise"]
    is_flight_query = any(kw in question.lower() for kw in flight_keywords)
    
    if is_flight_query:
        # Lass ChatGPT die Daten extrahieren
        extract_prompt = f"""Analysiere diese Anfrage und extrahiere Flugdaten.
Anfrage: "{question}"

Antworte NUR mit JSON in diesem Format (keine anderen Texte):
{{"action": "search_flight", "from": "IATA-Code oder Stadt", "to": "IATA-Code oder Stadt", "date": "YYYY-MM-DD oder null"}}

Wenn es KEINE Flugsuche ist, antworte:
{{"action": "chat", "message": "normale Antwort"}}"""

        response = ask_chatgpt(extract_prompt)
        
        try:
            # Versuche JSON zu parsen
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                if data.get("action") == "search_flight":
                    return {
                        "type": "flight_search",
                        "from": data.get("from"),
                        "to": data.get("to"),
                        "date": data.get("date"),
                        "message": f"Ich suche Flüge von {data.get('from')} nach {data.get('to')}..."
                    }
        except:
            pass
    
    # Normale Chat-Antwort
    answer = ask_chatgpt(question)
    return {"type": "chat", "answer": answer}

# Datenbank-Tabellen erstellen
create_db_and_tables()