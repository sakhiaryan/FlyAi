"""
Warenkorb Service
Verwaltet Flüge, Hotels und Aktivitäten im Warenkorb
"""

from sqlmodel import Session, select
from typing import List, Dict, Optional
import json
from datetime import datetime

from models.cart import CartItem


def add_to_cart(
    engine,
    session_id: str,
    item_type: str,
    item_data: dict,
    price: float,
    currency: str = "EUR"
) -> CartItem:
    """
    Fügt ein Item zum Warenkorb hinzu

    Args:
        engine: SQLModel Engine
        session_id: Benutzer/Session ID
        item_type: "flight", "hotel" oder "activity"
        item_data: Details zum Item
        price: Preis
        currency: Währung

    Returns:
        Das erstellte CartItem
    """
    with Session(engine) as session:
        cart_item = CartItem(
            session_id=session_id,
            item_type=item_type,
            item_data=json.dumps(item_data),
            price=price,
            currency=currency
        )
        session.add(cart_item)
        session.commit()
        session.refresh(cart_item)
        return cart_item


def get_cart(engine, session_id: str) -> List[Dict]:
    """
    Holt alle Items aus dem Warenkorb

    Returns:
        Liste von Cart-Items als Dictionaries
    """
    with Session(engine) as session:
        statement = select(CartItem).where(CartItem.session_id == session_id)
        items = session.exec(statement).all()

        return [{
            "id": item.id,
            "type": item.item_type,
            "data": json.loads(item.item_data),
            "price": item.price,
            "currency": item.currency,
            "quantity": item.quantity,
            "added_at": item.added_at.isoformat()
        } for item in items]


def get_cart_summary(engine, session_id: str) -> Dict:
    """
    Gibt Zusammenfassung des Warenkorbs zurück
    """
    items = get_cart(engine, session_id)

    total = sum(item["price"] * item["quantity"] for item in items)

    # Gruppiere nach Typ
    flights = [i for i in items if i["type"] == "flight"]
    hotels = [i for i in items if i["type"] == "hotel"]
    activities = [i for i in items if i["type"] == "activity"]

    return {
        "session_id": session_id,
        "items": items,
        "flights": flights,
        "hotels": hotels,
        "activities": activities,
        "total_price": round(total, 2),
        "currency": "EUR",
        "item_count": len(items),
        "flight_count": len(flights),
        "hotel_count": len(hotels),
        "activity_count": len(activities)
    }


def remove_from_cart(engine, session_id: str, item_id: int) -> bool:
    """
    Entfernt ein Item aus dem Warenkorb

    Returns:
        True wenn erfolgreich, False wenn nicht gefunden
    """
    with Session(engine) as session:
        statement = select(CartItem).where(
            CartItem.session_id == session_id,
            CartItem.id == item_id
        )
        item = session.exec(statement).first()

        if item:
            session.delete(item)
            session.commit()
            return True
        return False


def clear_cart(engine, session_id: str) -> int:
    """
    Leert den gesamten Warenkorb

    Returns:
        Anzahl der gelöschten Items
    """
    with Session(engine) as session:
        statement = select(CartItem).where(CartItem.session_id == session_id)
        items = session.exec(statement).all()

        count = len(items)
        for item in items:
            session.delete(item)

        session.commit()
        return count


def get_best_combo(engine, session_id: str) -> Dict:
    """
    Analysiert den Warenkorb und gibt Preis-Leistungs-Empfehlung

    Returns:
        Dict mit Empfehlungen
    """
    summary = get_cart_summary(engine, session_id)

    recommendations = []

    # Prüfe Flüge
    if summary["flights"]:
        cheapest_flight = min(summary["flights"], key=lambda x: x["price"])
        recommendations.append({
            "type": "flight",
            "recommendation": "Günstigster Flug",
            "item": cheapest_flight,
            "savings": 0
        })

    # Prüfe Hotels
    if summary["hotels"]:
        # Beste Preis-Leistung: Preis / Bewertung
        for hotel in summary["hotels"]:
            rating = hotel["data"].get("rating", 7)
            hotel["value_score"] = hotel["price"] / rating if rating > 0 else hotel["price"]

        best_value_hotel = min(summary["hotels"], key=lambda x: x.get("value_score", float("inf")))
        recommendations.append({
            "type": "hotel",
            "recommendation": "Beste Preis-Leistung",
            "item": best_value_hotel,
            "value_score": best_value_hotel.get("value_score", 0)
        })

    return {
        "cart_summary": summary,
        "recommendations": recommendations,
        "total_savings": sum(r.get("savings", 0) for r in recommendations)
    }


def format_cart_for_chat(engine, session_id: str) -> str:
    """
    Formatiert den Warenkorb für den Chatbot
    """
    summary = get_cart_summary(engine, session_id)

    if summary["item_count"] == 0:
        return "🛒 Dein Warenkorb ist leer."

    parts = [f"🛒 **Dein Warenkorb** ({summary['item_count']} Artikel):\n"]

    # Flüge
    if summary["flights"]:
        parts.append("✈️ **Flüge:**")
        for flight in summary["flights"]:
            data = flight["data"]
            parts.append(f"   • {data.get('from', '?')} → {data.get('to', '?')}: {flight['price']} {flight['currency']}")

    # Hotels
    if summary["hotels"]:
        parts.append("\n🏨 **Hotels:**")
        for hotel in summary["hotels"]:
            data = hotel["data"]
            parts.append(f"   • {data.get('name', 'Hotel')}: {hotel['price']} {hotel['currency']}")

    # Aktivitäten
    if summary["activities"]:
        parts.append("\n🎫 **Aktivitäten:**")
        for activity in summary["activities"]:
            data = activity["data"]
            parts.append(f"   • {data.get('name', 'Aktivität')}: {activity['price']} {activity['currency']}")

    parts.append(f"\n💰 **Gesamt: {summary['total_price']} {summary['currency']}**")

    return "\n".join(parts)
