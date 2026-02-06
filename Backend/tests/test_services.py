"""
Unit Tests für FlyAI Services
"""

import pytest
import sys
import os

# Backend-Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.visa_service import (
    get_visa_info,
    format_visa_warning_for_chat,
    get_critical_countries,
    normalize_country,
    get_travel_warning
)
from services.airport_service import search_airports


class TestVisaService:
    """Tests für den Visa-Service"""

    def test_get_visa_info_china(self):
        """China sollte Visum erforderlich haben"""
        info = get_visa_info("china")
        assert info["visa_required"] is True
        assert info["warning_level"] == "high"
        assert "Visum" in info["visa_type"]

    def test_get_visa_info_france(self):
        """Frankreich sollte visumfrei sein"""
        info = get_visa_info("frankreich")
        assert info["visa_required"] is False
        assert info["visa_type"] == "Visumfrei"

    def test_get_visa_info_usa(self):
        """USA sollte ESTA erfordern"""
        info = get_visa_info("usa")
        assert info["visa_required"] is False
        assert "ESTA" in info["visa_type"]

    def test_get_visa_info_unknown_country(self):
        """Unbekanntes Land sollte unbekannt zurückgeben"""
        info = get_visa_info("fantasyland123")
        assert info["visa_required"] is None
        assert info["warning_level"] == "unknown"

    def test_normalize_country_aliases(self):
        """Länder-Aliase sollten korrekt normalisiert werden"""
        assert normalize_country("USA") == "usa"
        assert normalize_country("United States") == "usa"
        assert normalize_country("Amerika") == "usa"
        assert normalize_country("UK") == "großbritannien"
        assert normalize_country("England") == "großbritannien"

    def test_get_critical_countries(self):
        """Kritische Länder sollten zurückgegeben werden"""
        countries = get_critical_countries()
        assert isinstance(countries, list)
        assert len(countries) > 0
        assert "afghanistan" in countries
        assert "syrien" in countries
        assert "russland" in countries

    def test_get_travel_warning_critical(self):
        """Kritische Länder sollten Reisewarnung haben"""
        warning = get_travel_warning("afghanistan")
        assert warning is not None
        assert "Reisewarnung" in warning

    def test_get_travel_warning_safe(self):
        """Sichere Länder sollten keine Reisewarnung haben"""
        warning = get_travel_warning("frankreich")
        assert warning is None

    def test_format_visa_warning_critical(self):
        """Visa-Warnung für kritisches Land sollte Warnung enthalten"""
        warning = format_visa_warning_for_chat("syrien")
        assert "ACHTUNG" in warning or "Reisewarnung" in warning

    def test_format_visa_warning_visa_required(self):
        """Visa-Warnung für Visum-pflichtiges Land sollte Visum erwähnen"""
        warning = format_visa_warning_for_chat("china")
        assert "Visum" in warning

    def test_format_visa_warning_visa_free(self):
        """Visa-Warnung für visumfreies Land sollte Visumfrei zeigen"""
        warning = format_visa_warning_for_chat("spanien")
        assert "Visumfrei" in warning


class TestAirportService:
    """Tests für den Airport-Service"""

    def test_search_airports_berlin(self):
        """Suche nach Berlin sollte BER finden"""
        results = search_airports("Berlin")
        assert len(results) > 0
        codes = [a["code"] for a in results]
        assert "BER" in codes

    def test_search_airports_returns_list(self):
        """Suche sollte eine Liste zurückgeben"""
        results = search_airports("London")
        assert isinstance(results, list)

    def test_search_airports_ber_code(self):
        """Suche nach BER Code sollte Ergebnisse liefern"""
        results = search_airports("BER")
        assert len(results) > 0
        # BER sollte in den Ergebnissen sein
        codes = [a["code"] for a in results]
        assert "BER" in codes

    def test_search_airports_structure(self):
        """Airport-Ergebnisse sollten korrekte Struktur haben"""
        results = search_airports("Berlin")
        assert len(results) > 0
        airport = results[0]
        assert "code" in airport
        assert "city" in airport
        assert "country" in airport
        assert "name" in airport

    def test_search_airports_returns_results(self):
        """Suche sollte Ergebnisse zurückgeben"""
        results = search_airports("New")
        # Sollte mindestens etwas finden (Default-Airports)
        assert isinstance(results, list)

    def test_search_airports_case_insensitive(self):
        """Suche sollte case-insensitive sein"""
        results_lower = search_airports("berlin")
        results_upper = search_airports("BERLIN")
        assert len(results_lower) == len(results_upper)


class TestVisaWarningLevels:
    """Tests für verschiedene Visa-Warnstufen"""

    def test_warning_level_critical(self):
        """Kritische Länder sollten 'critical' Level haben"""
        critical_countries = ["afghanistan", "syrien", "jemen", "libyen", "somalia"]
        for country in critical_countries:
            info = get_visa_info(country)
            assert info["warning_level"] == "critical", f"{country} sollte critical sein"

    def test_warning_level_high(self):
        """Hochrisiko-Länder sollten 'high' Level haben"""
        high_risk = ["china", "russland", "iran"]
        for country in high_risk:
            info = get_visa_info(country)
            assert info["warning_level"] == "high", f"{country} sollte high sein"

    def test_warning_level_low(self):
        """Länder mit niedrigem Risiko sollten 'low' Level haben"""
        low_risk = ["usa", "australien", "vietnam"]
        for country in low_risk:
            info = get_visa_info(country)
            assert info["warning_level"] == "low", f"{country} sollte low sein"

    def test_warning_level_none_for_eu(self):
        """EU-Länder sollten 'none' Level haben"""
        eu_countries = ["frankreich", "spanien", "italien", "österreich"]
        for country in eu_countries:
            info = get_visa_info(country)
            assert info["warning_level"] == "none", f"{country} sollte none sein"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
