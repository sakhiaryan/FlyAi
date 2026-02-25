# FlyAI QA Test Report

**Datum:** 2026-02-25
**Tester:** QA-Tester Agent (Automated)
**Backend:** http://127.0.0.1:8000
**Environment:** macOS Darwin 25.3.0, Python Backend (uvicorn)

---

## 1. Endpoint Tests

### 1.1 Health Check

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/health` | GET | PASS | 200 | 0.004s | Returns `{"status":"ok"}` |

### 1.2 Airport Search

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/airports?q=Berlin` | GET | WARN | 200 | 0.120s | Returns 3 airports (BER, JFK, LHR) - see Bug #1 |
| `/airports?q=London` | GET | WARN | 200 | 1.069s | Returns same 3 airports regardless of query - see Bug #1 |
| `/airports?q=New` | GET | WARN | 200 | 0.091s | Returns same 3 airports regardless of query - see Bug #1 |
| `/airports?q=xyz_nonexistent` | GET | WARN | 200 | 0.091s | Returns same 3 airports for non-existent query - see Bug #1 |

### 1.3 Flight Search

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/search_flights?from_airport=BER&to_airport=LHR&date=2026-04-15&adults=1` | GET | PASS | 200 | 0.317s | Returns 10 flights, prices 59-124 EUR, mock/demo data |

### 1.4 Hotel Search

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/search_destination?q=berlin` | GET | PASS | 200 | 0.130s | Returns destination entity with mock source |
| `/search_hotels?destination=berlin&checkin=2026-04-15&checkout=2026-04-18&adults=2` | GET | PASS | 200 | 0.284s | Returns 13 hotels, prices 53-330 EUR/night, mock data |

### 1.5 Chat / AI

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `POST /chat` (Greeting) | POST | PASS | 200 | 1.752s | AI responds with greeting and suggested replies |
| `POST /chat` (Japan travel) | POST | PASS | 200 | 2.975s | Detects country "japan", includes AA link |
| `POST /chat` (Cart query) | POST | PASS | 200 | 0.003s | Returns empty cart response (type: "cart") |

### 1.6 Visa Information

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/visa/japan` | GET | PASS | 200 | 0.002s | Visa-free for German citizens |
| `/visa/china` | GET | PASS | 200 | 0.001s | Visa required, high warning level |
| `/visa/frankreich` | GET | PASS | 200 | 0.001s | Visa-free (EU) |
| `/visa/usa` | GET | PASS | 200 | 0.001s | ESTA required - see Bug #2 |
| `/visa/critical/list` | GET | PASS | 200 | 0.001s | Returns 18 critical countries |

### 1.7 Travel Info & Auswaertiges Amt

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `/travel-info/thailand` | GET | PASS | 200 | 0.002s | Visa-free, includes AA URL |
| `/aa/japan` | GET | PASS | 200 | 0.001s | Returns AA URL for Japan |

### 1.8 Cart (Full CRUD Flow)

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `POST /cart/add` (flight) | POST | PASS | 200 | 0.008s | Flight added, total 599.99 EUR |
| `GET /cart/qa-test-cart` (1 item) | GET | PASS | 200 | 0.002s | Shows 1 flight in cart |
| `POST /cart/add` (hotel) | POST | PASS | 200 | 0.003s | Hotel added, total 1049.99 EUR |
| `GET /cart/qa-test-cart` (2 items) | GET | PASS | 200 | 0.002s | Shows flight + hotel, correct total |
| `DELETE /cart/clear/qa-test-cart` | DELETE | PASS | 200 | 0.003s | Cart cleared, 2 items removed |

### 1.9 Authentication

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `POST /auth/login` (valid) | POST | PASS | 200 | 0.001s | Returns user + token |
| `POST /auth/login` (invalid user) | POST | WARN | 200 | 0.001s | Returns error but HTTP 200 - see Bug #3 |
| `POST /auth/login` (wrong password) | POST | WARN | 200 | 0.001s | Returns error but HTTP 200 - see Bug #3 |
| `POST /auth/register` | POST | PASS | 200 | 0.001s | User created with token |
| `GET /auth/check-email?email=demo@flyai.de` | GET | PASS | 200 | 0.001s | Returns `{"exists": true}` |

### 1.10 Search History

| Endpoint | Method | Status | HTTP Code | Response Time | Notes |
|----------|--------|--------|-----------|---------------|-------|
| `GET /search_history` | GET | PASS | 200 | 0.006s | Returns 20 recent searches |

---

## 2. Security Tests

| Test | Status | HTTP Code | Response Time | Notes |
|------|--------|-----------|---------------|-------|
| **XSS Injection** (`<script>alert(1)</script>`) | PASS | 200 | 2.176s | AI gracefully handles script tag, no reflection of raw HTML |
| **SQL Injection** (`Berlin' OR 1=1 --`) | PASS | 200 | 0.091s | No SQL error, returns normal response (static airport list) |
| **Long Input** (3000 chars) | PASS | 422 | 0.003s | Properly rejected: "question must be at most 2000 characters" |
| **Invalid Flight Data** (empty params) | PASS | 400 | 0.002s | Returns `"from_airport is required"` |
| **Invalid Hotel Data** (empty destination) | PASS | 400 | 0.002s | Returns `"destination is required"` |

