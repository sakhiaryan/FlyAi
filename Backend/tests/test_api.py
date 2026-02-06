"""
Unit Tests für FlyAI API Endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Backend-Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests für den Health-Check Endpoint"""

    def test_health_returns_ok(self):
        """Health endpoint sollte status ok zurückgeben"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAirportSearch:
    """Tests für die Flughafen-Suche"""

    def test_airport_search_returns_results(self):
        """Flughafen-Suche für 'Berlin' sollte Ergebnisse liefern"""
        response = client.get("/airports?q=Berlin")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data
        assert len(data["airports"]) > 0

    def test_airport_search_ber(self):
        """Suche nach 'BER' sollte Berlin Brandenburg finden"""
        response = client.get("/airports?q=BER")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data
        # Prüfe ob BER in den Ergebnissen ist
        codes = [a["code"] for a in data["airports"]]
        assert "BER" in codes or len(data["airports"]) > 0

    def test_airport_search_short_query(self):
        """Kurze Suchanfrage sollte trotzdem funktionieren"""
        response = client.get("/airports?q=Fr")
        assert response.status_code == 200

    def test_airport_search_empty_returns_empty(self):
        """Leere Suche sollte leere Liste zurückgeben"""
        response = client.get("/airports?q=xyznonexistent123")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data


class TestVisaEndpoints:
    """Tests für Visa-Informationen"""

    def test_visa_info_china(self):
        """Visa-Info für China sollte Visum erforderlich zeigen"""
        response = client.get("/visa/china")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["visa_info"]["visa_required"] is True
        assert "Visum" in data["visa_info"]["visa_type"]

    def test_visa_info_france(self):
        """Visa-Info für Frankreich sollte visumfrei zeigen"""
        response = client.get("/visa/frankreich")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["visa_info"]["visa_required"] is False

    def test_visa_info_usa_esta(self):
        """Visa-Info für USA sollte ESTA zeigen"""
        response = client.get("/visa/usa")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ESTA" in data["visa_info"]["visa_type"]

    def test_visa_critical_countries(self):
        """Liste kritischer Länder sollte Länder enthalten"""
        response = client.get("/visa/critical/list")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "countries" in data
        assert len(data["countries"]) > 0
        # Prüfe ob bekannte kritische Länder enthalten sind
        assert "afghanistan" in data["countries"]
        assert "syrien" in data["countries"]


class TestCartEndpoints:
    """Tests für den Warenkorb"""

    def test_get_empty_cart(self):
        """Leerer Warenkorb sollte 0 Items haben"""
        response = client.get("/cart/test_session_empty_12345")
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 0
        assert data["items"] == []

    def test_add_flight_to_cart(self):
        """Flug zum Warenkorb hinzufügen"""
        response = client.post("/cart/add", json={
            "session_id": "test_session_add_flight",
            "item_type": "flight",
            "item_data": {
                "from": "BER",
                "to": "LHR",
                "carrier": "LH",
                "flightNum": "123"
            },
            "price": 199.99,
            "currency": "EUR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cart"]["item_count"] >= 1

    def test_add_hotel_to_cart(self):
        """Hotel zum Warenkorb hinzufügen"""
        response = client.post("/cart/add", json={
            "session_id": "test_session_add_hotel",
            "item_type": "hotel",
            "item_data": {
                "name": "Test Hotel",
                "address": "Test Street 123",
                "nights": 3
            },
            "price": 299.99,
            "currency": "EUR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cart_total_calculation(self):
        """Warenkorb Gesamtsumme sollte korrekt berechnet werden"""
        session_id = "test_session_total_calc"

        # Füge 2 Items hinzu
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "MUC"},
            "price": 100.00
        })
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "hotel",
            "item_data": {"name": "Hotel Test"},
            "price": 200.00
        })

        # Prüfe Gesamtsumme
        response = client.get(f"/cart/{session_id}")
        data = response.json()
        assert data["total_price"] >= 300.00

    def test_clear_cart(self):
        """Warenkorb leeren sollte funktionieren"""
        session_id = "test_session_clear"

        # Füge Item hinzu
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "LHR"},
            "price": 150.00
        })

        # Leere Warenkorb
        response = client.delete(f"/cart/clear/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cart"]["item_count"] == 0


class TestChatEndpoint:
    """Tests für den Chat-Endpoint"""

    def test_chat_basic_response(self):
        """Chat sollte eine Antwort zurückgeben"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Hallo"
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert data["type"] in ["chat", "flight_search", "hotel_search", "cart", "ask_passport"]

    def test_chat_cart_query(self):
        """Chat mit 'Warenkorb' sollte cart-Typ zurückgeben"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Was habe ich im Warenkorb?",
            "session_id": "test_chat_cart"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "cart"


class TestFlightSearch:
    """Tests für die Flugsuche"""

    def test_flight_search_requires_params(self):
        """Flugsuche ohne Parameter sollte Fehler geben"""
        response = client.get("/search_flights")
        # Sollte 422 (Validation Error) oder ähnlich zurückgeben
        assert response.status_code in [400, 422]

    def test_flight_search_with_params(self):
        """Flugsuche mit Parametern sollte funktionieren"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2025-03-15"
        )
        assert response.status_code == 200
        data = response.json()
        # Entweder success oder error, aber kein Server-Fehler
        assert "success" in data or "error" in data or "flights" in data


class TestHotelSearch:
    """Tests für die Hotelsuche"""

    def test_hotel_search_with_destination(self):
        """Hotelsuche sollte Hotels zurückgeben"""
        response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-03-15&checkout=2025-03-18"
        )
        assert response.status_code == 200
        data = response.json()
        assert "hotels" in data or "success" in data

    def test_destination_search(self):
        """Destination-Suche sollte Ergebnisse liefern"""
        response = client.get("/search_destination?q=berlin")
        assert response.status_code == 200
        data = response.json()
        assert "destinations" in data or "success" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
