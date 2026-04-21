"""Budowa kolejki cyklu z kolekcji artystow w Shopify + delta detection.

Kolekcje artystow: custom collections o tytule 'Nazwisko, Imie' (patrz
SHOP_KNOWLEDGE sekcja 4-5). Sort alfabetyczny po nazwisku (przed przecinkiem).

Dla kazdego artysty zbieramy produkty z jego kolekcji (kolejnosc wg Shopify
sort_order kolekcji - jesli custom to user-defined; jesli smart to best-selling).

Dla kazdego produktu pobieramy:
- body_html (PL) - z REST /products/{id}.json
- body_html (EN) - z GraphQL translatableResource(resourceId, locale: "en")
- pierwsze 3 akapity (< sekcja SZCZEGOLY) z kazdej wersji
- glowne zdjecie (product.image.src) - CDN URL do uzytku przez IG

Flagi kontekstu:
- is_first_of_artist / is_last_of_artist (intro/outro).
- next_artist (do outro).

Delta detection: porownanie hashow zestawu kolekcji/produktow z generation_state.
Gdy pojawi sie nowy artysta lub nowy obraz - dodajemy je z flagami
is_new_artist / is_new_painting, ktore prompt wyczyta i wygeneruje intro
'na stronie pojawil sie nowy artysta X'.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

# Reuse klienta Shopify z komponentu dodajobraz
from Komponenty.dodajobraz import shopify_client as sc  # type: ignore

from . import images, storage


# Wzorzec tytulu kolekcji artysty: "Nazwisko, Imie"
# (zgodnie z sekcja 5 SHOP_KNOWLEDGE)
_ARTIST_COLL_RE = re.compile(r"^[^,]+,\s+[^,]+$")


# ---------------------------------------------------------------------------
# Helpers: body_html -> 3 akapity
# ---------------------------------------------------------------------------

_SZCZEGOLY_RE = re.compile(r"szczegó?ł?y|details|detaljer|detaglios|dettagli",
                           re.IGNORECASE)


class _ParagraphExtractor(HTMLParser):
    """Ekstrahuje tekst z pierwszych 3 tagow <p> PRZED sekcja SZCZEGOLY.

    Zakladamy ze body_html zbudowane przez Komponenty/dodajobraz ma na poczatku
    3 akapity opisu, potem tabele 'SZCZEGOLY'. Szczegoly pomijamy - chcemy
    zmiescic sie w caption social media.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._current: list[str] = []
        self._in_p = False
        self._stop = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._stop:
            return
        if tag.lower() == "p":
            self._in_p = True
            self._current = []

    def handle_endtag(self, tag: str) -> None:
        if self._stop:
            return
        if tag.lower() == "p" and self._in_p:
            text = " ".join("".join(self._current).split())
            if text:
                if _SZCZEGOLY_RE.search(text):
                    self._stop = True
                else:
                    self.paragraphs.append(text)
            self._in_p = False
            self._current = []
            if len(self.paragraphs) >= 3:
                self._stop = True

    def handle_data(self, data: str) -> None:
        if self._stop or not self._in_p:
            return
        self._current.append(data)


def extract_3_paragraphs(body_html: str) -> list[str]:
    if not body_html:
        return []
    p = _ParagraphExtractor()
    try:
        p.feed(body_html)
    except Exception:  # noqa: BLE001
        return []
    return p.paragraphs[:3]


# ---------------------------------------------------------------------------
# Fetch z Shopify
# ---------------------------------------------------------------------------

@dataclass
class ArtistCollection:
    id: int
    title: str            # "Dahl, Hans"
    surname: str          # "Dahl"
    given_name: str       # "Hans"
    display_name: str     # "Hans Dahl" (kolejnosc ludzka)
    handle: str           # dla folderu Obrazy/


def _parse_artist_title(title: str) -> tuple[str, str]:
    """Z 'Dahl, Hans' -> ('Dahl', 'Hans'). Gdy brak przecinka -> (title, '')."""
    parts = [p.strip() for p in title.split(",", 1)]
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0], parts[1]
    return title.strip(), ""


