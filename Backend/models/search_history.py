from sqlmodel import SQLModel, Field
from datetime import datetime

class SearchHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    from_airport: str
    to_airport: str
    date: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)