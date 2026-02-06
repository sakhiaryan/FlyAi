const API_URL = 'http://127.0.0.1:8000';

let currentHotels = [];
let selectedDestination = '';

// Datum-Inputs initialisieren
document.addEventListener('DOMContentLoaded', () => {
    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const checkoutDate = new Date(today.getTime() + 10 * 24 * 60 * 60 * 1000);

    document.getElementById('checkin').value = formatDate(nextWeek);
    document.getElementById('checkout').value = formatDate(checkoutDate);

    // Autocomplete für Destination
    setupDestinationAutocomplete();
});

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// ==================== DESTINATION AUTOCOMPLETE ====================

function setupDestinationAutocomplete() {
    const input = document.getElementById('destination');
    let dropdown = document.getElementById('destination-dropdown');

    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'destination-dropdown';
        dropdown.className = 'dropdown';
        input.parentElement.appendChild(dropdown);
    }

    input.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        // Suche Destinationen
        const destinations = await searchDestinations(query);
        showDestinationDropdown(dropdown, destinations, input);
    });

    input.addEventListener('focus', async () => {
        const query = input.value;
        if (query.length >= 2) {
            const destinations = await searchDestinations(query);
            showDestinationDropdown(dropdown, destinations, input);
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.field-group')) {
            dropdown.style.display = 'none';
        }
    });
}

