<p align="center">
  <img src="https://img.shields.io/badge/FlyAI-KI--gest%C3%BCtzte%20Reiseplattform-5ac8fa?style=for-the-badge&logo=airplane&logoColor=white" alt="FlyAI Badge"/>
</p>

<h1 align="center">FlyAI</h1>
<p align="center">
  <strong>Intelligente Reiseplattform mit KI-Chatbot, Flug- & Hotelsuche</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI"/>
  <img src="https://img.shields.io/badge/Design-Liquid%20Glass-bf5af2?style=flat-square" alt="Design"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#tech-stack">Tech Stack</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#api-dokumentation">API</a> &bull;
  <a href="#projektstruktur">Struktur</a> &bull;
  <a href="#screenshots">Screenshots</a>
</p>

---

## Ueber das Projekt

FlyAI ist eine vollstaendige Reiseplattform, die KI-gestuetzte Flug- und Hotelsuche mit einem intelligenten Chatbot kombiniert. Die Plattform vergleicht Preise ueber Skyscanner und bietet zusaetzlich automatische Visa-Informationen, Reisewarnungen vom Auswaertigen Amt und einen Warenkorb fuer die Reiseplanung.

Das Frontend nutzt ein **Apple Liquid Glass** Design-System, inspiriert von iOS 26 / macOS Tahoe -- mit durchscheinenden Glasoberflaechen, prismatischen Lichtbrechungseffekten und einem kuehlen Blau-Lila Farbschema.

---

## Features

### Flugsuche
- Echtzeit-Flugsuche ueber **Skyscanner API**
- Hin- & Rueckflug, Nur Hinflug, Multi-City
- Flughafen-Autocomplete mit IATA-Codes
- Erweiterte Filter (Airline, Preis, Stops, Dauer)
- Preisalarm-System mit E-Mail-Benachrichtigung

### Hotelsuche
- Hotelsuche ueber **Sky-Scrapper API**
- Ziel-Autocomplete
- Bewertungen, Ausstattung, Preisvergleich
- Buchungs-Integration

### KI-Chatbot (Reiseberater)
- **GPT-4** basierter Reiseberater mit Konversations-History
- Automatische Flug-/Hotelsuche aus natuerlicher Sprache
- Visa-Informationen fuer deutsche Staatsangehoerige
- Reisewarnungen & Sicherheitshinweise vom **Auswaertigen Amt**
- Wetter- und Klimainformationen
- Budget- und Reiseplanungs-Tipps
- Quick-Action Buttons fuer haeufige Anfragen

### Warenkorb
- Fluege und Hotels zum Warenkorb hinzufuegen
- Session-basierte Warenkorbverwaltung
- Gesamtpreis-Berechnung
- Checkout-Flow

### Weitere Features
- Benutzer-Authentifizierung (Login/Registrierung)
- Suchverlauf
- Responsive Design (Desktop, Tablet, Mobile)
- Dark Mode (Liquid Glass Aesthetic)
- Mehrsprachig vorbereitet (DE/EN)

---

## Tech Stack

### Frontend
| Technologie | Verwendung |
|---|---|
| **HTML5 / CSS3** | Seitenstruktur & Styling |
| **Vanilla JavaScript** | Interaktivitaet & API-Calls |
| **Clash Display + Satoshi** | Typografie (Fontshare) |
| **Font Awesome 6** | Icons |
| **CSS Backdrop-Filter** | Liquid Glass Effekte |

### Backend
| Technologie | Verwendung |
|---|---|
| **Python 3.13** | Backend-Sprache |
| **FastAPI** | REST API Framework |
| **Uvicorn** | ASGI Server |
| **SQLModel** | ORM & Datenbankmodelle |
| **SQLite** | Datenbank |
| **SlowAPI** | Rate Limiting |

### APIs & Services
| Service | Verwendung |
|---|---|
| **OpenAI GPT-4** | KI-Chatbot |
| **Skyscanner API** | Flugsuche (via RapidAPI) |
| **Sky-Scrapper API** | Hotelsuche (via RapidAPI) |
| **Auswaertiges Amt** | Reisewarnungen & Sicherheit |

