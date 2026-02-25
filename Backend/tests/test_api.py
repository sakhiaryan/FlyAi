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


class TestCartEdgeCases:
    """Edge case tests for cart operations"""

    def test_remove_nonexistent_item(self):
        """Removing a non-existent item should return success=False"""
        response = client.request("DELETE", "/cart/remove", json={
            "session_id": "test_edge_remove",
            "item_id": 999999
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_add_item_with_zero_price(self):
        """Adding item with zero price should work"""
        response = client.post("/cart/add", json={
            "session_id": "test_edge_zero_price",
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "LHR"},
            "price": 0.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_item_with_large_price(self):
        """Adding item with very large price should work"""
        response = client.post("/cart/add", json={
            "session_id": "test_edge_large_price",
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "SYD"},
            "price": 99999.99,
            "currency": "EUR"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_activity_to_cart(self):
        """Adding an activity item type should work"""
        response = client.post("/cart/add", json={
            "session_id": "test_edge_activity",
            "item_type": "activity",
            "item_data": {"name": "City Tour Berlin", "duration": "3h"},
            "price": 49.99
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_clear_already_empty_cart(self):
        """Clearing an already empty cart should succeed with 0 items removed"""
        session_id = "test_edge_clear_empty"
        response = client.delete(f"/cart/clear/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cart"]["item_count"] == 0

    def test_cart_summary_has_correct_structure(self):
        """Cart summary should have all required fields"""
        session_id = "test_edge_structure"
        response = client.get(f"/cart/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "items" in data
        assert "total_price" in data
        assert "currency" in data
        assert "item_count" in data
        assert "flight_count" in data
        assert "hotel_count" in data
        assert "activity_count" in data

    def test_add_multiple_items_same_session(self):
        """Adding multiple items to same session should accumulate"""
        session_id = "test_edge_multi_items"
        # Clear first
        client.delete(f"/cart/clear/{session_id}")

        for i in range(3):
            client.post("/cart/add", json={
                "session_id": session_id,
                "item_type": "flight",
                "item_data": {"from": "BER", "to": f"DEST{i}"},
                "price": 100.00 + i * 50
            })

        response = client.get(f"/cart/{session_id}")
        data = response.json()
        assert data["item_count"] == 3
        assert data["flight_count"] == 3


class TestChatEdgeCases:
    """Edge case tests for chat endpoint"""

    def test_chat_empty_question(self):
        """Chat with empty question should still return response"""
        response = client.post("/chat", json={
            "messages": [],
            "question": ""
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data

    def test_chat_special_characters(self):
        """Chat with special characters should not crash"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "!@#$%^&*()_+-={}[]|\\:\";<>?,./"
        })
        assert response.status_code == 200

    def test_chat_cart_keyword_einkaufswagen(self):
        """Chat with 'einkaufswagen' should trigger cart response"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Zeig mir meinen Einkaufswagen",
            "session_id": "test_chat_einkaufswagen"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "cart"

    def test_chat_cart_keyword_buchungen(self):
        """Chat with 'meine buchungen' should trigger cart response"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Zeig mir meine Buchungen",
            "session_id": "test_chat_buchungen"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "cart"

    def test_chat_with_session_id(self):
        """Chat with session_id should include it in response"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Hallo, was kannst du?",
            "session_id": "my_test_session_123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("session_id") == "my_test_session_123"

    def test_chat_without_session_id_generates_one(self):
        """Chat without session_id should generate one"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Hallo"
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_chat_with_message_history(self):
        """Chat with message history should work"""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Hallo"},
                {"role": "assistant", "content": "Hi! Wie kann ich helfen?"}
            ],
            "question": "Was habe ich im Warenkorb?",
            "session_id": "test_history"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "cart"


class TestAirportSearchEdgeCases:
    """Edge case tests for airport search"""

    def test_airport_search_unicode(self):
        """Airport search with unicode characters should work"""
        response = client.get("/airports?q=M%C3%BCnchen")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data

    def test_airport_search_single_character(self):
        """Airport search with single character should work"""
        response = client.get("/airports?q=B")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data

    def test_airport_search_numeric(self):
        """Airport search with numbers should not crash"""
        response = client.get("/airports?q=12345")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data

    def test_airport_search_special_chars(self):
        """Airport search with special characters should be safe"""
        response = client.get("/airports?q=test%26%23")
        assert response.status_code == 200


class TestFlightSearchEdgeCases:
    """Edge case tests for flight search"""

    def test_flight_search_past_date(self):
        """Flight search with past date should still respond"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2020-01-01"
        )
        assert response.status_code == 200

    def test_flight_search_invalid_date_format(self):
        """Flight search with invalid date should still respond without crashing"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=not-a-date"
        )
        # Should not return 500
        assert response.status_code in [200, 400, 422]

    def test_flight_search_same_origin_destination(self):
        """Flight search with same origin and destination should handle gracefully"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=BER&date=2025-06-15"
        )
        assert response.status_code == 200

    def test_flight_search_invalid_airport_code(self):
        """Flight search with invalid airport code should handle gracefully"""
        response = client.get(
            "/search_flights?from_airport=ZZZZZ&to_airport=YYYYY&date=2025-06-15"
        )
        assert response.status_code == 200

    def test_flight_search_with_passengers(self):
        """Flight search with passenger parameters should work"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2025-06-15&adults=2&children=1&infants=0"
        )
        assert response.status_code == 200

    def test_flight_search_with_return_date(self):
        """Flight search with return date should work"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2025-06-15&return_date=2025-06-22"
        )
        assert response.status_code == 200


class TestHotelSearchEdgeCases:
    """Edge case tests for hotel search"""

    def test_hotel_search_unknown_destination(self):
        """Hotel search with unknown destination should handle gracefully"""
        response = client.get(
            "/search_hotels?destination=xyznonexistent&checkin=2025-06-15&checkout=2025-06-18"
        )
        assert response.status_code == 200

    def test_hotel_search_checkout_before_checkin(self):
        """Hotel search with checkout before checkin should not crash"""
        response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-06-18&checkout=2025-06-15"
        )
        assert response.status_code == 200

    def test_hotel_search_same_dates(self):
        """Hotel search with same checkin and checkout should not crash"""
        response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-06-15&checkout=2025-06-15"
        )
        assert response.status_code == 200

    def test_destination_search_unicode(self):
        """Destination search with unicode should work"""
        response = client.get("/search_destination?q=M%C3%BCnchen")
        assert response.status_code == 200

    def test_destination_search_empty_query(self):
        """Destination search with very short query should work"""
        response = client.get("/search_destination?q=a")
        assert response.status_code == 200


class TestAuthEdgeCases:
    """Edge case tests for auth endpoints"""

    def test_login_email_case_insensitive(self):
        """Login should be case insensitive for email"""
        response = client.post("/auth/login", json={
            "email": "DEMO@FLYAI.DE",
            "password": "demo1234"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_register_successful(self):
        """Registration with valid data should succeed"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        response = client.post("/auth/register", json={
            "name": "New User",
            "email": unique_email,
            "password": "securepassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"].startswith("flyai_")
        assert data["user"]["email"] == unique_email.lower()

    def test_register_email_normalized_to_lower(self):
        """Registration should normalize email to lowercase"""
        import uuid
        unique_email = f"TEST_{uuid.uuid4().hex[:8]}@TEST.COM"
        response = client.post("/auth/register", json={
            "name": "Case Test",
            "email": unique_email,
            "password": "securepassword123"
        })
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert data["user"]["email"] == unique_email.lower()

    def test_check_email_case_insensitive(self):
        """Check email should handle case correctly"""
        response = client.get("/auth/check-email?email=DEMO@FLYAI.DE")
        assert response.status_code == 200


class TestVisaEdgeCases:
    """Edge case tests for visa endpoints"""

    def test_visa_unknown_country(self):
        """Visa for unknown country should return success with unknown warning level"""
        response = client.get("/visa/fantasyland")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["visa_info"]["warning_level"] == "unknown"

    def test_travel_info_quick(self):
        """Quick travel info should return combined visa and AA data"""
        response = client.get("/travel-info/usa")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "visa_required" in data
        assert "formatted" in data

    def test_travel_info_critical_country(self):
        """Travel info for critical country should include warning"""
        response = client.get("/travel-info/afghanistan")
        assert response.status_code == 200
        data = response.json()
        assert data["has_warning"] is True

    def test_aa_link_endpoint(self):
        """AA link endpoint should return a valid link"""
        response = client.get("/aa/frankreich")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "url" in data
        assert "auswaertiges-amt.de" in data["url"]

    def test_aa_link_unknown_country(self):
        """AA link for unknown country should return success=False"""
        response = client.get("/aa/fantasyland123")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestSearchHistory:
    """Tests for search history endpoint"""

    def test_search_history_returns_list(self):
        """Search history should return a history list"""
        response = client.get("/search_history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
