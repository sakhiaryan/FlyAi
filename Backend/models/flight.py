from sqlmodel import SQLModel, Field

class Flight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin: str
    destination: str
    departure_date: str
    airline: str | None = None
    price: float | None = None
    currency: str | None = None
    stops: int | None = None