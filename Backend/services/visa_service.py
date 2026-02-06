"""
Visa & Reisepass Service
Prüft Visa-Anforderungen und gibt Warnungen für kritische Länder
"""

from typing import Dict, List, Optional

# Kritische Länder mit Visa-Pflicht für deutsche Staatsbürger
VISA_REQUIRED_COUNTRIES = {
    # Asien
    "china": {"visa": True, "type": "Visum vor Einreise", "warning": "high", "note": "Visum muss vor Reise bei Botschaft beantragt werden. Bearbeitungszeit: 4-7 Werktage."},
    "indien": {"visa": True, "type": "e-Visa oder Visum", "warning": "medium", "note": "E-Visum online möglich (mind. 4 Tage vorher). Klassisches Visum bei Botschaft."},
    "vietnam": {"visa": True, "type": "e-Visa", "warning": "low", "note": "E-Visum online für 30 Tage. Oder Visa on Arrival mit Genehmigungsschreiben."},
    "russland": {"visa": True, "type": "Visum vor Einreise", "warning": "high", "note": "Visum erforderlich. Einladung nötig. Aktuelle Reisewarnung beachten!"},
    "nordkorea": {"visa": True, "type": "Visum + Genehmigung", "warning": "critical", "note": "Nur organisierte Gruppenreisen. Extrem eingeschränkt."},
    "myanmar": {"visa": True, "type": "e-Visa", "warning": "high", "note": "E-Visum erforderlich. Aktuelle Sicherheitslage kritisch!"},
    "saudi-arabien": {"visa": True, "type": "e-Visa oder Visum", "warning": "medium", "note": "Touristenvisum seit 2019 möglich. E-Visum online."},
    "iran": {"visa": True, "type": "Visum vor Einreise", "warning": "high", "note": "Visum bei Botschaft. Aktuelle Reisewarnung beachten!"},
    "pakistan": {"visa": True, "type": "Visum vor Einreise", "warning": "high", "note": "Visum erforderlich. Sicherheitslage in manchen Regionen kritisch."},
    "afghanistan": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG! Nicht reisen! Extrem gefährlich."},
    "syrien": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG! Nicht reisen! Krieg und extreme Gefahr."},
    "jemen": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG! Nicht reisen! Krieg und humanitäre Krise."},
    "irak": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG für viele Regionen! Visum bei Botschaft."},
    "libyen": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG! Nicht reisen! Bürgerkriegssituation."},

    # Afrika
    "nigeria": {"visa": True, "type": "Visum vor Einreise", "warning": "high", "note": "Visum bei Botschaft. Sicherheitslage in vielen Regionen kritisch."},
    "kenia": {"visa": True, "type": "e-Visa", "warning": "medium", "note": "E-Visum online erforderlich. Safari-Destination."},
    "tansania": {"visa": True, "type": "e-Visa oder Visa on Arrival", "warning": "low", "note": "E-Visum empfohlen. Visa on Arrival möglich."},
    "äthiopien": {"visa": True, "type": "e-Visa", "warning": "medium", "note": "E-Visum online. Sicherheitslage in manchen Regionen beachten."},
    "ägypten": {"visa": True, "type": "Visa on Arrival oder e-Visa", "warning": "low", "note": "Visum am Flughafen (25 USD) oder vorher online."},
    "sudan": {"visa": True, "type": "Visum vor Einreise", "warning": "critical", "note": "REISEWARNUNG! Visum bei Botschaft. Aktuell sehr gefährlich."},
    "somalia": {"visa": True, "type": "Visum", "warning": "critical", "note": "REISEWARNUNG! Nicht reisen! Extrem gefährlich."},

    # Amerika
    "usa": {"visa": False, "type": "ESTA (Einreisegenehmigung)", "warning": "low", "note": "Kein Visum, aber ESTA erforderlich (mind. 72h vorher online, 21 USD)."},
    "kanada": {"visa": False, "type": "eTA (elektronische Reisegenehmigung)", "warning": "low", "note": "Kein Visum, aber eTA erforderlich (online, 7 CAD)."},
    "kuba": {"visa": True, "type": "Touristenkarte", "warning": "low", "note": "Touristenkarte erforderlich (erhältlich bei Airline oder Botschaft)."},
    "brasilien": {"visa": False, "type": "Visumfrei 90 Tage", "warning": "low", "note": "Kein Visum für Aufenthalte bis 90 Tage."},
    "venezuela": {"visa": False, "type": "Visumfrei 90 Tage", "warning": "high", "note": "Visumfrei, aber REISEWARNUNG wegen Sicherheitslage!"},

    # Ozeanien
    "australien": {"visa": True, "type": "eVisitor oder ETA", "warning": "low", "note": "eVisitor (kostenlos) oder ETA (20 AUD) online erforderlich."},
    "neuseeland": {"visa": False, "type": "NZeTA", "warning": "low", "note": "NZeTA (elektronische Reisegenehmigung) online erforderlich."},
}

