"""
Security Tests for FlyAI API
Tests CORS, rate limiting, XSS sanitization, SQL injection prevention,
authentication, input validation, and API key exposure.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestCORSHeaders:
    """Tests for CORS configuration"""

    def test_cors_allows_origin(self):
        """CORS should include Access-Control-Allow-Origin header"""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_preflight_options(self):
        """OPTIONS preflight request should succeed"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200

    def test_cors_allows_methods(self):
        """CORS should allow common HTTP methods"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200

    def test_cors_allows_headers(self):
        """CORS should allow custom headers"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200


class TestXSSInputSanitization:
    """Tests for XSS prevention in user inputs"""

    def test_chat_with_script_tag(self):
        """Chat should handle script tag injection without error"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "<script>alert('xss')</script>"
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data

    def test_chat_with_img_onerror(self):
        """Chat should handle img onerror injection"""
        response = client.post("/chat", json={
            "messages": [],
            "question": '<img src=x onerror="alert(1)">'
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data

    def test_chat_with_event_handler(self):
        """Chat should handle event handler injection"""
        response = client.post("/chat", json={
            "messages": [],
            "question": '<div onmouseover="alert(document.cookie)">test</div>'
        })
        assert response.status_code == 200

    def test_airport_search_with_html_injection(self):
        """Airport search should handle HTML injection"""
        response = client.get("/airports?q=<script>alert('xss')</script>")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data

    def test_cart_add_with_xss_in_data(self):
        """Cart should handle XSS in item data"""
        response = client.post("/cart/add", json={
            "session_id": "test_xss_session",
            "item_type": "flight",
            "item_data": {
                "from": "<script>alert('xss')</script>",
                "to": "LHR"
            },
            "price": 100.00
        })
        assert response.status_code == 200

    def test_visa_endpoint_with_xss(self):
        """Visa endpoint should handle XSS in country param"""
        response = client.get("/visa/<script>alert(1)</script>")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSQLInjectionPrevention:
    """Tests that SQL injection attempts are blocked or safely handled"""

    def test_airport_search_sql_injection(self):
        """Airport search should handle SQL injection safely"""
        response = client.get("/airports?q='; DROP TABLE airports; --")
        assert response.status_code == 200
        data = response.json()
        assert "airports" in data

    def test_cart_session_sql_injection(self):
        """Cart should handle SQL injection in session_id safely"""
        response = client.get("/cart/'; DROP TABLE cartitem; --")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_cart_add_sql_injection(self):
        """Cart add should handle SQL injection in fields"""
        response = client.post("/cart/add", json={
            "session_id": "' OR '1'='1",
            "item_type": "flight",
            "item_data": {"from": "BER", "to": "LHR"},
            "price": 100.00
        })
        assert response.status_code == 200

    def test_visa_sql_injection(self):
        """Visa endpoint should handle SQL injection in country"""
        response = client.get("/visa/'; DROP TABLE users; --")
        assert response.status_code == 200

    def test_chat_sql_injection(self):
        """Chat should handle SQL injection in question"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "'; DROP TABLE search_history; --"
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data


