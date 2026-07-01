"""HTTP JSON dla silnika wyszukiwania (stdlib)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "GicleeArt-StronyZObrazami/1.0 (collection search; +https://giclee.art)"


def get_json(
    url: str,
    *,
    timeout: float = 25.0,
    headers: dict[str, str] | None = None,
) -> Any:
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Niepoprawny JSON z {url}") from exc


def post_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout: float = 25.0,
    headers: dict[str, str] | None = None,
) -> Any:
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        h.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Niepoprawny JSON z {url}") from exc
