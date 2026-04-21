import argparse
import html as html_lib
import json
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import requests
from PIL import Image, ImageFile
from requests.adapters import HTTPAdapter

DEFAULT_SERVICE_ID = "https://www.nationalgallery.org.uk/server.iip?IIIF=/fronts/N-1050-00-000033-FS-PYR.tif"
DEFAULT_FULL_W, DEFAULT_FULL_H = 7242, 5277
DEFAULT_TILE = None
DEFAULT_OUT_FILE = "obraz_full.png"
DEFAULT_TEMP_FILE = "obraz_full.partial.png"
DEFAULT_STATE_FILE = "obraz_full.state.json"

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

THREAD_LOCAL = threading.local()

def parse_args():
    parser = argparse.ArgumentParser(description="Pobieranie pelnego obrazu IIIF przez kafelki.")
    parser.add_argument("--page-url", help="URL strony obrazu (skrypt sam wyszuka IIIF)")
    parser.add_argument("--info-url", help="Bezposredni URL do IIIF info.json")
    parser.add_argument("--service-id", help="IIIF service id z info.json")
    parser.add_argument("--width", type=int, help="Szerokosc pelnego obrazu")
    parser.add_argument("--height", type=int, help="Wysokosc pelnego obrazu")
    parser.add_argument("--tile", type=int, help="Rozmiar pobieranego fragmentu; domyslnie auto z info.json")
    parser.add_argument("--out", help="Nazwa pliku wynikowego")
    parser.add_argument("--temp", default=DEFAULT_TEMP_FILE, help="Nazwa pliku tymczasowego obrazu")
    parser.add_argument("--state", default=DEFAULT_STATE_FILE, help="Nazwa pliku stanu")
    parser.add_argument("--workers", type=int, default=8, help="Liczba rownoleglych pobran")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout jednego zapytania (sekundy)")
    parser.add_argument("--retries", type=int, default=4, help="Liczba prob pobrania kafla")
    parser.add_argument(
        "--backoff-base",
        type=float,
        default=1.2,
        help="Bazowe opoznienie miedzy retry (sekundy, rosnie wykladniczo)",
    )
    parser.add_argument("--quality", default="default", help="IIIF quality, np. default/color/gray")
    parser.add_argument("--format", default="jpg", help="IIIF format, np. jpg/webp")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=0,
        help="Zapis stanu co N pobran; 0 wylacza checkpointy w trakcie i przyspiesza pobieranie",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=5,
        help="Pokazuj postep co N fragmentow; 0 pokazuje tylko start i koniec",
    )
    return parser.parse_args()


def tile_key(row, col):
    return f"{row}:{col}"


def load_state(state_file, total_tiles, chunk_size, width, height):
    path = Path(state_file)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("chunk_size") != chunk_size or data.get("width") != width or data.get("height") != height:
        print("Znaleziono stary stan z innymi parametrami. Pomijam go i zaczynam od nowa.")
        return set()
    done = set(data.get("done_tiles", []))
    print(f"Wczytano stan: {len(done)}/{total_tiles} kafelkow.")
    return done


def save_state(state_file, done_tiles, chunk_size, width, height):
    data = {
        "chunk_size": chunk_size,
        "width": width,
        "height": height,
        "done_tiles": sorted(done_tiles),
    }
    Path(state_file).parent.mkdir(parents=True, exist_ok=True)
    Path(state_file).write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")


def get_canvas(temp_file, width, height, force_new=False):
    temp_path = Path(temp_file)
    if temp_path.exists() and not force_new:
        print(f"Wznawiam z pliku tymczasowego: {temp_file}")
        return np.array(Image.open(temp_path).convert("RGB"))
    print("Tworze nowy canvas.")
    return np.zeros((height, width, 3), dtype=np.uint8)


def print_progress(done_count, total_tiles):
    percent = (done_count / total_tiles) * 100 if total_tiles else 100
    print(f"Postep: {done_count}/{total_tiles} ({percent:.2f}%)")