### 2.1 Security Headers

| Header | Present | Value | Status |
|--------|---------|-------|--------|
| `X-Content-Type-Options` | Yes | `nosniff` | PASS |
| `X-Frame-Options` | Yes | `DENY` | PASS |
| `X-XSS-Protection` | Yes | `1; mode=block` | PASS |
| `Referrer-Policy` | Yes | `strict-origin-when-cross-origin` | PASS |
| `Permissions-Policy` | Yes | `camera=(), microphone=(), geolocation=()` | PASS |
| `Cache-Control` | Yes | `no-store, no-cache, must-revalidate` | PASS |
| `Content-Security-Policy` | No | - | WARN - CSP header missing |
| `Strict-Transport-Security` | No | - | WARN - HSTS header missing (relevant for production) |

### 2.2 CORS Configuration

| Test | Result | Status |
|------|--------|--------|
| Preflight (OPTIONS) from `evil.com` | 400 Bad Request, no `Access-Control-Allow-Origin` returned | PASS |
| `access-control-allow-credentials` | `true` | WARN - credentials allowed |
| `access-control-allow-methods` | `GET, POST, DELETE` | PASS |
| `access-control-max-age` | `600` | PASS |

---

## 3. Bugs Found

### Bug #1: Airport Search Returns Static List (Severity: MEDIUM)
- **Endpoint:** `GET /airports?q=<query>`
- **Issue:** Airport search returns the same 3 airports (BER, JFK, LHR) regardless of query string. Searching for "Berlin", "London", "New", "xyz_nonexistent", and even a SQL injection string all return identical results.
- **Expected:** Results should be filtered based on the query parameter.
- **Impact:** Users cannot search for specific airports. The search functionality is effectively non-functional as a filter.
- **Note:** This may be intentional if using a static/fallback demo list, but the endpoint should still filter results.

### Bug #2: Visa Endpoint Displays "Usa" Instead of "USA" (Severity: LOW)
- **Endpoint:** `GET /visa/usa`
- **Issue:** The `country` field in the response shows `"Usa"` (title case) instead of `"USA"` (uppercase abbreviation).
- **Expected:** Country name should be `"USA"` for proper display.
- **Impact:** Minor display issue in frontend.

