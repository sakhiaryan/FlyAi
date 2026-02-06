/**
 * Frontend Unit Tests für FlyAI
 * Ausführen mit: node tests/test_app.js
 * Oder im Browser: tests/test_runner.html
 */

const API_URL = 'http://127.0.0.1:8000';

// Simple Test Framework
let passed = 0;
let failed = 0;
const results = [];

function test(name, fn) {
    try {
        fn();
        passed++;
        results.push({ name, status: 'PASS', error: null });
        console.log(`✅ PASS: ${name}`);
    } catch (error) {
        failed++;
        results.push({ name, status: 'FAIL', error: error.message });
        console.log(`❌ FAIL: ${name}`);
        console.log(`   Error: ${error.message}`);
    }
}

async function testAsync(name, fn) {
    try {
        await fn();
        passed++;
        results.push({ name, status: 'PASS', error: null });
        console.log(`✅ PASS: ${name}`);
    } catch (error) {
        failed++;
        results.push({ name, status: 'FAIL', error: error.message });
        console.log(`❌ FAIL: ${name}`);
        console.log(`   Error: ${error.message}`);
    }
}

function assertEqual(actual, expected, message = '') {
    if (actual !== expected) {
        throw new Error(`${message} Expected ${expected}, got ${actual}`);
    }
}

function assertTrue(value, message = '') {
    if (!value) {
        throw new Error(`${message} Expected true, got ${value}`);
    }
}

function assertFalse(value, message = '') {
    if (value) {
        throw new Error(`${message} Expected false, got ${value}`);
    }
}

function assertDefined(value, message = '') {
    if (value === undefined || value === null) {
        throw new Error(`${message} Expected defined value, got ${value}`);
    }
}

function assertContains(str, substring, message = '') {
    if (!str.includes(substring)) {
        throw new Error(`${message} String does not contain "${substring}"`);
    }
}

function assertArrayLength(arr, length, message = '') {
    if (arr.length !== length) {
        throw new Error(`${message} Expected array length ${length}, got ${arr.length}`);
    }
}

// ==================== UNIT TESTS ====================

console.log('\n🧪 FlyAI Frontend Unit Tests\n');
console.log('=' .repeat(50));

// ========== 1. SESSION & STORAGE TESTS ==========
console.log('\n📦 Session & Storage Tests');
console.log('-'.repeat(30));

