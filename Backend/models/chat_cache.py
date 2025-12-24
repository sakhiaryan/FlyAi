from sqlmodel import SQLModel, Field
from datetime import datetime

class ChatCache(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    question: str = Field(index=True)
    answer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
