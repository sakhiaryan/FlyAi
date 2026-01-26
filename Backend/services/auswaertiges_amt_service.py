import httpx
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict

# Mapping von Ländernamen zu URL-Slugs auf auswaertiges-amt.de
COUNTRY_SLUGS = {
    # Europa
    "frankreich": "frankreich",
    "spanien": "spanien",
    "italien": "italien",
    "griechenland": "griechenland",
    "portugal": "portugal",
    "niederlande": "niederlande",
    "holland": "niederlande",
    "belgien": "belgien",
    "österreich": "oesterreich",
    "schweiz": "schweiz",
    "polen": "polen",
    "tschechien": "tschechien",
    "ungarn": "ungarn",
    "kroatien": "kroatien",
    "türkei": "tuerkei",
    "grossbritannien": "grossbritannien",
    "england": "grossbritannien",
    "uk": "grossbritannien",
    "irland": "irland",
    "schweden": "schweden",
    "norwegen": "norwegen",
    "finnland": "finnland",
    "dänemark": "daenemark",

    # Asien
    "thailand": "thailand",
    "vietnam": "vietnam",
    "japan": "japan",
    "china": "china",
    "südkorea": "korearepublik",
    "korea": "korearepublik",
    "indien": "indien",
    "indonesien": "indonesien",
    "bali": "indonesien",
    "malaysia": "malaysia",
    "singapur": "singapur",
    "philippinen": "philippinen",
    "kambodscha": "kambodscha",
    "sri lanka": "srilanka",
    "nepal": "nepal",
    "taiwan": "taiwan",
    "hongkong": "hongkong",
    "malediven": "malediven",
    "vereinigte arabische emirate": "vereinigtearabischeemirate",
    "vae": "vereinigtearabischeemirate",
    "dubai": "vereinigtearabischeemirate",
    "katar": "katar",
    "israel": "israel",
    "jordanien": "jordanien",

    # Amerika
    "usa": "usa",
    "vereinigte staaten": "usa",
    "amerika": "usa",
    "kanada": "kanada",
    "mexiko": "mexiko",
    "brasilien": "brasilien",
    "argentinien": "argentinien",
    "chile": "chile",
    "peru": "peru",
    "kolumbien": "kolumbien",
    "kuba": "kuba",
    "dominikanische republik": "dominikanischerepublik",
    "costa rica": "costarica",
    "panama": "panama",

    # Afrika
    "ägypten": "aegypten",
    "marokko": "marokko",
    "tunesien": "tunesien",
    "südafrika": "suedafrika",
    "kenia": "kenia",
    "tansania": "tansania",
    "namibia": "namibia",
    "mauritius": "mauritius",
    "seychellen": "seychellen",

    # Ozeanien
    "australien": "australien",
    "neuseeland": "neuseeland",
    "fidschi": "fidschi",
}


def get_country_slug(country: str) -> Optional[str]:
    """Findet den URL-Slug für ein Land"""
    country_lower = country.lower().strip()

    # Direkte Suche
    if country_lower in COUNTRY_SLUGS:
        return COUNTRY_SLUGS[country_lower]

    # Teilsuche
    for key, slug in COUNTRY_SLUGS.items():
        if country_lower in key or key in country_lower:
            return slug

    return None


async def fetch_travel_info(country: str) -> Dict:
    """
    Holt Reise- und Sicherheitshinweise vom Auswärtigen Amt.

    Returns:
        Dict mit: visa_info, safety_warning, entry_requirements, source_url
    """
    slug = get_country_slug(country)

    if not slug:
        return {
            "success": False,
            "error": f"Land '{country}' nicht gefunden",
            "country": country
        }

    url = f"https://www.auswaertiges-amt.de/de/service/laender/{slug}-node/{slug}/reise-und-sicherheitshinweise"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers, follow_redirects=True)

            if response.status_code != 200:
                # Versuche alternative URL
                alt_url = f"https://www.auswaertiges-amt.de/de/aussenpolitik/laender/{slug}-node"
                response = await client.get(alt_url, headers=headers, follow_redirects=True)

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Seite nicht erreichbar (Status: {response.status_code})",
                        "country": country
                    }

            soup = BeautifulSoup(response.text, 'html.parser')

            result = {
                "success": True,
                "country": country,
                "source_url": str(response.url),
                "visa_info": None,
                "safety_warning": None,
                "entry_requirements": None,
                "current_warnings": []
            }

            # Suche nach Reisewarnung/Sicherheitshinweis im Header
            warning_box = soup.find('div', class_='reisewarnung') or soup.find('div', class_='c-teaser--warning')
            if warning_box:
                result["safety_warning"] = warning_box.get_text(strip=True)[:500]

            # Suche nach aktuellem Hinweis (Aktuelles)
            aktuelles = soup.find('h2', string=re.compile(r'Aktuelles', re.I))
            if aktuelles:
                aktuelles_content = aktuelles.find_next('div')
                if aktuelles_content:
                    text = aktuelles_content.get_text(strip=True)[:800]
                    result["current_warnings"].append(text)

            # Suche nach Einreise-Infos
            einreise = soup.find('h2', string=re.compile(r'Einreise', re.I)) or soup.find('h3', string=re.compile(r'Einreise', re.I))
            if einreise:
                einreise_content = einreise.find_next(['p', 'div', 'ul'])
                if einreise_content:
                    result["entry_requirements"] = einreise_content.get_text(strip=True)[:600]

            # Suche nach Visum-Infos
            visum = soup.find('h3', string=re.compile(r'Visum', re.I)) or soup.find('h4', string=re.compile(r'Visum', re.I))
            if visum:
                visum_content = visum.find_next(['p', 'div', 'ul'])
                if visum_content:
                    result["visa_info"] = visum_content.get_text(strip=True)[:600]

            # Fallback: Suche im gesamten Text nach Visum-Keywords
            if not result["visa_info"]:
                full_text = soup.get_text()
                visum_match = re.search(
                    r'(Visum[^.]*(?:erforderlich|nicht erforderlich|visumfrei|benötigen|brauchen)[^.]*\.)',
                    full_text,
                    re.I
                )
                if visum_match:
                    result["visa_info"] = visum_match.group(1).strip()

            # Sicherheitshinweise suchen
            sicherheit = soup.find('h2', string=re.compile(r'Sicherheit', re.I))
            if sicherheit and not result["safety_warning"]:
                sicherheit_content = sicherheit.find_next(['p', 'div'])
                if sicherheit_content:
                    text = sicherheit_content.get_text(strip=True)[:500]
                    if "Reisewarnung" in text or "Warnung" in text or "Gefahr" in text:
                        result["safety_warning"] = text

            return result

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Zeitüberschreitung beim Abrufen der Daten",
            "country": country
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Fehler: {str(e)}",
            "country": country
        }


def format_aa_info_for_chat(info: Dict) -> str:
    """Formatiert die AA-Infos für den Chatbot"""
    if not info.get("success"):
        return ""

    parts = []

    if info.get("safety_warning"):
        parts.append(f"⚠️ REISEWARNUNG: {info['safety_warning']}")

    if info.get("current_warnings"):
        for warning in info["current_warnings"][:2]:  # Max 2 aktuelle Hinweise
            parts.append(f"📢 Aktuell: {warning[:300]}...")

    if info.get("visa_info"):
        parts.append(f"🛂 Visum: {info['visa_info']}")

    if info.get("entry_requirements"):
        parts.append(f"✈️ Einreise: {info['entry_requirements'][:300]}...")

    if parts:
        parts.append(f"\n📎 Quelle: {info['source_url']}")
        return "\n\n".join(parts)

    return ""