def fetch_artist_collections(shop: str, token: str) -> list[ArtistCollection]:
    """Zwraca posortowana alfabetycznie po nazwisku liste kolekcji artystow."""
    result: list[ArtistCollection] = []
    page_info: str | None = None
    url = f"https://{shop}/admin/api/{sc.API_VERSION}/custom_collections.json?limit=250"
    raw_all: list[dict] = []

    # Pobieramy WSZYSTKIE custom_collections (paginacja przez Link header)
    import json as _json
    import ssl as _ssl
    import urllib.error
    import urllib.request

    while url:
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Shopify-Access-Token": token,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl.create_default_context()) as resp:
                body = resp.read().decode("utf-8")
                link_header = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise sc.ShopifyError(f"HTTP {e.code} GET custom_collections\n{detail}") from e
        data = _json.loads(body) if body else {}
        raw_all.extend((data or {}).get("custom_collections") or [])

        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if part.endswith('rel="next"'):
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                    break
        url = next_url

    for c in raw_all:
        title = (c.get("title") or "").strip()
        if not _ARTIST_COLL_RE.match(title):
            continue
        surname, given = _parse_artist_title(title)
        display = f"{given} {surname}".strip() if given else surname
        result.append(
            ArtistCollection(
                id=int(c.get("id")),
                title=title,
                surname=surname,
                given_name=given,
                display_name=display,
                handle=images.slugify(display),
            )
        )

    # Sort alfabetyczny po nazwisku (lowercase), secondary po imieniu
    result.sort(key=lambda a: (a.surname.lower(), a.given_name.lower()))
    _ = page_info  # unused
    return result


def _parse_product_title(title: str) -> tuple[str, str]:
    """Z 'Hans Dahl - Babie lato' -> ('Hans Dahl', 'Babie lato'). Fallback do ('', title)."""
    # Obslugujemy rozne separatory: ' - ', ' – ', ' — '
    for sep in (" - ", " – ", " — "):
        if sep in title:
            a, t = title.split(sep, 1)
            return a.strip(), t.strip()
    return "", title.strip()


@dataclass
class PaintingData:
    product_id: int
    product_gid: str
    title_full: str            # "Hans Dahl - Babie lato"
    title_painting_pl: str     # "Babie lato"
    title_painting_en: str     # "Indian Summer" (z translations, fallback=PL)
    handle: str                # slug
    image_url: str
    image_alt: str
    description_pl: str        # 3 akapity sklejone "\n\n"
    description_en: str


