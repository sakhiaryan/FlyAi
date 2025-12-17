from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models.search_history import SearchHistory
from sqlmodel import Session
# Services importieren
from services.amadeus_service import search_flights_amadeus
from services.airport_service import search_airports
from services.openai_service import ask_chatgpt
from sqlmodel import SQLModel, create_engine
# .env laden
load_dotenv()

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
create_db_and_tables()


app = FastAPI(title="FlyAI", description="KI-gestützte Flugsuche", version="1.0.0")


@app.get("/ask")
def ask(question: str):
    """Stellt eine Frage an ChatGPT"""
    answer = ask_chatgpt(question)
    return {"answer": answer}


# CORS erlauben (damit Frontend zugreifen kann)
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

@app.get("/search_flights")
def search_flights(from_airport: str, to_airport: str, date: str, adults: int = 1):
    """
    Sucht echte Flüge über Amadeus API
    Beispiel: /search_flights?from_airport=BER&to_airport=JFK&date=2025-12-20
    """
    result = search_flights_amadeus(
        origin=from_airport,
        destination=to_airport,
        date=date,
        adults=adults
    )
    return result

@app.post("/save_search")
def save_search(from_airport: str, to_airport: str, date: str):
    search = SearchHistory(from_airport=from_airport, to_airport=to_airport, date=date)
    with Session(engine) as session:
        session.add(search)
        session.commit()
        session.refresh(search)
    return {"success": True, "search": search}

@app.get("/airports")
def get_airports(q: str):
    """Sucht Flughäfen - für Autocomplete"""
    results = search_airports(q)
    return {"airports": results}