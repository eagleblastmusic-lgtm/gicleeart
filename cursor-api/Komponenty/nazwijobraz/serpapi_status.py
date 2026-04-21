"""Wspolne wykrywanie bledow SerpAPI - limit miesieczny, zly klucz, rate limit.

Wszystkie miejsca w nazwijobraz wywolujace SerpAPI (visual_search,
extra_searches.google_text/art_sites/wikiart) uzywaja `detect_serpapi_limit`
zaraz po dostaniu odpowiedzi i przy wykryciu rzucaja `SerpApiLimitError`.

GUI lapie ten exception w `_process_one`, ustawia globalna flage 'wyczerpane'
i pokazuje dialog z linkiem do dashboard SerpAPI + polem na nowy klucz.
"""

from __future__ import annotations


class SerpApiLimitError(RuntimeError):
    """SerpAPI zwrocil blad zwiazany z limitem / kluczem.

    Pole `reason` zawiera czytelny dla uzytkownika opis (z odpowiedzi serwera).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# Substringi w polu `error` z odpowiedzi SerpAPI ktore wskazuja na limit
# / nieprawidlowy klucz. Wszystkie sprawdzane w lower-case.
_LIMIT_PATTERNS: tuple[str, ...] = (
    "run out of searches",
    "out of searches",
    "no more searches",
    "exceeded your",
    "exceeded the",
    "credit limit",
    "search limit",
    "monthly limit",
    "rate limit",
    "rate-limit",
    "rate limited",
    "invalid api key",
    "invalid_api_key",
    "your api key",
    "api key is invalid",
    "missing api_key",
    "missing api key",
    "no api_key",
    "no api key",
    "account is locked",
    "account suspended",
)


def detect_serpapi_limit(data: dict | None, status_code: int = 200) -> str:
    """Zwraca powod blokady (string) gdy odpowiedz wskazuje wyczerpany limit
    / zly klucz, inaczej pusty string.

    Args:
        data: sparsowany JSON z SerpAPI (lub None gdy nie udalo sie sparsowac).
        status_code: HTTP status code odpowiedzi.

    Returns:
        Powod blokady do pokazania userowi (np. "Your account has run out
        of searches"), albo "" gdy odpowiedz jest OK / inny blad.
    """
    if status_code in (401, 403):
        return f"HTTP {status_code} (klucz API nieprawidlowy lub brak uprawnien)"
    if status_code == 429:
        return "HTTP 429 (rate limit / limit zapytan na sekunde wyczerpany)"
    if not isinstance(data, dict):
        return ""
    err_raw = data.get("error")
    if not err_raw:
        return ""
    err_lower = str(err_raw).lower()
    for pat in _LIMIT_PATTERNS:
        if pat in err_lower:
            return str(err_raw)
    return ""


def raise_if_serpapi_limit(data: dict | None, status_code: int = 200) -> None:
    """Helper: wykryj limit i rzuc SerpApiLimitError gdy wystapi."""
    reason = detect_serpapi_limit(data, status_code)
    if reason:
        raise SerpApiLimitError(reason)
