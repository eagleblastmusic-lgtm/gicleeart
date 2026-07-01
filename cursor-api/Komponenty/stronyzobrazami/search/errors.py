"""Czytelne komunikaty bledow wyszukiwania per zrodlo."""

from __future__ import annotations

import re


def format_source_error(raw: str, *, source_name: str = "") -> str:
    """Skraca techniczny wyjatek do komunikatu dla uzytkownika."""
    text = (raw or "").strip()
    if not text:
        return "Nieznany blad."

    low = text.lower()
    prefix = f"{source_name}: " if source_name else ""

    if "smithsonian_api_key" in low or "brak smithsonian" in low:
        return prefix + "Brak klucza API — ustaw SMITHSONIAN_API_KEY w .env lub «Klucz Smithsonian…»."

    if "europeana_api_key" in low or "brak europeana" in low:
        return prefix + "Brak klucza — ustaw EUROPEANA_API_KEY w cursor-api/.env (pro.europeana.eu)."

    if "cooper_hewitt" in low and "token" in low:
        return prefix + "Brak tokenu — ustaw COOPER_HEWITT_ACCESS_TOKEN w cursor-api/.env."

    if "nypl_api_token" in low or "brak nypl" in low:
        return prefix + "Brak tokenu — ustaw NYPL_API_TOKEN w cursor-api/.env (api.repo.nypl.org)."

    if "timed out" in low or "timeout" in low:
        return prefix + "Przekroczono czas oczekiwania — sprobuj ponownie lub zmniejsz limit wynikow."

    if "http 429" in low or "too many requests" in low:
        return prefix + "Limit zapytan (429) — odczekaj chwile i sprobuj ponownie."

    if "http 401" in low or "http 403" in low:
        return prefix + "Odmowa dostepu (401/403) — sprawdz klucz API lub uprawnienia."

    if "http 404" in low:
        return prefix + "Nie znaleziono zasobu (404) — API moglo sie zmienic."

    if "http 410" in low:
        return prefix + "API wycofane (410) — wymagana aktualizacja adaptera."

    m = re.search(r"HTTP (\d{3})", text, re.I)
    if m:
        code = m.group(1)
        if code.startswith("5"):
            return prefix + f"Blad serwera ({code}) — sprobuj pozniej."
        return prefix + f"Blad HTTP {code}."

    if "urlerror" in low or "getaddrinfo" in low or "nodename nor servname" in low:
        return prefix + "Brak polaczenia z internetem lub DNS."

    if "niepoprawny json" in low:
        return prefix + "Serwer zwrocil niepoprawna odpowiedz."

    if len(text) > 140:
        return prefix + text[:137] + "..."
    return prefix + text
