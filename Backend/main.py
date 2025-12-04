from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search_flights")
def search_flights(from_airport: str, to_airport: str, date: str):

    # Fake / Mock Flugdaten
    flights = [
        {
            "flight_number": "FA123",
            "from": from_airport,
            "to": to_airport,
            "date": date,
            "price": 450,
            "stops": 0,
            "baggage_included": True
        },
        {
            "flight_number": "FA456",
            "from": from_airport,
            "to": to_airport,
            "date": date,
            "price": 380,
            "stops": 1,
            "baggage_included": False
        }
    ]

    return {"flights": flights}