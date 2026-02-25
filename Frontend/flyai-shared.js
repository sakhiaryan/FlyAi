/**
 * FlyAI Shared Utilities
 * Provides consistent cart, session, auth, and chat functionality
 * across all pages (hotels, mietwagen, aktivitaeten).
 *
 * index.html/app.js has its own full implementation.
 * This file is for secondary pages that need the same features.
 */

const API_URL = 'http://127.0.0.1:8000';

// ==================== SESSION MANAGEMENT ====================
let sessionId = localStorage.getItem('flyai_session') || generateSessionId();
localStorage.setItem('flyai_session', sessionId);

function generateSessionId() {
    return 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

// ==================== LANGUAGE ====================
let currentLanguage = localStorage.getItem('flyai_language') || 'de';

// ==================== XSS SANITIZATION ====================
function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function sanitizeChatText(text) {
    let safe = escapeHTML(text);
    safe = safe.replace(/\n/g, '<br>');
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return safe;
}

function sanitizeChatTextWithLinks(text) {
    let safe = sanitizeChatText(text);
    safe = safe.replace(
        /(https?:\/\/[^\s<&]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer" class="chat-link">$1</a>'
    );
    return safe;
}

// ==================== CART ====================
let cart = [];

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
                <span>Fuege Fluege, Hotels oder Mietwagen hinzu</span>
            </div>
        `;
        if (cartFooter) cartFooter.style.display = 'none';
    } else {
        let total = 0;
        cartItems.innerHTML = cart.map(item => {
            total += item.price;
            const icon = item.type === 'flight' ? 'fa-plane' : item.type === 'hotel' ? 'fa-hotel' : item.type === 'car' ? 'fa-car' : 'fa-ticket';
            const data = item.data;

            let title = '';
            let details = '';

            if (item.type === 'flight') {
                title = `${data.from} → ${data.to}`;
                details = `${data.carrier || ''} ${data.flightNum || ''} | ${data.depTime || ''}`;
            } else if (item.type === 'hotel') {
                title = data.name || 'Hotel';
                details = `${data.nights || 1} Naechte | ${data.address || ''}`;
            } else if (item.type === 'car') {
                title = data.name || 'Mietwagen';
                details = `${data.supplier || ''} | ${data.days || ''} Tage`;
            } else {
                title = data.name || 'Aktivitaet';
                details = data.description || '';
            }

            return `
                <div class="cart-item">
                    <div class="cart-item-header">
                        <span class="cart-item-type ${item.type}">
                            <i class="fa-solid ${icon}"></i>
                            ${item.type === 'flight' ? 'Flug' : item.type === 'hotel' ? 'Hotel' : item.type === 'car' ? 'Mietwagen' : 'Aktivitaet'}
                        </span>
                        <button class="cart-item-remove" onclick="removeFromCart(${item.id})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                    <div class="cart-item-title">${escapeHTML(title)}</div>
                    <div class="cart-item-details">${escapeHTML(details)}</div>
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
            const typeLabel = type === 'flight' ? 'Flug' : type === 'hotel' ? 'Hotel' : type === 'car' ? 'Mietwagen' : 'Aktivitaet';
            showToast(`${typeLabel} zum Warenkorb hinzugefuegt!`, 'success');
        } else {
            showToast(data.error || 'Fehler beim Hinzufuegen', 'error');
        }
    } catch (e) {
        console.error('addToCart error:', e);
        showToast('Fehler beim Hinzufuegen zum Warenkorb', 'error');
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

// ==================== TOAST NOTIFICATIONS ====================
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fa-solid fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'triangle-exclamation' : 'info-circle'}"></i>
        <span>${escapeHTML(message)}</span>
    `;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== AUTH / USER UI ====================
function updateUserUI() {
    const user = JSON.parse(localStorage.getItem('flyai_user') || 'null');
    const loginBtns = document.querySelectorAll('.btn-login');

    loginBtns.forEach(btn => {
        if (user) {
            btn.innerHTML = `<i class="fa-solid fa-user-circle"></i><span>${escapeHTML(user.name)}</span>`;
            btn.onclick = showUserMenu;
        } else {
            btn.innerHTML = `<i class="fa-solid fa-user"></i><span>${currentLanguage === 'de' ? 'Anmelden' : 'Sign In'}</span>`;
            btn.onclick = showLoginModal;
        }
    });
}

function showUserMenu() {
    const user = JSON.parse(localStorage.getItem('flyai_user') || 'null');
    if (!user) return showLoginModal();

    if (confirm(currentLanguage === 'de' ? 'Moechtest du dich abmelden?' : 'Do you want to sign out?')) {
        localStorage.removeItem('flyai_user');
        localStorage.removeItem('flyai_token');
        showToast(currentLanguage === 'de' ? 'Abgemeldet!' : 'Signed out!', 'success');
        updateUserUI();
    }
}

function showLoginModal() {
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
                    <div class="logo-icon"><i class="fa-solid fa-plane"></i></div>
                    <span class="logo-text" style="color: #1a1a2e;">Fly<span class="logo-highlight">AI</span></span>
                </div>
                <h2>${currentLanguage === 'de' ? 'Willkommen zurueck!' : 'Welcome back!'}</h2>
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
                <button type="submit" class="login-submit">
                    <i class="fa-solid fa-arrow-right"></i> ${currentLanguage === 'de' ? 'Anmelden' : 'Sign In'}
                </button>
            </form>
            <form class="register-form" id="register-form" onsubmit="handleRegister(event)" style="display: none;">
                <div class="login-field">
                    <label><i class="fa-solid fa-user"></i> Name</label>
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
        </div>
    `;
    document.body.appendChild(modal);
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

    const submitBtn = document.querySelector('#login-form .login-submit');
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Anmelden...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.success) {
            localStorage.setItem('flyai_user', JSON.stringify(data.user));
            localStorage.setItem('flyai_token', data.token);
            showToast(data.message || 'Erfolgreich angemeldet!', 'success');
            closeLoginModal();
            updateUserUI();
        } else {
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

    if (name.length < 2) {
        showToast('Name muss mindestens 2 Zeichen haben', 'error');
        return;
    }
    if (password.length < 8) {
        showToast('Passwort muss mindestens 8 Zeichen haben', 'error');
        return;
    }

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

// ==================== CHAT (for secondary pages) ====================
// Chat history shared across pages via localStorage
window.chatHistory = JSON.parse(localStorage.getItem('flyai_chat_history') || '[]');

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
                messages: window.chatHistory,
                question: msg,
                session_id: sessionId
            })
        });

        const data = await res.json();
        removeChatMessage(loadingId);

        const answer = data.answer || data.message || 'Keine Antwort';
        appendChatMessage(answer, 'ai');

        // Update history
        window.chatHistory.push({ role: 'user', content: msg });
        window.chatHistory.push({ role: 'assistant', content: answer });

        // Keep history manageable
        if (window.chatHistory.length > 20) {
            window.chatHistory = window.chatHistory.slice(-20);
        }
        localStorage.setItem('flyai_chat_history', JSON.stringify(window.chatHistory));

    } catch (e) {
        removeChatMessage(loadingId);
        appendChatMessage('Fehler beim Abrufen der Antwort. Bitte versuche es erneut.', 'ai');
    }
}