# Visumfreie Länder für deutsche Staatsbürger
VISA_FREE_COUNTRIES = [
    # Europa (Schengen + EU)
    "deutschland", "österreich", "schweiz", "frankreich", "italien", "spanien",
    "portugal", "niederlande", "belgien", "luxemburg", "dänemark", "schweden",
    "norwegen", "finnland", "island", "griechenland", "polen", "tschechien",
    "ungarn", "kroatien", "slowenien", "slowakei", "rumänien", "bulgarien",
    "irland", "großbritannien", "uk", "england",

    # Weitere visumfreie
    "türkei", "japan", "südkorea", "singapur", "malaysia", "thailand",
    "indonesien", "philippinen", "mexiko", "argentinien", "chile", "peru",
    "kolumbien", "marokko", "tunesien", "südafrika", "israel",
    "vereinigte arabische emirate", "vae", "dubai", "katar", "bahrain", "oman",
]

# Länder mit Reisewarnungen (Stand: dynamisch aktualisieren)
TRAVEL_WARNINGS = {
    "afghanistan": "Reisewarnung - Nicht reisen!",
    "syrien": "Reisewarnung - Nicht reisen!",
    "jemen": "Reisewarnung - Nicht reisen!",
    "libyen": "Reisewarnung - Nicht reisen!",
    "somalia": "Reisewarnung - Nicht reisen!",
    "sudan": "Reisewarnung - Aktuelle Krise!",
    "nordkorea": "Reisewarnung - Nicht reisen!",
    "russland": "Reisewarnung - Nicht reisen!",
    "ukraine": "Reisewarnung - Nicht reisen (Krieg)!",
    "belarus": "Reisewarnung - Erhöhte Vorsicht!",
    "iran": "Reisewarnung - Erhöhte Vorsicht!",
    "irak": "Teilweise Reisewarnung",
    "venezuela": "Reisewarnung - Erhöhte Vorsicht!",
    "myanmar": "Reisewarnung - Erhöhte Vorsicht!",
    "haiti": "Reisewarnung - Nicht reisen!",
    "mali": "Reisewarnung - Nicht reisen!",
    "burkina faso": "Reisewarnung - Nicht reisen!",
    "niger": "Reisewarnung - Erhöhte Vorsicht!",
}


def normalize_country(country: str) -> str:
    """Normalisiert Ländernamen"""
    country = country.lower().strip()

    # Aliase
    aliases = {
        "vereinigte staaten": "usa",
        "united states": "usa",
        "america": "usa",
        "amerika": "usa",
        "vereinigtes königreich": "großbritannien",
        "united kingdom": "großbritannien",
        "england": "großbritannien",
        "uk": "großbritannien",
        "vae": "vereinigte arabische emirate",
        "emirates": "vereinigte arabische emirate",
        "korea": "südkorea",
        "süd korea": "südkorea",
        "north korea": "nordkorea",
        "nord korea": "nordkorea",
        "russia": "russland",
        "china": "china",
        "volksrepublik china": "china",
        "prc": "china",
    }

    return aliases.get(country, country)


