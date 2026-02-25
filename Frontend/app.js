const API_URL = 'http://127.0.0.1:8000';

let selectedFrom = '';
let selectedTo = '';
let tripType = 'roundtrip'; // 'roundtrip', 'oneway', 'multicity'
let currentFlights = []; // Speichert aktuelle Suchergebnisse
let currentLanguage = localStorage.getItem('flyai_language') || 'de';

// ==================== XSS SANITIZATION ====================
function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function sanitizeChatText(text) {
    // Escape HTML first, then apply safe formatting
    let safe = escapeHTML(text);
    // Convert newlines to <br>
    safe = safe.replace(/\n/g, '<br>');
    // Convert **bold** to <strong>bold</strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return safe;
}

function sanitizeChatTextWithLinks(text) {
    let safe = sanitizeChatText(text);
    // Convert URLs to safe links (only http/https)
    safe = safe.replace(
        /(https?:\/\/[^\s<&]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer" class="chat-link">$1</a>'
    );
    return safe;
}

// ==================== MOBILE MENU ====================
function toggleMobileMenu() {
    const mobileNav = document.querySelector('.mobile-nav');
    const overlay = document.querySelector('.mobile-nav-overlay');
    const menuBtn = document.querySelector('.mobile-menu-btn');

    if (mobileNav && overlay) {
        mobileNav.classList.toggle('active');
        overlay.classList.toggle('active');
        menuBtn?.classList.toggle('active');

        // Body scroll verhindern wenn Menü offen
        document.body.style.overflow = mobileNav.classList.contains('active') ? 'hidden' : '';
    }
}

// ==================== LANGUAGE SWITCH ====================
function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('flyai_language', lang);

    // Update active button
    document.querySelectorAll('.mobile-lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(lang === 'de' ? 'Deutsch' : 'English')) {
            btn.classList.add('active');
        }
    });

    // Update desktop language button
    const langBtn = document.querySelector('.btn-lang');
    if (langBtn) {
        langBtn.innerHTML = lang === 'de'
            ? '<span class="flag">🇩🇪</span><span>DE</span><i class="fa-solid fa-chevron-down"></i>'
            : '<span class="flag">🇬🇧</span><span>EN</span><i class="fa-solid fa-chevron-down"></i>';
    }

    // Translate UI elements
    translateUI(lang);

    showToast(lang === 'de' ? 'Sprache: Deutsch' : 'Language: English', 'success');
    toggleMobileMenu();
}

// UI Übersetzung
const translations = {
    de: {
        'flights': 'Flüge',
        'hotels': 'Hotels',
        'rental_cars': 'Mietwagen',
        'activities': 'Aktivitäten',
        'login': 'Anmelden',
        'search_flights': 'Flüge suchen',
        'from': 'Von',
        'to': 'Nach',
        'departure': 'Hinflug',
        'return': 'Rückflug',
        'passengers': 'Reisende',
        'roundtrip': 'Hin & Rückflug',
        'oneway': 'Nur Hinflug',
        'cheapest': 'Günstigste',
        'fastest': 'Schnellste',
        'hero_title': 'Entdecke die <span class="gradient-text">besten Flugdeals</span>',
        'hero_sub': 'Vergleiche tausende Flüge in Sekunden. Spare Zeit und Geld mit unserer intelligenten Suchmaschine.',
        'chat_placeholder': 'Schreibe eine Nachricht...',
        'chat_intro': 'Hallo! Ich bin dein persönlicher Reiseberater. Frag mich alles über:',
        'hero_badge': 'KI-gestützte Suche',
        'feature_fast': 'Blitzschnell',
        'feature_secure': 'Sicher buchen',
        'feature_price': 'Bestpreisgarantie',
        'from_placeholder': 'Stadt oder Flughafen',
        'to_placeholder': 'Stadt oder Flughafen',
        'passengers_1': '1 Erwachsener',
        'cart_title': 'Dein Warenkorb',
        'cart_empty': 'Dein Warenkorb ist leer',
        'cart_empty_sub': 'Füge Flüge oder Hotels hinzu',
        'cart_total': 'Gesamt:',
        'cart_checkout': 'Zur Buchung',
        'multi_city': 'Multi-City'
    },
    en: {
        'flights': 'Flights',
        'hotels': 'Hotels',
        'rental_cars': 'Rental Cars',
        'activities': 'Activities',
        'login': 'Sign In',
        'search_flights': 'Search Flights',
        'from': 'From',
        'to': 'To',
        'departure': 'Departure',
        'return': 'Return',
        'passengers': 'Passengers',
        'roundtrip': 'Round Trip',
        'oneway': 'One Way',
        'cheapest': 'Cheapest',
        'fastest': 'Fastest',
        'hero_title': 'Discover the <span class="gradient-text">best flight deals</span>',
        'hero_sub': 'Compare thousands of flights in seconds. Save time and money with our intelligent search engine.',
        'chat_placeholder': 'Write a message...',
        'chat_intro': 'Hello! I\'m your personal travel advisor. Ask me anything about:',
        'hero_badge': 'AI-Powered Search',
        'feature_fast': 'Lightning Fast',
        'feature_secure': 'Book Safely',
        'feature_price': 'Best Price Guarantee',
        'from_placeholder': 'City or Airport',
        'to_placeholder': 'City or Airport',
        'passengers_1': '1 Adult',
        'cart_title': 'Your Cart',
        'cart_empty': 'Your cart is empty',
        'cart_empty_sub': 'Add flights or hotels',
        'cart_total': 'Total:',
        'cart_checkout': 'Checkout',
        'multi_city': 'Multi-City'
    }
};

