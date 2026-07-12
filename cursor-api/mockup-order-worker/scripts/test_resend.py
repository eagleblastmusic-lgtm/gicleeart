#!/usr/bin/env python3
"""Ręczny test wysyłki Resend używający tego samego adresu co Worker."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = ROOT / ".env"
RESEND_ENDPOINT = "https://api.resend.com/emails"
DEFAULT_RECIPIENT = "gicleeartpl@gmail.com"


def load_env_file(path: Path = DEFAULT_ENV_PATH) -> None:
    """Wczytaj proste wpisy KEY=VALUE bez nadpisywania istniejącego środowiska."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        os.environ.setdefault(
            key.strip(),
            value.strip().strip('"').strip("'"),
        )


def resolve_api_key(env_path: Path = DEFAULT_ENV_PATH) -> str:
    """Zwróć klucz Resend z procesu lub opcjonalnego pliku .env."""
    load_env_file(env_path)
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def build_request(
    api_key: str,
    *,
    recipient: str = DEFAULT_RECIPIENT,
) -> urllib.request.Request:
    """Zbuduj żądanie testowe bez wykonywania połączenia sieciowego."""
    payload = {
        "from": "Giclee Art <onboarding@resend.dev>",
        "to": [recipient],
        "subject": "Test Giclee mockup worker",
        "html": "<p>Test wysylki z scripts/test_resend.py</p>",
    }

    return urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GicleeApp/1.0 (test_resend)",
        },
        method="POST",
    )


def send_test_email(
    api_key: str,
    *,
    recipient: str = DEFAULT_RECIPIENT,
    opener: Callable[..., Any] | None = None,
) -> tuple[int, str]:
    """Wyślij testową wiadomość i zwróć status HTTP oraz treść odpowiedzi."""
    request = build_request(api_key, recipient=recipient)
    open_request = opener or urllib.request.urlopen

    with open_request(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        return int(response.status), body


def main() -> int:
    """Uruchom ręczny test i zwróć kod procesu bez efektów ubocznych przy imporcie."""
    api_key = resolve_api_key()
    if not api_key:
        print("Brak RESEND_API_KEY w cursor-api/.env — skopiuj klucz z panelu Resend.")
        return 1

    try:
        status, body = send_test_email(api_key)
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        print("Resend BLAD", error.code, error_body)
        return 1
    except urllib.error.URLError as error:
        print("Resend BLAD", error.reason)
        return 1

    print("Resend OK", status, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
