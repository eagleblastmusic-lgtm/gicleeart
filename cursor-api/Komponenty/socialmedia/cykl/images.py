"""Zarzadzanie zdjeciami cyklu.

Struktura folderu (wewnatrz Komponenty/socialmedia/data/cykl/Obrazy/):

    <artysta-handle>/
        <tytul-handle>/
            main.<ext>                    # glowne zdjecie do FB + 1-sze IG karuzeli
            zoom_*.<ext>                  # zdjecia zblizen do IG karuzeli
            MOCKUP_*.<ext>                # mockup w ramce - ostatnie w IG karuzeli
            <cokolwiek_MOCKUP>.<ext>      # sufiks MOCKUP rozpoznawany case-insensitive

Konwencja:
- Pliki o nazwie 'main.*' (case-insensitive) -> image_main.
- Pliki zawierajace 'MOCKUP' w nazwie -> image_mockup (jest to ostatnie zdjecie
  w karuzeli Instagram i NIE idzie na Facebook).
- Wszystkie pozostale zdjecia (JPG/PNG/WEBP) -> zooms.

Checklista braku:
- main: MUSI byc (fallback: CDN URL product.image.src z Shopify, ale lepiej lokalny).
- min 1 zoom: zalecane dla IG karuzeli.
- mockup: zalecany do ostatniego slotu IG karuzeli.

Rozszerzenia akceptowane: .jpg .jpeg .png .webp
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import storage

ACCEPTED_EXTS = (".jpg", ".jpeg", ".png", ".webp")
_MOCKUP_RE = re.compile(r"mockup", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Slugifikacja - konsystentna z tags_taxonomy.py
# ---------------------------------------------------------------------------

_PL_MAP = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def slugify(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    v = v.translate(_PL_MAP)
    v = re.sub(r"[^A-Za-z0-9]+", "-", v).strip("-").lower()
    return v or ""


# ---------------------------------------------------------------------------
# ImageSet - opis zawartosci folderu
# ---------------------------------------------------------------------------

@dataclass
class ImageSet:
    main: str = ""              # wzgledna sciezka wewnatrz Obrazy/
    zooms: list[str] = field(default_factory=list)
    mockup: str = ""
    other: list[str] = field(default_factory=list)  # nierozpoznane

    def has_main(self) -> bool:
        return bool(self.main)

    def has_any_zoom(self) -> bool:
        return len(self.zooms) > 0

    def has_mockup(self) -> bool:
        return bool(self.mockup)

    def all_for_ig_carousel(self) -> list[str]:
        """Kolejnosc dla IG karuzeli: main -> zoomy (alfabetycznie) -> mockup (ostatni)."""
        out: list[str] = []
        if self.main:
            out.append(self.main)
        out.extend(sorted(self.zooms))
        if self.mockup:
            out.append(self.mockup)
        return out


# ---------------------------------------------------------------------------
# Operacje na katalogu
# ---------------------------------------------------------------------------

def painting_dir_rel(artist_handle: str, painting_handle: str) -> str:
    ah = artist_handle or "unknown"
    ph = painting_handle or "unknown"
    return f"{ah}/{ph}"


def painting_dir_abs(artist_handle: str, painting_handle: str) -> Path:
    rel = painting_dir_rel(artist_handle, painting_handle)
    return storage.images_dir() / rel


def ensure_painting_dir(artist_handle: str, painting_handle: str) -> Path:
    p = painting_dir_abs(artist_handle, painting_handle)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_images_for(artist_handle: str, painting_handle: str) -> ImageSet:
    p = painting_dir_abs(artist_handle, painting_handle)
    out = ImageSet()
    if not p.is_dir():
        return out
    rel_prefix = painting_dir_rel(artist_handle, painting_handle)
    for f in sorted(p.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in ACCEPTED_EXTS:
            continue
        name = f.name
        stem = f.stem
        rel = f"{rel_prefix}/{name}"
        if _MOCKUP_RE.search(stem):
            # Pierwszy wygrywa, kolejne -> other
            if not out.mockup:
                out.mockup = rel
            else:
                out.other.append(rel)
            continue
        if stem.lower() == "main":
            if not out.main:
                out.main = rel
            else:
                out.other.append(rel)
            continue
        out.zooms.append(rel)
    return out


def resolve_abs(rel_path: str) -> Path:
    """Zamien sciezke wzgledna (od Obrazy/) na pelna Path."""
    return storage.images_dir() / rel_path


def copy_into(
    source: Path,
    artist_handle: str,
    painting_handle: str,
    *,
    role: str = "zoom",
    target_name: str | None = None,
) -> str:
    """Kopiuje plik zrodlowy do folderu obrazu i zwraca sciezke WZGLEDNA (od Obrazy/).

    role: 'main' | 'zoom' | 'mockup' - wplywa tylko na domyslna nazwe docelowa.

    Gdy target_name=None:
    - role=main  -> 'main.<ext>' (nadpisuje istniejacy)
    - role=mockup-> '<oryginalna_nazwa_bez_ext>_MOCKUP.<ext>'
    - role=zoom  -> '<oryginalna_nazwa>' (z kolizjami: ' (1)', ' (2)' ...)
    """
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in ACCEPTED_EXTS:
        raise ValueError(f"Niedozwolone rozszerzenie: {source.suffix} (akceptowane: {ACCEPTED_EXTS})")

    target_dir = ensure_painting_dir(artist_handle, painting_handle)

    if target_name is None:
        if role == "main":
            target_name = f"main{source.suffix.lower()}"
        elif role == "mockup":
            stem = source.stem
            if not _MOCKUP_RE.search(stem):
                stem = f"{stem}_MOCKUP"
            target_name = f"{stem}{source.suffix.lower()}"
        else:
            target_name = source.name

    target = target_dir / target_name
    # Unikaj kolizji dla zoomow
    if role == "zoom" and target.exists() and target.resolve() != source.resolve():
        i = 1
        stem = Path(target_name).stem
        ext = Path(target_name).suffix
        while True:
            candidate = target_dir / f"{stem} ({i}){ext}"
            if not candidate.exists():
                target = candidate
                break
            i += 1

    if source.resolve() != target.resolve():
        shutil.copy2(source, target)

    rel = f"{painting_dir_rel(artist_handle, painting_handle)}/{target.name}"
    return rel


def delete_image(rel_path: str) -> bool:
    if not rel_path:
        return False
    p = resolve_abs(rel_path)
    try:
        if p.is_file():
            p.unlink()
            return True
    except OSError:
        return False
    return False


# ---------------------------------------------------------------------------
# Checklista braku zdjec
# ---------------------------------------------------------------------------

@dataclass
class MissingReport:
    item_id: str
    artist: str
    title_pl: str
    scheduled_at: str
    has_main: bool
    zooms_count: int
    has_mockup: bool

    def missing_labels(self) -> list[str]:
        out: list[str] = []
        if not self.has_main:
            out.append("main")
        if self.zooms_count == 0:
            out.append("min 1 zoom")
        if not self.has_mockup:
            out.append("MOCKUP")
        return out


def missing_report(items: list[storage.CykleItem]) -> list[MissingReport]:
    reports: list[MissingReport] = []
    for it in items:
        if it.status in ("done", "skipped"):
            continue
        im = list_images_for(it.artist_handle, it.painting_handle)
        reports.append(
            MissingReport(
                item_id=it.id,
                artist=it.artist,
                title_pl=it.painting_title_pl,
                scheduled_at=it.scheduled_at,
                has_main=im.has_main() or bool(it.product_image_url),
                zooms_count=len(im.zooms),
                has_mockup=im.has_mockup(),
            )
        )
    return reports


def sync_item_images(item: storage.CykleItem) -> None:
    """Aktualizuje pola image_* na item wg zawartosci folderu.

    Policy:
    - Default (master) pola image_main/zooms/mockup zawsze odswiezamy.
    - image_fb_* / image_ig_* synchronizujemy z folderem TYLKO gdy uzytkownik
      ich jeszcze NIE ustawil (puste) ALBO gdy set identyczny jak master.
      Dzieki temu manualny ovveride w panelu bocznym / edit_dialog nie jest
      nadpisywany przy kazdym refreshu.
    """
    im = list_images_for(item.artist_handle, item.painting_handle)
    item.image_main = im.main
    item.image_zooms = sorted(im.zooms)
    item.image_mockup = im.mockup

    def _is_empty(main: str, zooms: list[str], mockup: str) -> bool:
        return not (main or zooms or mockup)

    # FB
    if _is_empty(item.image_fb_main, item.image_fb_zooms, item.image_fb_mockup):
        item.image_fb_main = im.main
        item.image_fb_zooms = sorted(im.zooms)
        item.image_fb_mockup = im.mockup

    # IG
    if _is_empty(item.image_ig_main, item.image_ig_zooms, item.image_ig_mockup):
        item.image_ig_main = im.main
        item.image_ig_zooms = sorted(im.zooms)
        item.image_ig_mockup = im.mockup

    # Migracja z legacy image_ig_pl (stare queue.json sprzed oddzielnych pol)
    if not item.image_ig_main and item.image_ig_pl:
        # Stary format: image_ig_pl = [main, zoom1, zoom2, ..., MOCKUP]
        old = list(item.image_ig_pl)
        if old:
            item.image_ig_main = old[0]
            last = old[-1] if len(old) > 1 else ""
            if last and "mockup" in last.lower():
                item.image_ig_mockup = last
                item.image_ig_zooms = old[1:-1]
            else:
                item.image_ig_zooms = old[1:]
    if not item.image_fb_main and item.image_fb_pl:
        item.image_fb_main = item.image_fb_pl


def open_images_folder() -> Path:
    """Zwraca Path do glownego folderu Obrazy/ (user moze go otworzyc w Explorerze)."""
    return storage.images_dir()