function translateUI(lang) {
    const t = translations[lang];

    // Navigation
    document.querySelectorAll('.nav-link span, .mobile-nav-link span').forEach(el => {
        const text = el.textContent.trim();
        if (text === 'Flüge' || text === 'Flights') el.textContent = t.flights;
        if (text === 'Hotels') el.textContent = t.hotels;
        if (text === 'Mietwagen' || text === 'Rental Cars') el.textContent = t.rental_cars;
        if (text === 'Aktivitäten' || text === 'Activities') el.textContent = t.activities;
    });

    // Login Button
    document.querySelectorAll('.btn-login span').forEach(el => {
        el.textContent = t.login;
    });

    // Hero
    const heroTitle = document.querySelector('.hero h1');
    if (heroTitle) heroTitle.innerHTML = t.hero_title;

    const heroSub = document.querySelector('.hero-sub');
    if (heroSub) heroSub.textContent = t.hero_sub;

    // Search Box Labels
    const labels = document.querySelectorAll('.field-group label');
    labels.forEach(label => {
        const text = label.textContent.trim();
        if (text.includes('Von') || text.includes('From')) {
            label.innerHTML = `<i class="fa-solid fa-plane-departure"></i> ${t.from}`;
        }
        if (text.includes('Nach') || text.includes('To')) {
            label.innerHTML = `<i class="fa-solid fa-plane-arrival"></i> ${t.to}`;
        }
        if (text.includes('Hinflug') || text.includes('Departure')) {
            label.innerHTML = `<i class="fa-solid fa-calendar"></i> ${t.departure}`;
        }
        if (text.includes('Rückflug') || text.includes('Return')) {
            label.innerHTML = `<i class="fa-solid fa-calendar"></i> ${t.return}`;
        }
        if (text.includes('Reisende') || text.includes('Passengers')) {
            label.innerHTML = `<i class="fa-solid fa-users"></i> ${t.passengers}`;
        }
    });

    // Search Button
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) {
        searchBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> ${t.search_flights}`;
    }

    // Trip Options
    document.querySelectorAll('.trip-option span').forEach((el, i) => {
        if (i === 0) el.textContent = t.roundtrip;
        if (i === 1) el.textContent = t.oneway;
    });

    // Filter Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.textContent.includes('Günstig') || btn.textContent.includes('Cheap')) {
            btn.innerHTML = `<i class="fa-solid fa-piggy-bank"></i> ${t.cheapest}`;
        }
        if (btn.textContent.includes('Schnell') || btn.textContent.includes('Fast')) {
            btn.innerHTML = `<i class="fa-solid fa-bolt"></i> ${t.fastest}`;
        }
    });

    // Chat
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.placeholder = t.chat_placeholder;

    const chatIntro = document.querySelector('.intro-text');
    if (chatIntro) chatIntro.textContent = t.chat_intro;

    // Hero Badge
    const heroBadge = document.querySelector('.hero-badge span');
    if (heroBadge) heroBadge.textContent = t.hero_badge;

    // Hero Features (Trust Badges)
    const heroFeatures = document.querySelectorAll('.hero-feature span');
    if (heroFeatures.length >= 3) {
        heroFeatures[0].textContent = t.feature_fast;
        heroFeatures[1].textContent = t.feature_secure;
        heroFeatures[2].textContent = t.feature_price;
    }

    // Input Placeholders
    const fromInput = document.getElementById('from');
    const toInput = document.getElementById('to');
    if (fromInput) fromInput.placeholder = t.from_placeholder;
    if (toInput) toInput.placeholder = t.to_placeholder;

    // Passengers Dropdown
    const passengersSelect = document.querySelector('.passengers-select');
    if (passengersSelect) {
        const firstOption = passengersSelect.querySelector('option');
        if (firstOption) firstOption.textContent = t.passengers_1;
    }

    // Cart Sidebar
    const cartTitle = document.querySelector('.cart-sidebar-header h3');
    if (cartTitle) cartTitle.innerHTML = `<i class="fa-solid fa-shopping-cart"></i> ${t.cart_title}`;

    const cartEmpty = document.querySelector('.cart-empty p');
    if (cartEmpty) cartEmpty.textContent = t.cart_empty;

    const cartEmptySub = document.querySelector('.cart-empty span');
    if (cartEmptySub) cartEmptySub.textContent = t.cart_empty_sub;

    const cartTotalLabel = document.querySelector('.cart-total span:first-child');
    if (cartTotalLabel) cartTotalLabel.textContent = t.cart_total;

    const cartCheckout = document.querySelector('.cart-checkout-btn');
    if (cartCheckout) cartCheckout.innerHTML = `<i class="fa-solid fa-credit-card"></i> ${t.cart_checkout}`;

    // Multi-City Trip Option
    const tripOptions = document.querySelectorAll('.trip-option span');
    if (tripOptions.length >= 3) {
        tripOptions[0].textContent = t.roundtrip;
        tripOptions[1].textContent = t.oneway;
        tripOptions[2].textContent = t.multi_city;
    }
}

// ==================== LOGIN MODAL ====================
function showLoginModal() {
    // Schließe Mobile Menu
    const mobileNav = document.querySelector('.mobile-nav');
    if (mobileNav?.classList.contains('active')) {
        toggleMobileMenu();
    }

    // Erstelle Modal
    const existingModal = document.querySelector('.login-modal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.className = 'login-modal';
    modal.innerHTML = `
        <div class="login-modal-overlay" onclick="closeLoginModal()"></div>
        <div class="login-modal-content">
            <button class="login-modal-close" onclick="closeLoginModal()">
                <i class="fa-solid fa-times"></i>
            </button>
            <div class="login-modal-header">
                <div class="logo" style="justify-content: center; margin-bottom: 20px;">
                    <div class="logo-icon">
                        <i class="fa-solid fa-plane"></i>
                    </div>
                    <span class="logo-text" style="color: #1a1a2e;">Fly<span class="logo-highlight">AI</span></span>
                </div>
                <h2>${currentLanguage === 'de' ? 'Willkommen zurück!' : 'Welcome back!'}</h2>
                <p>${currentLanguage === 'de' ? 'Melde dich an oder erstelle ein Konto' : 'Sign in or create an account'}</p>
            </div>
            <div class="login-tabs">
                <button class="login-tab active" onclick="switchLoginTab('login')">${currentLanguage === 'de' ? 'Anmelden' : 'Sign In'}</button>
                <button class="login-tab" onclick="switchLoginTab('register')">${currentLanguage === 'de' ? 'Registrieren' : 'Register'}</button>
            </div>
            <form class="login-form" id="login-form" onsubmit="handleLogin(event)">
                <div class="login-field">
                    <label><i class="fa-solid fa-envelope"></i> E-Mail</label>
                    <input type="email" id="login-email" placeholder="name@beispiel.de" required>
                </div>
                <div class="login-field">
                    <label><i class="fa-solid fa-lock"></i> ${currentLanguage === 'de' ? 'Passwort' : 'Password'}</label>
                    <input type="password" id="login-password" placeholder="••••••••" required>
                </div>
                <div class="login-options">
                    <label class="login-remember">
                        <input type="checkbox"> ${currentLanguage === 'de' ? 'Angemeldet bleiben' : 'Stay signed in'}
                    </label>
                    <a href="#" class="login-forgot">${currentLanguage === 'de' ? 'Passwort vergessen?' : 'Forgot password?'}</a>
                </div>
                <button type="submit" class="login-submit">
                    <i class="fa-solid fa-arrow-right"></i> ${currentLanguage === 'de' ? 'Anmelden' : 'Sign In'}
                </button>
            </form>
            <form class="register-form" id="register-form" onsubmit="handleRegister(event)" style="display: none;">
                <div class="login-field">
                    <label><i class="fa-solid fa-user"></i> ${currentLanguage === 'de' ? 'Name' : 'Name'}</label>
                    <input type="text" id="register-name" placeholder="${currentLanguage === 'de' ? 'Dein Name' : 'Your name'}" required>
                </div>
                <div class="login-field">
                    <label><i class="fa-solid fa-envelope"></i> E-Mail</label>
                    <input type="email" id="register-email" placeholder="name@beispiel.de" required>
                </div>
                <div class="login-field">
                    <label><i class="fa-solid fa-lock"></i> ${currentLanguage === 'de' ? 'Passwort' : 'Password'}</label>
                    <input type="password" id="register-password" placeholder="••••••••" required minlength="8">
                </div>
                <button type="submit" class="login-submit">
                    <i class="fa-solid fa-user-plus"></i> ${currentLanguage === 'de' ? 'Konto erstellen' : 'Create Account'}
                </button>
            </form>
            <div class="login-divider">
                <span>${currentLanguage === 'de' ? 'oder fortfahren mit' : 'or continue with'}</span>
            </div>
            <div class="social-login">
                <button class="social-btn google" onclick="socialLogin('google')">
                    <i class="fa-brands fa-google"></i>
                </button>
                <button class="social-btn apple" onclick="socialLogin('apple')">
                    <i class="fa-brands fa-apple"></i>
                </button>
                <button class="social-btn facebook" onclick="socialLogin('facebook')">
                    <i class="fa-brands fa-facebook-f"></i>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Animation
    setTimeout(() => modal.classList.add('active'), 10);
}

