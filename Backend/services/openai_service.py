import openai
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("flyai.openai")

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Du bist FlyAI, ein erstklassiger KI-Reiseberater - wie ein erfahrener Freund, der die ganze Welt kennt.

DEIN STIL:
- Antworte kurz, natuerlich und auf Augenhöhe - wie ein reiseerfahrener Kumpel
- Max 2-3 Saetze pro Antwort, ausser der User fragt explizit nach Details
- Antworte IMMER auf Deutsch, es sei denn der User schreibt auf Englisch
- Nutze ab und zu ein Emoji, aber uebertreib nicht

PROAKTIVES VERHALTEN (wie Booking.com & Kayak):
- Wenn der User ein Reiseziel nennt, frag proaktiv: "Wann moechtest du hin?" und "Wie viele Personen?"
- Wenn ein Flug gefunden wurde, schlage automatisch vor: "Soll ich auch Hotels dort suchen?"
- Wenn Budget genannt wird, passe Empfehlungen an (Budget/Mittel/Luxus)
- Biete immer den naechsten logischen Schritt an

REISEBERATUNG (wie Hopper & Expedia):
- Gib saisonale Tipps: "November ist perfekt fuer Thailand - Trockenzeit und weniger Touristen!"
- Nenne Geheimtipps und lokale Empfehlungen
- Bei Staedtetrips: Empfehle Viertel zum Uebernachten
- Bei Strandurlaub: Nenne die besten Straende
- Gib kulturelle Hinweise: "In Japan Schuhe ausziehen beim Betreten von Haeusern"

PAKET-EMPFEHLUNGEN:
- Wenn Flug + Hotel gefragt: Kombiniere beides und zeige Ersparnis
- Schlage Komplettpakete vor: "Flug + 5 Naechte Hotel ab ca. X EUR"
- Bei Familienreisen: Weise auf kinderfreundliche Hotels hin

WICHTIG FUER VISA & SICHERHEIT:
- Wenn du Infos vom Auswaertigen Amt bekommst, nutze diese als Hauptquelle
- Erwaehne bei Visa/Sicherheitsfragen kurz "laut Auswaertigem Amt"
- Bei Reisewarnungen: Immer ernst nehmen und User warnen
- Bleib trotzdem locker, aber bei Sicherheit keine Witze

KONTEXT-MERKEN:
- Merke dir den Namen, Budget, Reisestil und Praeferenzen des Users
- Beziehe dich auf fruehere Nachrichten: "Du hattest nach Thailand gefragt - da hab ich noch was..."
- Wenn Zielland bekannt: Erinnere an Visa, Impfungen, beste Reisezeit

BEISPIELE fuer gute Antworten:
- "Paris hat mega gutes Essen! Suchst du was Bestimmtes - fancy, casual oder Street Food?"
- "Als Deutscher brauchst du fuer Japan kein Visum - bis 90 Tage easy mit Reisepass!"
- "Bali im August? Perfekt - Trockenzeit! Soll ich Fluege suchen?"
- "Fuer 1000 EUR Budget wuerde ich Suedostasien empfehlen - Flug ab 400 EUR, vor Ort super guenstig!"