---

## Installation

### Voraussetzungen

- Python 3.10+
- pip
- Ein moderner Browser (Chrome, Firefox, Safari)
- Live Server Extension (VS Code) oder vergleichbarer HTTP-Server

### 1. Repository klonen

```bash
git clone https://github.com/sakhiaryan/FlyAi.git
cd FlyAi
```

### 2. Backend einrichten

```bash
cd Backend

# Virtuelle Umgebung erstellen & aktivieren
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Abhaengigkeiten installieren
pip install -r requirements.txt
```

### 3. Umgebungsvariablen konfigurieren

Erstelle eine `.env` Datei im `Backend/` Verzeichnis:

```env
OPENAI_API_KEY=dein-openai-api-key
AMADEUS_API_KEY=dein-amadeus-key
AMADEUS_API_SECRET=dein-amadeus-secret
RAPIDAPI_KEY=dein-rapidapi-key
```

> **API Keys besorgen:**
> - OpenAI: [platform.openai.com](https://platform.openai.com/)
> - RapidAPI (Skyscanner & Hotels): [rapidapi.com](https://rapidapi.com/)
> - Amadeus (optional): [developers.amadeus.com](https://developers.amadeus.com/)

### 4. Backend starten

```bash
cd Backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Der Server laeuft auf `http://127.0.0.1:8000`

### 5. Frontend starten

Oeffne das `Frontend/` Verzeichnis mit einem HTTP-Server:

**Option A: VS Code Live Server**
- Rechtsklick auf `index.html` -> "Open with Live Server"

**Option B: Python HTTP Server**
```bash
cd Frontend
python -m http.server 5500
```

Die App ist erreichbar unter `http://127.0.0.1:5500`

---

## API-Dokumentation

Nach dem Start des Backends ist die interaktive API-Dokumentation verfuegbar:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/health` | Health Check |
| `GET` | `/airports?q=` | Flughafen-Suche (Autocomplete) |
| `GET` | `/search_flights` | Flugsuche via Skyscanner |
| `GET` | `/search_hotels` | Hotelsuche |
| `GET` | `/search_destination?q=` | Ziel-Autocomplete (Hotels) |
| `POST` | `/chat` | KI-Chat mit History |
| `GET` | `/smart_ask?question=` | Einfacher Chat (Legacy) |
| `GET` | `/search_history` | Suchverlauf |
| `POST` | `/cart/add` | Warenkorb: Item hinzufuegen |
| `GET` | `/cart/{session_id}` | Warenkorb: Items abrufen |
| `DELETE` | `/cart/remove` | Warenkorb: Item entfernen |
| `DELETE` | `/cart/clear/{session_id}` | Warenkorb: Leeren |
| `POST` | `/auth/login` | Benutzer-Login |
| `POST` | `/auth/register` | Registrierung |
| `GET` | `/auth/me` | Aktueller Benutzer |
| `GET` | `/visa/{country}` | Visa-Informationen |
| `GET` | `/travel-info/{country}` | Kombinierte Reiseinfo |
| `GET` | `/aa/{country}` | Auswaertiges Amt Link |

---

## Projektstruktur

```
FlyAi/
├── Backend/
│   ├── main.py                    # FastAPI App & alle Endpunkte
│   ├── requirements.txt           # Python-Abhaengigkeiten
│   ├── .env                       # API Keys (nicht im Repo)
│   ├── database.db                # SQLite Datenbank
│   ├── models/
│   │   ├── cart.py                # Warenkorb-Modell
│   │   ├── chat_cache.py          # Chat-Cache-Modell
│   │   ├── flight.py              # Flug-Modell
│   │   └── search_history.py      # Suchverlauf-Modell
│   ├── services/
│   │   ├── airport_service.py     # Flughafen-Suche
│   │   ├── amadeus_service.py     # Amadeus API Integration
│   │   ├── auswaertiges_amt_service.py  # AA Reisehinweise
│   │   ├── cart_service.py        # Warenkorb-Logik
│   │   ├── hotel_service.py       # Hotel-Suche API
│   │   ├── openai_service.py      # GPT-4 Integration
│   │   ├── skyscanner_service.py  # Skyscanner API
│   │   └── visa_service.py        # Visa-Datenbank
│   ├── routers/
│   │   └── flights.py             # Flug-Router
│   └── tests/
│       ├── test_api.py            # API-Tests
│       └── test_services.py       # Service-Tests
├── Frontend/
│   ├── index.html                 # Hauptseite (Flugsuche)
│   ├── hotels.html                # Hotelsuche
│   ├── mietwagen.html             # Mietwagen (Coming Soon)
│   ├── aktivitaeten.html          # Aktivitaeten (Coming Soon)
│   ├── style.css                  # Liquid Glass Design System
│   ├── app.js                     # Haupt-JavaScript
│   ├── hotel-app.js               # Hotel-spezifisches JS
│   └── tests/
│       ├── test_app.js            # Frontend-Tests
│       └── test_runner.html       # Test-Runner
├── Data/
│   └── data.sql                   # Datenbank-Schema
├── .gitignore
└── README.md
```

---

## Design System: Liquid Glass

Das UI basiert auf dem **Apple Liquid Glass** Designkonzept:

- **Glasoberflaechen**: Alle Karten und Panels nutzen `backdrop-filter: blur(40px)` mit transluzenten Hintergruenden
- **Prismatische Raender**: Subtile Regenbogen-Lichtbrechung an Elementkanten (Blau -> Lila -> Pink -> Orange -> Gruen)
- **Ambient Orbs**: Grosse, weiche Farbkugeln im Hintergrund, die durch die Glaselemente durchscheinen
- **Farbpalette**: Kuehles Blau (`#5ac8fa`) und Lila (`#bf5af2`) als Primaerfarben
- **Typografie**: Clash Display (Headlines) + Satoshi (Body) von Fontshare
- **Animationen**: CSS-only Orb-Drift, Shine-Effekte, sanfte Hover-Transitions

---

## Tests ausfuehren

### Backend-Tests
```bash
cd Backend
source venv/bin/activate
pytest tests/ -v
```

### Frontend-Tests
Oeffne `Frontend/tests/test_runner.html` im Browser.

---

## Umgebungsvariablen

| Variable | Beschreibung | Erforderlich |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API Key fuer den Chatbot | Ja |
| `RAPIDAPI_KEY` | RapidAPI Key fuer Skyscanner & Hotels | Ja |
| `AMADEUS_API_KEY` | Amadeus API Key (optional) | Nein |
| `AMADEUS_API_SECRET` | Amadeus API Secret (optional) | Nein |

---

## Rate Limiting

Die API verwendet Rate Limiting zum Schutz vor Missbrauch:

| Endpunkt | Limit |
|---|---|
| Flugsuche | 10 Anfragen/Minute |
| Hotelsuche | 10 Anfragen/Minute |
| Chat | 20 Anfragen/Minute |
| Flughafen-Autocomplete | 30 Anfragen/Minute |

---

## Roadmap

- [x] Flugsuche mit Skyscanner
- [x] KI-Chatbot mit GPT-4
- [x] Hotelsuche
- [x] Visa-Informationen
- [x] Warenkorb-System
- [x] Benutzer-Authentifizierung
- [x] Preisalarm-System
- [x] Liquid Glass Design
- [ ] Mietwagen-Integration
- [ ] Aktivitaeten-Buchung
- [ ] Zahlungsintegration (Stripe)
- [ ] Push-Benachrichtigungen
- [ ] Progressive Web App (PWA)
- [ ] Mehrsprachigkeit (EN, FR, ES)

---

## Mitwirken

Beitraege sind willkommen! So geht's:

1. Forke das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/neues-feature`)
3. Committe deine Aenderungen (`git commit -m 'Add: Neues Feature'`)
4. Pushe den Branch (`git push origin feature/neues-feature`)
5. Oeffne einen Pull Request

---

## Lizenz

Dieses Projekt steht unter der [MIT License](LICENSE).

---

<p align="center">
  Gebaut mit Leidenschaft von <a href="https://github.com/sakhiaryan">Aryan Sakhi</a>
</p>
