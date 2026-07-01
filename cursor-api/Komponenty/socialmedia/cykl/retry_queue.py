"""Kolejka awaryjna (retry queue) dla publikacji Meta.

Gdy `publish_item()` lapie wyjatek w czasie publikacji pojedynczego kanalu,
zapisuje `published_{channel} = "error: ..."` i `status = "error"` na poziomie
itemu (gdy wszystkie kanaly padly) lub `status = "error"` gdy sa mieszane
rezultaty. Tych itemow `publish_due_items()` nie dopina ponownie — wlasnie po
to jest ten modul.

API:
- `retry_candidates()` -> list[(item, failed_channels)]
- `retry_item(item_id)` -> dict{channel: status_msg}
- `retry_all(max_items=None)` -> list[(item_id, results)]
- `mark_item_skipped(item_id)` -> przestajemy proponowac do retry
- `error_messages(item)` -> list[(channel, message)]

Limit powtorzen: `config.retry_max_attempts` (domyslnie 3). Licznik w meta_state
(liczymy wpisy z `status=error` per (item, channel) od ostatniego `status=done`).
"""

from __future__ import annotations

from typing import Any

from . import storage
from .meta_publisher import publish_item


DEFAULT_MAX_ATTEMPTS = 3


def _max_attempts() -> int:
    cfg = storage.load_config()
    raw = cfg.get("retry_max_attempts")
    try:
        n = int(raw) if raw is not None else DEFAULT_MAX_ATTEMPTS
    except (TypeError, ValueError):
        n = DEFAULT_MAX_ATTEMPTS
    return max(1, n)


def _failed_channels(item: storage.CykleItem) -> list[str]:
    out: list[str] = []
    for ch in item.channels_enabled or []:
        val = getattr(item, f"published_{ch}", "") or ""
        if val.startswith("error"):
            out.append(ch)
    return out


def _channel_attempt_counts(item_id: str) -> dict[str, int]:
    """Zlicza ile razy dany kanal probowal sie opublikowac od ostatniego success."""
    log = storage.load_meta_log(limit=500)
    counts: dict[str, int] = {}
    done_after: dict[str, int] = {}
    for entry in log:
        if str(entry.get("item_id")) != item_id:
            continue
        ch = str(entry.get("channel") or "")
        status = str(entry.get("status") or "")
        if not ch:
            continue
        if status == "done":
            done_after[ch] = 0  # reset
            counts[ch] = 0
        elif status == "error":
            counts[ch] = counts.get(ch, 0) + 1
    return counts


def error_messages(item: storage.CykleItem) -> list[tuple[str, str]]:
    """Pary (kanal, komunikat bledu) dla kanalow ze statusem error."""
    out: list[tuple[str, str]] = []
    for ch in _failed_channels(item):
        val = getattr(item, f"published_{ch}", "") or ""
        out.append((ch, val.removeprefix("error:").strip() or "?"))
    return out


def retry_candidates() -> list[tuple[storage.CykleItem, list[str]]]:
    """Items ze statusem `error` lub `publishing` z co najmniej jednym kanalem `error:`."""
    items = storage.load_queue()
    out: list[tuple[storage.CykleItem, list[str]]] = []
    cap = _max_attempts()
    for it in items:
        if it.status in ("done", "skipped"):
            continue
        failed = _failed_channels(it)
        if not failed:
            continue
        # Odfiltruj te kanaly ktore juz wyczerpaly max prob
        attempts = _channel_attempt_counts(it.id)
        still = [ch for ch in failed if attempts.get(ch, 0) < cap]
        if still:
            out.append((it, still))
    return out


def retry_item(item_id: str, *, channels: list[str] | None = None, logger=None) -> dict[str, str]:
    """Ponawia publikacje dla itemu. Zwraca wyniki z `publish_item`.

    - Jesli `channels` jest None, ponawia tylko te, ktore maja error i nie
      wyczerpaly `retry_max_attempts`.
    - Kanaly `done@...` zostaja — `publish_item` sam je pomija.
    """
    items = storage.load_queue()
    for i, it in enumerate(items):
        if it.id != item_id:
            continue
        cap = _max_attempts()
        attempts = _channel_attempt_counts(it.id)
        if channels is None:
            channels = [
                ch for ch in _failed_channels(it)
                if attempts.get(ch, 0) < cap
            ]
        if not channels:
            return {}
        results = publish_item(it, channels=channels, logger=logger)
        items[i] = it
        storage.save_queue(items)
        return results
    return {}


def retry_all(*, max_items: int | None = None, logger=None) -> list[tuple[str, dict[str, str]]]:
    """Ponawia wszystkie kandydaty (z limitem ilosci). Zwraca pary (id, results)."""
    out: list[tuple[str, dict[str, str]]] = []
    cands = retry_candidates()
    for it, chans in cands:
        if max_items is not None and len(out) >= max_items:
            break
        try:
            r = retry_item(it.id, channels=chans, logger=logger)
        except Exception as e:  # noqa: BLE001
            r = {ch: f"error: {e}" for ch in chans}
        out.append((it.id, r))
    return out


def mark_item_skipped(item_id: str) -> bool:
    it = storage.update_item(item_id, status="skipped")
    return it is not None


def retry_summary() -> dict[str, Any]:
    """Krotkie podsumowanie do pokazania w GUI."""
    cands = retry_candidates()
    total_channels = sum(len(ch) for _it, ch in cands)
    return {
        "items_count": len(cands),
        "channels_count": total_channels,
        "cap": _max_attempts(),
    }