function closeLoginModal() {
    const modal = document.querySelector('.login-modal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

function switchLoginTab(tab) {
    document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.login-tab:${tab === 'login' ? 'first' : 'last'}-child`).classList.add('active');

    document.getElementById('login-form').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('register-form').style.display = tab === 'register' ? 'block' : 'none';
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const rememberMe = document.querySelector('.login-remember input')?.checked || false;

    // Disable button während Login
    const submitBtn = document.querySelector('.login-submit');
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Anmelden...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, remember_me: rememberMe })
        });

        const data = await response.json();

        if (data.success) {
            // User und Token speichern
            localStorage.setItem('flyai_user', JSON.stringify(data.user));
            localStorage.setItem('flyai_token', data.token);

            showToast(data.message || 'Erfolgreich angemeldet!', 'success');
            closeLoginModal();
            updateUserUI();
        } else {
            // Fehler anzeigen
            showToast(data.error || 'Login fehlgeschlagen', 'error');
            submitBtn.innerHTML = '<i class="fa-solid fa-arrow-right"></i> Anmelden';
            submitBtn.disabled = false;
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Verbindungsfehler. Bitte versuche es erneut.', 'error');
        submitBtn.innerHTML = '<i class="fa-solid fa-arrow-right"></i> Anmelden';
        submitBtn.disabled = false;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    // Validierung
    if (name.length < 2) {
        showToast('Name muss mindestens 2 Zeichen haben', 'error');
        return;
    }

    if (password.length < 8) {
        showToast('Passwort muss mindestens 8 Zeichen haben', 'error');
        return;
    }

    // Disable button
    const submitBtn = document.querySelector('#register-form .login-submit');
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registrieren...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (data.success) {
            // User und Token speichern
            localStorage.setItem('flyai_user', JSON.stringify(data.user));
            localStorage.setItem('flyai_token', data.token);

            showToast(data.message || 'Konto erstellt!', 'success');
            closeLoginModal();
            updateUserUI();
        } else {
            showToast(data.error || 'Registrierung fehlgeschlagen', 'error');
            submitBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Konto erstellen';
            submitBtn.disabled = false;
        }
    } catch (error) {
        console.error('Register error:', error);
        showToast('Verbindungsfehler. Bitte versuche es erneut.', 'error');
        submitBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Konto erstellen';
        submitBtn.disabled = false;
    }
}

function socialLogin(provider) {
    showToast(`${provider.charAt(0).toUpperCase() + provider.slice(1)} Login kommt bald!`, 'info');
}

function updateUserUI() {
    const user = JSON.parse(localStorage.getItem('flyai_user'));
    const loginBtns = document.querySelectorAll('.btn-login');

    loginBtns.forEach(btn => {
        if (user) {
            btn.innerHTML = `<i class="fa-solid fa-user-circle"></i><span>${user.name}</span>`;
            btn.onclick = showUserMenu;
        } else {
            btn.innerHTML = `<i class="fa-solid fa-user"></i><span>${currentLanguage === 'de' ? 'Anmelden' : 'Sign In'}</span>`;
            btn.onclick = showLoginModal;
        }
    });
}

function showUserMenu() {
    const user = JSON.parse(localStorage.getItem('flyai_user'));
    if (!user) return showLoginModal();

    if (confirm(currentLanguage === 'de' ? 'Möchtest du dich abmelden?' : 'Do you want to sign out?')) {
        localStorage.removeItem('flyai_user');
        showToast(currentLanguage === 'de' ? 'Abgemeldet!' : 'Signed out!', 'success');
        updateUserUI();
    }
}

// Init User UI on load
document.addEventListener('DOMContentLoaded', () => {
    updateUserUI();
    // Apply saved language
    if (currentLanguage !== 'de') {
        translateUI(currentLanguage);
    }
});

// Passagiere
let passengers = {
    adults: 1,
    children: 0,
    infants: 0
};

// Chat-History speichern (global für Debugging)
window.chatHistory = JSON.parse(localStorage.getItem('flyai_chat_history') || '[]');

// Chat-Nachrichten für UI (separat von History)
window.chatMessages = JSON.parse(localStorage.getItem('flyai_chat_messages') || '[]');

// Funktion zum Speichern des Chat-Verlaufs
function saveChatToStorage() {
    localStorage.setItem('flyai_chat_history', JSON.stringify(window.chatHistory));
    localStorage.setItem('flyai_chat_messages', JSON.stringify(window.chatMessages));
}

// Chat-Verlauf beim Laden wiederherstellen
function restoreChatMessages() {
    const container = document.getElementById('chat-messages');
    if (!container || window.chatMessages.length === 0) return;

    // Alte Nachrichten wiederherstellen
    window.chatMessages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `chat-message ${msg.type}`;
        div.innerHTML = msg.html;
        container.appendChild(div);
    });

    // Ans Ende scrollen
    container.scrollTop = container.scrollHeight;
}

// Session ID für Warenkorb
let sessionId = localStorage.getItem('flyai_session') || generateSessionId();
localStorage.setItem('flyai_session', sessionId);

// Warenkorb
let cart = [];

function generateSessionId() {
    return 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

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

    const departureEl = document.getElementById('departure');
    const returnEl = document.getElementById('return');

    if (departureEl) departureEl.value = formatDate(nextWeek);
    if (returnEl) returnEl.value = formatDate(twoWeeks);

    if (document.getElementById('from')) {
        setupAutocomplete('from', 'from-dropdown', true);
    }
    if (document.getElementById('to')) {
        setupAutocomplete('to', 'to-dropdown', false);
    }

    // Chat-Verlauf wiederherstellen
    restoreChatMessages();

    // Trip-Toggle Setup
    document.querySelectorAll('.trip-option').forEach((option, index) => {
        option.addEventListener('click', () => {
            document.querySelectorAll('.trip-option').forEach(o => o.classList.remove('active'));
            option.classList.add('active');

            const returnField = returnEl?.closest('.field-group');
            if (!returnField) return;
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
    setupFilterButtons();

    // Warenkorb laden
    loadCart();

    // Sprache beim Laden anwenden
    if (currentLanguage !== 'de') {
        translateUI(currentLanguage);
    }
});

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// ==================== WARENKORB ====================
async function loadCart() {
    try {
        const res = await fetch(`${API_URL}/cart/${sessionId}`);
        const data = await res.json();
        cart = data.items || [];
        updateCartUI();
    } catch (e) {
        console.log('Cart laden fehlgeschlagen:', e);
    }
}

function updateCartUI() {
    const badge = document.getElementById('cart-badge');
    const cartItems = document.getElementById('cart-items');
    const cartFooter = document.getElementById('cart-footer');
    const cartTotal = document.getElementById('cart-total-price');

    if (badge) {
        badge.textContent = cart.length;
        badge.style.display = cart.length > 0 ? 'flex' : 'none';
    }

    if (!cartItems) return;

    if (cart.length === 0) {
        cartItems.innerHTML = `
            <div class="cart-empty">
                <i class="fa-solid fa-shopping-cart"></i>
                <p>Dein Warenkorb ist leer</p>
                <span>Füge Flüge oder Hotels hinzu</span>
            </div>
        `;
        if (cartFooter) cartFooter.style.display = 'none';
    } else {
        let total = 0;
        cartItems.innerHTML = cart.map(item => {
            total += item.price;
            const icon = item.type === 'flight' ? 'fa-plane' : item.type === 'hotel' ? 'fa-hotel' : 'fa-ticket';
            const data = item.data;

            let title = '';
            let details = '';

            if (item.type === 'flight') {
                title = `${data.from} → ${data.to}`;
                details = `${data.carrier || ''} ${data.flightNum || ''} | ${data.depTime || ''}`;
            } else if (item.type === 'hotel') {
                title = data.name || 'Hotel';
                details = `${data.nights || 1} Nächte | ${data.address || ''}`;
            } else {
                title = data.name || 'Aktivität';
                details = data.description || '';
            }

            return `
                <div class="cart-item">
                    <div class="cart-item-header">
                        <span class="cart-item-type ${item.type}">
                            <i class="fa-solid ${icon}"></i>
                            ${item.type === 'flight' ? 'Flug' : item.type === 'hotel' ? 'Hotel' : 'Aktivität'}
                        </span>
                        <button class="cart-item-remove" onclick="removeFromCart(${item.id})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                    <div class="cart-item-title">${title}</div>
                    <div class="cart-item-details">${details}</div>
                    <div class="cart-item-price">${item.price} ${item.currency}</div>
                </div>
            `;
        }).join('');

        if (cartFooter) {
            cartFooter.style.display = 'block';
            if (cartTotal) cartTotal.textContent = `${total.toFixed(2)} EUR`;
        }
    }
}

function toggleCart() {
    const sidebar = document.getElementById('cart-sidebar');
    const overlay = document.getElementById('cart-overlay');

    if (sidebar && overlay) {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('show');
    }
}

async function addToCart(type, itemData, price, currency = 'EUR') {
    try {
        const res = await fetch(`${API_URL}/cart/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                item_type: type,
                item_data: itemData,
                price: price,
                currency: currency
            })
        });

        const data = await res.json();
        if (data.success) {
            cart = data.cart.items || [];
            updateCartUI();
            showToast(`${type === 'flight' ? 'Flug' : type === 'hotel' ? 'Hotel' : 'Aktivität'} zum Warenkorb hinzugefügt!`, 'success');
        }
    } catch (e) {
        showToast('Fehler beim Hinzufügen', 'error');
    }
}

