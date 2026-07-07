"""Optional performance diagnostics for GicleeApp Studio.

Enabled only when GICLEE_STUDIO_PERF=1.
This module must never crash the UI.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_ENV_FLAG = "GICLEE_STUDIO_PERF"
_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "studio_perf.log"


def is_enabled() -> bool:
    value = os.environ.get(_ENV_FLAG, "").strip().lower()
    return value in {"1", "true", "yes", "on", "debug"}


def _safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    # Keep diagnostics compact and avoid dumping large/private values.
    text = text.replace("\\", "/")
    if len(text) > 180:
        text = text[:177] + "..."
    return text


def log_event(event: str, *, elapsed_ms: float | None = None, **fields: Any) -> None:
    if not is_enabled():
        return

    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "event": str(event),
        }
        if elapsed_ms is not None:
            payload["elapsed_ms"] = round(float(elapsed_ms), 2)
        for key, value in fields.items():
            payload[str(key)] = _safe_value(value)

        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        # Performance diagnostics must never affect Studio.
        return


@contextmanager
def span(event: str, **fields: Any) -> Iterator[None]:
    if not is_enabled():
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        log_event(event, elapsed_ms=elapsed, **fields)