def should_print_progress(done_count, total_tiles, progress_every):
    if done_count == 0 or done_count == total_tiles:
        return True
    if progress_every <= 0:
        return False
    return done_count % progress_every == 0


def create_session(pool_size):
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "iiif-full-download/1.0"})
    return session


def get_thread_session(pool_size):
    session = getattr(THREAD_LOCAL, "session", None)
    if session is None:
        session = create_session(pool_size)
        THREAD_LOCAL.session = session
    return session


def fetch_info_json(info_url, timeout):
    resp = create_session(4).get(info_url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # IIIF v2 ma id w "@id", v3 w "id" - bierzemy jedno albo drugie.
    service_id = data.get("id") or data.get("@id")
    width = data.get("width")
    height = data.get("height")
    max_width = data.get("maxWidth")
    max_height = data.get("maxHeight")
    tiles = data.get("tiles") or []
    tile_width = None
    tile_height = None
    if tiles:
        tile_width = tiles[0].get("width")
        tile_height = tiles[0].get("height", tile_width)

    if not service_id or not width or not height:
        raise RuntimeError(f"Brak wymaganych pol w info.json: {info_url}")

    auto_chunk = min(
        int(max_width or tile_width or DEFAULT_TILE or 256),
        int(max_height or tile_height or max_width or tile_width or DEFAULT_TILE or 256),
    )

    # ---- Wspierane qualities / formats ----
    # IIIF v2: "profile": ["http://iiif.io/api/image/2/level2.json", { "formats": [...], "qualities": [...] }]
    # IIIF v3: "extraQualities": [...], "extraFormats": [...]
    qualities: list[str] = []
    formats: list[str] = []
    profile = data.get("profile")
    if isinstance(profile, list):
        for entry in profile:
            if isinstance(entry, dict):
                for q in entry.get("qualities") or []:
                    if q not in qualities:
                        qualities.append(q)
                for f in entry.get("formats") or []:
                    if f not in formats:
                        formats.append(f)
    elif isinstance(profile, dict):
        for q in profile.get("qualities") or []:
            if q not in qualities:
                qualities.append(q)
        for f in profile.get("formats") or []:
            if f not in formats:
                formats.append(f)
    for q in data.get("extraQualities") or []:
        if q not in qualities:
            qualities.append(q)
    for f in data.get("extraFormats") or []:
        if f not in formats:
            formats.append(f)
    # IIIF spec: 'default' quality i 'jpg' format SA zawsze gwarantowane.
    if "default" not in qualities:
        qualities.insert(0, "default")
    if "jpg" not in formats:
        formats.append("jpg")

    return service_id, int(width), int(height), auto_chunk, qualities, formats


def sanitize_for_filename(text):
    """Usuwa znaki nielegalne dla Windows. Zachowuje unicode (é, ø, ł, etc.)."""
    if not text:
        return "obraz full"
    # Windows-illegal: < > : " / \ | ? * + control chars
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "obraz full"


# Prefixy atrybucji uzywane przez muzea. Sortowane od najdluzszych - dopasowujemy
# zachłannie zeby "Possibly by" nie wpadlo do "by".
_ATTRIBUTION_PREFIXES = (
    "Probably by",
    "Possibly by",
    "Attributed to",
    "Workshop of",
    "Follower of",
    "Imitator of",
    "Associate of",
    "Manner of",
    "Studio of",
    "Circle of",
    "School of",
    "Style of",
    "Copy after",
    "After",
)

# Czastki nazwisk - traktujemy je jako czesc nazwiska przy odwracaniu
# "Imie Nazwisko" -> "Nazwisko, Imie".
# "Leonardo da Vinci" -> "da Vinci, Leonardo" (a NIE "Vinci, Leonardo da")
_SURNAME_PARTICLES = {
    "da", "de", "del", "dell", "della", "di", "do", "dos", "du",
    "la", "le", "les", "lo",
    "van", "von", "der", "den", "ten", "ter",
    "af", "av",
    "el", "al",
    "st", "st.", "saint", "ste", "ste.",
    "mc", "mac",
    "y",  # hiszpanski compound
    "auf", "zur", "zum", "zu",
}


def _decode_html(s):
    """Dekoduje encje HTML i normalizuje biale znaki."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", html_lib.unescape(s)).strip()


def parse_ng_page_meta(html):
    """Wyciaga (artist_full, title) z <title> National Gallery.

    Format strony NG to zawsze:
        Artysta | Tytul | NG#### | National Gallery, London

    Zwraca (artist, title) albo (None, None) gdy nie da sie sparsowac.
    """
    m = re.search(r"<title>(.*?)</title>", html or "", re.S | re.I)
    if not m:
        return None, None
    title_tag = _decode_html(m.group(1))
    parts = [p.strip() for p in title_tag.split("|") if p.strip()]
    # Standardowo 4 segmenty - ostatnie 2 to numer NG i nazwa galerii.
    if len(parts) < 2:
        return None, None
    artist = parts[0]
    title = parts[1]
    # Filtr na strony nieobrazowe (np. listing).
    if not artist or not title or "national gallery" in artist.lower():
        return None, None
    return artist, title


def split_artist_attribution(artist_full):
    """Rozdziela 'Follower of Leonardo da Vinci' -> ('Leonardo da Vinci', 'Follower of').

    Dla 'Associate of Leonardo da Vinci, possibly Francesco Napoletano' bierzemy
    primary artist (przed ', possibly') i prefix attribution.
    Zwraca (clean_artist, attribution_or_empty).
    """
    if not artist_full:
        return "", ""
    text = artist_full.strip()
    # Odetnij ", possibly X" / ", probably X" - zostawiamy tylko primary artist.
    text = re.split(r",\s*(possibly|probably|or)\b", text, maxsplit=1, flags=re.I)[0].strip()
    # Wyszukaj prefix atrybucji (case-insensitive, na starcie).
    for prefix in _ATTRIBUTION_PREFIXES:
        if text.lower().startswith(prefix.lower() + " "):
            return text[len(prefix):].strip(), prefix
    return text, ""


def format_artist_for_folder(artist):
    """'Leonardo da Vinci' -> 'da Vinci, Leonardo'. Compound surnames OK."""
    if not artist:
        return ""
    # Tokenizacja - zachowujemy myslniki (Fantin-Latour to JEDNO slowo).
    tokens = artist.split()
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0]  # 'Caravaggio'
    if len(tokens) == 2:
        first, last = tokens
        return f"{last}, {first}"  # 'John Smith' -> 'Smith, John'
    # 3+ slowa - znajdz gdzie zaczyna sie nazwisko (od konca, lapiac particles).
    # Idziemy od ostatniego slowa wstecz dopoki widzimy particle - zalaczamy.
    surname_start = len(tokens) - 1  # zaczynamy od ostatniego
    while surname_start > 1 and tokens[surname_start - 1].lower().rstrip(".") in _SURNAME_PARTICLES:
        surname_start -= 1
    surname = " ".join(tokens[surname_start:])
    given = " ".join(tokens[:surname_start])
    return f"{surname}, {given}"


def derive_names_from_html(page_url, html):
    """Glowna funkcja - z URL+HTML wraca (folder, filename) gotowe do uzycia.

    Strategia:
    1) Sparsuj <title> - to 100% wiarygodne dla National Gallery.
    2) Rozdziel atrybucje (Follower of / Attributed to / ...).
    3) Folder = 'Nazwisko, Imie' (czysty artysta, BEZ atrybucji - zeby
       wszystkie prace tego samego artysty trafialy do tego samego folderu).
    4) Plik = '<Folder> - <Tytul>.png' z opcjonalnym ' (Follower of)' na koncu.
    5) Fallback do starej heurystyki ze sluga gdy <title> nie ma sensu.
    """
    artist_full, title = parse_ng_page_meta(html)
    if artist_full and title:
        artist_clean, attribution = split_artist_attribution(artist_full)
        folder = sanitize_for_filename(format_artist_for_folder(artist_clean))
        title_clean = sanitize_for_filename(title)
        suffix = f" ({attribution})" if attribution else ""
        filename = sanitize_for_filename(f"{folder} - {title_clean}{suffix}") + ".png"
        return folder or None, filename
    # ---- Fallback: heurystyka ze sluga, ale lepsza niz 'words[0]+words[1]' ----
    return _fallback_names_from_slug(page_url)


def _fallback_names_from_slug(page_url):
    """Awaryjny parser - gdy nie mamy HTML albo title nie ma typowej struktury."""
    slug = page_url.rstrip("/").split("/")[-1]
    words = [w for w in slug.split("-") if w]
    if not words:
        return None, "obraz full.png"
    # Heurystyka: pierwsze 2-3 slowa to autor (jesli nie ma stop-wordow), reszta tytul.
    # To i tak slabe - stad preferujemy parse <title>.
    if len(words) >= 2:
        author = f"{words[1].title()}, {words[0].title()}"
        rest = " ".join(w.title() for w in words[2:])
        title = sanitize_for_filename(f"{author} - {rest}".strip(" -"))
        return sanitize_for_filename(author), title + ".png"
    return None, sanitize_for_filename(words[0].title()) + ".png"


# ---- Backward-compat aliasy (zachowane dla zewn. importerow, ale zalecamy derive_names_from_html) ----

def suggest_out_filename(page_url, html):
    _, filename = derive_names_from_html(page_url, html)
    return filename


def suggest_author_folder(page_url):
    folder, _ = _fallback_names_from_slug(page_url)
    return folder


def default_checkpoint_paths(out_file, temp_file, state_file):
    out_path = Path(out_file)
    if temp_file == DEFAULT_TEMP_FILE:
        temp_file = str(out_path.with_name(f"{out_path.stem}.partial.png"))
    if state_file == DEFAULT_STATE_FILE:
        state_file = str(out_path.with_name(f"{out_path.stem}.state.json"))
    return temp_file, state_file


def normalize_service_id(candidate_url):
    # Gdy strona zwraca URL obrazka IIIF (z /full/.../default.jpg),
    # przycinamy go do bazowego service-id.
    marker = ".tif"
    pos = candidate_url.find(marker)
    if pos != -1:
        return candidate_url[: pos + len(marker)]
    return candidate_url


def resolve_from_page_url(page_url, timeout):
    resp = create_session(4).get(page_url, timeout=timeout)
    resp.raise_for_status()
    html = resp.text.replace("\\/", "/")
    # Z HTML wyciagamy 'czysty' folder autora i nazwe pliku - parsujac <title>
    # strony NG (zamiast slepo guess'owac z URL'a, co dawalo rzeczy typu
    # "Of, Follower" albo "Da, Leonardo").
    author_folder, suggested_out = derive_names_from_html(page_url, html)

    patterns = [
        r"/server\.iip\?IIIF=[^\"' <]+",
        r"https://www\.nationalgallery\.org\.uk/server\.iip\?IIIF=[^\"' <]+",
        r"https?://[^\"' <]+\?IIIF=[^\"' <]+",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        if matches:
            service_id = normalize_service_id(urljoin(page_url, matches[0]))
            info_url = f"{service_id}/info.json"
            service_id, width, height, auto_chunk, qualities, formats = fetch_info_json(info_url, timeout)
            if author_folder:
                suggested_out = str(Path(author_folder) / suggested_out)
            return service_id, width, height, suggested_out, auto_chunk, qualities, formats

    raise RuntimeError("Nie znaleziono adresu IIIF na podanej stronie.")


def resolve_source(args):
    # Priorytet:
    # 1) --info-url
    # 2) --page-url (auto wykrywanie IIIF)
    # 3) --service-id + --width + --height (lub fallback domyslny)
    qualities: list[str] = []
    formats: list[str] = []
    if args.info_url:
        service_id, width, height, auto_chunk, qualities, formats = fetch_info_json(args.info_url, args.timeout)
        suggested_out = None
    elif args.page_url:
        service_id, width, height, suggested_out, auto_chunk, qualities, formats = resolve_from_page_url(
            args.page_url, args.timeout,
        )
    else:
        service_id = args.service_id or DEFAULT_SERVICE_ID
        width = args.width or DEFAULT_FULL_W
        height = args.height or DEFAULT_FULL_H
        suggested_out = None
        auto_chunk = DEFAULT_TILE or 256

    # Jawnie podane argumenty zawsze nadpisuja auto.
    if args.service_id:
        service_id = args.service_id
    if args.width:
        width = args.width
    if args.height:
        height = args.height

    if not service_id or not width or not height:
        raise RuntimeError("Brak danych zrodla. Podaj --page-url, --info-url lub komplet --service-id --width --height.")

    out_file = args.out or suggested_out or DEFAULT_OUT_FILE
    chunk_size = args.tile or auto_chunk or 256
    return service_id, int(width), int(height), out_file, int(chunk_size), qualities, formats


def negotiate_quality_and_format(args, qualities, formats):
    """Dostosowuje args.quality / args.format do tego, co serwer faktycznie wspiera.

    Wywolywane PO pobraniu info.json (mamy juz wspierane qualities/formats).
    Dla National Gallery serwer zwraca tylko {default,color,gray,bitonal} + {jpg};
    bez tej negocjacji 'native.tif' kazdorazowo daje 400 Bad Request.
    """
    # ---- Quality ----
    if qualities and args.quality not in qualities:
        # 'native' (IIIF v2) lub 'oryginalna' user-intent: chcemy najlepszej
        # dostepnej jakosci. 'default' jest gwarantowane przez spec i typowo
        # zwraca obraz "as-is".
        preferred = "default" if "default" in qualities else qualities[0]
        print(
            f"[info] Serwer nie wspiera quality='{args.quality}'. "
            f"Uzywam '{preferred}' (wspierane: {qualities})"
        )
        args.quality = preferred
    # ---- Format ----
    if formats and args.format not in formats:
        # 'tif' nie zawsze jest wspierany (np. National Gallery oferuje tylko jpg).
        # Fallback: jpg jesli dostepny, w przeciwnym razie pierwszy z listy.
        preferred = "jpg" if "jpg" in formats else formats[0]
        print(
            f"[info] Serwer nie wspiera format='{args.format}'. "
            f"Uzywam '{preferred}' (wspierane: {formats})"
        )
        args.format = preferred


def build_jobs(width, height, tile):
    cols = math.ceil(width / tile)
    rows = math.ceil(height / tile)
    for r in range(rows):
        for c in range(cols):
            x = c * tile
            y = r * tile
            w = min(tile, width - x)
            h = min(tile, height - y)
            yield r, c, x, y, w, h


def fetch_tile(job, args):
    r, c, x, y, w, h = job
    key = tile_key(r, c)
    last_error = None
    session = get_thread_session(max(args.workers * 2, 8))

    # Lokalna kopia quality/format - jesli dostaniemy 400 i jeszcze nie
    # probowalismy fallbacka, przelaczamy GLOBALNIE na default/jpg dla calego
    # batcha (atomowo, raz, zeby kolejne kafelki juz uzywaly poprawnych).
    quality = args.quality
    fmt = args.format

    for attempt in range(1, args.retries + 1):
        url = f"{args.service_id}/{x},{y},{w},{h}/{w},{h}/0/{quality}.{fmt}"
        try:
            resp = session.get(url, timeout=args.timeout)
            resp.raise_for_status()
            tile_img = Image.open(BytesIO(resp.content)).convert("RGB")
            if tile_img.size != (w, h):
                raise RuntimeError(f"Niepoprawny rozmiar kafla {key}: {tile_img.size}, oczekiwano {(w, h)}")
            return key, x, y, w, h, np.array(tile_img)
        except requests.HTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response is not None else 0
            # 400/404 = niewspierana kombinacja quality.format. Sprobuj z
            # default.jpg jednorazowo zanim zmarnujemy retries.
            if status in (400, 404) and (quality, fmt) != ("default", "jpg"):
                print(
                    f"[fallback] kafel {key}: HTTP {status} dla "
                    f"{quality}.{fmt} - przelaczam globalnie na default.jpg"
                )
                quality, fmt = "default", "jpg"
                args.quality, args.format = "default", "jpg"
                continue  # natychmiastowy retry, bez sleep
            if attempt < args.retries:
                sleep_s = args.backoff_base * (2 ** (attempt - 1))
                print(f"Retry {attempt}/{args.retries - 1} dla tile {key} za {sleep_s:.1f}s...")
                time.sleep(sleep_s)
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if attempt < args.retries:
                sleep_s = args.backoff_base * (2 ** (attempt - 1))
                print(f"Retry {attempt}/{args.retries - 1} dla tile {key} za {sleep_s:.1f}s...")
                time.sleep(sleep_s)

    raise RuntimeError(f"Nie udalo sie pobrac kafla {key}: {last_error}") from last_error


def save_checkpoint(canvas, temp_file, state_file, done_tiles, chunk_size, width, height):
    Path(temp_file).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(temp_file, format="PNG")
    save_state(state_file, done_tiles, chunk_size, width, height)
    print("Checkpoint zapisany.")


def main():
    args = parse_args()
    (
        args.service_id, args.width, args.height, args.out, args.tile,
        qualities, formats,
    ) = resolve_source(args)
    negotiate_quality_and_format(args, qualities, formats)
    args.temp, args.state = default_checkpoint_paths(args.out, args.temp, args.state)
    print(f"Uzywam IIIF: {args.service_id}")
    print(f"Wymiary obrazu: {args.width}x{args.height}")
    print(f"Rozmiar fragmentu: {args.tile}x{args.tile}")
    print(f"Quality/Format: {args.quality}.{args.format}")
    print(f"Plik wynikowy: {args.out}")

    cols = math.ceil(args.width / args.tile)
    rows = math.ceil(args.height / args.tile)
    total_tiles = rows * cols

    done_tiles = load_state(args.state, total_tiles, args.tile, args.width, args.height)
    canvas = get_canvas(args.temp, args.width, args.height, force_new=not bool(done_tiles) and Path(args.state).exists())
    print_progress(len(done_tiles), total_tiles)

    jobs = [job for job in build_jobs(args.width, args.height, args.tile) if tile_key(job[0], job[1]) not in done_tiles]
    if not jobs:
        print("Wszystkie kafelki sa juz pobrane. Finalizuje plik wynikowy...")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.out, format="PNG")
        return

    new_done_since_checkpoint = 0
    futures = []

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for job in jobs:
                futures.append(executor.submit(fetch_tile, job, args))

            for future in as_completed(futures):
                key, x, y, w, h, tile_arr = future.result()
                canvas[y:y + h, x:x + w] = tile_arr
                done_tiles.add(key)
                new_done_since_checkpoint += 1
                if should_print_progress(len(done_tiles), total_tiles, args.progress_every):
                    print_progress(len(done_tiles), total_tiles)

                if args.checkpoint_every > 0 and new_done_since_checkpoint >= args.checkpoint_every:
                    save_checkpoint(canvas, args.temp, args.state, done_tiles, args.tile, args.width, args.height)
                    new_done_since_checkpoint = 0
    except KeyboardInterrupt:
        print("\nPrzerwano przez uzytkownika. Anuluje zadania i zapisuje stan...")
        for future in futures:
            future.cancel()
        save_checkpoint(canvas, args.temp, args.state, done_tiles, args.tile, args.width, args.height)
        print("Stan zapisany. Uruchom ponownie skrypt, aby wznowic.")
        return

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(args.out, format="PNG")
    print(f"Gotowe: {args.out}")
    Path(args.temp).unlink(missing_ok=True)
    Path(args.state).unlink(missing_ok=True)
    print("Usunieto pliki tymczasowe.")


if __name__ == "__main__":
    main()