async function removeFromCart(itemId) {
    try {
        const res = await fetch(`${API_URL}/cart/remove`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                item_id: itemId
            })
        });

        const data = await res.json();
        if (data.success) {
            cart = data.cart.items || [];
            updateCartUI();
            showToast('Item entfernt', 'info');
        }
    } catch (e) {
        showToast('Fehler beim Entfernen', 'error');
    }
}

function checkout() {
    if (cart.length === 0) {
        showToast('Dein Warenkorb ist leer!', 'error');
        return;
    }
    showToast('Buchungsfunktion kommt bald!', 'info');
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
let searchProgressInterval = null;

function animateSearchProgress() {
    const fill = document.getElementById('progress-fill');
    const text = document.getElementById('progress-text');
    const stepSearch = document.getElementById('step-search');
    const stepCompare = document.getElementById('step-compare');
    const stepResults = document.getElementById('step-results');

    if (!fill || !text) return;

    let progress = 10;
    const messages = [
        'Durchsuche 500+ Airlines...',
        'Vergleiche Preise...',
        'Analysiere Verbindungen...',
        'Finde die besten Deals...',
        'Optimiere Ergebnisse...'
    ];

    let msgIndex = 0;
    searchProgressInterval = setInterval(() => {
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

function completeSearchProgress() {
    if (searchProgressInterval) {
        clearInterval(searchProgressInterval);
        searchProgressInterval = null;
    }
    const fill = document.getElementById('progress-fill');
    const stepResults = document.getElementById('step-results');
    const stepSearch = document.getElementById('step-search');
    const stepCompare = document.getElementById('step-compare');

    if (fill) fill.style.width = '100%';
    if (stepSearch) { stepSearch.classList.remove('active'); stepSearch.classList.add('done'); }
    if (stepCompare) { stepCompare.classList.remove('active'); stepCompare.classList.add('done'); }
    if (stepResults) { stepResults.classList.remove('active'); stepResults.classList.add('done'); }
}

function resetSearchProgress() {
    const fill = document.getElementById('progress-fill');
    const stepSearch = document.getElementById('step-search');
    const stepCompare = document.getElementById('step-compare');
    const stepResults = document.getElementById('step-results');

    if (fill) fill.style.width = '10%';
    if (stepSearch) { stepSearch.className = 'step active'; }
    if (stepCompare) { stepCompare.className = 'step'; }
    if (stepResults) { stepResults.className = 'step'; }
}

async function searchFlights() {
    const fromCode = selectedFrom || extractCode(document.getElementById('from').value);
    const toCode = selectedTo || extractCode(document.getElementById('to').value);
    const date = document.getElementById('departure').value;
    const adults = passengers.adults;

    if (!fromCode || !toCode) {
        const msg = currentLanguage === 'de'
            ? 'Bitte wähle einen Flughafen aus der Vorschlagsliste oder gib einen bekannten Stadtnamen ein.'
            : 'Please select an airport from the suggestions or enter a known city name.';
        showToast(msg, 'error');
        return;
    }

    // Hide popular destinations
    const popDest = document.getElementById('popular-destinations');
    if (popDest) popDest.style.display = 'none';

    // Show loading with skeleton
    resetSearchProgress();
    document.getElementById('loading').style.display = 'block';
    animateSearchProgress();

    document.getElementById('results').innerHTML = '';
    document.getElementById('filters').style.display = 'none';
    const summary = document.getElementById('results-summary');
    if (summary) summary.style.display = 'none';
    const qf = document.getElementById('quick-filters');
    if (qf) qf.style.display = 'none';

    try {
        const response = await fetch(
            `${API_URL}/search_flights?from_airport=${fromCode}&to_airport=${toCode}&date=${date}&adults=${adults}`
        );
        const data = await response.json();

        completeSearchProgress();
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';

            if (data.success && data.flights && data.flights.length > 0) {
                document.getElementById('filters').style.display = 'flex';
                if (summary) summary.style.display = 'flex';
                if (qf) qf.style.display = 'flex';
                // Filter-Buttons neu initialisieren
                setTimeout(() => reinitFilterButtons(), 100);
                displayFlights(data.flights);
                updateResultsSummary(data.flights);
            } else {
                displayError(data.error || 'Keine Flüge gefunden');
            }
        }, 500);
    } catch (error) {
        completeSearchProgress();
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
            displayError('Verbindungsfehler: ' + error.message);
        }, 500);
    }
}

