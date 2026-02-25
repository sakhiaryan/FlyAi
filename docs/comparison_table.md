# FlyAI — Comparison Table: Prompting-Techniken & API-Outputs

## 1. Prompt Engineering Vergleich

### Intent-Erkennung: Flugsuche-Extraktion

| Technik | Prompt-Stil | Output-Format | Genauigkeit | Tokens | Kosten/Anfrage |
|---------|-------------|---------------|-------------|--------|----------------|
| **Zero-Shot** | "Extrahiere Flugdaten aus: '{user_input}'" | Freitext | ~60% | ~150 | ~$0.00015 |
| **Few-Shot** | Mit 3 Beispielen (BER→LHR, MUC→JFK, etc.) | JSON | ~80% | ~300 | ~$0.00030 |
| **Structured Output** ✅ | `response_format={"type":"json_object"}` + Schema | Garantiert JSON | ~95% | ~200 | ~$0.00020 |
| **Chain-of-Thought** | "Denke Schritt für Schritt..." | Freitext + JSON | ~85% | ~400 | ~$0.00040 |

**Gewählt: Structured Output** — Beste Balance aus Genauigkeit, Kosten und Zuverlässigkeit.

---

### Reise-Chatbot: System-Prompt Varianten

| Variante | Beschreibung | Beispiel-Output | Tokens/Antwort | User-Zufriedenheit |
|----------|-------------|-----------------|----------------|-------------------|
| **Formal** | "Sie sind ein professioneller Reiseberater..." | "Für Ihre Reise nach Japan empfehle ich folgende Schritte: 1. Visum prüfen 2. ..." | ~250 | ⭐⭐⭐ |
| **Buddy-Stil** ✅ | "Du bist ein freundlicher Reise-Buddy..." | "Japan ist mega! Brauchst kein Visum als Deutscher, bis 90 Tage easy ✈️" | ~80 | ⭐⭐⭐⭐⭐ |
| **Minimal** | "Antworte kurz auf Reisefragen." | "Kein Visum nötig. 90 Tage." | ~30 | ⭐⭐ |
| **Expert** | "Du bist ein zertifizierter Reiseexperte mit 20 Jahren Erfahrung..." | Sehr detailliert, manchmal zu viel Information | ~350 | ⭐⭐⭐⭐ |

**Gewählt: Buddy-Stil** — Kurz, natürlich, spart Tokens und fühlt sich wie ein Gespräch an.

---

## 2. API-Vergleich: Flugsuche

| API | Endpunkt | Antwortzeit | Datenqualität | Preis | Verfügbarkeit |
|-----|----------|-------------|---------------|-------|---------------|
| **Skyscanner (RapidAPI)** ✅ | `/api/v2/flights/searchFlights` | ~2-5s | Hoch (Echtzeit) | $0.01/Anfrage | 99.5% |
| **Amadeus** | `/v2/shopping/flight-offers` | ~3-8s | Sehr hoch (GDS) | $0.005/Anfrage | 98% |
| **Kiwi.com** | `/v2/search` | ~1-3s | Mittel | Kostenlos (limitiert) | 95% |

**Gewählt: Skyscanner** — Beste Balance aus Geschwindigkeit, Datenqualität und einfacher Integration.

---

## 3. API-Vergleich: KI-Modelle

| Modell | Antwortzeit | Qualität (DE) | Kosten/1K Tokens | Max Tokens | Structured Output |
|--------|-------------|---------------|-------------------|------------|-------------------|
| **GPT-4o** | ~2-4s | ⭐⭐⭐⭐⭐ | $0.005/$0.015 | 128K | ✅ |
| **GPT-4o-mini** ✅ | ~0.5-1.5s | ⭐⭐⭐⭐ | $0.00015/$0.0006 | 128K | ✅ |
| **GPT-3.5-turbo** | ~0.3-1s | ⭐⭐⭐ | $0.0005/$0.0015 | 16K | ✅ |
| **Claude 3.5 Sonnet** | ~1-3s | ⭐⭐⭐⭐⭐ | $0.003/$0.015 | 200K | ❌ |
| **Gemini 1.5 Flash** | ~0.5-2s | ⭐⭐⭐⭐ | $0.000075/$0.0003 | 1M | ✅ |

**Gewählt: GPT-4o-mini** — 10x günstiger als GPT-4o, sehr gute Deutsch-Qualität, schnell, Structured Output.

---

## 4. Temperatur-Vergleich (GPT-4o-mini)

| Temperature | Anwendung | Beispiel-Prompt | Output-Stil | Genutzt in |
|-------------|-----------|-----------------|-------------|------------|
| **0.0** | Daten-Extraktion | "Extrahiere JSON aus..." | Deterministisch, konsistent | — |
| **0.3** ✅ | Structured Output | "Analysiere und gib JSON zurück" | Konsistent + leicht variabel | `ask_chatgpt_structured()` |
| **0.7** ✅ | Chat-Konversation | "Tipps für Japan?" | Natürlich, kreativ, abwechslungsreich | `ask_chatgpt_with_history()` |
| **1.0** | Kreatives Schreiben | "Schreibe Reiseblog..." | Sehr kreativ, manchmal ungenau | — |

**Gewählt: 0.3 für JSON + 0.7 für Chat** — Optimale Kombination aus Zuverlässigkeit und Natürlichkeit.

---

## 5. Token-Optimierung: Visa-Antworten

| Methode | Ablauf | Tokens/Anfrage | Antwortzeit | Genauigkeit |
|---------|--------|----------------|-------------|-------------|
| **Voll-KI** | User → GPT → Antwort | ~200-400 | 1-3s | ~90% |
| **Hybrid** | User → Lokale DB + GPT | ~100-200 | 0.5-2s | ~95% |
| **Direkt-Lookup** ✅ | User → Lokale DB → Antwort | **0 Tokens** | <50ms | 100% |

**Gewählt: Direkt-Lookup für Visa** — Spart 100% Tokens, sofortige Antwort, immer korrekt.

---

## Zusammenfassung der Entscheidungen

| Bereich | Gewählte Lösung | Hauptgrund |
|---------|-----------------|------------|
| Intent-Erkennung | Structured Output (JSON Mode) | Garantiert valides JSON |
| System-Prompt | Buddy-Stil, max 2-3 Sätze | Natürlich, token-effizient |
| Flugsuche-API | Skyscanner via RapidAPI | Echtzeit-Daten, einfach |
| KI-Modell | GPT-4o-mini | Kosten-effizient, schnell |
| Temperatur | 0.3 (JSON) / 0.7 (Chat) | Balance Konsistenz/Kreativität |
| Visa-Info | Lokaler Lookup ohne KI | 0 Tokens, sofortige Antwort |
