"""Skladanie obrazu z dziela w pole A4 szablonu mockupu."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

from .templates import MockupTemplate


def _fit_cover(art: Image.Image, target_w: int, target_h: int) -> Image.Image:
    aw, ah = art.size
    if aw <= 0 or ah <= 0 or target_w <= 0 or target_h <= 0:
        raise ValueError("Nieprawidlowy rozmiar obrazu lub slotu.")
    scale = max(target_w / aw, target_h / ah)
    new_w = max(1, int(round(aw * scale)))
    new_h = max(1, int(round(ah * scale)))
    resized = art.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _is_hole_pixel(r: int, g: int, b: int, a: int) -> bool:
    if a < 128:
        return True
    return a > 128 and r < 45 and g < 45 and b < 45


def detect_slot(image: Image.Image) -> tuple[int, int, int, int]:
    """Wykrywa pole A4: flood-fill od srodka (przezroczystosc lub ciemny otwor w passe-partout)."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    cx, cy = w // 2, h // 2

    if not _is_hole_pixel(*px[cx, cy]):
        raise ValueError("Srodek szablonu nie lezy w polu na obraz — podaj wspolrzedne recznie.")

    visited: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque([(cx, cy)])
    visited.add((cx, cy))
    min_x = max_x = cx
    min_y = max_y = cy

    while q:
        x, y = q.popleft()
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                continue
            if (nx, ny) in visited:
                continue
            if _is_hole_pixel(*px[nx, ny]):
                visited.add((nx, ny))
                q.append((nx, ny))

    bw = max_x - min_x + 1
    bh = max_y - min_y + 1
    if bw < w * 0.08 or bh < h * 0.08:
        raise ValueError("Wykryte pole jest za male — sprawdz szablon lub podaj slot recznie.")
    return (min_x, min_y, bw, bh)


def _slot_uses_overlay(mockup: Image.Image, slot: tuple[int, int, int, int]) -> bool:
    """True gdy mockup ma przezroczyste/alfowe otwory (obraz idzie pod spodem)."""
    x, y, sw, sh = slot
    if sw <= 0 or sh <= 0:
        return False
    alpha = mockup.convert("RGBA").split()[3]
    region = alpha.crop((x, y, x + sw, y + sh))
    lo, hi = region.getextrema()
    return lo < 200


def composite_artwork(
    template: MockupTemplate,
    artwork_path: Path,
    *,
    slot: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Naklada artwork w pole A4 szablonu. Zwraca obraz RGBA gotowy do zapisu."""
    if not template.path.is_file():
        raise FileNotFoundError(f"Brak pliku mockupu: {template.path}")
    if not artwork_path.is_file():
        raise FileNotFoundError(f"Brak pliku obrazu: {artwork_path}")

    mockup = Image.open(template.path).convert("RGBA")
    art = Image.open(artwork_path).convert("RGBA")

    use_slot = slot or template.slot
    if use_slot == (0, 0, 0, 0):
        use_slot = detect_slot(mockup)
    else:
        # Weryfikacja: jesli reczny slot wyglada na cala ramke, probuj auto.
        x, y, sw, sh = use_slot
        mw, mh = mockup.size
        if sw > mw * 0.85 or sh > mh * 0.85:
            try:
                use_slot = detect_slot(mockup)
            except ValueError:
                pass

    x, y, sw, sh = use_slot
    art_fit = _fit_cover(art, sw, sh)

    if _slot_uses_overlay(mockup, use_slot):
        canvas = Image.new("RGBA", mockup.size, (255, 255, 255, 255))
        canvas.paste(art_fit, (x, y))
        canvas.alpha_composite(mockup)
        return canvas

    result = mockup.copy()
    result.paste(art_fit, (x, y))
    return result