async function searchDestinations(query) {
    try {
        const response = await fetch(`${API_URL}/search_destination?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        return data.destinations || [];
    } catch (error) {
        console.error('Destination search error:', error);
        return [];
    }
}

function showDestinationDropdown(dropdown, destinations, input) {
    if (destinations.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item">Keine Ergebnisse gefunden</div>';
    } else {
        dropdown.innerHTML = destinations.map(dest => `
            <div class="dropdown-item" onclick="selectDestination('${dest.entityId}', '${dest.name}', '${dest.country || ''}')">
                <span><i class="fa-solid fa-location-dot"></i></span>
                <div class="airport-info">
                    <span class="airport-city">${dest.name}</span>
                    <span class="airport-name">${dest.country || ''}</span>
                </div>
            </div>
        `).join('');
    }
    dropdown.style.display = 'block';
}

function selectDestination(entityId, name, country) {
    const input = document.getElementById('destination');
    input.value = country ? `${name}, ${country}` : name;
    selectedDestination = name;
    document.getElementById('destination-dropdown').style.display = 'none';
}

// ==================== HOTEL SUCHE ====================

async function searchHotels() {
    const destination = document.getElementById('destination').value || selectedDestination;
    const checkin = document.getElementById('checkin').value;
    const checkout = document.getElementById('checkout').value;
    const rooms = document.getElementById('rooms').value;
    const guests = document.getElementById('guests').value;

    if (!destination) {
        showToast('Bitte gib ein Reiseziel ein!', 'error');
        return;
    }

    if (!checkin || !checkout) {
        showToast('Bitte wähle Check-in und Check-out Datum!', 'error');
        return;
    }

    // Check-in vor Check-out
    if (new Date(checkin) >= new Date(checkout)) {
        showToast('Check-out muss nach Check-in sein!', 'error');
        return;
    }

    // Loading anzeigen
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').innerHTML = '';
    document.getElementById('filters').style.display = 'none';

    // Coming Soon Card ausblenden
    const comingSoon = document.querySelector('.coming-soon-card');
    if (comingSoon) comingSoon.style.display = 'none';

    try {
        const response = await fetch(
            `${API_URL}/search_hotels?destination=${encodeURIComponent(destination)}&checkin=${checkin}&checkout=${checkout}&adults=${guests}&rooms=${rooms}`
        );
        const data = await response.json();

        document.getElementById('loading').style.display = 'none';

        if (data.success && data.hotels && data.hotels.length > 0) {
            currentHotels = data.hotels;
            document.getElementById('filters').style.display = 'flex';
            displayHotels(data.hotels);

            // Automatisch zu Ergebnissen scrollen
            setTimeout(() => {
                document.getElementById('filters').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);

            // Zeige Info über Datenquelle
            if (data.source === 'mock') {
                showToast(`${data.hotels.length} Hotels in ${destination} gefunden`, 'success');
            }
        } else {
            displayHotelError(data.error || 'Keine Hotels gefunden');
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        displayHotelError('Verbindungsfehler: ' + error.message);
    }
}

function displayHotels(hotels) {
    const container = document.getElementById('results');

    container.innerHTML = hotels.map((hotel, index) => {
        const stars = '★'.repeat(hotel.stars) + '☆'.repeat(5 - hotel.stars);
        const amenities = hotel.amenities?.slice(0, 4) || [];

        return `
            <div class="hotel-card" data-index="${index}">
                <div class="hotel-image">
                    <img src="${hotel.image || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400'}"
                         alt="${hotel.name}"
                         onerror="this.src='https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400'">
                    ${hotel.freeCancel ? '<span class="hotel-badge">Kostenlose Stornierung</span>' : ''}
                </div>
                <div class="hotel-info">
                    <div class="hotel-header">
                        <h3 class="hotel-name">${hotel.name}</h3>
                        <div class="hotel-stars">${stars}</div>
                    </div>
                    <div class="hotel-location">
                        <i class="fa-solid fa-location-dot"></i>
                        <span>${hotel.distance || hotel.address}</span>
                    </div>
                    <div class="hotel-rating">
                        <span class="rating-score">${hotel.rating}</span>
                        <span class="rating-text">${getRatingText(hotel.rating)}</span>
                        <span class="rating-count">(${hotel.reviewsCount} Bewertungen)</span>
                    </div>
                    <div class="hotel-amenities">
                        ${amenities.map(a => `<span class="amenity"><i class="fa-solid fa-check"></i> ${a}</span>`).join('')}
                    </div>
                </div>
                <div class="hotel-price">
                    <div class="price-info">
                        <span class="price-per-night">${hotel.pricePerNight} ${hotel.currency}</span>
                        <span class="price-label">pro Nacht</span>
                    </div>
                    <div class="price-total">
                        <span>Gesamt: <strong>${hotel.totalPrice} ${hotel.currency}</strong></span>
                        <span class="nights-info">${hotel.nights} Nächte</span>
                    </div>
                    <button class="select-btn" onclick="selectHotel(${index})">
                        <i class="fa-solid fa-check"></i>
                        Auswählen
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function getRatingText(rating) {
    if (rating >= 9) return 'Hervorragend';
    if (rating >= 8) return 'Sehr gut';
    if (rating >= 7) return 'Gut';
    if (rating >= 6) return 'Befriedigend';
    return 'Ausreichend';
}

function displayHotelError(message) {
    document.getElementById('results').innerHTML = `
        <div class="error-card">
            <div class="error-icon"><i class="fa-solid fa-hotel"></i></div>
            <h3>Keine Hotels gefunden</h3>
            <p>${message}</p>
            <button class="retry-btn" onclick="searchHotels()">
                <i class="fa-solid fa-rotate"></i> Erneut suchen
            </button>
        </div>
    `;
}

// ==================== SORTIERUNG ====================

function sortHotels(sortIndex) {
    if (!currentHotels || currentHotels.length === 0) return;

    let sorted = [...currentHotels];

    if (sortIndex === 1) {
        // Günstigste
        sorted.sort((a, b) => a.totalPrice - b.totalPrice);
    } else if (sortIndex === 2) {
        // Beste Bewertung
        sorted.sort((a, b) => b.rating - a.rating);
    }
    // index 0 = "Empfohlen" bleibt original

    displayHotels(sorted);
}

// ==================== HOTEL AUSWÄHLEN ====================

function selectHotel(hotelIndex) {
    const hotel = currentHotels[hotelIndex];
    if (!hotel) return;

    // Modal anzeigen
    showBookingModal(hotel);
}

function showBookingModal(hotel) {
    const modal = document.createElement('div');
    modal.className = 'booking-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">
                <i class="fa-solid fa-times"></i>
            </button>
            <div class="modal-header">
                <i class="fa-solid fa-hotel"></i>
                <h2>Hotel ausgewählt</h2>
            </div>
            <div class="modal-body">
                <div class="modal-hotel-info">
                    <h3>${hotel.name}</h3>
                    <p>${hotel.address || hotel.distance}</p>
                    <div class="modal-rating">
                        <span class="rating-score">${hotel.rating}</span>
                        <span>${getRatingText(hotel.rating)}</span>
                    </div>
                </div>
                <div class="modal-price">
                    <span class="price-label">Gesamtpreis für ${hotel.nights} Nächte</span>
                    <span class="price-value">${hotel.totalPrice} ${hotel.currency}</span>
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

// ==================== CHAT (falls vorhanden) ====================

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    const loadingId = appendChatMessage('Denke nach...', 'ai');

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: [],
                question: msg
            })
        });

        const data = await res.json();
        removeChatMessage(loadingId);
        appendChatMessage(data.answer || data.message || 'Keine Antwort', 'ai');
    } catch (e) {
        removeChatMessage(loadingId);
        appendChatMessage('Fehler beim Abrufen der Antwort.', 'ai');
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