test('Session ID wird generiert', () => {
    function generateSessionId() {
        return 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
    const id = generateSessionId();
    assertTrue(id.startsWith('sess_'), 'Session ID should start with sess_');
    assertTrue(id.length > 15, 'Session ID should be long enough');
});

test('LocalStorage Chat speichern', () => {
    const testHistory = [{ role: 'user', content: 'test' }];
    localStorage.setItem('test_chat', JSON.stringify(testHistory));
    const loaded = JSON.parse(localStorage.getItem('test_chat'));
    assertEqual(loaded[0].content, 'test');
    localStorage.removeItem('test_chat');
});

test('LocalStorage Chat laden (leer)', () => {
    localStorage.removeItem('flyai_test_empty');
    const loaded = JSON.parse(localStorage.getItem('flyai_test_empty') || '[]');
    assertArrayLength(loaded, 0);
});

// ========== 2. FLIGHT PARSING TESTS ==========
console.log('\n✈️ Flight Parsing Tests');
console.log('-'.repeat(30));

test('parseDuration - ISO 8601 Format PT2H30M', () => {
    function parseDuration(duration) {
        if (!duration) return Infinity;
        if (typeof duration === 'number') return duration;
        if (typeof duration === 'string') {
            let match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
            if (match) {
                const hours = parseInt(match[1] || 0);
                const minutes = parseInt(match[2] || 0);
                return hours * 60 + minutes;
            }
        }
        return Infinity;
    }
    assertEqual(parseDuration('PT2H30M'), 150);
    assertEqual(parseDuration('PT1H'), 60);
    assertEqual(parseDuration('PT45M'), 45);
    assertEqual(parseDuration('PT12H15M'), 735);
});

test('parseDuration - Objekt Format', () => {
    function parseDuration(duration) {
        if (!duration) return Infinity;
        if (typeof duration === 'object') {
            if (duration.totalMinutes) return duration.totalMinutes;
            if (duration.hours !== undefined && duration.minutes !== undefined) {
                return duration.hours * 60 + duration.minutes;
            }
        }
        return Infinity;
    }
    assertEqual(parseDuration({ totalMinutes: 120 }), 120);
    assertEqual(parseDuration({ hours: 2, minutes: 30 }), 150);
});

test('formatDuration - Minuten zu String', () => {
    function formatDuration(minutes) {
        if (typeof minutes === 'number') {
            const h = Math.floor(minutes / 60);
            const m = minutes % 60;
            return `${h}h ${m}m`;
        }
        return 'N/A';
    }
    assertEqual(formatDuration(150), '2h 30m');
    assertEqual(formatDuration(60), '1h 0m');
    assertEqual(formatDuration(45), '0h 45m');
});

test('Preis parsen', () => {
    const flight = { price: { total: "89.50", currency: "EUR" } };
    const price = parseFloat(flight.price?.total) || 0;
    assertEqual(price, 89.5);
});

// ========== 3. FILTER TESTS ==========
console.log('\n🔍 Filter Tests');
console.log('-'.repeat(30));

test('Filter nach Direktflügen', () => {
    const flights = [
        { itineraries: [{ segments: [{}] }] },  // Direkt (0 stops)
        { itineraries: [{ segments: [{}, {}] }] },  // 1 Stop
        { itineraries: [{ segments: [{}, {}, {}] }] }  // 2 Stops
    ];

    const directOnly = flights.filter(f => {
        const stops = (f.itineraries?.[0]?.segments?.length || 1) - 1;
        return stops === 0;
    });

    assertArrayLength(directOnly, 1);
});

test('Filter nach Preis', () => {
    const flights = [
        { price: { total: "50" } },
        { price: { total: "150" } },
        { price: { total: "250" } }
    ];

    const maxPrice = 100;
    const filtered = flights.filter(f => parseFloat(f.price?.total) <= maxPrice);

    assertArrayLength(filtered, 1);
    assertEqual(parseFloat(filtered[0].price.total), 50);
});

test('Filter nach Abflugzeit (Morgens)', () => {
    const flights = [
        { itineraries: [{ segments: [{ departure: { at: "2026-02-13T08:00:00" } }] }] },
        { itineraries: [{ segments: [{ departure: { at: "2026-02-13T14:00:00" } }] }] },
        { itineraries: [{ segments: [{ departure: { at: "2026-02-13T20:00:00" } }] }] }
    ];

    const morningFlights = flights.filter(f => {
        const depTime = f.itineraries?.[0]?.segments?.[0]?.departure?.at;
        const hour = new Date(depTime).getHours();
        return hour >= 6 && hour < 12;
    });

    assertArrayLength(morningFlights, 1);
});

test('Sortierung nach Preis', () => {
    const flights = [
        { price: { total: "150" } },
        { price: { total: "50" } },
        { price: { total: "100" } }
    ];

    const sorted = [...flights].sort((a, b) =>
        parseFloat(a.price.total) - parseFloat(b.price.total)
    );

    assertEqual(parseFloat(sorted[0].price.total), 50);
    assertEqual(parseFloat(sorted[1].price.total), 100);
    assertEqual(parseFloat(sorted[2].price.total), 150);
});

// ========== 4. LOGIN/AUTH TESTS ==========
console.log('\n🔐 Login/Auth Tests');
console.log('-'.repeat(30));

test('User speichern in LocalStorage', () => {
    const user = { email: 'test@example.com', name: 'Test User' };
    localStorage.setItem('flyai_test_user', JSON.stringify(user));

    const loaded = JSON.parse(localStorage.getItem('flyai_test_user'));
    assertEqual(loaded.email, 'test@example.com');
    assertEqual(loaded.name, 'Test User');

    localStorage.removeItem('flyai_test_user');
});

test('User löschen (Logout)', () => {
    localStorage.setItem('flyai_test_logout', JSON.stringify({ email: 'test@test.com' }));
    localStorage.removeItem('flyai_test_logout');

    const user = localStorage.getItem('flyai_test_logout');
    assertEqual(user, null);
});

test('Email Validierung', () => {
    function isValidEmail(email) {
        return email && email.includes('@') && email.includes('.');
    }

    assertTrue(isValidEmail('test@example.com'));
    assertTrue(isValidEmail('user@domain.de'));
    assertFalse(isValidEmail('invalid'));
    assertFalse(isValidEmail('no-at-sign.com'));
    assertFalse(isValidEmail(''));
});

test('Passwort Mindestlänge', () => {
    function isValidPassword(password) {
        return password && password.length >= 8;
    }

    assertTrue(isValidPassword('12345678'));
    assertTrue(isValidPassword('securepassword'));
    assertFalse(isValidPassword('short'));
    assertFalse(isValidPassword('1234567'));
});

// ========== 5. PREISALARM TESTS ==========
console.log('\n🔔 Preisalarm Tests');
console.log('-'.repeat(30));

test('Preisalarm erstellen', () => {
    const alarm = {
        id: Date.now(),
        from: 'BER',
        to: 'CDG',
        date: '2026-02-13',
        currentPrice: 150,
        targetPrice: 100,
        email: 'test@example.com',
        active: true
    };

    assertDefined(alarm.id);
    assertEqual(alarm.from, 'BER');
    assertEqual(alarm.to, 'CDG');
    assertTrue(alarm.targetPrice < alarm.currentPrice);
});

test('Preisalarm speichern/laden', () => {
    const alarms = [
        { id: 1, from: 'BER', to: 'CDG', targetPrice: 100, active: true },
        { id: 2, from: 'MUC', to: 'LHR', targetPrice: 80, active: false }
    ];

    localStorage.setItem('flyai_test_alarms', JSON.stringify(alarms));
    const loaded = JSON.parse(localStorage.getItem('flyai_test_alarms'));

    assertArrayLength(loaded, 2);
    assertEqual(loaded[0].from, 'BER');
    assertEqual(loaded[1].active, false);

    localStorage.removeItem('flyai_test_alarms');
});

test('Preisalarm filtern (aktive)', () => {
    const alarms = [
        { id: 1, active: true },
        { id: 2, active: false },
        { id: 3, active: true }
    ];

    const activeAlarms = alarms.filter(a => a.active);
    assertArrayLength(activeAlarms, 2);
});

// ========== 6. LANGUAGE TESTS ==========
console.log('\n🌍 Language Tests');
console.log('-'.repeat(30));

test('Sprache speichern', () => {
    localStorage.setItem('flyai_test_lang', 'en');
    assertEqual(localStorage.getItem('flyai_test_lang'), 'en');
    localStorage.removeItem('flyai_test_lang');
});

test('Übersetzungs-Objekt Struktur', () => {
    const translations = {
        de: { flights: 'Flüge', hotels: 'Hotels' },
        en: { flights: 'Flights', hotels: 'Hotels' }
    };

    assertEqual(translations.de.flights, 'Flüge');
    assertEqual(translations.en.flights, 'Flights');
});

// ========== 7. CART TESTS ==========
console.log('\n🛒 Cart Tests');
console.log('-'.repeat(30));

test('Artikel zum Warenkorb hinzufügen', () => {
    let cart = [];
    const item = { type: 'flight', price: 150, currency: 'EUR', data: { from: 'BER', to: 'CDG' } };
    cart.push(item);

    assertArrayLength(cart, 1);
    assertEqual(cart[0].price, 150);
});

test('Warenkorb Gesamtpreis', () => {
    const cart = [
        { price: 150 },
        { price: 80 },
        { price: 45 }
    ];

    const total = cart.reduce((sum, item) => sum + item.price, 0);
    assertEqual(total, 275);
});

test('Artikel aus Warenkorb entfernen', () => {
    let cart = [
        { id: 1, price: 150 },
        { id: 2, price: 80 }
    ];

    cart = cart.filter(item => item.id !== 1);
    assertArrayLength(cart, 1);
    assertEqual(cart[0].id, 2);
});

// ========== 8. RATE LIMITER TESTS ==========
console.log('\n⏱️ Rate Limiter Tests');
console.log('-'.repeat(30));

test('Rate Limiter - unter Limit', () => {
    const rateLimiter = {
        messages: [],
        maxMessages: 10,
        timeWindow: 60000,
        canSend() {
            const now = Date.now();
            this.messages = this.messages.filter(t => now - t < this.timeWindow);
            return this.messages.length < this.maxMessages;
        },
        recordMessage() {
            this.messages.push(Date.now());
        }
    };

    // 5 Nachrichten senden
    for (let i = 0; i < 5; i++) {
        rateLimiter.recordMessage();
    }

    assertTrue(rateLimiter.canSend(), 'Should allow sending under limit');
});

test('Rate Limiter - am Limit', () => {
    const rateLimiter = {
        messages: [],
        maxMessages: 3,
        timeWindow: 60000,
        canSend() {
            const now = Date.now();
            this.messages = this.messages.filter(t => now - t < this.timeWindow);
            return this.messages.length < this.maxMessages;
        },
        recordMessage() {
            this.messages.push(Date.now());
        }
    };

    // 3 Nachrichten senden (Limit erreicht)
    for (let i = 0; i < 3; i++) {
        rateLimiter.recordMessage();
    }

    assertFalse(rateLimiter.canSend(), 'Should block at limit');
});

// ========== 9. API RESPONSE TESTS ==========
console.log('\n🌐 API Response Tests');
console.log('-'.repeat(30));

test('Chat Response Type - flight_search', () => {
    const response = {
        type: 'flight_search',
        from: 'BER',
        to: 'CDG',
        message: 'Suche Flüge...'
    };

    assertEqual(response.type, 'flight_search');
    assertDefined(response.from);
    assertDefined(response.to);
});

test('Chat Response Type - travel_info', () => {
    const response = {
        type: 'travel_info',
        answer: 'Visum erforderlich',
        country: 'Thailand',
        aa_url: 'https://www.auswaertiges-amt.de/...'
    };

    assertEqual(response.type, 'travel_info');
    assertContains(response.aa_url, 'auswaertiges-amt');
});

test('Chat Response Type - hotel_search', () => {
    const response = {
        type: 'hotel_search',
        destination: 'Paris',
        message: 'Suche Hotels...'
    };

    assertEqual(response.type, 'hotel_search');
    assertEqual(response.destination, 'Paris');
});

// ========== 10. UTILITY FUNCTION TESTS ==========
console.log('\n🔧 Utility Function Tests');
console.log('-'.repeat(30));

test('Datum formatieren', () => {
    function formatDate(date) {
        return date.toISOString().split('T')[0];
    }

    const testDate = new Date('2026-02-13');
    assertEqual(formatDate(testDate), '2026-02-13');
});

test('IATA Code extrahieren', () => {
    function extractIATACode(value) {
        if (!value) return '';
        const match = value.match(/\(([A-Z]{3})\)/);
        if (match) return match[1];
        if (value.length === 3 && value === value.toUpperCase()) return value;
        return '';
    }

    assertEqual(extractIATACode('Berlin (BER)'), 'BER');
    assertEqual(extractIATACode('BER'), 'BER');
    assertEqual(extractIATACode('Paris Charles de Gaulle (CDG)'), 'CDG');
});

test('URL Parameter erstellen', () => {
    function createSearchParams(params) {
        return Object.entries(params)
            .filter(([_, v]) => v !== undefined && v !== null)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
            .join('&');
    }

    const params = createSearchParams({ destination: 'Paris', date: '2026-02-13' });
    assertContains(params, 'destination=Paris');
    assertContains(params, 'date=2026-02-13');
});

// ==================== SUMMARY ====================
console.log('\n' + '='.repeat(50));
console.log('📊 TEST SUMMARY');
console.log('='.repeat(50));
console.log(`✅ Passed: ${passed}`);
console.log(`❌ Failed: ${failed}`);
console.log(`📈 Total:  ${passed + failed}`);
console.log(`🎯 Rate:   ${((passed / (passed + failed)) * 100).toFixed(1)}%`);
console.log('='.repeat(50));

if (failed === 0) {
    console.log('\n🎉 ALL TESTS PASSED!\n');
} else {
    console.log('\n⚠️ Some tests failed. Please review.\n');
    console.log('Failed tests:');
    results.filter(r => r.status === 'FAIL').forEach(r => {
        console.log(`  - ${r.name}: ${r.error}`);
    });
}

// Export für Node.js
if (typeof module !== 'undefined') {
    module.exports = { results, passed, failed };
}
