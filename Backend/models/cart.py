"""
Warenkorb Model für Flüge, Hotels und Aktivitäten
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import json


class CartItem(SQLModel, table=True):
    """Einzelnes Item im Warenkorb"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)  # Session/User ID
    item_type: str  # "flight", "hotel", "activity"
    item_data: str  # JSON-String mit allen Details
    price: float
    currency: str = "EUR"
    quantity: int = 1
    added_at: datetime = Field(default_factory=datetime.utcnow)

    def get_item_data(self) -> dict:
        """Parsed das JSON item_data"""
        return json.loads(self.item_data)

    def set_item_data(self, data: dict):
        """Setzt item_data als JSON"""
        self.item_data = json.dumps(data)


class CartSummary(SQLModel):
    """Zusammenfassung des Warenkorbs (nicht in DB gespeichert)"""
    session_id: str
    items: list = []
    total_price: float = 0.0
    currency: str = "EUR"
    item_count: int = 0