Bleib locker und hilf dem User bei allem rund ums Reisen - Fluege, Hotels, Visa, Tipps, Packlisten, Budget, was auch immer.
"""


def ask_chatgpt_with_history(messages: list):
    """Chat mit Konversations-History"""

    # System-Prompt am Anfang hinzufuegen
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    full_messages.extend(messages)

    try:
        logger.info("OpenAI request: %d messages", len(full_messages))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            max_tokens=500,
            temperature=0.7,
            timeout=30.0,
        )
        logger.info("OpenAI response received (tokens: %s)", response.usage.total_tokens if response.usage else "unknown")
        return response.choices[0].message.content
    except openai.APITimeoutError:
        logger.error("OpenAI API timeout")
        return "Entschuldigung, die Antwort hat zu lange gedauert. Bitte versuche es nochmal."
    except openai.RateLimitError:
        logger.error("OpenAI API rate limit exceeded")
        return "Zu viele Anfragen gerade. Bitte warte einen Moment und versuche es nochmal."
    except openai.APIConnectionError as e:
        logger.error("OpenAI API connection error: %s", e)
        return "Verbindungsproblem mit dem Chat-Service. Bitte versuche es nochmal."
    except openai.APIError as e:
        logger.error("OpenAI API error: %s", e)
        return "Ein Fehler ist aufgetreten. Bitte versuche es nochmal."


def ask_chatgpt_structured(prompt: str, json_schema: dict = None):
    """
    Structured Output: Erzwingt JSON-Antwort von OpenAI.
    Nutzt response_format fuer garantiert valides JSON.

    Args:
        prompt: Die Frage/Anfrage
        json_schema: Optionales JSON-Schema fuer die Antwort

    Returns:
        dict: Parsed JSON-Antwort von OpenAI
    """
    messages = [
        {"role": "system", "content": "Du bist ein JSON-API-Assistent. Antworte IMMER mit validem JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        logger.info("OpenAI structured output request")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.3,
            timeout=30.0,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        logger.info("Structured output received (tokens: %s)", response.usage.total_tokens if response.usage else "unknown")
        return result
    except openai.APITimeoutError:
        logger.error("OpenAI structured output timeout")
        return {"error": "Timeout", "action": "chat"}
    except openai.RateLimitError:
        logger.error("OpenAI structured output rate limit")
        return {"error": "Rate limit", "action": "chat"}
    except (openai.APIError, openai.APIConnectionError) as e:
        logger.error("OpenAI structured output error: %s", e)
        return {"error": str(e), "action": "chat"}
    except json.JSONDecodeError as e:
        logger.error("Failed to parse structured output JSON: %s", e)
        return {"error": "JSON parse error", "action": "chat"}


def detect_intent(question: str, chat_history: list = None):
    """
    Erweiterte Intent-Erkennung mit KI.
    Erkennt Pauschalreise, Inspiration, Vergleich, Packliste, Budget etc.
    """
    history_context = ""
    if chat_history and len(chat_history) > 0:
        last_messages = chat_history[-6:]  # Letzte 3 Paare
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in last_messages])

    prompt = f"""Analysiere die User-Anfrage und den Konversationsverlauf.

Konversationsverlauf:
{history_context}

Aktuelle Anfrage: "{question}"

Erkenne den Intent und antworte mit JSON:
{{
    "intent": "einer von: flight_search, hotel_search, package_search, inspiration, compare, packing_list, budget_calc, visa_info, weather, planning, cart, general_chat",
    "destination": "Zielort falls erwaehnt oder null",
    "destination_country": "Zielland falls erwaehnt oder null",
    "origin": "Abflugort falls erwaehnt oder null",
    "date": "Reisedatum YYYY-MM-DD falls erwaehnt oder null",
    "return_date": "Rueckreisedatum YYYY-MM-DD falls erwaehnt oder null",
    "budget": "Budget in EUR falls erwaehnt oder null",
    "travelers": "Anzahl Reisende falls erwaehnt oder null",
    "compare_destinations": ["Ort1", "Ort2"] oder null,
    "season": "Jahreszeit falls erwaehnt oder null",
    "preferences": "Praeferenzen wie luxury, budget, family, adventure oder null",
    "suggested_replies": ["Vorschlag 1", "Vorschlag 2", "Vorschlag 3"]
}}

WICHTIG fuer suggested_replies - waehle 2-4 passende Follow-up Vorschlaege:
- Nach Flugsuche: ["Hotels anzeigen", "Guenstigerer Flug?", "Visa-Info", "Packliste"]
- Nach Hotelsuche: ["Aktivitaeten vor Ort", "Beste Restaurants", "Transfer zum Hotel"]
- Nach Inspiration: ["Fluege suchen", "Hotels anzeigen", "Mehr Infos"]
- Nach Visa-Info: ["Fluege suchen", "Hotels suchen", "Reiseversicherung"]
- Nach Budget: ["Guenstige Fluege", "Budget Hotels", "Spartipps"]
- Nach Packliste: ["Fluege suchen", "Wetter checken", "Visa-Info"]
- Allgemein: ["Wohin soll ich reisen?", "Guenstige Deals", "Reise planen"]
"""

    result = ask_chatgpt_structured(prompt)

    # Fallback wenn KI-Erkennung fehlschlaegt
    if "error" in result or "intent" not in result:
        return {
            "intent": "general_chat",
            "destination": None,
            "suggested_replies": ["Wohin soll ich reisen?", "Guenstige Fluege", "Reise planen"]
        }

    return result


def generate_inspiration(preferences: str = None, budget: str = None, season: str = None):
    """Generiert Reise-Inspirationen basierend auf Praeferenzen"""
    prompt = f"""Du bist ein Reise-Inspirator. Schlage 3 tolle Reiseziele vor.

Praeferenzen: {preferences or 'keine angegeben'}
Budget: {budget or 'flexibel'}
Jahreszeit: {season or 'egal'}

Fuer jedes Ziel nenne:
1. Ort + Land
2. Warum gerade jetzt (1 Satz)
3. Geschaetzter Flugpreis ab Deutschland
4. Ein Geheimtipp