def get_visa_info(country: str, passport_country: str = "deutschland") -> Dict:
    """
    Gibt Visa-Informationen für ein Land zurück

    Args:
        country: Zielland
        passport_country: Staatsbürgerschaft des Reisenden

    Returns:
        Dict mit visa_required, visa_type, warning_level, notes
    """
    country = normalize_country(country)

    # Prüfe auf Visa-Pflicht
    if country in VISA_REQUIRED_COUNTRIES:
        info = VISA_REQUIRED_COUNTRIES[country]
        return {
            "country": country.title(),
            "visa_required": info["visa"],
            "visa_type": info["type"],
            "warning_level": info["warning"],
            "notes": info["note"],
            "has_warning": country in TRAVEL_WARNINGS,
            "warning_text": TRAVEL_WARNINGS.get(country, "")
        }

    # Prüfe auf visumfreie Länder
    if country in VISA_FREE_COUNTRIES:
        return {
            "country": country.title(),
            "visa_required": False,
            "visa_type": "Visumfrei",
            "warning_level": "none",
            "notes": f"Kein Visum erforderlich für deutsche Staatsbürger.",
            "has_warning": country in TRAVEL_WARNINGS,
            "warning_text": TRAVEL_WARNINGS.get(country, "")
        }

    # Unbekanntes Land
    return {
        "country": country.title(),
        "visa_required": None,
        "visa_type": "Unbekannt",
        "warning_level": "unknown",
        "notes": "Bitte informiere dich bei der Botschaft des Ziellandes.",
        "has_warning": country in TRAVEL_WARNINGS,
        "warning_text": TRAVEL_WARNINGS.get(country, "")
    }


def get_travel_warning(country: str) -> Optional[str]:
    """Gibt Reisewarnung für ein Land zurück, falls vorhanden"""
    country = normalize_country(country)
    return TRAVEL_WARNINGS.get(country)


def check_passport_requirements(destination: str, passport_type: str = "deutsch") -> Dict:
    """
    Prüft Pass-Anforderungen

    Args:
        destination: Zielland
        passport_type: Art des Reisepasses

    Returns:
        Dict mit Anforderungen
    """
    destination = normalize_country(destination)

    # Generelle Anforderungen
    requirements = {
        "passport_validity": "6 Monate über Reiseende hinaus",
        "blank_pages": "Mindestens 2 leere Seiten empfohlen",
        "passport_type": passport_type,
    }

    # Spezielle Anforderungen je nach Land
    special_requirements = {
        "usa": "ESTA erforderlich, Maschinenlesbarer Reisepass (ePass)",
        "china": "Visum erforderlich, Pass 6 Monate gültig, 2 leere Seiten",
        "indien": "E-Visum oder Visum, Pass 6 Monate gültig",
        "australien": "eVisitor/ETA erforderlich, Biometrischer Pass empfohlen",
        "russland": "Visum erforderlich, Einladung nötig",
        "saudi-arabien": "E-Visum, keine Israel-Stempel im Pass",
        "iran": "Visum erforderlich, keine Israel-Stempel im Pass",
    }

    if destination in special_requirements:
        requirements["special_notes"] = special_requirements[destination]

    return requirements


def format_visa_warning_for_chat(country: str) -> str:
    """
    Formatiert Visa-Warnung für den Chatbot
    """
    info = get_visa_info(country)

    parts = []

    # Reisewarnung zuerst
    if info["has_warning"]:
        parts.append(f"⚠️ **ACHTUNG: {info['warning_text']}**")

    # Visa-Info
    if info["visa_required"] is True:
        parts.append(f"📋 **Visum erforderlich** für {info['country']}")
        parts.append(f"   Typ: {info['visa_type']}")
        parts.append(f"   {info['notes']}")
    elif info["visa_required"] is False:
        if "ESTA" in info.get("visa_type", "") or "eTA" in info.get("visa_type", ""):
            parts.append(f"📋 **{info['visa_type']} erforderlich** für {info['country']}")
            parts.append(f"   {info['notes']}")
        else:
            parts.append(f"✅ **Visumfrei** für {info['country']} (deutsche Staatsbürger)")
    else:
        parts.append(f"❓ Visa-Status für {info['country']} unbekannt - bitte bei Botschaft prüfen.")

    return "\n".join(parts)


def get_countries_needing_visa() -> List[str]:
    """Gibt Liste aller Länder zurück, die ein Visum benötigen"""
    return list(VISA_REQUIRED_COUNTRIES.keys())


def get_critical_countries() -> List[str]:
    """Gibt Liste aller Länder mit Reisewarnung zurück"""
    return list(TRAVEL_WARNINGS.keys())
