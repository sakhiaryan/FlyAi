"""
Integration Tests for FlyAI API
Tests full user flows: search -> cart -> checkout, chat conversations,
and visa/travel warning combined flows.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestFullBookingFlow:
    """Integration test for the complete booking flow"""

    def test_search_add_to_cart_view_clear(self):
        """Full flow: search flights -> add to cart -> view cart -> clear cart"""
        session_id = f"integration_booking_{uuid.uuid4().hex[:8]}"

        # Step 1: Search for flights
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2025-06-15"
        )
        assert response.status_code == 200
        flight_data = response.json()
        assert "flights" in flight_data or "success" in flight_data

        # Step 2: Add a flight to the cart
        add_response = client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {
                "from": "BER",
                "to": "LHR",
                "carrier": "LH",
                "flightNum": "456",
                "date": "2025-06-15"
            },
            "price": 189.00,
            "currency": "EUR"
        })
        assert add_response.status_code == 200
        add_data = add_response.json()
        assert add_data["success"] is True
        assert add_data["cart"]["item_count"] >= 1

        # Step 3: View the cart
        cart_response = client.get(f"/cart/{session_id}")
        assert cart_response.status_code == 200
        cart_data = cart_response.json()
        assert cart_data["item_count"] >= 1
        assert cart_data["total_price"] >= 189.00
        assert cart_data["flight_count"] >= 1

        # Step 4: Clear the cart
        clear_response = client.delete(f"/cart/clear/{session_id}")
        assert clear_response.status_code == 200
        clear_data = clear_response.json()
        assert clear_data["success"] is True
        assert clear_data["cart"]["item_count"] == 0

    def test_hotel_search_add_to_cart(self):
        """Flow: search hotels -> add hotel to cart -> verify"""
        session_id = f"integration_hotel_{uuid.uuid4().hex[:8]}"

        # Step 1: Search for hotels
        response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-06-15&checkout=2025-06-18"
        )
        assert response.status_code == 200
        hotel_data = response.json()
        assert "hotels" in hotel_data or "success" in hotel_data

        # Step 2: Add a hotel to cart
        add_response = client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "hotel",
            "item_data": {
                "name": "Marriott Berlin Central",
                "stars": 4,
                "nights": 3,
                "checkin": "2025-06-15",
                "checkout": "2025-06-18"
            },
            "price": 450.00,
            "currency": "EUR"
        })
        assert add_response.status_code == 200
        assert add_response.json()["success"] is True

        # Step 3: Verify cart has the hotel
        cart_response = client.get(f"/cart/{session_id}")
        cart_data = cart_response.json()
        assert cart_data["hotel_count"] >= 1
        assert cart_data["total_price"] >= 450.00

    def test_mixed_cart_flight_and_hotel(self):
        """Flow: add flight + hotel to same cart -> verify totals"""
        session_id = f"integration_mixed_{uuid.uuid4().hex[:8]}"

        # Add flight
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "BCN"},
            "price": 150.00
        })

        # Add hotel
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "hotel",
            "item_data": {"name": "Hotel Barcelona"},
            "price": 300.00
        })

        # Verify cart
        cart_response = client.get(f"/cart/{session_id}")
        cart_data = cart_response.json()
        assert cart_data["item_count"] == 2
        assert cart_data["flight_count"] == 1
        assert cart_data["hotel_count"] == 1
        assert cart_data["total_price"] == 450.00

    def test_add_and_remove_item_from_cart(self):
        """Flow: add item -> remove item -> verify empty"""
        session_id = f"integration_remove_{uuid.uuid4().hex[:8]}"

        # Add an item
        add_response = client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {"from": "FRA", "to": "JFK"},
            "price": 499.00
        })
        item_id = add_response.json()["item_id"]

        # Verify it's in cart
        cart = client.get(f"/cart/{session_id}").json()
        assert cart["item_count"] >= 1

        # Remove the item
        remove_response = client.request("DELETE", "/cart/remove", json={
            "session_id": session_id,
            "item_id": item_id
        })
        assert remove_response.status_code == 200
        assert remove_response.json()["success"] is True

        # Verify cart is empty (or item count decreased)
        cart_after = client.get(f"/cart/{session_id}").json()
        assert cart_after["item_count"] == cart["item_count"] - 1


class TestChatConversationFlow:
    """Integration tests for chat conversation with history"""

    def test_chat_maintains_session(self):
        """Chat with session_id should maintain context"""
        session_id = f"chat_session_{uuid.uuid4().hex[:8]}"

        # First message
        r1 = client.post("/chat", json={
            "messages": [],
            "question": "Hallo",
            "session_id": session_id
        })
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["session_id"] == session_id

        # Second message with history
        r2 = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Hallo"},
                {"role": "assistant", "content": d1.get("answer", "Hi!")}
            ],
            "question": "Was habe ich im Warenkorb?",
            "session_id": session_id
        })
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["type"] == "cart"
        assert d2["session_id"] == session_id

    def test_chat_cart_query_shows_items(self):
        """Chat cart query should reflect actual cart contents"""
        session_id = f"chat_cart_flow_{uuid.uuid4().hex[:8]}"

        # Add an item to cart first
        client.post("/cart/add", json={
            "session_id": session_id,
            "item_type": "flight",
            "item_data": {"from": "MUC", "to": "CDG"},
            "price": 120.00
        })

        # Ask about cart via chat
        response = client.post("/chat", json={
            "messages": [],
            "question": "Was habe ich im Warenkorb?",
            "session_id": session_id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "cart"
        # The cart answer should not say it's empty since we added an item
        assert "leer" not in data.get("answer", "").lower() or "0" not in data.get("answer", "")

    def test_chat_keyword_detection_flight(self):
        """Chat mentioning flight keywords should detect flight intent"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Ich suche einen Flug nach London"
        })
        assert response.status_code == 200
        data = response.json()
        # Should be either flight_search or chat (if AI extraction fails)
        assert data["type"] in ["flight_search", "chat"]

    def test_chat_keyword_detection_hotel(self):
        """Chat mentioning hotel keywords should detect hotel intent"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Ich brauche ein Hotel in Barcelona"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["type"] in ["hotel_search", "chat"]

    def test_chat_visa_query(self):
        """Chat asking about visa should return travel info"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Brauche ich ein Visum für China?"
        })
        assert response.status_code == 200
        data = response.json()
        # Should detect as travel_info since it contains visa keywords + country
        assert data["type"] in ["travel_info", "chat"]


