"""Scheduler - przypisywanie slotow czasowych do pozycji w kolejce.

3 sloty dziennie: rano / popoludnie / wieczor (godziny z config.json,
domyslnie 08:00 / 14:00 / 20:00).

Reguly:
- Tylko pozycje ze statusem 'pending' sa przeliczane.
- Kolejnosc zachowana jak w liscie (index) - to jest glowne zrodlo prawdy
  ('kto pierwszy w liscie, ten pierwszy w czasie').
- assign_slots startuje od `start_date` (domyslnie dzis, skip past=True
  pominie sloty ktorych godzina juz minela).
- shift_all_pending: przesuwa WSZYSTKIE pending o N dni (+/-).
- shift_single: przesuwa jeden post o N dni (reszta bez zmian).
- reorder_move: zmienia pozycje w liscie (bez reassign slotow - wolamy
  osobno reassign_slots jesli chcemy zaktualizowac scheduled_at).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from . import platforms_cykl as _cp
from . import storage


SLOT_ORDER = _cp.SLOT_CODES  # ("morning", "afternoon", "evening")


def _parse_hhmm(s: str) -> time:
    s = (s or "").strip()
    try:
        hh, mm = s.split(":", 1)
        return time(int(hh), int(mm))
    except (ValueError, IndexError):
        return time(8, 0)


def _slot_times_from_config(cfg: dict | None = None) -> dict[str, time]:
    if cfg is None:
        cfg = storage.load_config()
    raw = cfg.get("slot_times") or _cp.DEFAULT_SLOT_TIMES
    return {slot: _parse_hhmm(raw.get(slot, _cp.DEFAULT_SLOT_TIMES[slot]))
            for slot in SLOT_ORDER}


def _iter_future_slots(
    start: datetime,
    slot_times: dict[str, time],
    *,
    skip_past: bool = True,
) -> Iterable[tuple[datetime, str]]:
    """Generator (datetime, slot_name) rosnacy w czasie od `start`."""
    day = start.date()
    while True:
        for slot in SLOT_ORDER:
            dt = datetime.combine(day, slot_times[slot])
            if skip_past and dt < start:
                continue
            yield dt, slot
        day += timedelta(days=1)


def assign_slots(
    items: list[storage.CykleItem],
    *,
    start_date: date | None = None,
    skip_past: bool = True,
    only_empty: bool = False,
) -> None:
    """Przypisuje scheduled_at + slot do pozycji 'pending' po kolei.

    - start_date: data startu (default: dzis lokalny).
    - skip_past: jesli True, pomija sloty ktorych godzina juz minela dzisiaj.
    - only_empty: jesli True, nadpisuje tylko te pozycje ktore nie maja scheduled_at.
      Domyslnie (False) nadpisuje wszystkie pending - do uzytku po shift/reorder.
    """
    cfg = storage.load_config()
    slot_times = _slot_times_from_config(cfg)
    now = datetime.now()
    if start_date is None:
        start_date = date.today()
    start_dt = datetime.combine(start_date, time(0, 0))
    if start_dt < now:
        start_dt = now
    slot_gen = _iter_future_slots(start_dt, slot_times, skip_past=skip_past)

    for it in items:
        if it.status not in ("pending", "ready"):
            continue
        if only_empty and it.scheduled_at:
            continue
        dt, slot_name = next(slot_gen)
        it.scheduled_at = dt.isoformat(timespec="seconds")
        it.slot = slot_name


def reassign_from_now(items: list[storage.CykleItem]) -> None:
    """Po zmianach (delta/reorder) przelicz sloty dla wszystkich pending."""
    assign_slots(items, start_date=date.today(), skip_past=True, only_empty=False)


def shift_all_pending(items: list[storage.CykleItem], delta_days: int) -> int:
    """Przesuwa wszystkie pozycje ze scheduled_at do przodu (+) lub do tylu (-).

    Zwraca liczbe przesunietych pozycji. Pozycje done/skipped nie sa ruszane.
    """
    count = 0
    delta = timedelta(days=delta_days)
    for it in items:
        if it.status in ("done", "skipped"):
            continue
        if not it.scheduled_at:
            continue
        try:
            dt = datetime.fromisoformat(it.scheduled_at)
        except ValueError:
            continue
        new_dt = dt + delta
        # Nie pozwol cofnac w przeszlosc (jesli delta < 0)
        if delta_days < 0 and new_dt < datetime.now():
            continue
        it.scheduled_at = new_dt.isoformat(timespec="seconds")
        count += 1
    return count


def shift_single(
    items: list[storage.CykleItem],
    item_id: str,
    delta_days: int,
) -> bool:
    for it in items:
        if it.id != item_id:
            continue
        if not it.scheduled_at:
            return False
        try:
            dt = datetime.fromisoformat(it.scheduled_at)
        except ValueError:
            return False
        new_dt = dt + timedelta(days=delta_days)
        if delta_days < 0 and new_dt < datetime.now():
            return False
        it.scheduled_at = new_dt.isoformat(timespec="seconds")
        return True
    return False


def rotate_to_artist(
    items: list[storage.CykleItem],
    artist_name: str,
    *,
    only_pending: bool = True,
) -> int:
    """Obraca kolejke tak, zeby pierwszy obraz podanego artysty byl na poczatku.

    Artysci ktorzy ALFABETYCZNIE byli PRZED wybranym trafiaja na koniec kolejki,
    zachowujac swoja wzgledna kolejnosc. Kolejnosc obrazow WEWNATRZ kazdego
    artysty jest zachowana.

    Args:
        items: lista pozycji (modyfikowana in-place).
        artist_name: dokladna nazwa artysty (jak w item.artist).
        only_pending: gdy True - rotuje tylko wsrod pending/ready (done/skipped
                      zostaja na swoich miejscach). Gdy False - rotuje wszystko.

    Zwraca liczbe pozycji ktore zostaly przesuniete na koniec (>0 = sukces,
    0 = artysta juz byl pierwszy albo nie znaleziono).

    UWAGA: po rotacji wywolaj `reassign_from_now(items)` aby zaktualizowac
    scheduled_at / slot dla nowych pozycji na poczatku.
    """
    if not artist_name:
        return 0

    # Podziel indeksy na 'ruchome' (pending/ready) i 'stale' (done/skipped)
    # zeby nie zadrzec statusami zakonczonymi.
    if only_pending:
        movable_idx = [i for i, it in enumerate(items) if it.status in ("pending", "ready")]
    else:
        movable_idx = list(range(len(items)))

    if not movable_idx:
        return 0

    movable_items = [items[i] for i in movable_idx]
    # Znajdz pierwsze wystapienie wybranego artysty
    first_hit = next(
        (j for j, it in enumerate(movable_items) if it.artist == artist_name),
        -1,
    )
    if first_hit < 0:
        return 0
    if first_hit == 0:
        return 0  # juz pierwszy

    # Nowa kolejnosc movable = [chosen+poz. dalej ...] + [artysci przed chosen]
    new_movable = movable_items[first_hit:] + movable_items[:first_hit]

    # Wstaw z powrotem na swoje indeksy (zachowujac done/skipped w miejscu)
    for idx_target, new_item in zip(movable_idx, new_movable, strict=True):
        items[idx_target] = new_item

    return first_hit


def reorder_move(
    items: list[storage.CykleItem],
    item_id: str,
    direction: int,
) -> bool:
    """Przesuwa pozycje o 1 miejsce gora (-1) / dol (+1) w liscie.

    Sam scheduled_at nie jest aktualizowany - wywolaj reassign_from_now osobno.
    Zwraca True gdy przesunieto.
    """
    if direction not in (-1, 1):
        return False
    idx = next((i for i, it in enumerate(items) if it.id == item_id), -1)
    if idx < 0:
        return False
    new_idx = idx + direction
    if new_idx < 0 or new_idx >= len(items):
        return False
    items[idx], items[new_idx] = items[new_idx], items[idx]
    return True


def generated_until(items: list[storage.CykleItem]) -> str:
    """Zwraca najpozniejsza date pozycji ktora ma juz tresc (caption_pl lub caption_en).

    Format ISO date 'YYYY-MM-DD'. Uzywane w status bar + reminder 'czas generowac tydzien'.
    """
    latest = ""
    for it in items:
        if not (it.caption_pl or it.caption_en):
            continue
        if not it.scheduled_at:
            continue
        try:
            d = datetime.fromisoformat(it.scheduled_at).date().isoformat()
        except ValueError:
            continue
        if d > latest:
            latest = d
    return latest


def days_of_content_left(items: list[storage.CykleItem]) -> int:
    """Liczba dni od dzis do ostatniego zaplanowanego postu Z TRESCIA."""
    limit = generated_until(items)
    if not limit:
        return 0
    try:
        d = datetime.fromisoformat(limit + "T00:00:00").date()
    except ValueError:
        return 0
    delta = (d - date.today()).days
    return max(0, delta)
