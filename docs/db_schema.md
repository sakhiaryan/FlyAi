# FlyAI — Database Schema

## Entity Relationship Diagram (Text-Format)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FlyAI Database (SQLite)                       │
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐                │
│  │     SearchHistory     │    │      ChatCache        │               │
│  ├──────────────────────┤    ├──────────────────────┤                │
│  │ PK id: INTEGER        │    │ PK id: INTEGER        │               │
│  │    from_airport: TEXT  │    │ IX question: TEXT      │               │
│  │    to_airport: TEXT    │    │    answer: TEXT        │               │
│  │    date: TEXT          │    │    created_at: DATETIME│               │
│  │    timestamp: DATETIME │    └──────────────────────┘                │
│  └──────────────────────┘                                            │
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐                │
│  │       CartItem        │    │       Flight          │               │
│  ├──────────────────────┤    ├──────────────────────┤                │
│  │ PK id: INTEGER        │    │ PK id: INTEGER        │               │
│  │ IX session_id: TEXT    │    │    origin: TEXT        │               │
│  │    item_type: TEXT     │    │    destination: TEXT   │               │
│  │    item_data: TEXT(JSON)│   │    departure_date: TEXT│               │
│  │    price: REAL         │    │    airline: TEXT (NULL) │              │
│  │    currency: TEXT      │    │    price: REAL (NULL)  │               │
│  │    quantity: INTEGER   │    │    currency: TEXT (NULL)│              │
│  │    added_at: DATETIME  │    │    stops: INTEGER(NULL)│               │
│  └──────────────────────┘    └──────────────────────┘                │
│                                                                      │
│  Legend:  PK = Primary Key   IX = Indexed   NULL = Nullable          │
└─────────────────────────────────────────────────────────────────────┘
```

## Tabellen-Details

### 1. SearchHistory
Speichert alle Flugsuchen der User für Analytics und Vorschläge.

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Eindeutige ID |
| `from_airport` | TEXT | NOT NULL | Abflughafen (IATA-Code) |
| `to_airport` | TEXT | NOT NULL | Zielflughafen (IATA-Code) |
| `date` | TEXT | NOT NULL | Reisedatum (YYYY-MM-DD) |
| `timestamp` | DATETIME | DEFAULT UTC NOW | Zeitstempel der Suche |

### 2. ChatCache
Cache für häufige Chat-Fragen, spart OpenAI API-Kosten.

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Eindeutige ID |
| `question` | TEXT | NOT NULL, INDEXED | Gestellte Frage |
| `answer` | TEXT | NOT NULL | Gecachte Antwort |
| `created_at` | DATETIME | DEFAULT UTC NOW | Cache-Zeitstempel |

### 3. CartItem
Warenkorb-Items (Flüge, Hotels, Aktivitäten) — Session-basiert.

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Eindeutige ID |
| `session_id` | TEXT | NOT NULL, INDEXED | Session/User ID |
| `item_type` | TEXT | NOT NULL | Typ: "flight", "hotel", "activity" |
| `item_data` | TEXT | NOT NULL | JSON-String mit Item-Details |
| `price` | REAL | NOT NULL | Preis des Items |
| `currency` | TEXT | DEFAULT "EUR" | Währung |
| `quantity` | INTEGER | DEFAULT 1 | Anzahl |
| `added_at` | DATETIME | DEFAULT UTC NOW | Hinzugefügt am |

### 4. Flight
Gespeicherte Flugdaten aus Suchergebnissen.

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Eindeutige ID |
| `origin` | TEXT | NOT NULL | Abflughafen |
| `destination` | TEXT | NOT NULL | Zielflughafen |
| `departure_date` | TEXT | NOT NULL | Abflugdatum |
| `airline` | TEXT | NULLABLE | Fluggesellschaft |
| `price` | REAL | NULLABLE | Preis |
| `currency` | TEXT | NULLABLE | Währung |
| `stops` | INTEGER | NULLABLE | Anzahl Zwischenstopps |

## Beziehungen

```
SearchHistory  ──(1:N)──  CartItem    (über session_id Kontext)
CartItem       ──(N:1)──  Flight      (item_type="flight", item_data referenziert Flugdaten)
ChatCache      ──(standalone)──        (unabhängiger Cache)
```

## In-Memory Datenstrukturen

Zusätzlich zu SQLite werden folgende Daten im Arbeitsspeicher gehalten:

### fake_users_db (dict)
```python
{
    "email@example.com": {
        "id": int,
        "name": str,
        "email": str,
        "password": str,  # bcrypt-gehashed
        "created_at": str  # ISO-Format
    }
}
```

### Visa-Datenbank (services/visa_service.py)
- 45+ Länder mit Visa-Anforderungen
- Kategorien: visumfrei, ESTA, Visum erforderlich, kritisch
- Warnstufen: none, low, high, critical

### Airport-Datenbank (services/airport_service.py)
- 50+ internationale Flughäfen
- Felder: code (IATA), name, city, country