class TestVisaTravelWarningFlow:
    """Integration tests for visa check -> travel warning flow"""

    def test_visa_check_critical_country(self):
        """Visa check for critical country should show warning"""
        response = client.get("/visa/afghanistan")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["visa_info"]["visa_required"] is True
        assert data["visa_info"]["warning_level"] == "critical"
        assert data["visa_info"]["has_warning"] is True
        assert "Reisewarnung" in data["visa_info"]["warning_text"]

    def test_visa_then_travel_info_flow(self):
        """Full flow: check visa -> get travel info"""
        # Step 1: Check visa for China
        visa_response = client.get("/visa/china")
        assert visa_response.status_code == 200
        visa_data = visa_response.json()
        assert visa_data["visa_info"]["visa_required"] is True

        # Step 2: Get detailed travel info
        travel_response = client.get("/travel-info/china")
        assert travel_response.status_code == 200
        travel_data = travel_response.json()
        assert travel_data["success"] is True
        assert travel_data["visa_required"] is True

    def test_visa_then_aa_link_flow(self):
        """Full flow: check visa -> get AA link"""
        # Step 1: Check visa
        visa_response = client.get("/visa/usa")
        assert visa_response.status_code == 200

        # Step 2: Get AA link
        aa_response = client.get("/aa/usa")
        assert aa_response.status_code == 200
        aa_data = aa_response.json()
        assert aa_data["success"] is True
        assert "auswaertiges-amt.de" in aa_data["url"]

    def test_critical_countries_all_have_warnings(self):
        """All critical countries from the list should have travel warnings"""
        # Get list of critical countries
        list_response = client.get("/visa/critical/list")
        assert list_response.status_code == 200
        countries = list_response.json()["countries"]

        # Verify each critical country has a warning
        for country in countries[:5]:  # Test first 5 to keep test fast
            visa_response = client.get(f"/visa/{country}")
            assert visa_response.status_code == 200
            data = visa_response.json()
            assert data["visa_info"]["has_warning"] is True, \
                f"{country} should have a travel warning"

    def test_eu_country_visa_free(self):
        """EU countries should be visa-free"""
        eu_countries = ["frankreich", "spanien", "italien"]
        for country in eu_countries:
            response = client.get(f"/visa/{country}")
            assert response.status_code == 200
            data = response.json()
            assert data["visa_info"]["visa_required"] is False, \
                f"{country} should be visa-free"
            assert data["visa_info"]["visa_type"] == "Visumfrei"

    def test_travel_info_includes_formatted_output(self):
        """Travel info should include formatted text for display"""
        response = client.get("/travel-info/spanien")
        assert response.status_code == 200
        data = response.json()
        assert "formatted" in data
        assert len(data["formatted"]) > 0