// Bekannte Stadt-zu-IATA Mappings für Direkteingabe ohne Autocomplete
const cityToIATA = {
    'berlin': 'BER', 'münchen': 'MUC', 'munich': 'MUC', 'frankfurt': 'FRA',
    'hamburg': 'HAM', 'düsseldorf': 'DUS', 'köln': 'CGN', 'cologne': 'CGN',
    'stuttgart': 'STR', 'hannover': 'HAJ', 'nürnberg': 'NUE', 'nuremberg': 'NUE',
    'leipzig': 'LEJ', 'dresden': 'DRS', 'dortmund': 'DTM', 'bremen': 'BRE',
    'london': 'LHR', 'paris': 'CDG', 'amsterdam': 'AMS', 'rom': 'FCO', 'rome': 'FCO',
    'madrid': 'MAD', 'barcelona': 'BCN', 'lissabon': 'LIS', 'lisbon': 'LIS',
    'wien': 'VIE', 'vienna': 'VIE', 'zürich': 'ZRH', 'zurich': 'ZRH',
    'istanbul': 'IST', 'athen': 'ATH', 'athens': 'ATH', 'prag': 'PRG', 'prague': 'PRG',
    'warschau': 'WAW', 'warsaw': 'WAW', 'budapest': 'BUD', 'kopenhagen': 'CPH',
    'new york': 'JFK', 'los angeles': 'LAX', 'chicago': 'ORD', 'miami': 'MIA',
    'bangkok': 'BKK', 'tokyo': 'NRT', 'tokio': 'NRT', 'dubai': 'DXB',
    'singapur': 'SIN', 'singapore': 'SIN', 'hong kong': 'HKG', 'hongkong': 'HKG',
    'sydney': 'SYD', 'melbourne': 'MEL', 'kairo': 'CAI', 'cairo': 'CAI',
    'kapstadt': 'CPT', 'cape town': 'CPT', 'johannesburg': 'JNB',
    'toronto': 'YYZ', 'vancouver': 'YVR', 'mexiko city': 'MEX', 'mexico city': 'MEX',
    'são paulo': 'GRU', 'sao paulo': 'GRU', 'buenos aires': 'EZE',
    'peking': 'PEK', 'beijing': 'PEK', 'shanghai': 'PVG', 'seoul': 'ICN',
    'mumbai': 'BOM', 'delhi': 'DEL', 'new delhi': 'DEL',
    'antalya': 'AYT', 'palma': 'PMI', 'mallorca': 'PMI', 'teneriffa': 'TFS',
    'kreta': 'HER', 'crete': 'HER', 'ibiza': 'IBZ', 'malaga': 'AGP',
    'mailand': 'MXP', 'milan': 'MXP', 'venedig': 'VCE', 'venice': 'VCE',
    'brüssel': 'BRU', 'brussels': 'BRU', 'oslo': 'OSL', 'stockholm': 'ARN',
    'helsinki': 'HEL', 'dublin': 'DUB', 'edinburgh': 'EDI', 'manchester': 'MAN',
    'nizza': 'NCE', 'nice': 'NCE', 'lyon': 'LYS', 'marseille': 'MRS'
};

function extractCode(value) {
    const match = value.match(/\(([A-Z]{3})\)/);
    if (match) return match[1];
    if (value.length === 3 && value === value.toUpperCase()) return value;
    // Fallback: Stadtname in IATA-Code auflösen
    const cityLookup = cityToIATA[value.trim().toLowerCase()];
    if (cityLookup) return cityLookup;
    return '';
}

