const API_URL = 'http://127.0.0.1:8000';

let selectedFrom = '';
let selectedTo = '';
let tripType = 'roundtrip'; // 'roundtrip', 'oneway', 'multicity'
let currentFlights = []; // Speichert aktuelle Suchergebnisse

// Passagiere
let passengers = {
    adults: 1,
    children: 0,
    infants: 0
};

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

    // Trip-Toggle Setup
    document.querySelectorAll('.trip-option').forEach((option, index) => {
        option.addEventListener('click', () => {
            document.querySelectorAll('.trip-option').forEach(o => o.classList.remove('active'));
            option.classList.add('active');

            const returnField = document.getElementById('return').closest('.field-group');
            if (index === 0) {
                tripType = 'roundtrip';
                returnField.style.display = 'block';
            } else if (index === 1) {
                tripType = 'oneway';
                returnField.style.display = 'none';
            } else {
                tripType = 'multicity';
                returnField.style.display = 'none';
                showToast('Multi-City wird bald verfügbar!', 'info');
            }
        });
    });

    // Filter-Buttons Setup
    document.querySelectorAll('.filter-btn').forEach((btn, index) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            sortFlights(index);
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
    const adults = passengers.adults;

    if (!fromCode || !toCode) {
        showToast('Bitte wähle Abflug- und Zielflughafen aus!', 'error');
        return;
    }

    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').innerHTML = '';
    document.getElementById('filters').style.display = 'none';

    try {
        const response = await fetch(
            `${API_URL}/search_flights?from_airport=${fromCode}&to_airport=${toCode}&date=${date}&adults=${adults}`
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

function displayFlights(flights, saveToState = true) {
    if (saveToState) {
        currentFlights = flights;
    }

    const container = document.getElementById('results');

    container.innerHTML = flights.map((flight, index) => {
        const segment = flight.itineraries?.[0]?.segments?.[0];
        const lastSegment = flight.itineraries?.[0]?.segments?.slice(-1)[0];
        const price = flight.price?.total || '---';
        const currency = flight.price?.currency || 'EUR';
        const departure = segment?.departure?.iataCode || 'N/A';
        const arrival = lastSegment?.arrival?.iataCode || 'N/A';
        const depTime = segment?.departure?.at?.slice(11, 16) || '--:--';
        const arrTime = lastSegment?.arrival?.at?.slice(11, 16) || '--:--';
        const carrier = segment?.carrierCode || 'XX';
        const flightNum = segment?.number || '000';
        const duration = formatDuration(flight.itineraries?.[0]?.duration);
        const stops = (flight.itineraries?.[0]?.segments?.length || 1) - 1;

        return `
            <div class="flight-card" data-index="${index}">
                <div class="flight-info">
                    <div class="flight-airline">
                        <div class="airline-logo"><i class="fa-solid fa-plane"></i></div>
                        <span>${carrier} ${flightNum}</span>
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
                    <button class="select-btn" onclick="selectFlight(${index})">
                        <i class="fa-solid fa-check"></i> Auswählen
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function formatDuration(duration) {
    if (!duration) return 'N/A';
    const match = duration.match(/PT(\d+)H?(\d+)?M?/);
    if (!match) return duration.replace('PT', '').toLowerCase();
    const hours = match[1] || '0';
    const minutes = match[2] || '0';
    return `${hours}h ${minutes}m`;
}

function displayError(message) {
    document.getElementById('results').innerHTML = `
        <div class="error-card">
            <div class="error-icon"><i class="fa-solid fa-plane-slash"></i></div>
            <h3>Keine Flüge gefunden</h3>
            <p>${message}</p>
            <button class="retry-btn" onclick="searchFlights()">
                <i class="fa-solid fa-rotate"></i> Erneut suchen
            </button>
        </div>
    `;
}

// ==================== SORTIERUNG ====================
function sortFlights(sortIndex) {
    if (!currentFlights || currentFlights.length === 0) return;

    let sorted = [...currentFlights];

    if (sortIndex === 1) {
        // Günstigste
        sorted.sort((a, b) => parseFloat(a.price?.total || 0) - parseFloat(b.price?.total || 0));
    } else if (sortIndex === 2) {
        // Schnellste
        sorted.sort((a, b) => {
            const durationA = parseDuration(a.itineraries?.[0]?.duration);
            const durationB = parseDuration(b.itineraries?.[0]?.duration);
            return durationA - durationB;
        });
    }
    // index 0 = "Beste" bleibt original

    displayFlights(sorted);
}

function parseDuration(duration) {
    if (!duration) return Infinity;
    const match = duration.match(/PT(\d+)H?(\d+)?M?/);
    if (!match) return Infinity;
    const hours = parseInt(match[1] || 0);
    const minutes = parseInt(match[2] || 0);
    return hours * 60 + minutes;
}

// ==================== TOAST NOTIFICATIONS ====================
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fa-solid fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== FLUG AUSWÄHLEN ====================
function selectFlight(flightIndex) {
    const flight = currentFlights[flightIndex];
    if (!flight) return;

    const segment = flight.itineraries?.[0]?.segments?.[0];
    const price = flight.price?.total || '---';
    const currency = flight.price?.currency || 'EUR';
    const departure = segment?.departure?.iataCode || 'N/A';
    const arrival = segment?.arrival?.iataCode || 'N/A';
    const depTime = segment?.departure?.at?.slice(11, 16) || '--:--';
    const carrier = segment?.carrierCode || 'XX';
    const flightNum = segment?.number || '000';

    // Modal anzeigen
    showBookingModal(flight, {
        price, currency, departure, arrival, depTime, carrier, flightNum
    });
}

function showBookingModal(flight, details) {
    const modal = document.createElement('div');
    modal.className = 'booking-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">
                <i class="fa-solid fa-times"></i>
            </button>
            <div class="modal-header">
                <i class="fa-solid fa-plane-departure"></i>
                <h2>Flug ausgewählt</h2>
            </div>
            <div class="modal-body">
                <div class="modal-flight-info">
                    <div class="modal-route">
                        <span class="modal-airport">${details.departure}</span>
                        <i class="fa-solid fa-arrow-right"></i>
                        <span class="modal-airport">${details.arrival}</span>
                    </div>
                    <div class="modal-details">
                        <span><i class="fa-solid fa-plane"></i> ${details.carrier}${details.flightNum}</span>
                        <span><i class="fa-solid fa-clock"></i> ${details.depTime}</span>
                    </div>
                </div>
                <div class="modal-price">
                    <span class="price-label">Gesamtpreis</span>
                    <span class="price-value">${details.price} ${details.currency}</span>
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn secondary" onclick="closeModal()">Abbrechen</button>
                <button class="modal-btn primary" onclick="proceedBooking()">
                    <i class="fa-solid fa-credit-card"></i> Zur Buchung
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

function closeModal() {
    const modal = document.querySelector('.booking-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

function proceedBooking() {
    closeModal();
    showToast('Buchungsfunktion kommt bald!', 'info');
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

// ==================== PASSENGERS SELECTOR ====================
// Setup passengers button click handler
document.addEventListener('DOMContentLoaded', () => {
    const passengersBtn = document.getElementById('passengers-btn');
    if (passengersBtn) {
        passengersBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            togglePassengerPopup();
        });
    }

    // Setup +/- buttons
    const buttonConfig = [
        { id: 'adults-minus', type: 'adults', delta: -1 },
        { id: 'adults-plus', type: 'adults', delta: 1 },
        { id: 'children-minus', type: 'children', delta: -1 },
        { id: 'children-plus', type: 'children', delta: 1 },
        { id: 'infants-minus', type: 'infants', delta: -1 },
        { id: 'infants-plus', type: 'infants', delta: 1 }
    ];

    buttonConfig.forEach(config => {
        const btn = document.getElementById(config.id);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                changePassengers(config.type, config.delta);
            });
        }
    });
});

function togglePassengerPopup() {
    const popup = document.getElementById('passengers-popup');
    const btn = document.getElementById('passengers-btn');

    if (!popup || !btn) return;

    if (popup.classList.contains('show')) {
        closePassengerPopup();
    } else {
        popup.classList.add('show');
        btn.classList.add('open');
        // Add click listener to close when clicking outside
        setTimeout(() => {
            document.addEventListener('click', handleOutsideClick);
        }, 10);
    }
}

function handleOutsideClick(e) {
    const popup = document.getElementById('passengers-popup');
    const selector = document.querySelector('.passengers-selector');

    if (popup && selector && !selector.contains(e.target)) {
        closePassengerPopup();
    }
}

function closePassengerPopup() {
    const popup = document.getElementById('passengers-popup');
    const btn = document.getElementById('passengers-btn');
    if (popup) popup.classList.remove('show');
    if (btn) btn.classList.remove('open');
    document.removeEventListener('click', handleOutsideClick);
}

function changePassengers(type, delta) {
    const newValue = passengers[type] + delta;

    // Validierung
    if (type === 'adults' && (newValue < 1 || newValue > 9)) return;
    if (type === 'children' && (newValue < 0 || newValue > 9)) return;
    if (type === 'infants' && (newValue < 0 || newValue > passengers.adults)) return;

    // Gesamtanzahl prüfen (max 9 Passagiere)
    const total = (type === 'adults' ? newValue : passengers.adults) +
                  (type === 'children' ? newValue : passengers.children);
    if (total > 9) return;

    passengers[type] = newValue;
    updatePassengerDisplay();
    updatePassengerButtons();
}

function updatePassengerDisplay() {
    const display = document.getElementById('passengers-display');
    const total = passengers.adults + passengers.children;

    let text = '';
    if (passengers.adults === 1 && passengers.children === 0 && passengers.infants === 0) {
        text = '1 Erwachsener';
    } else {
        const parts = [];
        if (passengers.adults > 0) {
            parts.push(`${passengers.adults} Erw.`);
        }
        if (passengers.children > 0) {
            parts.push(`${passengers.children} Kind${passengers.children > 1 ? 'er' : ''}`);
        }
        if (passengers.infants > 0) {
            parts.push(`${passengers.infants} Baby${passengers.infants > 1 ? 's' : ''}`);
        }
        text = parts.join(', ');
    }

    display.textContent = text;

    // Update count displays
    document.getElementById('adults-count').textContent = passengers.adults;
    document.getElementById('children-count').textContent = passengers.children;
    document.getElementById('infants-count').textContent = passengers.infants;
}

function updatePassengerButtons() {
    const adultMinus = document.getElementById('adults-minus');
    const adultPlus = document.getElementById('adults-plus');
    const childMinus = document.getElementById('children-minus');
    const childPlus = document.getElementById('children-plus');
    const infantMinus = document.getElementById('infants-minus');
    const infantPlus = document.getElementById('infants-plus');

    if (adultMinus) adultMinus.disabled = passengers.adults <= 1;
    if (adultPlus) adultPlus.disabled = passengers.adults >= 9 || (passengers.adults + passengers.children) >= 9;
    if (childMinus) childMinus.disabled = passengers.children <= 0;
    if (childPlus) childPlus.disabled = passengers.children >= 9 || (passengers.adults + passengers.children) >= 9;
    if (infantMinus) infantMinus.disabled = passengers.infants <= 0;
    if (infantPlus) infantPlus.disabled = passengers.infants >= passengers.adults;
}

