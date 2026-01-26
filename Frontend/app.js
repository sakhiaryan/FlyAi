const API_URL = 'http://127.0.0.1:8000';

let selectedFrom = '';
let selectedTo = '';

// Chat-History speichern (global für Debugging)
window.chatHistory = [];

// Rate Limiter: Max 10 Nachrichten pro Minute
const rateLimiter = {
    messages: [],
    maxMessages: 10,
    timeWindow: 60000, // 1 Minute in ms

    canSend() {
        const now = Date.now();
        // Alte Nachrichten entfernen
        this.messages = this.messages.filter(t => now - t < this.timeWindow);
        return this.messages.length < this.maxMessages;
    },

    recordMessage() {
        this.messages.push(Date.now());
    },

    getWaitTime() {
        if (this.messages.length === 0) return 0;
        const oldest = this.messages[0];
        const waitMs = this.timeWindow - (Date.now() - oldest);
        return Math.ceil(waitMs / 1000);
    }
};

// Datum-Inputs auf heute + 7 Tage setzen
document.addEventListener('DOMContentLoaded', () => {
    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const twoWeeks = new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000);

    document.getElementById('departure').value = formatDate(nextWeek);
    document.getElementById('return').value = formatDate(twoWeeks);

    setupAutocomplete('from', 'from-dropdown', true);
    setupAutocomplete('to', 'to-dropdown', false);

    document.querySelectorAll('.trip-option').forEach(option => {
        option.addEventListener('click', () => {
            document.querySelectorAll('.trip-option').forEach(o => o.classList.remove('active'));
            option.classList.add('active');
        });
    });
});

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// ==================== AUTOCOMPLETE ====================
function setupAutocomplete(inputId, dropdownId, isFrom) {
    const input = document.getElementById(inputId);

    input.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            hideDropdown(dropdownId);
            return;
        }
        const airports = await searchAirports(query);
        showDropdown(dropdownId, airports, inputId, isFrom);
    });

    input.addEventListener('focus', async () => {
        const query = input.value;
        if (query.length >= 2) {
            const airports = await searchAirports(query);
            showDropdown(dropdownId, airports, inputId, isFrom);
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.field-group')) {
            hideDropdown(dropdownId);
        }
    });
}