### Bug #3: Auth Login Returns HTTP 200 for Failed Authentication (Severity: MEDIUM)
- **Endpoint:** `POST /auth/login`
- **Issue:** Failed login attempts (wrong email or wrong password) return HTTP 200 instead of HTTP 401 (Unauthorized).
- **Response for wrong user:** `{"success":false,"error":"Benutzer nicht gefunden","error_code":"USER_NOT_FOUND"}` with HTTP 200
- **Response for wrong password:** `{"success":false,"error":"Falsches Passwort","error_code":"INVALID_PASSWORD"}` with HTTP 200
- **Expected:** Failed authentication should return HTTP 401.
- **Impact:** API clients relying on HTTP status codes for error handling may not properly detect authentication failures.
- **Additional Note:** Error messages distinguish between "user not found" and "invalid password", which could allow user enumeration. Consider returning a generic "Invalid credentials" message for both cases.

### Bug #4: Missing Content-Security-Policy Header (Severity: LOW)
- **Endpoint:** All endpoints
- **Issue:** No `Content-Security-Policy` header is set in responses.
- **Impact:** Reduces protection against XSS and data injection attacks in production.

### Bug #5: Missing Strict-Transport-Security Header (Severity: LOW)
- **Endpoint:** All endpoints
- **Issue:** No `Strict-Transport-Security` (HSTS) header is set.
- **Impact:** Not critical for local development, but should be added for production deployment.

---

## 4. Performance Summary

| Category | Avg Response Time | Fastest | Slowest |
|----------|-------------------|---------|---------|
| Health | 0.004s | 0.004s | 0.004s |
| Airport Search | 0.427s | 0.091s | 1.069s |
| Flight Search | 0.317s | 0.317s | 0.317s |
| Hotel Search | 0.207s | 0.130s | 0.284s |
| Chat (AI) | 1.577s | 0.003s (cart) | 2.975s (travel) |
| Visa | 0.001s | 0.001s | 0.002s |
| Travel Info | 0.002s | 0.001s | 0.002s |
| Cart Operations | 0.004s | 0.002s | 0.008s |
| Auth | 0.001s | 0.001s | 0.001s |
| Search History | 0.006s | 0.006s | 0.006s |

**Notes:**
- All non-AI endpoints respond in under 1.1s (most under 10ms).
- AI chat responses take 1.7-3.0s, which is expected for LLM-based responses.
- Airport "London" query took 1.069s, significantly slower than others (0.09-0.12s).

---

## 5. Test Summary

| Category | Total | Passed | Warnings | Failed |
|----------|-------|--------|----------|--------|
| Health | 1 | 1 | 0 | 0 |
| Airport Search | 4 | 0 | 4 | 0 |
| Flight Search | 1 | 1 | 0 | 0 |
| Hotel Search | 2 | 2 | 0 | 0 |
| Chat / AI | 3 | 3 | 0 | 0 |
| Visa | 5 | 5 | 0 | 0 |
| Travel Info | 2 | 2 | 0 | 0 |
| Cart (CRUD) | 5 | 5 | 0 | 0 |
| Auth | 5 | 3 | 2 | 0 |
| Search History | 1 | 1 | 0 | 0 |
| Security Tests | 5 | 5 | 0 | 0 |
| Security Headers | 8 | 6 | 2 | 0 |
| CORS | 4 | 3 | 1 | 0 |
| **TOTAL** | **46** | **37** | **9** | **0** |

### Overall Result: 37/46 PASS, 9 WARN, 0 FAIL

**Summary:**
- All core endpoints are functional and return valid responses.
- No hard failures - all endpoints return responses within expected timeframes.
- 5 bugs identified (0 critical, 2 medium, 3 low severity).
- Security posture is generally good: XSS handled, SQL injection not exploitable, input length validation works, proper security headers present.
- Main areas for improvement: airport search filtering (Bug #1), proper HTTP status codes for auth errors (Bug #3), and additional security headers (CSP, HSTS).
- Flight and hotel data comes from mock/demo sources, which is expected for development.

---

*Report generated automatically by QA-Tester Agent on 2026-02-25*
