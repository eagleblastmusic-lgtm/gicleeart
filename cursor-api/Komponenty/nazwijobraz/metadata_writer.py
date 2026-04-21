"""Zapis metadanych obrazu po znalezieniu tytulu.

Zapisuje:
- ImageDescription / Artist  - angielski tytul, autor (EXIF)
- XPSubject / XPTitle        - oryginalny tytul (UTF-16LE, Windows-friendly)
- XPComment                  - jezyk oryginalu + URL zrodla

Dla JPEG uzywa piexif (in-place, bez utraty jakosci, jesli zainstalowany).
W przeciwnym wypadku zapisuje sidecar JSON: '<plik>.metadata.json'.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import piexif  # type: ignore

    _HAS_PIEXIF = True
except ImportError:
    _HAS_PIEXIF = False

try:
    from PIL import Image  # type: ignore
    from PIL.PngImagePlugin import PngInfo  # type: ignore

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Pillow EXIF tag IDs (te same co w piexif.ImageIFD).
_TAG_IMAGE_DESCRIPTION = 270
_TAG_ARTIST = 315
_TAG_COPYRIGHT = 33432
_TAG_DATETIME = 306        # 0th IFD: ostatnia modyfikacja pliku
_TAG_XP_TITLE = 40091
_TAG_XP_COMMENT = 40092
_TAG_XP_AUTHOR = 40093
_TAG_XP_KEYWORDS = 40094
_TAG_XP_SUBJECT = 40095
# Exif IFD (sub-dict "Exif" w piexif):
_TAG_DATETIME_ORIGINAL = 36867    # data POWSTANIA obrazu
_TAG_DATETIME_DIGITIZED = 36868


@dataclass
class ArtworkMetadata:
    english_title: str = ""
    original_title: str = ""
    original_lang: str = ""
    artist: str = ""
    creation_year: str = ""  # rok powstania obrazu (P571), np. "1875"
    source_url: str = ""
    source_name: str = ""  # np. "wikidata", "met", "artic"


def _to_xp_bytes(text: str) -> bytes:
    # Windows XP* tagi zapisuja UTF-16LE z koncowym \x00\x00.
    return (text or "").encode("utf-16le") + b"\x00\x00"


def _ascii(text: str) -> bytes:
    # EXIF ASCII tag: bezpieczny ASCII (nie-ASCII zamieniane na "?").
    # piexif sam dodaje null-terminator przy zapisie - nie dopisujemy.
    return (text or "").encode("ascii", errors="replace")


def _write_jpeg_exif(path: Path, meta: ArtworkMetadata) -> None:
    """Zapis EXIF do JPEG przez piexif (bez ponownego kodowania pikseli)."""
    if not _HAS_PIEXIF:
        return
    try:
        exif_dict = piexif.load(str(path))  # type: ignore[attr-defined]
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    zeroth = exif_dict.setdefault("0th", {})
    exif_sub = exif_dict.setdefault("Exif", {})
    if meta.english_title:
        zeroth[_TAG_IMAGE_DESCRIPTION] = _ascii(meta.english_title)
        zeroth[_TAG_XP_TITLE] = _to_xp_bytes(meta.english_title)
    if meta.artist:
        zeroth[_TAG_ARTIST] = _ascii(meta.artist)
        zeroth[_TAG_XP_AUTHOR] = _to_xp_bytes(meta.artist)
    if meta.original_title:
        zeroth[_TAG_XP_SUBJECT] = _to_xp_bytes(meta.original_title)
    if meta.creation_year:
        dt = _exif_datetime_for_year(meta.creation_year)
        if dt:
            exif_sub[_TAG_DATETIME_ORIGINAL] = dt.encode("ascii")
            exif_sub[_TAG_DATETIME_DIGITIZED] = dt.encode("ascii")
    comment = _build_xp_comment(meta)
    if comment:
        zeroth[_TAG_XP_COMMENT] = _to_xp_bytes(comment)

    try:
        exif_bytes = piexif.dump(exif_dict)  # type: ignore[attr-defined]
        piexif.insert(exif_bytes, str(path))  # type: ignore[attr-defined]
    except Exception:
        # cicho - sidecar i tak zostanie zapisany
        pass


def _build_xp_comment(meta: ArtworkMetadata) -> str:
    parts: list[str] = []
    if meta.creation_year:
        parts.append(f"year={meta.creation_year}")
    if meta.original_lang:
        parts.append(f"original_lang={meta.original_lang}")
    if meta.original_title:
        parts.append(f"original_title={meta.original_title}")
    if meta.source_name:
        parts.append(f"source={meta.source_name}")
    if meta.source_url:
        parts.append(f"url={meta.source_url}")
    return " | ".join(parts)


def _exif_datetime_for_year(year: str) -> str:
    """Zamien rok typu '1875' na EXIF DateTimeOriginal format 'YYYY:01:01 00:00:00'.

    EXIF spec wymaga dokladnie 'YYYY:MM:DD HH:MM:SS' - 19 znakow ASCII. Brak
    dokladnego miesiaca/dnia oznaczamy '01:01 00:00:00', bo pole nie wspiera
    luznego "tylko rok". Aplikacje czytajace EXIF (Windows Explorer, Lightroom)
    pokaza sam rok w kolumnie "Data wykonania".
    """
    y = (year or "").strip()
    if not y or not y.isdigit():
        return ""
    year_int = int(y)
    if year_int < 1 or year_int > 9999:
        return ""
    return f"{year_int:04d}:01:01 00:00:00"


def _write_png_metadata(path: Path, meta: ArtworkMetadata) -> bool:
    """Zapis metadanych do PNG przez tEXt chunki (Title/Author/Description/...).

    PIL nadpisuje plik w miejscu - obraz jest dekodowany i ponownie zapisany,
    ale PNG jest stratny tylko jezeli zmienisz kompresje. Zachowujemy poziom 6.
    """
    if not _HAS_PIL:
        return False
    try:
        with Image.open(path) as img:
            img.load()
            info = PngInfo()
            if meta.english_title:
                info.add_text("Title", meta.english_title)
            if meta.artist:
                info.add_text("Author", meta.artist)
            if meta.english_title:
                info.add_text("Description", meta.english_title)
            if meta.original_title:
                info.add_text("OriginalTitle", meta.original_title)
            if meta.original_lang:
                info.add_text("OriginalLanguage", meta.original_lang)
            if meta.creation_year:
                # "CreationTime" to standardowy keyword PNG dla daty utworzenia,
                # "Year" dajemy dodatkowo dla wygody (niektore narzedzia czytaja).
                info.add_text("CreationTime", meta.creation_year)
                info.add_text("Year", meta.creation_year)
            if meta.source_url:
                info.add_text("Source", meta.source_url)
            if meta.source_name:
                info.add_text("SourceName", meta.source_name)
            tmp = path.with_suffix(path.suffix + ".tmp")
            img.save(tmp, format="PNG", pnginfo=info, optimize=False)
        tmp.replace(path)
        return True
    except (OSError, ValueError):
        return False


def _build_piexif_dict(meta: ArtworkMetadata) -> dict | None:
    """Buduje slownik exif do piexif.dump - uzywany dla JPEG i WebP."""
    if not _HAS_PIEXIF:
        return None
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    zeroth = exif_dict["0th"]
    exif_sub = exif_dict["Exif"]
    if meta.english_title:
        zeroth[_TAG_IMAGE_DESCRIPTION] = _ascii(meta.english_title)
        zeroth[_TAG_XP_TITLE] = _to_xp_bytes(meta.english_title)
    if meta.artist:
        zeroth[_TAG_ARTIST] = _ascii(meta.artist)
        zeroth[_TAG_XP_AUTHOR] = _to_xp_bytes(meta.artist)
    if meta.original_title:
        zeroth[_TAG_XP_SUBJECT] = _to_xp_bytes(meta.original_title)
    if meta.creation_year:
        dt = _exif_datetime_for_year(meta.creation_year)
        if dt:
            exif_sub[_TAG_DATETIME_ORIGINAL] = dt.encode("ascii")
            exif_sub[_TAG_DATETIME_DIGITIZED] = dt.encode("ascii")
    comment = _build_xp_comment(meta)
    if comment:
        zeroth[_TAG_XP_COMMENT] = _to_xp_bytes(comment)
    return exif_dict


def _write_webp_metadata(path: Path, meta: ArtworkMetadata) -> bool:
    """Zapis EXIF do WebP - przepisanie pliku z `exif=...`."""
    if not (_HAS_PIL and _HAS_PIEXIF):
        return False
    exif_dict = _build_piexif_dict(meta)
    if exif_dict is None:
        return False
    try:
        exif_bytes = piexif.dump(exif_dict)  # type: ignore[attr-defined]
        with Image.open(path) as img:
            img.load()
            tmp = path.with_suffix(path.suffix + ".tmp")
            # WebP: lossless=True jesli oryginal byl lossless? Trudno wykryc;
            # zostawmy quality=95 jako domyslne i zachowajmy method=4.
            save_kwargs: dict = {"exif": exif_bytes, "quality": 95, "method": 4}
            img.save(tmp, format="WEBP", **save_kwargs)
        tmp.replace(path)
        return True
    except (OSError, ValueError, KeyError):
        return False


def _write_sidecar(path: Path, meta: ArtworkMetadata) -> Path:
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    payload = {k: v for k, v in asdict(meta).items() if v}
    sidecar.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return sidecar


def write_artwork_metadata(path: str | Path, meta: ArtworkMetadata) -> dict[str, str]:
    """Zapisuje metadane do pliku obrazu i zwraca info o tym, co zostalo zapisane.

    Wynik:
        {"exif": "ok"|"skipped"|"unsupported", "sidecar": "<plik>" }
    """
    p = Path(path)
    info: dict[str, str] = {"exif": "skipped", "sidecar": ""}
    if not p.is_file():
        return info

    ext = p.suffix.lower()
    if ext in {".jpg", ".jpeg", ".jpe", ".jfif"}:
        if _HAS_PIEXIF:
            _write_jpeg_exif(p, meta)
            info["exif"] = "ok"
        else:
            info["exif"] = "skipped"
    elif ext == ".png":
        if _HAS_PIL and _write_png_metadata(p, meta):
            info["exif"] = "png-text"
        else:
            info["exif"] = "skipped"
    elif ext == ".webp":
        if _HAS_PIL and _HAS_PIEXIF and _write_webp_metadata(p, meta):
            info["exif"] = "webp-exif"
        else:
            info["exif"] = "skipped"
    else:
        info["exif"] = "unsupported"

    # Zawsze sidecar - dziala dla wszystkich formatow i jest czytelny.
    if any([meta.english_title, meta.original_title, meta.artist]):
        try:
            sc = _write_sidecar(p, meta)
            info["sidecar"] = sc.name
        except OSError:
            pass

    return info