function displayFlights(flights, saveToState = true) {
    if (saveToState) {
        currentFlights = flights;
    }

    const container = document.getElementById('results');

    // Find cheapest and fastest for badges
    let cheapestPrice = Infinity;
    let cheapestIdx = -1;
    let fastestDuration = Infinity;
    let fastestIdx = -1;

    flights.forEach((flight, i) => {
        const p = parseFloat(flight.price?.total) || Infinity;
        if (p < cheapestPrice) { cheapestPrice = p; cheapestIdx = i; }
        const d = parseDuration(flight.itineraries?.[0]?.duration);
        if (d < fastestDuration) { fastestDuration = d; fastestIdx = i; }
    });

    // Airline name mapping for badges
    const airlineNames = {
        'LH': 'Lufthansa', 'BA': 'British Airways', 'AF': 'Air France',
        'KL': 'KLM', 'EW': 'Eurowings', 'FR': 'Ryanair', 'U2': 'easyJet',
        'LX': 'Swiss', 'OS': 'Austrian', 'IB': 'Iberia', 'TK': 'Turkish Airlines',
        'EK': 'Emirates', 'QR': 'Qatar Airways', 'SQ': 'Singapore Airlines',
        'DL': 'Delta', 'UA': 'United', 'AA': 'American Airlines',
        'SK': 'SAS', 'AZ': 'ITA Airways', 'VY': 'Vueling', 'W6': 'Wizz Air',
        'DE': 'Condor', 'X3': 'TUIfly', 'AB': 'Air Berlin', 'EN': 'Air Dolomiti'
    };

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
        const airlineName = airlineNames[carrier] || carrier;

        // Build badges
        let badges = '';
        let cardClass = 'flight-card';
        if (index === cheapestIdx) {
            badges += '<span class="flight-badge cheapest"><i class="fa-solid fa-tag"></i> Guenstigster</span>';
            cardClass += ' cheapest-card';
        }
        if (index === fastestIdx) {
            badges += '<span class="flight-badge fastest"><i class="fa-solid fa-bolt"></i> Schnellster</span>';
            cardClass += ' fastest-card';
        }
        if (stops === 0) {
            badges += '<span class="flight-badge direct-badge"><i class="fa-solid fa-arrow-right"></i> Direkt</span>';
        }

        // Build detail chips
        let detailChips = '<div class="flight-details-row">';
        detailChips += `<span class="flight-detail-chip"><i class="fa-solid fa-chair"></i> Economy</span>`;
        if (flight.pricingOptions?.includedCheckedBagsOnly || Math.random() > 0.5) {
            detailChips += `<span class="flight-detail-chip luggage-included"><i class="fa-solid fa-suitcase-rolling"></i> Gepaeck inkl.</span>`;
        }
        detailChips += `<span class="flight-detail-chip"><i class="fa-solid fa-clock"></i> ${duration}</span>`;
        if (stops > 0) {
            const stopCodes = flight.itineraries?.[0]?.segments?.slice(0, -1).map(s => s.arrival?.iataCode).filter(Boolean).join(', ') || '';
            if (stopCodes) {
                detailChips += `<span class="flight-detail-chip"><i class="fa-solid fa-map-pin"></i> via ${stopCodes}</span>`;
            }
        }
        detailChips += '</div>';

        return `
            <div class="${cardClass}" data-index="${index}">
                <div class="flight-info">
                    ${badges ? '<div class="flight-badges">' + badges + '</div>' : ''}
                    <div class="flight-airline">
                        <div class="airline-badge">
                            <span class="airline-code">${carrier}</span>
                            <span class="airline-text">${airlineName}</span>
                            <span class="flight-number" style="color:var(--text-muted);font-size:0.75rem;margin-left:4px">${carrier}${flightNum}</span>
                        </div>
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
                    ${detailChips}
                </div>
                <div class="flight-price">
                    <div class="price">${price} ${currency}</div>
                    <div class="price-note">pro Person</div>
                    <div class="flight-actions">
                        <button class="select-btn" onclick="selectFlight(${index})">
                            <i class="fa-solid fa-cart-plus"></i> Buchen
                        </button>
                        <button class="alarm-btn" onclick="setPriceAlarm(${index})" title="Preisalarm setzen">
                            <i class="fa-solid fa-bell"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function formatDuration(duration) {
    if (!duration) return 'N/A';

    // Wenn es eine Zahl ist (Minuten vom Backend)
    if (typeof duration === 'number') {
        const hours = Math.floor(duration / 60);
        const minutes = duration % 60;
        return `${hours}h ${minutes}m`;
    }

    // Wenn es ein String ist (ISO 8601 Format "PT2H30M")
    if (typeof duration === 'string') {
        const match = duration.match(/PT(\d+)H?(\d+)?M?/);
        if (!match) return duration.replace('PT', '').toLowerCase();
        const hours = match[1] || '0';
        const minutes = match[2] || '0';
        return `${hours}h ${minutes}m`;
    }

    return 'N/A';
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

// ==================== FILTER SETUP ====================
let filterButtonsInitialized = false;

function setupFilterButtons() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    if (filterButtons.length === 0 || filterButtonsInitialized) return;
    filterButtonsInitialized = true;

    filterButtons.forEach((btn, index) => {
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);

        newBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            sortFlights(index);
        });
    });
}

function reinitFilterButtons() {
    filterButtonsInitialized = false;
    setupFilterButtons();
}

// ==================== ADVANCED FILTERS ====================
let originalFlights = []; // Speichert ungefilterte Flüge

function toggleAdvancedFilters() {
    const filters = document.getElementById('advanced-filters');
    const toggleBtn = document.querySelector('.filter-toggle-btn');

    if (filters.style.display === 'none') {
        filters.style.display = 'grid';
        toggleBtn?.classList.add('active');
        populateAirlineFilters();
    } else {
        filters.style.display = 'none';
        toggleBtn?.classList.remove('active');
    }
}

function populateAirlineFilters() {
    const container = document.getElementById('airline-filters');
    if (!container || !currentFlights.length) return;

    // Extrahiere alle Airlines aus den Flügen
    const airlines = new Set();
    currentFlights.forEach(flight => {
        const segments = flight.itineraries?.[0]?.segments || [];
        segments.forEach(seg => {
            if (seg.carrierCode) {
                airlines.add(seg.carrierCode);
            }
        });
    });

    // Airline Namen Mapping
    const airlineNames = {
        'LH': 'Lufthansa',
        'BA': 'British Airways',
        'AF': 'Air France',
        'KL': 'KLM',
        'EW': 'Eurowings',
        'FR': 'Ryanair',
        'U2': 'easyJet',
        'LX': 'Swiss',
        'OS': 'Austrian',
        'IB': 'Iberia',
        'TK': 'Turkish Airlines',
        'EK': 'Emirates',
        'QR': 'Qatar Airways',
        'SQ': 'Singapore Airlines'
    };

    container.innerHTML = Array.from(airlines).map(code => `
        <label class="airline-chip active" data-airline="${code}">
            <input type="checkbox" checked onchange="applyFilters()" style="display:none;">
            ${airlineNames[code] || code}
        </label>
    `).join('');

    // Click Handler für Chips
    container.querySelectorAll('.airline-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('active');
            chip.querySelector('input').checked = chip.classList.contains('active');
            applyFilters();
        });
    });
}

function updatePriceRange() {
    const range = document.getElementById('price-range');
    const valueDisplay = document.getElementById('price-range-value');
    if (range && valueDisplay) {
        valueDisplay.textContent = `Max: ${range.value}€`;
        applyFilters();
    }
}

function applyFilters() {
    if (!originalFlights.length) {
        originalFlights = [...currentFlights];
    }

    let filtered = [...originalFlights];

    // Filter: Stops
    const directOnly = document.getElementById('filter-direct')?.checked;
    const max1Stop = document.getElementById('filter-1stop')?.checked;
    const allow2Stops = document.getElementById('filter-2stops')?.checked;

    filtered = filtered.filter(flight => {
        const stops = (flight.itineraries?.[0]?.segments?.length || 1) - 1;
        if (directOnly && stops === 0) return true;
        if (max1Stop && stops <= 1) return true;
        if (allow2Stops && stops >= 2) return true;
        if (!directOnly && !max1Stop && !allow2Stops) return true;
        return directOnly ? stops === 0 : (max1Stop ? stops <= 1 : true);
    });

    // Filter: Abflugzeit
    const morning = document.getElementById('filter-morning')?.checked;
    const afternoon = document.getElementById('filter-afternoon')?.checked;
    const evening = document.getElementById('filter-evening')?.checked;

    if (morning || afternoon || evening) {
        filtered = filtered.filter(flight => {
            const depTime = flight.itineraries?.[0]?.segments?.[0]?.departure?.at;
            if (!depTime) return true;
            const hour = new Date(depTime).getHours();
            if (morning && hour >= 6 && hour < 12) return true;
            if (afternoon && hour >= 12 && hour < 18) return true;
            if (evening && hour >= 18 || hour < 6) return true;
            return false;
        });
    }

    // Filter: Preis
    const maxPrice = parseInt(document.getElementById('price-range')?.value || 2000);
    filtered = filtered.filter(flight => {
        const price = parseFloat(flight.price?.total) || 0;
        return price <= maxPrice;
    });

    // Filter: Airlines
    const activeAirlines = [];
    document.querySelectorAll('.airline-chip.active').forEach(chip => {
        activeAirlines.push(chip.dataset.airline);
    });

    if (activeAirlines.length > 0) {
        filtered = filtered.filter(flight => {
            const carrier = flight.itineraries?.[0]?.segments?.[0]?.carrierCode;
            return activeAirlines.includes(carrier);
        });
    }

    // Update Anzeige
    displayFlights(filtered, false);
    showToast(`${filtered.length} Flüge gefunden`, 'info');
}

// ==================== PREISALARM ====================
let priceAlarms = JSON.parse(localStorage.getItem('flyai_price_alarms') || '[]');

function setPriceAlarm(flightIndex) {
    const flight = currentFlights[flightIndex];
    if (!flight) return;

    const segment = flight.itineraries?.[0]?.segments?.[0];
    const lastSegment = flight.itineraries?.[0]?.segments?.slice(-1)[0];
    const price = parseFloat(flight.price?.total) || 0;
    const from = segment?.departure?.iataCode || 'N/A';
    const to = lastSegment?.arrival?.iataCode || 'N/A';
    const date = segment?.departure?.at?.slice(0, 10) || '';
    const carrier = segment?.carrierCode || '';

    // Check ob Alarm schon existiert
    const existingAlarm = priceAlarms.find(a =>
        a.from === from && a.to === to && a.date === date
    );

    if (existingAlarm) {
        showToast('Preisalarm bereits aktiv für diese Route!', 'info');
        showPriceAlarmModal();
        return;
    }

    // Modal anzeigen
    const modal = document.createElement('div');
    modal.className = 'price-alarm-modal';
    modal.innerHTML = `
        <div class="price-alarm-overlay" onclick="closePriceAlarmModal()"></div>
        <div class="price-alarm-content">
            <button class="price-alarm-close" onclick="closePriceAlarmModal()">
                <i class="fa-solid fa-times"></i>
            </button>
            <div class="price-alarm-header">
                <i class="fa-solid fa-bell"></i>
                <h2>Preisalarm setzen</h2>
            </div>
            <div class="price-alarm-route">
                <span class="route-from">${from}</span>
                <i class="fa-solid fa-plane"></i>
                <span class="route-to">${to}</span>
            </div>
            <div class="price-alarm-info">
                <div class="info-item">
                    <i class="fa-solid fa-calendar"></i>
                    <span>${date}</span>
                </div>
                <div class="info-item">
                    <i class="fa-solid fa-euro-sign"></i>
                    <span>Aktueller Preis: ${price}€</span>
                </div>
            </div>
            <div class="price-alarm-target">
                <label>Benachrichtigen wenn Preis unter:</label>
                <div class="price-input-group">
                    <input type="number" id="target-price" value="${Math.floor(price * 0.9)}" min="1" max="${price}">
                    <span>€</span>
                </div>
                <input type="range" id="price-slider" min="1" max="${price}" value="${Math.floor(price * 0.9)}"
                    oninput="document.getElementById('target-price').value = this.value">
            </div>
            <div class="price-alarm-email">
                <label>E-Mail für Benachrichtigung:</label>
                <input type="email" id="alarm-email" placeholder="deine@email.de"
                    value="${localStorage.getItem('flyai_user') ? JSON.parse(localStorage.getItem('flyai_user')).email || '' : ''}">
            </div>
            <button class="price-alarm-submit" onclick="confirmPriceAlarm('${from}', '${to}', '${date}', ${price}, '${carrier}')">
                <i class="fa-solid fa-bell"></i> Alarm aktivieren
            </button>
        </div>
    `;
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('active'), 10);
}

function closePriceAlarmModal() {
    const modal = document.querySelector('.price-alarm-modal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

function confirmPriceAlarm(from, to, date, currentPrice, carrier) {
    const targetPrice = parseInt(document.getElementById('target-price').value);
    const email = document.getElementById('alarm-email').value;

    if (!email || !email.includes('@')) {
        showToast('Bitte gib eine gültige E-Mail ein', 'error');
        return;
    }

    if (targetPrice >= currentPrice) {
        showToast('Zielpreis muss niedriger als aktueller Preis sein', 'error');
        return;
    }

    const alarm = {
        id: Date.now(),
        from,
        to,
        date,
        currentPrice,
        targetPrice,
        email,
        carrier,
        createdAt: new Date().toISOString(),
        active: true
    };

    priceAlarms.push(alarm);
    localStorage.setItem('flyai_price_alarms', JSON.stringify(priceAlarms));

    closePriceAlarmModal();
    showToast(`Preisalarm gesetzt! Wir benachrichtigen dich bei ${targetPrice}€`, 'success');

    // Update UI
    updateAlarmBadge();
}

function showPriceAlarmModal() {
    const modal = document.createElement('div');
    modal.className = 'price-alarm-modal';
    modal.innerHTML = `
        <div class="price-alarm-overlay" onclick="closePriceAlarmModal()"></div>
        <div class="price-alarm-content price-alarm-list">
            <button class="price-alarm-close" onclick="closePriceAlarmModal()">
                <i class="fa-solid fa-times"></i>
            </button>
            <div class="price-alarm-header">
                <i class="fa-solid fa-bell"></i>
                <h2>Meine Preisalarme</h2>
            </div>
            <div class="alarm-list">
                ${priceAlarms.length === 0 ? `
                    <div class="no-alarms">
                        <i class="fa-solid fa-bell-slash"></i>
                        <p>Keine aktiven Preisalarme</p>
                    </div>
                ` : priceAlarms.map(alarm => `
                    <div class="alarm-item ${alarm.active ? 'active' : 'inactive'}">
                        <div class="alarm-route">
                            <strong>${alarm.from} → ${alarm.to}</strong>
                            <span class="alarm-date">${alarm.date}</span>
                        </div>
                        <div class="alarm-prices">
                            <span class="current-price">Aktuell: ${alarm.currentPrice}€</span>
                            <span class="target-price">Ziel: ${alarm.targetPrice}€</span>
                        </div>
                        <div class="alarm-actions">
                            <button class="alarm-toggle" onclick="toggleAlarm(${alarm.id})">
                                <i class="fa-solid fa-${alarm.active ? 'pause' : 'play'}"></i>
                            </button>
                            <button class="alarm-delete" onclick="deleteAlarm(${alarm.id})">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('active'), 10);
}

function toggleAlarm(alarmId) {
    const alarm = priceAlarms.find(a => a.id === alarmId);
    if (alarm) {
        alarm.active = !alarm.active;
        localStorage.setItem('flyai_price_alarms', JSON.stringify(priceAlarms));
        closePriceAlarmModal();
        showPriceAlarmModal();
        showToast(alarm.active ? 'Alarm aktiviert' : 'Alarm pausiert', 'info');
    }
}

function deleteAlarm(alarmId) {
    priceAlarms = priceAlarms.filter(a => a.id !== alarmId);
    localStorage.setItem('flyai_price_alarms', JSON.stringify(priceAlarms));
    closePriceAlarmModal();
    showPriceAlarmModal();
    updateAlarmBadge();
    showToast('Alarm gelöscht', 'success');
}

function updateAlarmBadge() {
    // Könnte ein Badge zum Header hinzufügen
    const activeAlarms = priceAlarms.filter(a => a.active).length;
    console.log(`${activeAlarms} aktive Preisalarme`);
}

// ==================== QUICK ACTIONS FÜR CHAT ====================
function addQuickActions(country) {
    const chat = document.getElementById('chat-messages');

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'quick-actions';
    actionsDiv.innerHTML = `
        <button class="quick-action-btn" onclick="quickSearch('flight', '${country}')">
            <i class="fa-solid fa-plane"></i> Flüge nach ${country}
        </button>
        <button class="quick-action-btn" onclick="quickSearch('hotel', '${country}')">
            <i class="fa-solid fa-hotel"></i> Hotels in ${country}
        </button>
        <button class="quick-action-btn" onclick="quickAsk('visum', '${country}')">
            <i class="fa-solid fa-passport"></i> Visum-Info
        </button>
    `;

    chat.appendChild(actionsDiv);
    chat.scrollTop = chat.scrollHeight;
}

function quickSearch(type, country) {
    if (type === 'flight') {
        document.getElementById('to').value = country;
        showToast(`Suche Flüge nach ${country}...`, 'info');
        setTimeout(() => searchFlights(), 500);
    } else if (type === 'hotel') {
        window.location.href = `hotels.html?destination=${encodeURIComponent(country)}`;
    }
}

function quickAsk(topic, country) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = `Brauche ich ein Visum für ${country}?`;
        sendChat();
    }
}

function resetFilters() {
    // Checkboxen zurücksetzen
    document.getElementById('filter-direct').checked = false;
    document.getElementById('filter-1stop').checked = true;
    document.getElementById('filter-2stops').checked = true;
    document.getElementById('filter-morning').checked = true;
    document.getElementById('filter-afternoon').checked = true;
    document.getElementById('filter-evening').checked = true;
    document.getElementById('filter-luggage').checked = false;
    document.getElementById('price-range').value = 2000;
    document.getElementById('price-range-value').textContent = 'Max: 2000€';

    // Airline Chips zurücksetzen
    document.querySelectorAll('.airline-chip').forEach(chip => {
        chip.classList.add('active');
        chip.querySelector('input').checked = true;
    });

    // Original Flüge anzeigen
    if (originalFlights.length) {
        displayFlights(originalFlights, false);
    }

    showToast('Filter zurückgesetzt', 'success');
}

// ==================== SORTIERUNG ====================
function sortFlights(sortIndex) {
    if (!currentFlights || currentFlights.length === 0) {
        console.log('Keine Flüge zum Sortieren');
        return;
    }

    console.log(`Sortiere ${currentFlights.length} Flüge mit Index ${sortIndex}`);

    let sorted = [...currentFlights];

    if (sortIndex === 1) {
        // Günstigste - nach Preis aufsteigend
        sorted.sort((a, b) => {
            const priceA = parseFloat(a.price?.total) || parseFloat(a.price?.amount) || 999999;
            const priceB = parseFloat(b.price?.total) || parseFloat(b.price?.amount) || 999999;
            console.log(`Preis A: ${priceA}, Preis B: ${priceB}`);
            return priceA - priceB;
        });
        showToast('Sortiert nach günstigstem Preis', 'info');
    } else if (sortIndex === 2) {
        // Schnellste - nach Flugdauer aufsteigend
        sorted.sort((a, b) => {
            const durationA = parseDuration(a.itineraries?.[0]?.duration || a.duration);
            const durationB = parseDuration(b.itineraries?.[0]?.duration || b.duration);
            console.log(`Dauer A: ${durationA}min, Dauer B: ${durationB}min`);
            return durationA - durationB;
        });
        showToast('Sortiert nach kürzester Flugdauer', 'info');
    } else {
        // index 0 = "Beste" - Originalreihenfolge
        showToast('Sortiert nach bester Übereinstimmung', 'info');
    }

    // Nicht zum State speichern (saveToState = false), damit Original erhalten bleibt
    displayFlights(sorted, false);
}

function parseDuration(duration) {
    if (!duration) return Infinity;

    // Wenn es bereits eine Zahl ist (Minuten)
    if (typeof duration === 'number') {
        return duration;
    }

    // Wenn es ein Objekt ist, versuche totalMinutes oder ähnliches zu extrahieren
    if (typeof duration === 'object') {
        if (duration.totalMinutes) return duration.totalMinutes;
        if (duration.minutes !== undefined && duration.hours !== undefined) {
            return duration.hours * 60 + duration.minutes;
        }
        // Versuche es als String zu konvertieren
        duration = String(duration);
    }

    // ISO 8601 Format: "PT2H30M" oder "PT12H" oder "PT45M"
    if (typeof duration === 'string') {
        // Versuche verschiedene Formate
        let match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
        if (match) {
            const hours = parseInt(match[1] || 0);
            const minutes = parseInt(match[2] || 0);
            return hours * 60 + minutes;
        }

        // Fallback: nur Stunden "PT12H"
        match = duration.match(/PT(\d+)H/);
        if (match) {
            return parseInt(match[1]) * 60;
        }

        // Fallback: nur Minuten "PT45M"
        match = duration.match(/PT(\d+)M/);
        if (match) {
            return parseInt(match[1]);
        }

        // Fallback: Format "3h 43m" oder "1h 58m"
        match = duration.match(/(\d+)h\s*(\d+)?m?/i);
        if (match) {
            const hours = parseInt(match[1] || 0);
            const minutes = parseInt(match[2] || 0);
            return hours * 60 + minutes;
        }
    }

    return Infinity;
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

// ==================== FLUG AUSWÄHLEN & ZUM WARENKORB ====================
function selectFlight(flightIndex) {
    const flight = currentFlights[flightIndex];
    if (!flight) return;

    const segment = flight.itineraries?.[0]?.segments?.[0];
    const lastSegment = flight.itineraries?.[0]?.segments?.slice(-1)[0];
    const price = parseFloat(flight.price?.total) || 0;
    const currency = flight.price?.currency || 'EUR';
    const departure = segment?.departure?.iataCode || 'N/A';
    const arrival = lastSegment?.arrival?.iataCode || 'N/A';
    const depTime = segment?.departure?.at?.slice(11, 16) || '--:--';
    const carrier = segment?.carrierCode || 'XX';
    const flightNum = segment?.number || '000';

    // Zum Warenkorb hinzufügen
    addToCart('flight', {
        from: departure,
        to: arrival,
        carrier: carrier,
        flightNum: flightNum,
        depTime: depTime,
        date: document.getElementById('departure').value
    }, price, currency);
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
                question: msg,
                session_id: sessionId
            })
        });

        const data = await res.json();

        removeChatMessage(loadingId);

        if (data.type === 'flight_search') {
            // KI hat Flugsuche erkannt - mit Visa-Warnung
            appendChatMessageHTML(data.message, 'ai', data.visa_info);

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

        } else if (data.type === 'hotel_search') {
            // Hotel-Suche erkannt
            appendChatMessageHTML(data.message, 'ai', data.visa_info);
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.message });

            // Zur Hotel-Seite weiterleiten
            showToast('Öffne Hotel-Suche...', 'info');
            setTimeout(() => {
                window.location.href = `hotels.html?destination=${encodeURIComponent(data.destination)}`;
            }, 1000);

        } else if (data.type === 'cart') {
            // Warenkorb-Anfrage
            appendChatMessage(data.answer, 'ai');
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.answer });

        } else if (data.type === 'ask_passport') {
            // Nachfrage nach Pass
            appendChatMessage(data.message, 'ai');
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.message });

        } else if (data.type === 'travel_info') {
            // Schnelle Reiseinfo mit AA-Link (Token-sparend!)
            appendChatMessageWithLink(data.answer, 'ai', data.visa_info, data.aa_url);
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.answer });

        } else if (data.type === 'travel_planning') {
            // Reiseplanung mit Empfehlungen
            appendChatMessageWithLink(data.answer, 'ai', data.visa_info, data.aa_url);
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.answer });

            // Quick Action Buttons hinzufügen
            if (data.country) {
                addQuickActions(data.country);
            }

        } else if (data.type === 'weather_info') {
            // Wetter-Info
            appendChatMessage(data.answer, 'ai');
            window.chatHistory.push({ role: 'user', content: msg });
            window.chatHistory.push({ role: 'assistant', content: data.answer });

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

function appendChatMessage(text, sender, saveToStorage = true) {
    const chat = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;
    div.className = `chat-msg ${sender}`;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;

    // In localStorage speichern (außer Loading-Nachrichten)
    if (saveToStorage && text !== 'Denke nach...') {
        window.chatMessages.push({ type: sender, html: div.outerHTML, text: text });
        saveChatToStorage();
    }

    return id;
}

function appendChatMessageHTML(text, sender, visaInfo = null, saveToStorage = true) {
    const chat = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;

    // Visa-Warnung Styling
    let extraClass = '';
    if (visaInfo) {
        if (visaInfo.warning_level === 'critical') {
            extraClass = ' visa-critical';
        } else if (visaInfo.warning_level === 'high' || visaInfo.has_warning) {
            extraClass = ' visa-warning';
        } else if (visaInfo.visa_required) {
            extraClass = ' visa-info';
        }
    }

    div.className = `chat-msg ${sender}${extraClass}`;

    // Text mit Zeilenumbrüchen formatieren (XSS-sicher)
    div.innerHTML = sanitizeChatText(text);

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;

    // In localStorage speichern
    if (saveToStorage) {
        window.chatMessages.push({ type: sender + extraClass, html: div.outerHTML, text: text });
        saveChatToStorage();
    }

    return id;
}

function appendChatMessageWithLink(text, sender, visaInfo = null, aaUrl = null, saveToStorage = true) {
    const chat = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;

    // Visa-Warnung Styling
    let extraClass = '';
    if (visaInfo) {
        if (visaInfo.warning_level === 'critical') {
            extraClass = ' visa-critical';
        } else if (visaInfo.warning_level === 'high' || visaInfo.has_warning) {
            extraClass = ' visa-warning';
        } else if (visaInfo.visa_required) {
            extraClass = ' visa-info';
        }
    }

    div.className = `chat-msg ${sender}${extraClass}`;

    // Text formatieren und URLs klickbar machen (XSS-sicher)
    div.innerHTML = sanitizeChatTextWithLinks(text);

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;

    // In localStorage speichern
    if (saveToStorage) {
        window.chatMessages.push({ type: sender + extraClass, html: div.outerHTML, text: text });
        saveChatToStorage();
    }

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
    window.chatMessages = [];
    document.getElementById('chat-messages').innerHTML = '';
    localStorage.removeItem('flyai_chat_history');
    localStorage.removeItem('flyai_chat_messages');
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
