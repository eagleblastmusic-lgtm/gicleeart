"""Klient Gemini API (REST) — tekst + obraz."""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from Komponenty.limity.env_config import load_dotenv_once

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

DEFAULT_MODEL = "gemini-3.6-flash"

# Free tier Flash: ~20 RPM — bezpieczna przerwa miedzy obrazami w batchu.
DEFAULT_BATCH_DELAY_S = 8.0
DEFAULT_API_TIMEOUT_S = 180.0
MAX_RETRY_SLEEP_S = 120.0
MIN_RATE_LIMIT_SLEEP_S = 25.0
MIN_503_SLEEP_S = 30.0

StatusCallback = Callable[[str], None] | None

_RETRY_IN_RE = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)
_RETRY_DELAY_JSON_RE = re.compile(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)\s*s?"', re.IGNORECASE)

ShouldAbort = Callable[[], bool] | None

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class GeminiError(RuntimeError):
    """Blad wywolania Gemini API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GeminiAborted(GeminiError):
    """Przerwano oczekiwanie / retry (np. Stop w batchu)."""


def is_daily_quota_exhausted(exc: BaseException) -> bool:
    """Dzienny limit free tier — retry co minute nie pomoze."""
    msg = str(exc).lower()
    return any(
        x in msg
        for x in (
            "per day",
            "perday",
            "daily",
            "generate_requests_per_day",
            "generaterequestsperday",
            "free_tier_requests",
        )
    )


def is_billing_quota_exhausted(exc: BaseException) -> bool:
    """Brak kredytow / billing — ponawianie 429 nie pomoze."""
    msg = str(exc).lower()
    return any(
        x in msg
        for x in (
            "prepayment credits",
            "credits are depleted",
            "manage your project and billing",
            "exceeded your current quota",
            "quota exceeded",
        )
    )


def is_permanent_quota_exhausted(exc: BaseException) -> bool:
    """429 bez sensu ponawiac (limit dzienny, kredyty, billing)."""
    return is_daily_quota_exhausted(exc) or is_billing_quota_exhausted(exc)


def is_rate_limit_error(exc: BaseException) -> bool:
    """Limit RPM (429) — nie mylic z 503 UNAVAILABLE."""
    if not isinstance(exc, GeminiError):
        msg = str(exc).lower()
        return "429" in msg or "resource_exhausted" in msg
    code = exc.status_code
    if code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg


def is_transient_network_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        x in msg
        for x in (
            "timed out",
            "timeout",
            "connection reset",
            "connection refused",
            "temporarily unavailable",
            "remote end closed",
            "broken pipe",
        )
    )


def is_transient_availability_error(exc: BaseException) -> bool:
    """503/502/504 — chwilowe przeciazenie modelu (retry + fallback)."""
    msg = str(exc).lower()
    code = getattr(exc, "status_code", None)
    return (
        code in (500, 502, 503, 504)
        or any(x in msg for x in ("503", "502", "504", "500"))
        or "unavailable" in msg
        or "high demand" in msg
    )


def is_retryable_gemini_error(exc: BaseException) -> bool:
    if isinstance(exc, GeminiError):
        if exc.status_code == 429 and is_permanent_quota_exhausted(exc):
            return False
        if exc.status_code in (429, 500, 502, 503, 504):
            return True
    return (
        is_rate_limit_error(exc)
        or is_transient_availability_error(exc)
        or is_transient_network_error(exc)
    )


def _notify_status(on_status: StatusCallback, message: str) -> None:
    """Callback UI nie moze przerwac petli retry."""
    if not on_status:
        return
    try:
        on_status(message)
    except Exception:
        pass


def format_gemini_error(exc: BaseException) -> str:
    """Krotki komunikat do UI (bez calego JSON)."""
    if isinstance(exc, GeminiAborted):
        return "Przerwano oczekiwanie na Gemini (Stop)."
    if is_rate_limit_error(exc) and is_permanent_quota_exhausted(exc):
        msg = str(exc).lower()
        if is_billing_quota_exhausted(exc):
            return (
                "Wyczerpane kredyty API Gemini (HTTP 429). "
                "Doladuj projekt w Google AI Studio (Billing / prepayment) "
                "albo wlacz platny plan."
            )
        if "credit" in msg or "billing" in msg:
            return (
                "Problem z limitem rozliczen Gemini (HTTP 429). "
                "Sprawdz Billing w Google AI Studio."
            )
        return (
            "Wyczerpany DZIENNY limit Gemini (HTTP 429). "
            "Free tier resetuje sie okolo polnocy PT — sprobuj jutro "
            "albo wlacz platny plan w Google AI Studio."
        )
    if is_rate_limit_error(exc):
        return (
            "Limit zapytan na minute (HTTP 429) — aplikacja czeka i probuje ponownie. "
            "Zwieksz «Przerwe miedzy obrazami» (np. 8–10 s) albo poczekaj."
        )
    if is_transient_availability_error(exc):
        return (
            "Model Gemini chwilowo przeciazony (HTTP 503). "
            "Aplikacja automatycznie czeka i ponawia — obserwuj pasek postepu "
            "(nie zamykaj okna). Moze potrwac kilka minut."
        )
    if is_transient_network_error(exc):
        return (
            "Blad polaczenia z Gemini (timeout/siec). "
            "Aplikacja ponawia automatycznie — poczekaj chwile."
        )
    text = str(exc).strip()
    if text.startswith("HTTP "):
        return text[:400]
    return text[:400]


def _parse_retry_delay_seconds(error_message: str) -> float | None:
    m = _RETRY_DELAY_JSON_RE.search(error_message)
    if m:
        return float(m.group(1))
    m = _RETRY_IN_RE.search(error_message)
    if m:
        return float(m.group(1))
    return None


def _retry_sleep_seconds(
    error_message: str,
    attempt: int,
    *,
    rate_limit: bool,
    unavailable: bool = False,
) -> float:
    parsed = _parse_retry_delay_seconds(error_message)
    if parsed is not None:
        base = parsed + 3.0
    elif unavailable:
        base = max(MIN_503_SLEEP_S, 25.0 * (attempt + 1))
    elif rate_limit:
        base = max(MIN_RATE_LIMIT_SLEEP_S, 15.0 * (attempt + 1))
    else:
        base = 10.0 * (attempt + 1)
    return min(MAX_RETRY_SLEEP_S, base)


def _sleep_with_status(
    seconds: float,
    message: str,
    on_status: StatusCallback,
    *,
    should_abort: ShouldAbort = None,
) -> None:
    if seconds <= 0:
        return
    _notify_status(on_status, message)
    remaining = seconds
    elapsed = 0.0
    while remaining > 0:
        if should_abort and should_abort():
            raise GeminiAborted("Przerwano podczas oczekiwania na Gemini.")
        chunk = min(1.0, remaining)
        time.sleep(chunk)
        remaining -= chunk
        elapsed += chunk
        if on_status and elapsed >= 5.0 and remaining > 0:
            _notify_status(on_status, f"{message}  (zostalo ~{remaining:.0f}s)")
            elapsed = 0.0


def gemini_api_key() -> str:
    load_dotenv_once()
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def gemini_api_key_hint() -> str:
    """Skrocony podglad klucza do UI (np. ...Ab12Cd)."""
    key = gemini_api_key()
    if not key:
        return ""
    if len(key) <= 8:
        return "..." + key[-4:]
    return "..." + key[-6:]


def set_gemini_api_key(value: str) -> Path:
    """Zapisuje GEMINI_API_KEY do cursor-api/.env i os.environ."""
    from Komponenty.limity.env_config import set_env_value

    key = (value or "").strip()
    if not key:
        raise ValueError("Klucz API nie moze byc pusty.")
    return set_env_value("GEMINI_API_KEY", key)


def image_mime_type(path: Path | str) -> str:
    ext = Path(path).suffix.lower()
    return _MIME_BY_EXT.get(ext, "image/jpeg")


def _read_image_part(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Pusty plik obrazu: {path}")
    return {
        "inline_data": {
            "mime_type": image_mime_type(path),
            "data": base64.standard_b64encode(data).decode("ascii"),
        }
    }


def _post_generate(
    *,
    model: str,
    api_key: str,
    parts: list[dict[str, Any]],
    timeout: float = 180.0,
    response_mime_type: str | None = None,
) -> str:
    url = f"{API_BASE}/{model}:generateContent?key={api_key}"
    generation_config: dict[str, Any] = {
        "temperature": 0.4,
        "maxOutputTokens": 4096,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiError(f"HTTP {exc.code}: {detail[:800]}", status_code=exc.code) from exc
    except TimeoutError as exc:
        raise GeminiError(f"Timeout: {exc}") from exc
    except URLError as exc:
        raise GeminiError(str(exc)) from exc

    api_err = body.get("error") if isinstance(body, dict) else None
    if isinstance(api_err, dict):
        code_raw = api_err.get("code")
        try:
            code = int(code_raw) if code_raw is not None else None
        except (TypeError, ValueError):
            code = None
        if code in (429, 500, 502, 503, 504) or str(api_err.get("status", "")).upper() == "UNAVAILABLE":
            raise GeminiError(
                f"HTTP {code or api_err.get('status')}: {json.dumps(api_err, ensure_ascii=False)[:800]}",
                status_code=code,
            )

    candidates = body.get("candidates") or []
    if not candidates:
        feedback = body.get("promptFeedback") or {}
        raise GeminiError(f"Brak odpowiedzi modelu: {feedback or body}")
    content = (candidates[0].get("content") or {}).get("parts") or []
    texts = [p.get("text", "") for p in content if p.get("text")]
    text = "\n".join(texts).strip()
    if not text:
        raise GeminiError("Pusta odpowiedz modelu.")
    return text


def _generate_with_retries(
    *,
    parts: list[dict[str, Any]],
    api_key: str,
    model: str,
    timeout: float,
    on_status: StatusCallback = None,
    should_abort: ShouldAbort = None,
    response_mime_type: str | None = None,
) -> tuple[str, str]:
    """Wywoluje Gemini; przy 429/503 ponawia do skutku (rosnace opoznienie)."""
    attempt = 0
    _notify_status(on_status, f"Gemini ({model}): wysylam obraz...")
    while True:
        if should_abort and should_abort():
            raise GeminiAborted("Przerwano przed wyslaniem do Gemini.")
        try:
            text = _post_generate(
                model=model,
                api_key=api_key,
                parts=parts,
                timeout=timeout,
                response_mime_type=response_mime_type,
            )
            if attempt > 0 and on_status:
                _notify_status(on_status, f"Gemini ({model}): polaczenie OK po {attempt + 1} probie.")
            return text, model
        except GeminiError as exc:
            if exc.status_code == 429 and is_permanent_quota_exhausted(exc):
                raise GeminiError(format_gemini_error(exc), status_code=429) from exc
            if is_retryable_gemini_error(exc):
                rate_limit = is_rate_limit_error(exc)
                unavailable = is_transient_availability_error(exc)
                wait_s = _retry_sleep_seconds(
                    str(exc),
                    attempt,
                    rate_limit=rate_limit,
                    unavailable=unavailable,
                )
                if unavailable:
                    label = "503 przeciazenie"
                elif rate_limit:
                    label = "429 limit/min"
                else:
                    label = "siec/timeout"
                _sleep_with_status(
                    wait_s,
                    (
                        f"Gemini ({label}) — czekam {wait_s:.0f}s, "
                        f"potem ponowie (proba {attempt + 2}, {model})"
                    ),
                    on_status,
                    should_abort=should_abort,
                )
                attempt += 1
                continue
            if "404" in str(exc).lower() or "not found" in str(exc).lower():
                raise GeminiError(
                    f"Model {model} niedostepny (404). Sprawdz nazwe modelu.",
                    status_code=404,
                ) from exc
            raise


def generate_from_image_file(
    *,
    image_path: Path | str,
    prompt: str,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_API_TIMEOUT_S,
    on_status: StatusCallback = None,
    should_abort: ShouldAbort = None,
) -> tuple[str, str]:
    """Wysyla obraz + prompt. Zwraca (tekst_odpowiedzi, uzyty_model)."""
    key = (api_key or gemini_api_key()).strip()
    if not key:
        raise GeminiError(
            "Brak GEMINI_API_KEY w cursor-api/.env "
            "(klucz z https://aistudio.google.com/apikey )."
        )
    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"Brak pliku obrazu: {path}")

    parts: list[dict[str, Any]] = [
        {"text": prompt},
        _read_image_part(path),
    ]
    return _generate_with_retries(
        parts=parts,
        api_key=key,
        model=model,
        timeout=timeout,
        on_status=on_status,
        should_abort=should_abort,
    )


def generate_from_image_bytes(
    *,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_API_TIMEOUT_S,
    on_status: StatusCallback = None,
    should_abort: ShouldAbort = None,
    response_mime_type: str | None = None,
) -> tuple[str, str]:
    """Jak generate_from_image_file, ale z bajtow (np. pobrany URL)."""
    key = (api_key or gemini_api_key()).strip()
    if not key:
        raise GeminiError("Brak GEMINI_API_KEY w cursor-api/.env.")
    if not image_bytes:
        raise ValueError("Pusty bufor obrazu.")
    parts: list[dict[str, Any]] = [
        {"text": prompt},
        {
            "inline_data": {
                "mime_type": mime_type or "image/jpeg",
                "data": base64.standard_b64encode(image_bytes).decode("ascii"),
            }
        },
    ]
    return _generate_with_retries(
        parts=parts,
        api_key=key,
        model=model,
        timeout=timeout,
        on_status=on_status,
        should_abort=should_abort,
        response_mime_type=response_mime_type,
    )