Halte es kurz und spannend! Nutze Emojis fuer Lesbarkeit."""

    return ask_chatgpt_with_history([{"role": "user", "content": prompt}])


def generate_comparison(dest1: str, dest2: str):
    """Vergleicht zwei Reiseziele"""
    prompt = f"""Vergleiche {dest1} und {dest2} als Reiseziele.

Vergleiche kurz (max 150 Woerter):
- Flugpreis ab Deutschland (geschaetzt)
- Beste Reisezeit
- Visa fuer Deutsche
- Tagesbudget vor Ort
- Highlights

Fazit: Welches Ziel fuer welchen Reisetyp?
Nutze Emojis und halte es uebersichtlich."""

    return ask_chatgpt_with_history([{"role": "user", "content": prompt}])


def generate_packing_list(destination: str, season: str = None, duration: str = None):
    """Generiert eine Packliste basierend auf Ziel und Jahreszeit"""
    prompt = f"""Erstelle eine kompakte Packliste fuer {destination}.

Jahreszeit: {season or 'nicht angegeben'}
Reisedauer: {duration or 'ca. 1 Woche'}

Kategorien:
- Kleidung (an Klima anpassen!)
- Dokumente & Geld
- Technik
- Hygiene
- Spezial fuer {destination}

Max 15 Items gesamt. Kurz und praktisch!
Nutze passende Emojis."""

    return ask_chatgpt_with_history([{"role": "user", "content": prompt}])


def generate_budget_calc(destination: str, duration: str = None, travelers: str = None, style: str = None):
    """Kalkuliert ein Reisebudget"""
    prompt = f"""Erstelle eine Budget-Kalkulation fuer eine Reise nach {destination}.

Reisedauer: {duration or '7 Tage'}
Reisende: {travelers or '2 Personen'}
Reisestil: {style or 'Mittelklasse'}

Aufschluesselung:
- Fluege (geschaetzt, hin + rueck pro Person)
- Unterkunft (pro Nacht)
- Essen (pro Tag)
- Transport vor Ort (pro Tag)
- Aktivitaeten/Eintritte
- GESAMT

Gib Budget/Mittel/Luxus Varianten.
Nutze EUR und halte es uebersichtlich."""

    return ask_chatgpt_with_history([{"role": "user", "content": prompt}])


def generate_suggested_replies(response_type: str, destination: str = None, context: dict = None):
    """
    Generiert kontextbezogene Suggested Replies.
    Wird als Fallback genutzt wenn die KI keine suggested_replies liefert.
    """
    replies_map = {
        "flight_search": [
            f"Hotels in {destination}" if destination else "Hotels suchen",
            "Guenstigerer Flug?",
            "Visa-Info",
            "Packliste erstellen"
        ],
        "hotel_search": [
            "Aktivitaeten vor Ort",
            "Beste Restaurants",
            f"Fluege nach {destination}" if destination else "Fluege suchen",
            "Transfer zum Hotel"
        ],
        "package_search": [
            "Guenstiger?",
            "Andere Daten",
            "Mehr Details",
            "Buchen"
        ],
        "inspiration": [
            "Fluege suchen",
            "Hotels anzeigen",
            "Mehr Inspirationen",
            "Budget berechnen"
        ],
        "compare": [
            "Fluege zum Favoriten",
            "Hotels vergleichen",
            "Andere Ziele vergleichen"
        ],
        "packing_list": [
            "Fluege suchen",
            "Wetter checken",
            "Visa-Info"
        ],
        "budget_calc": [
            "Guenstige Fluege suchen",
            "Budget Hotels",
            "Spartipps"
        ],
        "visa_info": [
            f"Fluege nach {destination}" if destination else "Fluege suchen",
            "Hotels suchen",
            "Reiseversicherung",
            "Packliste"
        ],
        "travel_info": [
            f"Fluege nach {destination}" if destination else "Fluege suchen",
            f"Hotels in {destination}" if destination else "Hotels suchen",
            "Visa-Info"
        ],
        "travel_planning": [
            f"Fluege nach {destination}" if destination else "Fluege suchen",
            f"Hotels in {destination}" if destination else "Hotels suchen",
            "Budget berechnen",
            "Packliste"
        ],
        "weather_info": [
            "Fluege suchen",
            "Hotels suchen",
            "Beste Reisezeit?"
        ],
        "cart": [
            "Weiter suchen",
            "Hotels hinzufuegen",
            "Zur Buchung"
        ],
        "general_chat": [
            "Wohin soll ich reisen?",
            "Guenstige Deals",
            "Reise planen",
            "Budget berechnen"
        ]
    }

    return replies_map.get(response_type, replies_map["general_chat"])


def ask_chatgpt(prompt: str):
    """Einfache Frage ohne History (fuer Kompatibilitaet)"""
    return ask_chatgpt_with_history([{"role": "user", "content": prompt}])
