/**
 * FlyAI Hotel Search
 * Hotel-specific functionality. Uses flyai-shared.js for cart, auth, chat, session.
 * API_URL, sessionId, addToCart, showToast, sendChat, etc. come from flyai-shared.js
 */

let currentHotels = [];
let selectedDestination = '';

// Datum-Inputs initialisieren
document.addEventListener('DOMContentLoaded', () => {
    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const checkoutDate = new Date(today.getTime() + 10 * 24 * 60 * 60 * 1000);

    document.getElementById('checkin').value = formatDate(nextWeek);
    document.getElementById('checkout').value = formatDate(checkoutDate);

    // Autocomplete fuer Destination
    setupDestinationAutocomplete();

    // Check URL params (e.g., from chat redirect)
    const urlParams = new URLSearchParams(window.location.search);
    const destParam = urlParams.get('destination');
    if (destParam) {
        document.getElementById('destination').value = destParam;
        selectedDestination = destParam;
        // Auto-search after short delay
        setTimeout(() => searchHotels(), 500);
    }
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

    let debounceTimer = null;

    input.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        // Debounce to avoid excessive API calls
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const destinations = await searchDestinations(query);
            showDestinationDropdown(dropdown, destinations, input);
        }, 300);
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
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
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
        dropdown.innerHTML = destinations.map(dest => {
            const safeName = escapeHTML(dest.name);
            const safeCountry = escapeHTML(dest.country || '');
            const safeEntityId = escapeHTML(dest.entityId || '');
            return `
            <div class="dropdown-item" onclick="selectDestination('${safeEntityId}', '${safeName}', '${safeCountry}')">
                <span><i class="fa-solid fa-location-dot"></i></span>
                <div class="airport-info">
                    <span class="airport-city">${safeName}</span>
                    <span class="airport-name">${safeCountry}</span>
                </div>
            </div>
        `;
        }).join('');
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
        showToast('Bitte waehle Check-in und Check-out Datum!', 'error');
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

    // Initial Card ausblenden
    const initialCard = document.getElementById('initial-card');
    if (initialCard) initialCard.style.display = 'none';

    // Coming Soon Card ausblenden
    const comingSoon = document.querySelector('.coming-soon-card');
    if (comingSoon) comingSoon.style.display = 'none';

    // Animate progress
    animateHotelProgress();

    try {
        const response = await fetch(
            `${API_URL}/search_hotels?destination=${encodeURIComponent(destination)}&checkin=${checkin}&checkout=${checkout}&adults=${guests}&rooms=${rooms}`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        completeHotelProgress();
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';

            if (data.success && data.hotels && data.hotels.length > 0) {
                currentHotels = data.hotels;
                document.getElementById('filters').style.display = 'flex';
                displayHotels(data.hotels);

                // Scroll to results
                setTimeout(() => {
                    document.getElementById('filters').scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);

                showToast(`${data.hotels.length} Hotels in ${destination} gefunden`, 'success');
            } else {
                displayHotelError(data.error || 'Keine Hotels gefunden');
            }
        }, 500);
    } catch (error) {
        completeHotelProgress();
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
            displayHotelError('Verbindungsfehler: ' + error.message);
        }, 500);
    }
}

// ==================== PROGRESS ANIMATION ====================
let hotelProgressInterval = null;

function animateHotelProgress() {
    const fill = document.getElementById('hotel-progress-fill');
    const text = document.getElementById('hotel-progress-text');
    const stepSearch = document.getElementById('hotel-step-search');
    const stepCompare = document.getElementById('hotel-step-compare');
    const stepResults = document.getElementById('hotel-step-results');

    if (!fill || !text) return;

    let progress = 10;
    const messages = [
        'Durchsuche 1M+ Hotels...',
        'Vergleiche Preise...',
        'Pruefe Verfuegbarkeit...',
        'Finde die besten Angebote...',
        'Optimiere Ergebnisse...'
    ];

    let msgIndex = 0;
    hotelProgressInterval = setInterval(() => {
        progress = Math.min(progress + Math.random() * 12, 90);
        fill.style.width = progress + '%';

        if (progress > 30 && stepSearch && stepCompare) {
            stepSearch.classList.remove('active');
            stepSearch.classList.add('done');
            stepCompare.classList.add('active');
        }
        if (progress > 65 && stepCompare && stepResults) {
            stepCompare.classList.remove('active');
            stepCompare.classList.add('done');
            stepResults.classList.add('active');
        }

        msgIndex = Math.min(Math.floor(progress / 20), messages.length - 1);
        text.textContent = messages[msgIndex];
    }, 400);
}

