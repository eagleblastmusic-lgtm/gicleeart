"""Szablony układu kafelków na płótnie kolażu."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class CollageSlot:
    """Pozycja kafelka: ułamki płótna (0–1) + obrót w stopniach + skala."""

    x: float
    y: float
    w: float
    h: float
    rotation: float = 0.0
    z: int = 0


LAYOUT_CHOICES: list[tuple[str, str]] = [
    ("museum_scatter", "Muzealny — rozrzucone karty"),
    ("editorial", "Redakcyjny — duży + siatka"),
    ("grid", "Siatka równomierna"),
    ("hero_center", "Hero — centralny akcent"),
    ("panorama", "Panorama — poziome pasy"),
    ("random_scatter", "Losowy — z seedem"),
]

CANVAS_PRESETS: list[tuple[str, int, int]] = [
    ("BIO sekcji autora (2400×1200)", 2400, 1200),
    ("Full HD (1920×1080)", 1920, 1080),
    ("Instagram kwadrat (1080×1080)", 1080, 1080),
    ("Banner szeroki (2560×900)", 2560, 900),
    ("4K (3840×2160)", 3840, 2160),
]


def _museum_scatter(count: int) -> list[CollageSlot]:
    base = [
        CollageSlot(0.06, 0.10, 0.34, 0.62, -8, 1),
        CollageSlot(0.26, 0.04, 0.36, 0.58, 6, 2),
        CollageSlot(0.50, 0.08, 0.34, 0.60, -4, 3),
        CollageSlot(0.16, 0.36, 0.32, 0.55, 5, 4),
        CollageSlot(0.44, 0.40, 0.34, 0.56, -6, 5),
        CollageSlot(0.66, 0.26, 0.30, 0.52, 7, 6),
        CollageSlot(0.72, 0.02, 0.26, 0.44, -3, 0),
        CollageSlot(0.02, 0.48, 0.28, 0.48, 4, 7),
    ]
    return base[: max(1, min(count, len(base)))]


def _editorial(count: int) -> list[CollageSlot]:
    slots: list[CollageSlot] = [
        CollageSlot(0.04, 0.06, 0.52, 0.88, -2, 1),
    ]
    small_positions = [
        (0.60, 0.06, 0.34, 0.40, 4),
        (0.60, 0.50, 0.34, 0.40, -3),
        (0.78, 0.28, 0.18, 0.22, 6),
    ]
    for i in range(1, count):
        if i - 1 < len(small_positions):
            x, y, w, h, rot = small_positions[i - 1]
            slots.append(CollageSlot(x, y, w, h, rot, i + 1))
        else:
            row = (i - 1) // 2
            col = (i - 1) % 2
            slots.append(
                CollageSlot(
                    0.58 + col * 0.20,
                    0.06 + row * 0.22,
                    0.18,
                    0.20,
                    (-1) ** i * 3,
                    i + 1,
                )
            )
    return slots[:count]


def _grid(count: int) -> list[CollageSlot]:
    cols = max(1, math.ceil(math.sqrt(count)))
    rows = max(1, math.ceil(count / cols))
    gap = 0.03
    cell_w = (1.0 - gap * (cols + 1)) / cols
    cell_h = (1.0 - gap * (rows + 1)) / rows
    slots: list[CollageSlot] = []
    for i in range(count):
        r, c = divmod(i, cols)
        slots.append(
            CollageSlot(
                gap + c * (cell_w + gap),
                gap + r * (cell_h + gap),
                cell_w,
                cell_h,
                0,
                i,
            )
        )
    return slots


def _hero_center(count: int) -> list[CollageSlot]:
    slots = [CollageSlot(0.22, 0.12, 0.56, 0.76, 0, 10)]
    ring = [
        (0.04, 0.08, 0.16, 0.28, -6),
        (0.04, 0.62, 0.16, 0.28, 5),
        (0.80, 0.08, 0.16, 0.28, 4),
        (0.80, 0.62, 0.16, 0.28, -4),
        (0.30, 0.02, 0.18, 0.14, 3),
        (0.52, 0.02, 0.18, 0.14, -2),
        (0.30, 0.86, 0.18, 0.10, 2),
        (0.52, 0.86, 0.18, 0.10, -3),
    ]
    for i in range(1, count):
        if i - 1 < len(ring):
            x, y, w, h, rot = ring[i - 1]
            slots.append(CollageSlot(x, y, w, h, rot, i))
    return slots[:count]


def _panorama(count: int) -> list[CollageSlot]:
    n = max(1, count)
    gap = 0.02
    h = 0.78
    y = 0.11
    w = (1.0 - gap * (n + 1)) / n
    return [
        CollageSlot(gap + i * (w + gap), y, w, h, (-1) ** i * 2, i)
        for i in range(n)
    ]


def _random_scatter(count: int, *, seed: int, margin: float = 0.04) -> list[CollageSlot]:
    rng = random.Random(seed)
    slots: list[CollageSlot] = []
    placed: list[tuple[float, float, float, float]] = []

    def overlaps(nx: float, ny: float, nw: float, nh: float) -> bool:
        for px, py, pw, ph in placed:
            if nx < px + pw * 0.72 and nx + nw * 0.72 > px and ny < py + nh * 0.72 and ny + nh * 0.72 > py:
                return True
        return False

    for i in range(count):
        size = rng.uniform(0.22, 0.38)
        aspect = rng.uniform(0.75, 1.35)
        w = size
        h = size / aspect
        h = min(h, 0.72)
        w = min(w, 0.42)
        for _ in range(80):
            x = rng.uniform(margin, max(margin, 1 - w - margin))
            y = rng.uniform(margin, max(margin, 1 - h - margin))
            if not overlaps(x, y, w, h):
                rot = rng.uniform(-12, 12)
                slots.append(CollageSlot(x, y, w, h, rot, i))
                placed.append((x, y, w, h))
                break
        else:
            slots.append(
                CollageSlot(
                    margin + (i % 3) * 0.30,
                    margin + (i // 3) * 0.28,
                    w,
                    h,
                    rng.uniform(-8, 8),
                    i,
                )
            )
            placed.append((slots[-1].x, slots[-1].y, w, h))
    return slots


def apply_spread(slots: list[CollageSlot], spread: float) -> list[CollageSlot]:
    """Skaluje pozycje kafelków względem środka grupy (1.0 = szablon, >1 rozsunięte, <1 zbite)."""
    if not slots or abs(spread - 1.0) < 0.001:
        return slots

    spread = max(0.25, min(2.5, float(spread)))
    centers = [(s.x + s.w / 2, s.y + s.h / 2) for s in slots]
    pivot_x = sum(c[0] for c in centers) / len(centers)
    pivot_y = sum(c[1] for c in centers) / len(centers)

    out: list[CollageSlot] = []
    for s in slots:
        cx = s.x + s.w / 2
        cy = s.y + s.h / 2
        ncx = pivot_x + (cx - pivot_x) * spread
        ncy = pivot_y + (cy - pivot_y) * spread
        out.append(
            CollageSlot(
                ncx - s.w / 2,
                ncy - s.h / 2,
                s.w,
                s.h,
                s.rotation,
                s.z,
            )
        )
    return out


def compute_layout_slots(
    layout_id: str,
    count: int,
    *,
    seed: int = 42,
) -> list[CollageSlot]:
    n = max(1, count)
    if layout_id == "museum_scatter":
        return _museum_scatter(n)
    if layout_id == "editorial":
        return _editorial(n)
    if layout_id == "grid":
        return _grid(n)
    if layout_id == "hero_center":
        return _hero_center(n)
    if layout_id == "panorama":
        return _panorama(n)
    if layout_id == "random_scatter":
        return _random_scatter(n, seed=seed)
    return _museum_scatter(n)
