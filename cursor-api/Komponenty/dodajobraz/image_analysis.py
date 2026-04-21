"""Analiza obrazu (Pillow) - automatyczne tagi: orientacja + dominujacy kolor.

Wynikowe tagi sa zgodne z taksonomia (`tags_taxonomy.py`) i napedzaja smart-collections.

Funkcje:
  * orientation_tag(path)             -> 'pionowy' | 'poziomy' | 'kwadrat' | 'panorama'
  * dominant_color_tag(path)          -> tag koloru z palety PL (np. 'niebieski')
  * analyze_image(path) -> {'orientation': ..., 'dominant_color': ..., 'aspect': float}

Zasady decyzji:
  - kwadrat:    aspect w przedziale [0.95, 1.05]
  - panorama:   aspect >= 2.4  (np. 30x70cm pejzaz panoramiczny)
  - poziomy:    aspect > 1.05 i < 2.4
  - pionowy:    aspect <= 0.95

Dominujacy kolor:
  - downscale obrazu do 96x96 -> kwantyzacja do 8 kolorow (PIL adaptive palette)
  - bierzemy najczestszy kolor PO ODFILTROWANIU bardzo jasnych (tlo) i bardzo
    ciemnych (cienie) pixeli, zeby nie reportowac 'czarny'/'bialy' dla wszystkich
    obrazow z czarna ramka albo bialym marginesem
  - mapowanie RGB -> nazwa PL po Euclidean distance w przestrzeni RGB do palety 12 kolorow.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as e:  # pragma: no cover - import-time error
    raise ImportError(
        "Pillow nie jest zainstalowany. Zainstaluj: pip install Pillow"
    ) from e


# ---------------------------------------------------------------------------
# Orientacja
# ---------------------------------------------------------------------------

ORIENTATION_TAGS = {
    "pionowy":    "format pionowy",
    "poziomy":    "format poziomy",
    "kwadrat":    "format kwadratowy",
    "panorama":   "panorama",
}


def orientation_kind(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "poziomy"
    aspect = width / height
    if 0.95 <= aspect <= 1.05:
        return "kwadrat"
    if aspect >= 2.4:
        return "panorama"
    if aspect > 1.05:
        return "poziomy"
    return "pionowy"


def orientation_tag(width: int, height: int) -> str:
    """Zwraca tag PL ('format pionowy' / 'format poziomy' / 'format kwadratowy' / 'panorama')."""
    return ORIENTATION_TAGS[orientation_kind(width, height)]


# ---------------------------------------------------------------------------
# Paleta kolorow PL (12 najczesciej wyszukiwanych w sklepach z obrazami w PL)
# ---------------------------------------------------------------------------
# RGB approximations - srodek prototypowy kazdego koloru.
# UWAGA: paleta i jej nazwy MUSZA pokrywac sie z tags_taxonomy.COLOR_TAG_TO_COLLECTION
# (jezeli chcemy smart-collections per kolor - dorobic w taksonomii).

COLOR_PALETTE: dict[str, tuple[int, int, int]] = {
    "czarny":     (20, 20, 20),
    "bialy":      (240, 240, 240),
    "szary":      (130, 130, 130),
    "be\u017cowy":(220, 200, 170),  # bezowy
    "br\u0105zowy":(110, 75, 50),   # brazowy
    "z\u0142oty": (190, 160, 70),   # zloty
    "czerwony":   (190, 50, 50),
    "r\u00f3\u017cowy":(220, 130, 160),  # rozowy
    "pomara\u0144czowy":(225, 130, 50),  # pomaranczowy
    "\u017c\u00f3\u0142ty":(230, 200, 60),  # zolty
    "zielony":    (90, 140, 70),
    "niebieski":  (60, 110, 180),
    "granatowy":  (30, 50, 110),
    "fioletowy":  (130, 80, 160),
    "turkusowy":  (60, 175, 175),
}


# Tag SEO uzywany w produkcie (jako tag) i tytule kolekcji
def color_seo_tag(color_name: str) -> str:
    """'niebieski' -> 'obraz niebieski' (lepsza fraza zakupowa PL)."""
    return f"obraz {color_name}"


# ---------------------------------------------------------------------------
# Dominujacy kolor
# ---------------------------------------------------------------------------

def _color_distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _nearest_palette_name(rgb: tuple[int, int, int]) -> str:
    return min(COLOR_PALETTE.keys(), key=lambda name: _color_distance_sq(rgb, COLOR_PALETTE[name]))


def _is_neutral_extreme(r: int, g: int, b: int) -> bool:
    """Pixel uznawany za 'tlo' (zbyt jasny), 'cien' (zbyt ciemny) lub 'osmolony szary'."""
    brightness = (r + g + b) / 3
    if brightness < 25:
        return True
    if brightness > 240:
        return True
    return False


def dominant_color_name(image_path: str | Path, *, sample_size: int = 96) -> str:
    """Zwraca nazwe najczestszego koloru z palety dla podanego obrazu.

    Filtrowanie:
      - skipujemy bardzo jasne/ciemne pixele (background / shadow),
      - jesli wszystkie sa odfiltrowane (np. obraz monochromatyczny) - bierzemy
        po prostu nearest_palette dla sredniej.
    """
    p = Path(image_path)
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((sample_size, sample_size))
        # Kwantyzacja do 16 kolorow zeby ograniczyc szum
        quant = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT).convert("RGB")
        pixels = list(quant.getdata())

    counts: Counter[str] = Counter()
    for r, g, b in pixels:
        if _is_neutral_extreme(r, g, b):
            continue
        name = _nearest_palette_name((r, g, b))
        counts[name] += 1

    if not counts:
        # Fallback: srednia z wszystkich pixeli (nie filtrujac)
        if not pixels:
            return "szary"
        avg_r = sum(p[0] for p in pixels) // len(pixels)
        avg_g = sum(p[1] for p in pixels) // len(pixels)
        avg_b = sum(p[2] for p in pixels) // len(pixels)
        return _nearest_palette_name((avg_r, avg_g, avg_b))

    return counts.most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Glowne API
# ---------------------------------------------------------------------------

def get_image_dimensions(image_path: str | Path) -> tuple[int, int]:
    """Zwraca (width, height) z uwzglednieniem EXIF rotation."""
    p = Path(image_path)
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im)
        return int(im.width), int(im.height)


def analyze_image(image_path: str | Path) -> dict:
    """Pelna analiza obrazu: orientacja, aspect ratio, dominujacy kolor.

    Zwraca slownik:
      {
        'width': int, 'height': int, 'aspect': float,
        'orientation_kind': 'pionowy'|'poziomy'|'kwadrat'|'panorama',
        'orientation_tag': str (pelna fraza PL),
        'dominant_color_name': str (np. 'niebieski'),
        'dominant_color_tag': str (np. 'obraz niebieski'),
        'extra_tags': list[str] (wszystkie auto-tagi do dolozenia do produktu),
      }

    'extra_tags' to wszystkie tagi gotowe do dorzucenia do listy 'tagi' w llm_data.
    """
    w, h = get_image_dimensions(image_path)
    kind = orientation_kind(w, h)
    color = dominant_color_name(image_path)
    extra = [
        ORIENTATION_TAGS[kind],
        color,
        color_seo_tag(color),
    ]
    return {
        "width": w,
        "height": h,
        "aspect": (w / h) if h > 0 else 0.0,
        "orientation_kind": kind,
        "orientation_tag": ORIENTATION_TAGS[kind],
        "dominant_color_name": color,
        "dominant_color_tag": color_seo_tag(color),
        "extra_tags": extra,
    }