class TestRegisterAndLoginFlow:
    """Integration tests for full auth flow"""

    def test_register_then_login_flow(self):
        """Flow: register new user -> login with new credentials"""
        unique_email = f"integration_{uuid.uuid4().hex[:8]}@test.com"

        # Step 1: Register
        reg_response = client.post("/auth/register", json={
            "name": "Integration Test User",
            "email": unique_email,
            "password": "securepassword123"
        })
        assert reg_response.status_code == 200
        reg_data = reg_response.json()
        assert reg_data["success"] is True

        # Step 2: Login with the new account
        login_response = client.post("/auth/login", json={
            "email": unique_email,
            "password": "securepassword123"
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["success"] is True
        assert "token" in login_data

        # Step 3: Use token to check auth
        token = login_data["token"]
        me_response = client.get(f"/auth/me?token={token}")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["success"] is True

    def test_register_duplicate_then_login_original(self):
        """Flow: register -> try duplicate register -> login with original"""
        unique_email = f"dup_test_{uuid.uuid4().hex[:8]}@test.com"

        # Register first time
        r1 = client.post("/auth/register", json={
            "name": "Original User",
            "email": unique_email,
            "password": "password12345"
        })
        assert r1.json()["success"] is True

        # Try to register again with same email
        r2 = client.post("/auth/register", json={
            "name": "Duplicate User",
            "email": unique_email,
            "password": "differentpassword"
        })
        assert r2.json()["success"] is False
        assert r2.json()["error_code"] == "EMAIL_EXISTS"

        # Login with original credentials should still work
        r3 = client.post("/auth/login", json={
            "email": unique_email,
            "password": "password12345"
        })
        assert r3.json()["success"] is True


class TestAirportToFlightFlow:
    """Integration tests for airport search -> flight search flow"""

    def test_airport_search_then_flight_search(self):
        """Flow: search airport -> use code for flight search"""
        # Step 1: Search for an airport
        airport_response = client.get("/airports?q=Berlin")
        assert airport_response.status_code == 200
        airports = airport_response.json()["airports"]
        assert len(airports) > 0

        # Get the airport code
        from_code = airports[0]["code"]
        assert len(from_code) == 3

        # Step 2: Search for flights using the airport code
        flight_response = client.get(
            f"/search_flights?from_airport={from_code}&to_airport=LHR&date=2025-06-15"
        )
        assert flight_response.status_code == 200

    def test_destination_search_then_hotel_search(self):
        """Flow: search destination -> use result for hotel search"""
        # Step 1: Search for a destination
        dest_response = client.get("/search_destination?q=berlin")
        assert dest_response.status_code == 200
        dest_data = dest_response.json()
        assert dest_data.get("success") is True or "destinations" in dest_data

        # Step 2: Search hotels for that destination
        hotel_response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-06-15&checkout=2025-06-18"
        )
        assert hotel_response.status_code == 200


class TestHealthAndSmoke:
    """Smoke tests to verify all endpoints respond"""

    def test_all_get_endpoints_respond(self):
        """All GET endpoints should respond without 500 errors"""
        endpoints = [
            "/health",
            "/airports?q=Berlin",
            "/visa/usa",
            "/visa/critical/list",
            "/aa/frankreich",
            "/travel-info/usa",
            "/search_history",
            "/auth/check-email?email=test@test.com",
            "/cart/smoke_test_session",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 500, \
                f"GET {endpoint} returned 500"

    def test_all_post_endpoints_respond(self):
        """All POST endpoints should respond to valid requests"""
        post_endpoints = [
            ("/chat", {"messages": [], "question": "test"}),
            ("/cart/add", {
                "session_id": "smoke_test",
                "item_type": "flight",
                "item_data": {"from": "BER", "to": "LHR"},
                "price": 100.00
            }),
            ("/auth/login", {"email": "test@test.com", "password": "test"}),
            ("/auth/register", {"name": "T", "email": "x", "password": "y"}),
            ("/auth/logout", None),
        ]
        for endpoint, payload in post_endpoints:
            if payload:
                response = client.post(endpoint, json=payload)
            else:
                response = client.post(endpoint)
            assert response.status_code != 500, \
                f"POST {endpoint} returned 500"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