def _get_translated_fields(shop: str, token: str, product_gid: str) -> dict[str, str]:
    """GraphQL: translatableResource(resourceId: $id).translations(locale: "en").

    Zwraca dict {key: value} (np. 'title', 'body_html').
    """
    query = """
    query($id: ID!, $locale: String!) {
      translatableResource(resourceId: $id) {
        translations(locale: $locale) { key value }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"id": product_gid, "locale": "en"})
    except sc.ShopifyError:
        return {}
    res = (data or {}).get("translatableResource") or {}
    out: dict[str, str] = {}
    for t in (res.get("translations") or []):
        k = (t or {}).get("key")
        v = (t or {}).get("value")
        if k and v is not None:
            out[str(k)] = str(v)
    return out


def fetch_paintings_for_artist(
    shop: str,
    token: str,
    collection_id: int,
) -> list[PaintingData]:
    """Pobiera produkty z kolekcji + pelny body_html + translations EN."""
    # Lekkie pobranie listy (id, title, handle, image) - shortcut
    light = sc.iter_collection_products(
        shop, token, collection_id,
        fields="id,title,handle,image",
    )
    out: list[PaintingData] = []
    for lp in light:
        pid = int(lp.get("id") or 0)
        if pid <= 0:
            continue
        full = sc.get_product(shop, token, pid)
        title_full = (full.get("title") or "").strip()
        _, title_pl = _parse_product_title(title_full)
        handle = (full.get("handle") or "").strip()
        img = (full.get("image") or {}) if isinstance(full.get("image"), dict) else {}
        image_url = str(img.get("src") or "")
        image_alt = str(img.get("alt") or "") or title_full
        body_pl = str(full.get("body_html") or "")
        paragraphs_pl = extract_3_paragraphs(body_pl)
        desc_pl = "\n\n".join(paragraphs_pl)

        gid = f"gid://shopify/Product/{pid}"
        tr_en = _get_translated_fields(shop, token, gid)
        body_en = tr_en.get("body_html") or ""
        paragraphs_en = extract_3_paragraphs(body_en) if body_en else []
        desc_en = "\n\n".join(paragraphs_en)

        title_en = tr_en.get("title") or ""
        # Translations.title trzyma caly "Artist - English title", wyciagamy tytul
        _, title_painting_en = _parse_product_title(title_en) if title_en else ("", "")
        if not title_painting_en:
            title_painting_en = title_pl  # fallback

        out.append(
            PaintingData(
                product_id=pid,
                product_gid=gid,
                title_full=title_full,
                title_painting_pl=title_pl,
                title_painting_en=title_painting_en,
                handle=handle or images.slugify(title_pl),
                image_url=image_url,
                image_alt=image_alt,
                description_pl=desc_pl,
                description_en=desc_en,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Hashe do delta detection
# ---------------------------------------------------------------------------

def _hash_artists(artists: list[ArtistCollection]) -> str:
    joined = "|".join(f"{a.id}:{a.title}" for a in artists)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _hash_paintings(artist_to_products: dict[int, list[int]]) -> str:
    parts = []
    for aid in sorted(artist_to_products.keys()):
        pids = ",".join(str(p) for p in artist_to_products[aid])
        parts.append(f"{aid}={pids}")
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Budowa kolejki
# ---------------------------------------------------------------------------

def build_queue_from_shopify(
    *,
    logger: callable = None,  # type: ignore[type-arg]
) -> list[storage.CykleItem]:
    """Pelny rebuild kolejki ze stanu Shopify. Nie zapisuje - zwraca liste."""
    shop, token = sc.load_session()
    if logger:
        logger("Pobieranie listy artystow...")
    artists = fetch_artist_collections(shop, token)
    if logger:
        logger(f"Znaleziono {len(artists)} artystow. Pobieranie obrazow...")

    items: list[storage.CykleItem] = []
    artist_to_products: dict[int, list[int]] = {}

    for ai, artist in enumerate(artists):
        if logger:
            logger(f"  [{ai + 1}/{len(artists)}] {artist.display_name}")
        paintings = fetch_paintings_for_artist(shop, token, artist.id)
        artist_to_products[artist.id] = [p.product_id for p in paintings]
        total = len(paintings)
        next_artist = artists[ai + 1].display_name if ai + 1 < len(artists) else ""
        for pi, painting in enumerate(paintings):
            is_first = (pi == 0)
            is_last = (pi == total - 1)
            it = storage.CykleItem.new(
                artist=artist.display_name,
                artist_handle=artist.handle,
                painting_title_pl=painting.title_painting_pl,
                painting_title_en=painting.title_painting_en,
                painting_handle=images.slugify(painting.title_painting_pl),
                product_id=painting.product_id,
                product_gid=painting.product_gid,
                product_image_url=painting.image_url,
                product_image_alt=painting.image_alt,
                description_pl=painting.description_pl,
                description_en=painting.description_en,
                artist_position=pi + 1,
                artist_total=total,
                is_first_of_artist=is_first,
                is_last_of_artist=is_last,
                next_artist=next_artist if is_last else "",
            )
            items.append(it)

    # Zapisz hashe w generation_state, zeby delta-detection znal "co bylo"
    state = storage.load_generation_state()
    state["artists_hash"] = _hash_artists(artists)
    state["paintings_hash"] = _hash_paintings(artist_to_products)
    state["artists_snapshot"] = [
        {"id": a.id, "title": a.title, "display_name": a.display_name,
         "handle": a.handle, "product_ids": artist_to_products.get(a.id, [])}
        for a in artists
    ]
    storage.save_generation_state(state)

    return items


# ---------------------------------------------------------------------------
# Delta detection
# ---------------------------------------------------------------------------

@dataclass
class DeltaReport:
    new_artists: list[ArtistCollection]                # artysci ktorzy NIE byli w snapshocie
    new_paintings: dict[int, list[PaintingData]]       # collection_id -> lista nowych obrazow
    summary_text: str


def detect_deltas(
    *,
    logger: callable = None,  # type: ignore[type-arg]
) -> DeltaReport:
    shop, token = sc.load_session()
    if logger:
        logger("Pobieranie listy artystow (delta)...")
    artists_now = fetch_artist_collections(shop, token)

    state = storage.load_generation_state()
    snapshot = state.get("artists_snapshot") or []
    snap_by_id: dict[int, dict] = {
        int(s.get("id") or 0): s for s in snapshot if s.get("id")
    }

    new_artists: list[ArtistCollection] = []
    new_paintings: dict[int, list[PaintingData]] = {}

    for artist in artists_now:
        if artist.id not in snap_by_id:
            new_artists.append(artist)
            if logger:
                logger(f"  NOWY ARTYSTA: {artist.display_name}")
            # Nie fetchujemy od razu jego produktow - zrobi to apply_deltas
            continue

        prev_pids = set(int(x) for x in (snap_by_id[artist.id].get("product_ids") or []))
        if logger:
            logger(f"  Sprawdzam {artist.display_name} ({len(prev_pids)} obrazow w snapshot)...")
        current_paintings = fetch_paintings_for_artist(shop, token, artist.id)
        new_for_artist = [p for p in current_paintings if p.product_id not in prev_pids]
        if new_for_artist:
            new_paintings[artist.id] = new_for_artist
            if logger:
                logger(f"    +{len(new_for_artist)} nowych obrazow")

    summary_parts = []
    if new_artists:
        summary_parts.append(
            f"Nowi artysci: {', '.join(a.display_name for a in new_artists)}"
        )
    if new_paintings:
        total = sum(len(v) for v in new_paintings.values())
        summary_parts.append(f"Nowe obrazy: {total} (u {len(new_paintings)} artystow)")
    if not summary_parts:
        summary_parts.append("Brak zmian od ostatniego odswiezenia.")

    return DeltaReport(
        new_artists=new_artists,
        new_paintings=new_paintings,
        summary_text=" | ".join(summary_parts),
    )


def apply_deltas(
    queue: list[storage.CykleItem],
    deltas: DeltaReport,
) -> int:
    """Wciska nowych artystow i nowe obrazy w kolejke wg reguly:

    - Nowy artysta: po ostatnim pending obrazie aktualnego artysty (tego
      ktory ma pending pozycje najbardziej 'z przodu' w kolejce). Pierwsza
      pozycja nowego artysty ma is_new_artist=True.
    - Nowy obraz istniejacego artysty: po jego ostatnim pending obrazie
      z flaga is_new_painting=True.

    Zwraca liczbe dodanych pozycji. UWAGA: po applyu nalezy wywolac
    scheduler.reassign_from_now(queue) aby przeliczyc sloty.
    """
    if not deltas.new_artists and not deltas.new_paintings:
        return 0

    shop, token = sc.load_session()
    added = 0

    # --- 1) Nowe obrazy u istniejacych artystow ---
    for coll_id, new_ps in deltas.new_paintings.items():
        # Znajdz ostatni index pending dla tego artysty
        artist_display = ""
        artist_handle = ""
        # Bierzemy ArtistCollection z snapshot / z aktualnego fetcha
        # (artysci w queue maja artist+artist_handle rowny nazwie w kolekcji)
        # Wyszukujemy po product_id - jesli juz sa obrazy tego artysty w queue.
        existing_artist_items = [
            (idx, it) for idx, it in enumerate(queue)
            if any(p.product_id != it.product_id for p in new_ps) is False or True
            # (kazda nowa pozycja -> znajdz wyglad artysty po dowolnym istniejacym itemie)
        ]
        # Prosciej: sprobujmy zidentyfikowac artyste po sasiedztwie - porownaj
        # artist_display_name ktorego wiemy z fetchu ArtistCollection.
        # Przeiterujmy snapshot z generation_state, zeby dostac display_name.
        state = storage.load_generation_state()
        snapshot = state.get("artists_snapshot") or []
        snap = next((s for s in snapshot if int(s.get("id") or 0) == coll_id), None)
        if snap:
            artist_display = str(snap.get("display_name") or "")
            artist_handle = str(snap.get("handle") or "")

        # Index ostatniego pending obrazu tego artysty
        last_idx = -1
        artist_total_pending = 0
        for i, it in enumerate(queue):
            if it.artist == artist_display and it.status in ("pending", "ready"):
                artist_total_pending += 1
                last_idx = i
        if last_idx < 0:
            # Artysta juz sie skonczyl - wrzucamy na koniec kolejki z flaga
            last_idx = len(queue) - 1

        # Dodaj nowe obrazy po last_idx
        for offset, painting in enumerate(new_ps, start=1):
            it = storage.CykleItem.new(
                artist=artist_display,
                artist_handle=artist_handle,
                painting_title_pl=painting.title_painting_pl,
                painting_title_en=painting.title_painting_en,
                painting_handle=images.slugify(painting.title_painting_pl),
                product_id=painting.product_id,
                product_gid=painting.product_gid,
                product_image_url=painting.image_url,
                product_image_alt=painting.image_alt,
                description_pl=painting.description_pl,
                description_en=painting.description_en,
                artist_position=0,  # zaktualizujemy po finalnym sortowaniu
                artist_total=0,
                is_new_painting=True,
            )
            queue.insert(last_idx + offset, it)
            added += 1

    # --- 2) Nowi artysci ---
    # Nowego artyste wciskamy po ostatnim pending obrazie AKTUALNEGO artysty
    # (czyli tego, ktory jest teraz "na topie" kolejki - pierwszy pending).
    for new_art in deltas.new_artists:
        # Pobierz jego obrazy
        paintings = fetch_paintings_for_artist(shop, token, new_art.id)
        if not paintings:
            continue

        # Znajdz indeks konca "aktualnego artysty" (pierwszego z pending w queue)
        insert_at = _end_of_current_artist_index(queue)
        total = len(paintings)
        for pi, painting in enumerate(paintings):
            is_first = (pi == 0)
            is_last = (pi == total - 1)
            it = storage.CykleItem.new(
                artist=new_art.display_name,
                artist_handle=new_art.handle,
                painting_title_pl=painting.title_painting_pl,
                painting_title_en=painting.title_painting_en,
                painting_handle=images.slugify(painting.title_painting_pl),
                product_id=painting.product_id,
                product_gid=painting.product_gid,
                product_image_url=painting.image_url,
                product_image_alt=painting.image_alt,
                description_pl=painting.description_pl,
                description_en=painting.description_en,
                artist_position=pi + 1,
                artist_total=total,
                is_first_of_artist=is_first,
                is_last_of_artist=is_last,
                is_new_artist=(pi == 0),  # info 'na stronie pojawil sie nowy artysta'
            )
            queue.insert(insert_at + pi, it)
            added += 1

    # Odswiez artist_position/total + is_first/is_last dla wszystkich pending
    _recompute_artist_positions(queue)
    return added


def _end_of_current_artist_index(queue: list[storage.CykleItem]) -> int:
    """Zwraca index ZA ostatnim pending obrazem aktualnego artysty.

    Aktualny artysta = ten, ktory ma pierwszy pending w queue. Gdy kolejka
    nie ma pending - zwraca len(queue) (czyli koniec).
    """
    first_pending_idx = next(
        (i for i, it in enumerate(queue) if it.status in ("pending", "ready")),
        -1,
    )
    if first_pending_idx < 0:
        return len(queue)
    current_artist = queue[first_pending_idx].artist
    last_for_artist = first_pending_idx
    for i in range(first_pending_idx, len(queue)):
        if queue[i].artist == current_artist and queue[i].status in ("pending", "ready"):
            last_for_artist = i
    return last_for_artist + 1


def _recompute_artist_positions(queue: list[storage.CykleItem]) -> None:
    """Przelicza artist_position/total i flagi is_first/is_last po modyfikacjach."""
    # Zgrupuj INDEXY pozycji per artysta wg kolejnosci pojawienia
    groups: dict[str, list[int]] = {}
    order_artists: list[str] = []
    for i, it in enumerate(queue):
        if it.artist not in groups:
            groups[it.artist] = []
            order_artists.append(it.artist)
        groups[it.artist].append(i)

    for ai, artist in enumerate(order_artists):
        idxs = groups[artist]
        total = len(idxs)
        next_artist = order_artists[ai + 1] if ai + 1 < len(order_artists) else ""
        for pos, qi in enumerate(idxs):
            it = queue[qi]
            it.artist_position = pos + 1
            it.artist_total = total
            it.is_first_of_artist = (pos == 0)
            it.is_last_of_artist = (pos == total - 1)
            it.next_artist = next_artist if (pos == total - 1) else ""