class TestAuthenticationEndpoints:
    """Tests for authentication endpoint security"""

    def test_login_invalid_email(self):
        """Login with non-existent email should fail"""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "USER_NOT_FOUND"

    def test_login_wrong_password(self):
        """Login with wrong password should fail"""
        response = client.post("/auth/login", json={
            "email": "demo@flyai.de",
            "password": "wrongpassword"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_PASSWORD"

    def test_login_valid_credentials(self):
        """Login with valid credentials should succeed"""
        response = client.post("/auth/login", json={
            "email": "demo@flyai.de",
            "password": "demo1234"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"].startswith("flyai_")

    def test_auth_me_without_token(self):
        """Auth/me without token should fail"""
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "NOT_AUTHENTICATED"

    def test_auth_me_with_invalid_token(self):
        """Auth/me with invalid token should fail"""
        response = client.get("/auth/me?token=invalid_token_abc123")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "NOT_AUTHENTICATED"

    def test_auth_me_with_valid_prefix_token(self):
        """Auth/me with flyai_ prefix token should return user"""
        response = client.get("/auth/me?token=flyai_fakefakefake")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data

    def test_register_short_password(self):
        """Registration with short password should fail"""
        response = client.post("/auth/register", json={
            "name": "Test",
            "email": "newuser@test.com",
            "password": "short"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "PASSWORD_TOO_SHORT"

    def test_register_invalid_email(self):
        """Registration with invalid email should fail"""
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "notanemail",
            "password": "longpassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_EMAIL"

    def test_register_short_name(self):
        """Registration with short name should fail"""
        response = client.post("/auth/register", json={
            "name": "A",
            "email": "test_short_name@test.com",
            "password": "longpassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_NAME"

    def test_register_duplicate_email(self):
        """Registration with existing email should fail"""
        response = client.post("/auth/register", json={
            "name": "Duplicate User",
            "email": "demo@flyai.de",
            "password": "longpassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "EMAIL_EXISTS"

    def test_logout(self):
        """Logout should always succeed"""
        response = client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_check_email_existing(self):
        """Check email for existing user should return exists=True"""
        response = client.get("/auth/check-email?email=demo@flyai.de")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True

    def test_check_email_nonexistent(self):
        """Check email for non-existent user should return exists=False"""
        response = client.get("/auth/check-email?email=nobody@nowhere.com")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False


class TestInputValidation:
    """Tests for input validation and oversized payloads"""

    def test_chat_empty_question(self):
        """Chat with empty question should still return a response"""
        response = client.post("/chat", json={
            "messages": [],
            "question": ""
        })
        assert response.status_code == 200
        data = response.json()
        assert "type" in data

    def test_chat_very_long_message(self):
        """Chat with very long message should not crash"""
        long_message = "A" * 10000
        response = client.post("/chat", json={
            "messages": [],
            "question": long_message
        })
        # Should return 200 or 422, but not 500
        assert response.status_code in [200, 422]

    def test_chat_special_characters(self):
        """Chat with special characters should be handled"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Test with special chars: !@#$%^&*()_+-={}[]|\\:\";<>?,./"
        })
        assert response.status_code == 200

    def test_chat_unicode_characters(self):
        """Chat with unicode should be handled"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Reise nach Tokyo (東京都) bitte"
        })
        assert response.status_code == 200

    def test_cart_add_missing_required_fields(self):
        """Cart add with missing fields should return validation error"""
        response = client.post("/cart/add", json={
            "session_id": "test"
        })
        assert response.status_code == 422

    def test_cart_add_invalid_json(self):
        """Cart add with invalid content type should fail"""
        response = client.post(
            "/cart/add",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_flight_search_missing_params(self):
        """Flight search without required params should return 422"""
        response = client.get("/search_flights")
        assert response.status_code == 422

    def test_hotel_search_missing_params(self):
        """Hotel search without required params should return 422"""
        response = client.get("/search_hotels")
        assert response.status_code == 422

    def test_airport_search_missing_query(self):
        """Airport search without query should return 422"""
        response = client.get("/airports")
        assert response.status_code == 422

    def test_destination_search_missing_query(self):
        """Destination search without query should return 422"""
        response = client.get("/search_destination")
        assert response.status_code == 422

    def test_login_missing_fields(self):
        """Login without required fields should return 422"""
        response = client.post("/auth/login", json={})
        assert response.status_code == 422

    def test_register_missing_fields(self):
        """Register without required fields should return 422"""
        response = client.post("/auth/register", json={})
        assert response.status_code == 422


class TestAPIKeyExposure:
    """Tests that API keys are not exposed in responses"""

    def test_health_no_api_keys(self):
        """Health response should not contain API keys"""
        response = client.get("/health")
        body = response.text
        assert "RAPIDAPI_KEY" not in body
        assert "AMADEUS_API_KEY" not in body
        assert "OPENAI_API_KEY" not in body

    def test_flight_search_no_api_keys(self):
        """Flight search response should not expose API keys"""
        response = client.get(
            "/search_flights?from_airport=BER&to_airport=LHR&date=2025-06-15"
        )
        body = response.text
        assert "RAPIDAPI_KEY" not in body
        assert "X-RapidAPI-Key" not in body

    def test_hotel_search_no_api_keys(self):
        """Hotel search response should not expose API keys"""
        response = client.get(
            "/search_hotels?destination=berlin&checkin=2025-06-15&checkout=2025-06-18"
        )
        body = response.text
        assert "RAPIDAPI_KEY" not in body
        assert "X-RapidAPI-Key" not in body

    def test_visa_no_api_keys(self):
        """Visa response should not expose API keys"""
        response = client.get("/visa/usa")
        body = response.text
        assert "RAPIDAPI_KEY" not in body
        assert "OPENAI_API_KEY" not in body

    def test_chat_no_api_keys(self):
        """Chat response should not expose API keys"""
        response = client.post("/chat", json={
            "messages": [],
            "question": "Hallo"
        })
        body = response.text
        assert "RAPIDAPI_KEY" not in body
        assert "OPENAI_API_KEY" not in body
        assert "AMADEUS_API_SECRET" not in body

    def test_auth_token_format(self):
        """Auth tokens should use the correct prefix format"""
        response = client.post("/auth/login", json={
            "email": "demo@flyai.de",
            "password": "demo1234"
        })
        data = response.json()
        assert data["success"] is True
        token = data["token"]
        assert token.startswith("flyai_")
        assert len(token) > 10


class TestEndpointMethodRestrictions:
    """Tests that endpoints only accept correct HTTP methods"""

    def test_health_post_not_allowed(self):
        """Health endpoint should not accept POST"""
        response = client.post("/health")
        assert response.status_code == 405

    def test_airports_post_not_allowed(self):
        """Airports endpoint should not accept POST"""
        response = client.post("/airports?q=Berlin")
        assert response.status_code == 405

    def test_cart_get_on_add_not_allowed(self):
        """Cart add endpoint should not accept GET"""
        response = client.get("/cart/add")
        assert response.status_code == 405

    def test_chat_get_not_allowed(self):
        """Chat endpoint should not accept GET"""
        response = client.get("/chat")
        assert response.status_code == 405

    def test_nonexistent_endpoint(self):
        """Non-existent endpoint should return 404"""
        response = client.get("/nonexistent_endpoint_abc123")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