async function searchAirports(query) {
    try {
        const response = await fetch(`${API_URL}/airports?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        return data.airports || [];
    } catch (error) {
        return [];
    }
}

function showDropdown(dropdownId, airports, inputId, isFrom) {
    const dropdown = document.getElementById(dropdownId);

    if (airports.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item">Keine Flughäfen gefunden</div>';
    } else {
        dropdown.innerHTML = airports.map(airport => `
            <div class="dropdown-item" onclick="selectAirport('${inputId}', '${dropdownId}', '${airport.code}', '${airport.city}', ${isFrom})">
                <span>✈️</span>
                <div class="airport-info">
                    <span class="airport-city">${airport.city}</span>
                    <span class="airport-name">${airport.name} (${airport.code})</span>
                </div>
                <span class="airport-country">${airport.country}</span>
            </div>
        `).join('');
    }
    dropdown.style.display = 'block';
}

function hideDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) dropdown.style.display = 'none';
}

function selectAirport(inputId, dropdownId, code, city, isFrom) {
    const input = document.getElementById(inputId);
    input.value = `${city} (${code})`;
    if (isFrom) selectedFrom = code;
    else selectedTo = code;
    hideDropdown(dropdownId);
}

function swapAirports() {
    const from = document.getElementById('from');
    const to = document.getElementById('to');
    const tempValue = from.value;
    const tempCode = selectedFrom;
    from.value = to.value;
    selectedFrom = selectedTo;
    to.value = tempValue;
    selectedTo = tempCode;
}

// ==================== FLUGSUCHE ====================
async function searchFlights() {
    const fromCode = selectedFrom || extractCode(document.getElementById('from').value);
    const toCode = selectedTo || extractCode(document.getElementById('to').value);
    const date = document.getElementById('departure').value;
    const passengers = document.getElementById('passengers').value;

    if (!fromCode || !toCode) {
        alert('Bitte wähle Abflug- und Zielflughafen aus!');
        return;
    }

    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').innerHTML = '';
    document.getElementById('filters').style.display = 'none';

    try {
        const response = await fetch(
            `${API_URL}/search_flights?from_airport=${fromCode}&to_airport=${toCode}&date=${date}&adults=${passengers}`
        );
        const data = await response.json();

        document.getElementById('loading').style.display = 'none';

        if (data.success && data.flights && data.flights.length > 0) {
            document.getElementById('filters').style.display = 'flex';
            displayFlights(data.flights);
        } else {
            displayError(data.error || 'Keine Flüge gefunden');
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        displayError('Verbindungsfehler: ' + error.message);
    }
}

function extractCode(value) {
    const match = value.match(/\(([A-Z]{3})\)/);
    if (match) return match[1];
    if (value.length === 3 && value === value.toUpperCase()) return value;
    return '';
}

function displayFlights(flights) {
    const container = document.getElementById('results');

    container.innerHTML = flights.map(flight => {
        const segment = flight.itineraries?.[0]?.segments?.[0];
        const price = flight.price?.total || '---';
        const currency = flight.price?.currency || 'EUR';
        const departure = segment?.departure?.iataCode || 'N/A';
        const arrival = segment?.arrival?.iataCode || 'N/A';
        const depTime = segment?.departure?.at?.slice(11, 16) || '--:--';
        const arrTime = segment?.arrival?.at?.slice(11, 16) || '--:--';
        const carrier = segment?.carrierCode || 'XX';
        const flightNum = segment?.number || '000';
        const duration = flight.itineraries?.[0]?.duration?.replace('PT', '').toLowerCase() || 'N/A';
        const stops = (flight.itineraries?.[0]?.segments?.length || 1) - 1;

        return `
            <div class="flight-card">
                <div class="flight-info">
                    <div class="flight-airline">
                        <div class="airline-logo">✈️</div>
                        <span>${carrier}${flightNum}</span>
                    </div>
                    <div class="flight-times">
                        <div class="departure">
                            <div class="time">${depTime}</div>
                            <div class="airport">${departure}</div>
                        </div>
                        <div class="flight-line">
                            <div class="duration">${duration}</div>
                            <div class="line"></div>
                            <div class="stops ${stops === 0 ? 'direct' : ''}">${stops === 0 ? 'Direkt' : stops + ' Stop(s)'}</div>
                        </div>
                        <div class="arrival">
                            <div class="time">${arrTime}</div>
                            <div class="airport">${arrival}</div>
                        </div>
                    </div>
                </div>
                <div class="flight-price">
                    <div class="price">${price} ${currency}</div>
                    <div class="price-note">pro Person</div>
                    <button class="select-btn">Auswählen</button>
                </div>
            </div>
        `;
    }).join('');
}

function displayError(message) {
    document.getElementById('results').innerHTML = `
        <div class="flight-card" style="justify-content: center; text-align: center;">
            <div>
                <div style="font-size: 3rem; margin-bottom: 1rem;">😕</div>
                <h3>Keine Flüge gefunden</h3>
                <p style="color: #888;">${message}</p>
            </div>
        </div>
    `;
}

// ==================== SMART CHATBOT MIT MEMORY ====================
async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    // Rate Limiter Check
    if (!rateLimiter.canSend()) {
        const waitTime = rateLimiter.getWaitTime();
        appendChatMessage(`Bitte warte ${waitTime} Sekunden bevor du weitere Nachrichten sendest.`, 'ai');
        return;
    }

    // User-Nachricht anzeigen
    appendChatMessage(msg, 'user');
    input.value = '';

    // Rate Limiter: Nachricht zählen
    rateLimiter.recordMessage();

    // Loading anzeigen
    const loadingId = appendChatMessage('Denke nach...', 'ai');

    try {
        // POST Request mit Chat-History
        const res = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messages: window.chatHistory,
                question: msg
            })
        });

        const data = await res.json();

        removeChatMessage(loadingId);

        if (data.type === 'flight_search') {
            // KI hat Flugsuche erkannt
            appendChatMessage(data.message, 'ai');

            // History updaten
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.message });

            // Felder ausfüllen
            if (data.from) {
                document.getElementById('from').value = data.from;
                selectedFrom = data.from;
            }
            if (data.to) {
                document.getElementById('to').value = data.to;
                selectedTo = data.to;
            }
            if (data.date) {
                document.getElementById('departure').value = data.date;
            }

            // Automatisch suchen
            setTimeout(() => searchFlights(), 500);

        } else {
            // Normale Chat-Antwort
            appendChatMessage(data.answer, 'ai');

            // History updaten
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.answer });
        }

        // History auf max 20 Nachrichten begrenzen (10 Paare)
        if (window.chatHistory.length > 20) {
            window.chatHistory = window.chatHistory.slice(-20);
        }

    } catch (e) {
        removeChatMessage(loadingId);
        appendChatMessage('Fehler beim Abrufen der Antwort. Bitte versuche es erneut.', 'ai');
    }
}

function appendChatMessage(text, sender) {
    const chat = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;
    div.className = `chat-msg ${sender}`;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return id;
}

function removeChatMessage(id) {
    const msg = document.getElementById(id);
    if (msg) msg.remove();
}

function handleChatEnter(event) {
    if (event.key === 'Enter') sendChat();
}

// Chat-History löschen (optional - Button kann hinzugefügt werden)
function clearChatHistory() {
    window.chatHistory = [];
    document.getElementById('chat-messages').innerHTML = '';
}
