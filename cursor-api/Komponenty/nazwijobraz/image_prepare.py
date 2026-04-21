"""Przygotowanie obrazu do wysylki: redukcja rozmiaru do max N MB.

Uzywa Pillow; jesli nie jest zainstalowane, wraca do oryginalnego pliku.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageFile, ImageOps  # type: ignore

    _HAS_PIL = True
    # Obrazy od uzytkownika moga miec bardzo wysoka rozdzielczosc (reprodukcje muzealne,
    # >200 megapikseli). Wylaczamy zabezpieczenie anty-"decompression bomb" Pillowa:
    # pliki pochodza z dysku uzytkownika, wiec ryzyko DoS nie dotyczy tego scenariusza.
    Image.MAX_IMAGE_PIXELS = None
    # Pozwol czytac lekko obciete pliki.
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    _HAS_PIL = False


DEFAULT_MAX_BYTES = 4_000_000  # ~4 MB - wieksza rozdzielczosc daje lepsze rozpoznanie
# w Google Lens / Yandex / Bing. Wczesniej 1.5 MB powodowalo agresywna kompresje
# do 0.2 MB co tracilo featury (np. dla "Babie lato" Chełmońskiego Lens nie
# rozpoznawal zmniejszonej wersji, dopiero z wieksza rozdzielczoscia trafia).
# Trade-off: upload 4 MB jest ~4x dluzszy niz 1 MB, ale daje wyraznie lepsze
# trafienia wizualne.
# Gorny limit dluzszego boku obrazu po zmniejszeniu - 2048 px zwykle wystarcza
# Lens, a daje znacznie wiecej szczegolu niz 1280 px.
_MAX_LONGEST_EDGE = 2048
_MIN_LONGEST_EDGE = 1024
_JPEG_QUALITIES = (88, 82, 74, 66, 58)


@dataclass
class PreparedImage:
    data: bytes
    filename: str  # np. 'orig_name.jpg'
    mime: str


def _read_raw(path: Path) -> PreparedImage:
    ext = (path.suffix or ".jpg").lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(ext, "application/octet-stream")
    return PreparedImage(data=path.read_bytes(), filename=path.name, mime=mime)


def prepare_for_upload(file_path: str | Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> PreparedImage:
    """Zwraca bytes+nazwa gotowe do uploadu; skaluje/JPEG-izuje jesli >max_bytes."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    size = p.stat().st_size
    if size <= max_bytes:
        return _read_raw(p)
    if not _HAS_PIL:
        # Brak Pillow: wysylamy oryginal (mozna ostrzec wyzej).
        return _read_raw(p)

    with Image.open(p) as im:  # type: ignore[attr-defined]
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        base_w, base_h = im.size
        longest = max(base_w, base_h)

        # Plan zmniejszania: zacznij od min(longest, _MAX_LONGEST_EDGE)
        edges = []
        start = min(longest, _MAX_LONGEST_EDGE)
        cur = start
        while cur >= _MIN_LONGEST_EDGE:
            edges.append(cur)
            cur = int(cur * 0.85)
        if edges and edges[-1] > _MIN_LONGEST_EDGE:
            edges.append(_MIN_LONGEST_EDGE)
        if not edges:
            edges = [min(longest, _MIN_LONGEST_EDGE)]

        best: bytes | None = None
        for edge in edges:
            scale = edge / longest
            w = max(1, int(base_w * scale))
            h = max(1, int(base_h * scale))
            resized = im.resize((w, h), Image.LANCZOS)  # type: ignore[attr-defined]
            for q in _JPEG_QUALITIES:
                buf = io.BytesIO()
                resized.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
                data = buf.getvalue()
                if len(data) <= max_bytes:
                    best = data
                    break
                best = data  # trzymaj najmniejszy wariant jako fallback
            if best is not None and len(best) <= max_bytes:
                break

        assert best is not None
        new_name = p.with_suffix(".jpg").name
        return PreparedImage(data=best, filename=new_name, mime="image/jpeg")