function appendChatMessage(text, sender) {
    const chat = document.getElementById('chat-messages');
    if (!chat) return null;
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

// ==================== MOBILE MENU ====================
function toggleMobileMenu() {
    const mobileNav = document.querySelector('.mobile-nav');
    const overlay = document.querySelector('.mobile-nav-overlay');
    const menuBtn = document.querySelector('.mobile-menu-btn');

    if (mobileNav && overlay) {
        mobileNav.classList.toggle('active');
        overlay.classList.toggle('active');
        menuBtn?.classList.toggle('active');
        document.body.style.overflow = mobileNav.classList.contains('active') ? 'hidden' : '';
    }
}

// ==================== CART SIDEBAR INJECTION ====================
function injectCartSidebar() {
    // Only inject if not already present
    if (document.getElementById('cart-sidebar')) return;

    const cartHTML = `
    <div id="cart-sidebar" class="cart-sidebar">
        <div class="cart-sidebar-header">
            <h3><i class="fa-solid fa-shopping-cart"></i> Dein Warenkorb</h3>
            <button class="cart-close-btn" onclick="toggleCart()" aria-label="Warenkorb schliessen"><i class="fa-solid fa-times"></i></button>
        </div>
        <div id="cart-items" class="cart-items">
            <div class="cart-empty">
                <i class="fa-solid fa-shopping-cart"></i>
                <p>Dein Warenkorb ist leer</p>
                <span>Fuege Fluege, Hotels oder Mietwagen hinzu</span>
            </div>
        </div>
        <div id="cart-footer" class="cart-footer" style="display: none;">
            <div class="cart-total">
                <span>Gesamt:</span>
                <span id="cart-total-price">0 EUR</span>
            </div>
            <button class="cart-checkout-btn" onclick="checkout()">
                <i class="fa-solid fa-credit-card"></i> Zur Buchung
            </button>
        </div>
    </div>
    <div id="cart-overlay" class="cart-overlay" onclick="toggleCart()"></div>
    `;

    document.body.insertAdjacentHTML('beforeend', cartHTML);
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    // Inject cart sidebar if needed
    injectCartSidebar();

    // Update user UI (login state)
    updateUserUI();

    // Load cart from backend
    loadCart();

    // Fix cart button on secondary pages: open cart sidebar instead of redirecting
    const cartBtn = document.querySelector('.btn-cart');
    if (cartBtn) {
        cartBtn.setAttribute('onclick', 'toggleCart()');
    }
});