function completeHotelProgress() {
    if (hotelProgressInterval) {
        clearInterval(hotelProgressInterval);
        hotelProgressInterval = null;
    }
    const fill = document.getElementById('hotel-progress-fill');
    if (fill) fill.style.width = '100%';
}

// ==================== DISPLAY HOTELS ====================

function displayHotels(hotels) {
    const container = document.getElementById('results');

    container.innerHTML = hotels.map((hotel, index) => {
        const stars = hotel.stars ? '\u2605'.repeat(hotel.stars) + '\u2606'.repeat(5 - hotel.stars) : '';
        const amenities = hotel.amenities?.slice(0, 4) || [];

        return `
            <div class="hotel-card" data-index="${index}">
                <div class="hotel-image">
                    <img src="${hotel.image || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400'}"
                         alt="${escapeHTML(hotel.name)}"
                         onerror="this.src='https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400'">
                    ${hotel.freeCancel ? '<span class="hotel-badge">Kostenlose Stornierung</span>' : ''}
                </div>
                <div class="hotel-info">
                    <div class="hotel-header">
                        <h3 class="hotel-name">${escapeHTML(hotel.name)}</h3>
                        <div class="hotel-stars">${stars}</div>
                    </div>
                    <div class="hotel-location">
                        <i class="fa-solid fa-location-dot"></i>
                        <span>${escapeHTML(hotel.distance || hotel.address || '')}</span>
                    </div>
                    <div class="hotel-rating">
                        <span class="rating-score">${hotel.rating}</span>
                        <span class="rating-text">${getRatingText(hotel.rating)}</span>
                        <span class="rating-count">(${hotel.reviewsCount || 0} Bewertungen)</span>
                    </div>
                    <div class="hotel-amenities">
                        ${amenities.map(a => `<span class="amenity"><i class="fa-solid fa-check"></i> ${escapeHTML(a)}</span>`).join('')}
                    </div>
                </div>
                <div class="hotel-price">
                    <div class="price-info">
                        <span class="price-per-night">${hotel.pricePerNight} ${hotel.currency || 'EUR'}</span>
                        <span class="price-label">pro Nacht</span>
                    </div>
                    <div class="price-total">
                        <span>Gesamt: <strong>${hotel.totalPrice} ${hotel.currency || 'EUR'}</strong></span>
                        <span class="nights-info">${hotel.nights || ''} Naechte</span>
                    </div>
                    <button class="select-btn" onclick="selectHotel(${index})">
                        <i class="fa-solid fa-cart-plus"></i>
                        Zum Warenkorb
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
            <p>${escapeHTML(message)}</p>
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
        sorted.sort((a, b) => a.totalPrice - b.totalPrice);
    } else if (sortIndex === 2) {
        sorted.sort((a, b) => b.rating - a.rating);
    }

    displayHotels(sorted);
}

// ==================== HOTEL AUSWAEHLEN & ZUM WARENKORB ====================

function selectHotel(hotelIndex) {
    const hotel = currentHotels[hotelIndex];
    if (!hotel) return;

    const checkin = document.getElementById('checkin').value;
    const checkout = document.getElementById('checkout').value;

    // Add to cart via API
    addToCart('hotel', {
        name: hotel.name,
        address: hotel.address || hotel.distance || '',
        rating: hotel.rating,
        stars: hotel.stars,
        nights: hotel.nights || 1,
        checkin: checkin,
        checkout: checkout,
        pricePerNight: hotel.pricePerNight
    }, hotel.totalPrice, hotel.currency || 'EUR');
}
