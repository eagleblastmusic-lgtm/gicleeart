"""Buduje prompt do LLM (w Cursor/chat) i waliduje zwrocony JSON."""
from __future__ import annotations

import json
import re
from typing import Any

from .parser import IMAGE_ROLE_FULL, IMAGE_ROLE_MOCKUP, IMAGE_ROLE_PREVIEW
from .tags_taxonomy import (
    ALWAYS_TAGS,
    GIFT_WHITELIST,
    ROOM_WHITELIST,
    STYLE_WHITELIST,
    expand_with_synonyms,
)
from .tags_taxonomy_i18n import all_foreign_tags

REQUIRED_KEYS = (
    "tytul_polski",
    "tytul_orginalny",
    "akapity",
    "data_powstania",
    "miejsce_powstania",
    "technika",
    "gatunek",
    "nurt",
    "forma",
    "tagi",
    "kategoria",
)

# Klucze tlumaczen jezykowych (musza pokrywac sie z .markets locales).
TRANSLATION_LANGS: tuple[str, ...] = ("en", "de", "fr", "es", "nl", "it")

# Wymagane pola w kazdym bloku 'tlumaczenia.<lang>'.
TRANSLATION_KEYS: tuple[str, ...] = (
    "tytul_polski",        # tytul produktu w jezyku docelowym (mimo nazwy klucza - to przetlumaczony tytul)
    "akapity",             # 3-4 akapity opisu w jezyku docelowym (4. opcjonalny)
    "seo_title",           # title_tag w jezyku docelowym
    "seo_description",     # description_tag w jezyku docelowym
    "alt_text",            # alt zdjecia w jezyku docelowym (max 125 znakow)
)

# Tagi obowiazkowe + kategoria sa centralnie zdefiniowane w tags_taxonomy.py.
# Tutaj reeksportujemy je pod alias 'REQUIRED_TAGS' (kompatybilnosc wsteczna) i opakowujemy
# w funkcje ensure_required_tags() / force_fixed_kategoria().
REQUIRED_TAGS: tuple[str, ...] = ALWAYS_TAGS

FIXED_KATEGORIA = "Obrazy"


def ensure_required_tags(tags: list[str]) -> list[str]:
    """Gwarantuje obecnosc ALWAYS_TAGS PL + ALWAYS_TAGS EN/DE/FR/ES/NL/IT na liscie tagow
    oraz dorzuca polskie synonimy SEO long-tail dla rozpoznawalnych gatunkow
    (np. 'krajobraz' -> dolaczy tez 'pejzaz', 'obraz krajobrazowy').

    Tagi sa dodawane w kolejnosci:
      1) ALWAYS_TAGS PL                                  (~17 tagow)
      2) ALWAYS_TAGS dla wszystkich jezykow obcych       (~120 tagow PL+EN+DE+FR+ES+NL+IT)
      3) tagi z LLM-a + synonimy gatunkow PL              (case-insensitive deduplikacja)

    Dzieki temu kazdy produkt jest znajdowany w wyszukiwarce kazdego rynku po lokalnych
    slowach kluczowych (wall art, Wandbild, tableau mural, cuadros decorativos, ...).
    """
    seen: set[str] = set()
    out: list[str] = []

    def _push(tag: str) -> None:
        s = (tag or "").strip()
        if not s:
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(s)

    for t in ALWAYS_TAGS:
        _push(t)
    for t in all_foreign_tags():
        _push(t)
    for t in expand_with_synonyms(tags or []):
        if isinstance(t, str):
            _push(t)
    return out


def force_fixed_kategoria(data: dict[str, Any]) -> None:
    """Nadpisuje pole 'kategoria' wartoscia FIXED_KATEGORIA - sklep sprzedaje tylko obrazy."""
    data["kategoria"] = FIXED_KATEGORIA


def _bullet_list(items: tuple[str, ...] | list[str]) -> str:
    return ", ".join(f"'{t}'" for t in items)


_REQUIRED_TAGS_HUMAN = _bullet_list(ALWAYS_TAGS)
_STYLE_HUMAN = _bullet_list(STYLE_WHITELIST)
_ROOM_HUMAN = _bullet_list(ROOM_WHITELIST)
_GIFT_HUMAN = _bullet_list(GIFT_WHITELIST)

_TAGS_GUIDELINES = (
    "Wymagania dla pola \"tagi\" (KRYTYCZNE - SEO sklepu PL):\n"
    "- 25-35 pozycji.\n"
    "- po polsku, male litery, bez hashy, bez srednikow, bez duplikatow.\n"
    "- celuj w MAKSYMALNY potencjal SEO PL: tagi maja sciagac polskich klientow, ktorzy chca\n"
    "  KUPIC reprodukcje obrazu na sciane (frazy zakupowe i dekoratorskie, nie tylko nazwy historyczne).\n"
    "\n"
    "Kazdy obraz MUSI miec tagi z kazdej z tych grup (gdy maja sens dla obrazu):\n"
    "  A) ARTYSTA: pelne imie i nazwisko + samo nazwisko (np. 'hans dahl', 'dahl').\n"
    "  B) GATUNEK i NURT: po polsku (np. 'pejzaz', 'marynistyka', 'romantyzm', 'realizm').\n"
    "  C) TECHNIKA i MEDIUM: np. 'olej na plotnie', 'akwarela'.\n"
    "  D) MOTYWY: konkretne elementy obrazu (np. 'morze', 'gory', 'kobieta', 'kwiaty', 'noc').\n"
    "  E) KOLORY DOMINUJACE: 1-3 kolory PL (np. 'niebieski', 'beżowy', 'szary', 'zlocisty').\n"
    "  F) STYL WNETRZA - 1-3 z nastepujacej WHITELISTY (TYLKO stad, nie wymyslaj):\n"
    f"     {_STYLE_HUMAN}.\n"
    "  G) POMIESZCZENIE - 1-3 z nastepujacej WHITELISTY (TYLKO stad):\n"
    f"     {_ROOM_HUMAN}.\n"
    "  H) OKAZJA / PREZENT - 1-3 z nastepujacej WHITELISTY (TYLKO stad, jesli pasuja):\n"
    f"     {_GIFT_HUMAN}.\n"
    "\n"
    "OBOWIAZKOWO dolacz wszystkie nastepujace stale tagi (dokladnie w tym brzmieniu, male litery)\n"
    "- one wystepuja na KAZDYM produkcie sklepu:\n"
    f"  {_REQUIRED_TAGS_HUMAN}."
)

_KATEGORIA_GUIDELINES = (
    "Pole \"kategoria\":\n"
    f"- ZAWSZE wpisz dokladnie: \"{FIXED_KATEGORIA}\". Nic innego. Bez sciezki Shopify, bez podkategorii."
)


_AKAPITY_GUIDELINES = """\
Wytyczne do pola "akapity" (opis obrazu — MINIMUM 3 AKAPITY, OPCJONALNIE 4.):
Napisz opis tego obrazu w jezyku polskim, w eleganckim, literackim stylu, ktory brzmi naturalnie, swiezo i interesujaco. Tekst ma budzic ciekawosc odbiorcy, zachecac do zatrzymania sie nad dzielem i sprawiac, ze klient bedzie chcial spojrzec na obraz dluzej.

Nie narzucaj sztywnej struktury ani schematu opisu. Pozwol, by tekst sam wynikal z charakteru obrazu i byl unikalny dla konkretnego dziela. Unikaj powtarzalnych formulek, szkolnego tonu i nadmiernie oczywistych sformulowan.

Opis powinien byc sugestywny, estetyczny i angazujacy, ale nie przesadnie patetyczny. Ma sprawiac wrazenie tekstu premium - takiego, ktory dobrze brzmi na stronie galerii, w ofercie dla klienta lub w katalogu sztuki.

Struktura akapitow:
- ZAWSZE dokladnie 3 akapity glownego opisu (estetyka, nastroj, znaczenie dziela).
- OPCJONALNIE 4. akapit — TYLKO gdy znasz autentyczne, konkretne ciekawostki zwiazane z TYM obrazem
  (np. historia powstania, ciekawa proweniencja, anegdota o modelu, kontekst wystawy, rzadki fakt
  z biografii artysty w zwiazku z tym dzielem). Nie wymyslaj ciekawostek na sile.
- Gdy brak sensownych ciekawostek — zwroc tablice z 3 elementami (bez pustego 4. akapitu).

Najwazniejsze: tekst ma wzbudzac zainteresowanie, emocje i wrazenie obcowania z czyms wyjatkowym.
"""


_TRANSLATIONS_GUIDELINES = """\
Pole "tlumaczenia" (KRYTYCZNE - 6 jezykow obcych):
- Sklep ma rynki w 6 jezykach obcych: en (Europa/UK), de (Niemcy), fr (Francja),
  es (Hiszpania), nl (Holandia), it (Wlochy). Kazdy z tych rynkow MUSI dostac
  produkt w lokalnym jezyku.
- Dla KAZDEGO z 6 jezykow utworz osobny obiekt z polami:
  * "tytul_polski"     -> tytul OBRAZU PRZETLUMACZONY na ten jezyk
                          (uzyj OFICJALNEGO tlumaczenia jesli istnieje, np. dla Indian Summer
                           niemieckie 'Altweibersommer'); klucz nazywa sie 'tytul_polski'
                           historycznie - wartoscia ma byc tytul w jezyku docelowym.
  * "akapity"          -> 3 akapity opisu w jezyku docelowym (+ opcjonalnie 4. z ciekawostkami,
                           jesli sa w wersji PL; NATURALNIE, nie doslowne tlumaczenie - dopuszczalna
                           lekka swobodna adaptacja stylistyczna; zachowaj fakty.)
  * "seo_title"        -> title_tag (do meta) w jezyku docelowym, max ok. 70 znakow,
                           format: 'Tytul - Artysta | <fraza zakupowa>' (np. 'Wall art / Wandbild / Tableau mural').
  * "seo_description"  -> description_tag, 140-160 znakow, w jezyku docelowym.
  * "alt_text"         -> alt zdjecia, max 125 znakow, w jezyku docelowym.

Format JSON:
"tlumaczenia": {
  "en": { "tytul_polski": "...", "akapity": ["...","...","..."] lub ["...","...","...","..."],
          "seo_title": "...", "seo_description": "...", "alt_text": "..." },
  "de": { ... },
  "fr": { ... },
  "es": { ... },
  "nl": { ... },
  "it": { ... }
}
"""

_ORIGINAL_TITLE_NOTE = (
    "WAZNE - jezyk tytulu oryginalnego:\n"
    "- Nazwa pliku zazwyczaj zawiera ANGIELSKI tytul, ale to NIE oznacza, ze angielski jest tytulem oryginalnym.\n"
    "  Czesto tytul oryginalny jest w jezyku artysty: dunski, niemiecki, francuski, wloski, rosyjski,\n"
    "  norweski, hiszpanski, niderlandzki itd. - zaleznie od pochodzenia/srodowiska tworcy.\n"
    "- Pole 'tytul_orginalny' musi zawierac TYTUL W JEZYKU ARTYSTY (oryginalny), a nie tlumaczenie\n"
    "  z pliku - chyba ze artysta tworzyl po angielsku (np. malarze brytyjscy/amerykanscy).\n"
    "- Najpierw sprawdz wiarygodne zrodla (Wikipedia w jezyku artysty, katalogi muzeow, monografie)\n"
    "  i podaj oryginal w jego natywnej pisowni (z diakrytykami).\n"
    "- Dopiero gdy oryginal jest naprawde nieznany - wpisz 'Nieznana'. Nie wpisuj wtedy angielskiej\n"
    "  wersji z pliku jako 'oryginalu' - chyba ze masz pewnosc, ze artysta byl anglojezyczny."
)


def canonical_product_filename(artist: str, base_title: str, *, suffix: str) -> str:
    """Nazwa pliku do promptu/JSON: «Artysta - Tytul.ext» bez preview/Full/mockup."""
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    return f"{artist.strip()} - {base_title.strip()}{ext}"


def _work_key(item: dict[str, Any]) -> tuple[str, str] | None:
    artist = (item.get("artist") or "").strip()
    base = (item.get("base_title") or item.get("title") or "").strip()
    if not artist or not base:
        return None
    return artist, base


def _rank_work_item(it: dict[str, Any]) -> int:
    if it.get("image_role") == IMAGE_ROLE_FULL:
        return 0
    if not it.get("image_role"):
        return 1
    return 2


def dedupe_queue_items_by_work(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Jeden wpis kolejki na dzielo (artysta + tytul bazowy).

    Pomija preview/mockup i dogrywki F/I. Preferuje plik Full przy tworzeniu produktu.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for it in queue_items:
        if it.get("follow_up_number") is not None:
            continue
        if it.get("image_role") in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_MOCKUP):
            continue
        key = _work_key(it)
        if key is None:
            continue
        groups.setdefault(key, []).append(it)

    out: list[dict[str, Any]] = []
    for key in sorted(groups.keys(), key=lambda k: (k[0].lower(), k[1].lower())):
        out.append(sorted(groups[key], key=_rank_work_item)[0])
    return out


def dedupe_items_for_prompt(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Jeden wpis promptu na dzielo — nazwa pliku bez sufiksow preview/Full."""
    out: list[dict[str, Any]] = []
    for rep in dedupe_queue_items_by_work(queue_items):
        path = rep["path"]
        artist = (rep.get("artist") or "").strip()
        base = (rep.get("base_title") or rep.get("title") or "").strip()
        filename = canonical_product_filename(artist, base, suffix=path.suffix or ".webp")
        out.append(
            {
                "filename": filename,
                "artist": artist,
                "title": base,
                "title_is_polish": rep.get("title_is_polish", True),
            }
        )
    return out


def lookup_llm_entry(item: dict[str, Any], llm_map: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Dopasowuje JSON po nazwie pliku w kolejce lub po nazwie kanonicznej (bez sufiksow)."""
    path = item.get("path")
    if path is not None:
        hit = llm_map.get(path.name)
        if hit:
            return hit
    key = _work_key(item)
    if key is None:
        return None
    suffix = path.suffix if path is not None else ".webp"
    return llm_map.get(canonical_product_filename(key[0], key[1], suffix=suffix))


def build_prompt(
    *,
    artist: str,
    title: str,
    image_filename: str,
    title_is_polish: bool = True,
) -> str:
    lang_hint = (
        "POLSKIM (tak zostal podany w nazwie pliku)"
        if title_is_polish
        else "ORYGINALNYM JEZYKU ARTYSTY/OBCYM (tak zostal podany w nazwie pliku)"
    )
    translation_instruction = (
        "- Pole 'tytul_polski': jesli tytul z pliku jest JUZ po polsku - przepisz go doslownie (1:1) do tego pola."
        if title_is_polish
        else "- Pole 'tytul_polski': PRZETLUMACZ tytul na polski. NAJPIERW sprawdz czy istnieje OFICJALNE polskie tlumaczenie (np. w polskich opracowaniach, Wikipedia PL, Culture.pl, katalogach muzeow) - jesli tak, UZYJ go dokladnie. Dopiero jesli oficjalnego tlumaczenia brak, przetlumacz naturalnie i idiomatycznie."
    )
    return f"""Jestes ekspertem od sztuki i copywritingu premium dla galerii obrazow.
Dla dziela ponizej przygotuj OPIS + komplet danych faktograficznych.
Zwroc WYLACZNIE pojedynczy obiekt JSON (bez komentarzy, bez code-fence markdown, bez tekstu dookola).

Dane wejsciowe:
- artysta: {artist}
- tytul (w jezyku {lang_hint}): {title}
- plik: {image_filename}

Tytul polski - wymagania:
{translation_instruction}

{_ORIGINAL_TITLE_NOTE}

Wymagane pola JSON (wszystkie obowiazkowe; jesli nie znasz pewnej wartosci historycznej, wpisz "Nieznana"):
{{
  "tytul_polski": "<polski tytul obrazu (oficjalny, jesli istnieje)>",
  "tytul_orginalny": "<oryginalny tytul w jezyku artysty (np. dunski/niemiecki/francuski/wloski/rosyjski); 'Nieznana' tylko gdy naprawde brak danych>",
  "akapity": [
    "<AKAPIT 1 opisu>",
    "<AKAPIT 2 opisu>",
    "<AKAPIT 3 opisu>",
    "<OPCJONALNIE AKAPIT 4: ciekawostki o tym obrazie — tylko gdy masz konkretne fakty>"
  ],
  "data_powstania": "<rok lub zakres; jesli nieznany: 'Nieznana'>",
  "miejsce_powstania": "<miasto/kraj; jesli nieznany: 'Nieznana'>",
  "technika": "<np. Olej na plotnie>",
  "gatunek": "<np. Pejzaz marynistyczny>",
  "nurt": "<np. Romantyzm/Realizm>",
  "forma": "<np. Malarstwo>",
  "tagi": ["<25-35 tagow SEO PL, male litery, bez hashy, bez cudzyslowow - patrz wytyczne nizej>"],
  "kategoria": "{FIXED_KATEGORIA}",
  "tlumaczenia": {{
    "en": {{ "tytul_polski": "<EN title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "de": {{ "tytul_polski": "<DE title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "fr": {{ "tytul_polski": "<FR title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "es": {{ "tytul_polski": "<ES title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "nl": {{ "tytul_polski": "<NL title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "it": {{ "tytul_polski": "<IT title>", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }}
  }}
}}

{_AKAPITY_GUIDELINES}

{_TAGS_GUIDELINES}

{_KATEGORIA_GUIDELINES}

{_TRANSLATIONS_GUIDELINES}

Zwracaj TYLKO jeden obiekt JSON.
"""


_UNKNOWN_TITLE_VALUES = frozenset({"nieznana", "unknown", "n/a", "—", "-"})


def build_new_description_prompt(
    *,
    artist: str,
    title: str = "",
    title_pl: str = "",
    title_en: str = "",
    title_original: str = "",
) -> str:
    """Prompt LLM tylko do nowego opisu (akapity PL) — bez tagow i tlumaczen.

    Do identyfikacji dziela podawaj tytul angielski i/lub oryginalny (gdy znane),
    bo polskie tytuly bywaja wspolne dla roznych obrazow tego samego artysty.
    """
    pl = (title_pl or title or "").strip()
    en = (title_en or "").strip()
    orig = (title_original or "").strip()
    if orig.lower() in _UNKNOWN_TITLE_VALUES:
        orig = ""

    title_lines: list[str] = [f"artysta: {artist}"]
    if en:
        title_lines.append(f"tytul (angielski): {en}")
    if orig:
        title_lines.append(f"tytul oryginalny (jezyk artysty): {orig}")
    if pl:
        title_lines.append(f"tytul (polski, w sklepie): {pl}")

    ident = ""
    if en or orig:
        ident = (
            "\nWazne: identyfikuj KONKRETNE dzielo po tytule angielskim i/lub oryginalnym — "
            "u tego artysty wiele obrazow ma ten sam lub podobny polski tytul.\n"
        )

    return f"""Jestes ekspertem od sztuki i copywritingu premium dla galerii obrazow.
Przygotuj OPIS.
{ident}
{chr(10).join(title_lines)}

- "akapity": MINIMUM 3 akapity opisu obrazu po polsku (+ opcjonalnie 4. z ciekawostkami) -
  trzymaj sie SZCZEGOLOWYCH WYTYCZNYCH dla pola "akapity" w dalszej czesci promptu.

"akapity": ["<AKAPIT 1>", "<AKAPIT 2>", "<AKAPIT 3>"] lub z opcjonalnym "<AKAPIT 4 ciekawostki>",

{_AKAPITY_GUIDELINES}
Zwroc WYLACZNIE obiekt JSON z polem "akapity" (bez markdown, bez tekstu dookola).
"""


_IMAGE_DESCRIPTION_PROMPT_TEMPLATE = """\
Działasz jako elitarny ekspert historii sztuki oraz wybitny copywriter premium dla luksusowych galerii sztuki i domów aukcyjnych. Twoim zadaniem jest stworzenie unikalnego, literackiego opisu obrazu, który załączam w pliku.

Zanim zaczniesz pisać tekst premium, przeprowadź wewnętrzną, rygorystyczną ANALIZĘ WIZUALNĄ załączonego obrazu. Zwróć szczególną uwagę na:
1. Spojrzenia i relacje: Gdzie DOKŁADNIE patrzą postacie? Czy patrzą na siebie, na widza, czy na konkretny przedmiot?
2. Kluczowe rekwizyty/atrybuty: Jaki unikalny przedmiot, zwierzę, roślinę lub detal trzymają postacie lub co znajduje się w ich bezpośrednim otoczeniu? Jaka jest tego symbolika?
3. Kompozycję i tło: Co znajduje się w tle? (np. surowa architektura, pejzaż, kotara, mrok). Jak światło i kolor budują nastrój?

WYTYCZNE DLA TEKSTU PREMIUM:
- Styl ma być elegancki, sugestywny, pełen polotu i głębi. Unikaj szkolnych formułek ("Na obrazie widzimy..."), tanich chwytów marketingowych, lania wody i ogólników, które pasowałyby do każdego innego dzieła z tej epoki.
- Tekst musi bezpośrednio wynikać z unikalnej dramaturgii TEGO KONKRETNEGO dzieła. Ma budzić zachwyt, ciekawość i chęć posiadania obrazu u wymagającego konesera.

STRUKTURA WYJŚCIOWA (Zwróć wyłącznie obiekt JSON z polem "akapity"):
- Dokładnie 3 akapity opisu (Akapit 1: Główna oś dramaturgii, relacje i unikalny punkt skupienia uwagi; Akapit 2: Przestrzeń, tło, kolorystyka i gra światła; Akapit 3: Detale warsztatowe, kunszt techniczny i podsumowanie estetyczne).
- OPCJONALNIE 4. akapit: Wyłącznie jeśli znasz autentyczną, fascynującą ciekawostkę (ikonograficzną, biograficzną lub historyczną) dotyczącą dokładnie TEGO dzieła lub motywu. Jeśli nie ma unikalnej ciekawostki, zwróć tylko 3 akapity.

Oto dane identyfikacyjne dzieła:
- Artysta: {artist}
- Tytuł: {title}
"""


def build_image_description_prompt(*, artist: str, title: str) -> str:
    """Prompt «Opis z obrazu» — analiza wizualna + opis premium (Gemini z załączonym zdjęciem)."""
    return _IMAGE_DESCRIPTION_PROMPT_TEMPLATE.format(
        artist=artist.strip(),
        title=title.strip(),
    )


_IMAGE_DESCRIPTION_PROMPT_V2_TEMPLATE = """\
Działasz jako elitarny ekspert historii sztuki oraz wybitny copywriter premium dla luksusowych galerii sztuki i domów aukcyjnych. Twoim zadaniem jest stworzenie unikalnego, literackiego opisu obrazu, który załączam w pliku.

Zanim zaczniesz pisać tekst premium, przeprowadź wewnętrzną, rygorystyczną ANALIZĘ WIZUALNĄ załączonego obrazu. Zwróć szczególną uwagę na:
1. Spojrzenia i relacje: Gdzie DOKŁADNIE patrzą postacie? Czy patrzą na siebie, na widza, czy na konkretny przedmiot?
2. Kluczowe rekwizyty/atrybuty: Jaki unikalny przedmiot, zwierzę, roślinę lub detal trzymają postacie lub co znajduje się w ich bezpośrednim otoczeniu? Jaka jest tego symbolika?
3. Kompozycję i tło: Co znajduje się w tle? (np. surowa architektura, pejzaż, kotara, mrok). Jak światło i kolor budują nastrój?

WYTYCZNE DLA TEKSTU PREMIUM:
- Styl ma być elegancki, sugestywny, pełen polotu i głębi. Ma brzmieć naturalnie, świeżo i interesująco. Unikaj szkolnych formułek ("Na obrazie widzimy..."), tanich chwytów marketingowych, lania wody i ogólników, które pasowałyby do każdego innego dzieła z tej epoki.
- Tekst musi bezpośrednio wynikać z unikalnej dramaturgii TEGO KONKRETNEGO dzieła. Ma budzić zachwyt, ciekawość i chęć posiadania obrazu u wymagającego konesera. Nie narzucaj sztywnej struktury ani schematu opisu. Pozwól, by tekst sam wynikał z charakteru obrazu i był unikalny dla konkretnego dzieła.

STRUKTURA WYJŚCIOWA (Zwróć wyłącznie obiekt JSON z polem "akapity"):
- Dokładnie 3 akapity opisu (Akapit 1: Główna oś dramaturgii, relacje i unikalny punkt skupienia uwagi; Akapit 2: Przestrzeń, tło, kolorystyka i gra światła; Akapit 3: Detale warsztatowe, kunszt techniczny i podsumowanie estetyczne).
- OPCJONALNIE 4. akapit: Wyłącznie jeśli znasz autentyczną, fascynującą ciekawostkę (ikonograficzną, biograficzną lub historyczną) dotyczącą dokładnie TEGO dzieła lub motywu. Jeśli nie ma unikalnej ciekawostki, zwróć tylko 3 akapity.

Oto dane identyfikacyjne dzieła:
- Artysta: {artist}
- Tytuł: {title}
"""


def build_image_description_prompt_v2(*, artist: str, title: str) -> str:
    """Prompt «Opis z obrazu v2» — naturalniejszy styl, bez sztywnego schematu."""
    return _IMAGE_DESCRIPTION_PROMPT_V2_TEMPLATE.format(
        artist=artist.strip(),
        title=title.strip(),
    )


BATCH_PROMPT_MODELS = ("opus", "gpt")
PROMPT_CHUNK_SIZE = 4


def _format_items_block(items: list[dict[str, Any]], *, start_index: int = 1) -> str:
    lines: list[str] = []
    for i, it in enumerate(items, start=start_index):
        lang = "POLSKI" if it.get("title_is_polish", True) else "OBCY (wymaga tlumaczenia na polski)"
        lines.append(
            f"{i}. plik: {it['filename']}\n"
            f"   artysta: {it['artist']}\n"
            f"   tytul: {it['title']}   [jezyk: {lang}]"
        )
    return "\n".join(lines) if lines else "(brak pozycji)"


def chunk_prompt_items(
    items: list[dict[str, Any]],
    *,
    chunk_size: int = PROMPT_CHUNK_SIZE,
) -> list[list[dict[str, Any]]]:
    """Dzieli liste dziel na paczki po max chunk_size (domyslnie 4) obrazow na jeden prompt LLM."""
    if not items:
        return []
    size = max(1, int(chunk_size))
    return [items[i : i + size] for i in range(0, len(items), size)]


def _chunk_preamble(
    *,
    chunk_no: int,
    chunk_total: int,
    chunk_count: int,
    global_start: int,
    global_total: int,
) -> str:
    if chunk_total <= 1:
        return ""
    end = global_start + chunk_count - 1
    return (
        f"=== CZESC {chunk_no} Z {chunk_total} (osobny request w Cursor / ChatGPT) ===\n"
        f"W tej czesci opracuj WYLACZNIE {chunk_count} dziel ponizej "
        f"(pozycje {global_start}–{end} z {global_total} lacznie).\n"
        f"Zwroc tablice JSON z DOKLADNIE {chunk_count} obiektami — po jednym na kazde dzielo z listy.\n"
        f"Nie dodawaj innych plikow. Po uzyskaniu wszystkich czesci polacz tablice recznie w Kroku 2.\n\n"
    )


def build_batch_prompt_chunk(
    items: list[dict[str, Any]],
    *,
    model: str = "opus",
    chunk_no: int = 1,
    chunk_total: int = 1,
    global_start_index: int = 1,
    global_total: int | None = None,
) -> str:
    """Jeden prompt dla podzbioru dziel (max PROMPT_CHUNK_SIZE w items)."""
    model_norm = (model or "opus").strip().lower()
    n = len(items)
    items_block = _format_items_block(items, start_index=global_start_index)
    total = global_total if global_total is not None else n
    preamble = _chunk_preamble(
        chunk_no=chunk_no,
        chunk_total=chunk_total,
        chunk_count=n,
        global_start=global_start_index,
        global_total=total,
    )
    if model_norm == "gpt":
        body = _build_batch_prompt_gpt(items_block, n)
    else:
        body = _build_batch_prompt_opus(items_block, n)
    return preamble + body


def build_all_prompt_chunks(
    items: list[dict[str, Any]],
    *,
    model: str = "opus",
    chunk_size: int = PROMPT_CHUNK_SIZE,
) -> list[tuple[int, int, str]]:
    """Zwraca [(numer_czesci, liczba_czesci, tekst_promptu), ...]."""
    parts = chunk_prompt_items(items, chunk_size=chunk_size)
    total = len(parts)
    out: list[tuple[int, int, str]] = []
    start = 1
    global_n = len(items)
    for i, chunk in enumerate(parts, start=1):
        out.append(
            (
                i,
                total,
                build_batch_prompt_chunk(
                    chunk,
                    model=model,
                    chunk_no=i,
                    chunk_total=total,
                    global_start_index=start,
                    global_total=global_n,
                ),
            )
        )
        start += len(chunk)
    return out


def build_batch_prompt(items: list[dict[str, Any]], *, model: str = "opus") -> str:
    """Buduje jeden prompt dla N dziel (po deduplikacji — jeden wpis na obraz).

    Gdy wiecej niz PROMPT_CHUNK_SIZE dziel, zwraca tylko pierwsza czesc (uzyj build_all_prompt_chunks).
    """
    chunks = build_all_prompt_chunks(items, model=model)
    if not chunks:
        return ""
    return chunks[0][2]


def _build_batch_prompt_opus(items_block: str, n: int) -> str:
    return f"""Jestes ekspertem od sztuki i copywritingu premium dla galerii obrazow.
Dla KAZDEGO z dziel ponizej przygotuj OPIS + komplet danych faktograficznych.
Zwroc WYLACZNIE jedna tablice JSON (bez komentarzy, bez code-fence markdown, bez tekstu dookola).
Tablica ma tyle obiektow, ile pozycji ponizej - jeden obiekt na jedno DZIELO (nie na kazdy plik preview/Full).

Pozycje do opracowania (nazwa pliku BEZ sufiksow preview/Full/mockup — to ten sam obraz):
{items_block}

Wymagania wspolne dla KAZDEGO obiektu:
- Pole "plik" MUSI dokladnie odpowiadac nazwie pliku z listy powyzej (bez «(preview)» i bez «Full»).
- Pole "tytul_polski":
  - jesli pozycja ma [jezyk: POLSKI] - przepisz tytul z pliku doslownie (1:1),
  - jesli [jezyk: OBCY (wymaga tlumaczenia na polski)] - PRZETLUMACZ na polski; NAJPIERW sprawdz czy
    istnieje OFICJALNE polskie tlumaczenie (Wikipedia PL, Culture.pl, katalogi muzeow) i UZYJ go
    dokladnie. Dopiero jesli oficjalnego brak - przetlumacz naturalnie i idiomatycznie.
- Pole "tytul_orginalny" - WAZNE:
  * Tytul w nazwie pliku jest CZESTO po angielsku jako wersja popularna/handlowa,
    ale tytul ORYGINALNY moze byc w zupelnie innym jezyku - dunskim, niemieckim, francuskim,
    wloskim, rosyjskim, norweskim, hiszpanskim, niderlandzkim - zaleznie od pochodzenia artysty.
  * Podaj tytul w JEZYKU ARTYSTY w jego natywnej pisowni (z diakrytykami). Sprawdz wiarygodne
    zrodla (Wikipedia w jezyku artysty, katalogi muzeow, monografie) zanim wpiszesz wartosc.
  * Tylko gdy artysta tworzyl po angielsku (malarze brytyjscy/amerykanscy itp.) - oryginalem
    moze byc tytul angielski z pliku.
  * Gdy oryginal naprawde nieznany - "Nieznana". Nie wpisuj wtedy mechanicznie tytulu z pliku.
- "akapity": MINIMUM 3 akapity opisu obrazu po polsku (+ opcjonalnie 4. z ciekawostkami) -
  trzymaj sie SZCZEGOLOWYCH WYTYCZNYCH dla pola "akapity" w dalszej czesci promptu.
- "tagi" (KRYTYCZNE - SEO sklepu PL): 25-35 pozycji po polsku, male litery, bez hashy,
  bez srednikow, bez duplikatow. Cel: maksymalny SEO PL pod klientow chcacych KUPIC obraz.
  Wymagane grupy:
    A) artysta + samo nazwisko;
    B) gatunek i nurt po polsku;
    C) technika ('olej na plotnie', 'akwarela', ...);
    D) motywy obrazu (np. 'morze', 'gory', 'kobieta', 'kwiaty');
    E) 1-3 kolory dominujace po polsku;
    F) 1-3 STYLE WNETRZA tylko z whitelisty: {_STYLE_HUMAN};
    G) 1-3 POMIESZCZENIA tylko z whitelisty: {_ROOM_HUMAN};
    H) 1-3 OKAZJE/PREZENTY tylko z whitelisty: {_GIFT_HUMAN}.
  OBOWIAZKOWO dolacz wszystkie stale tagi (kazdy produkt sklepu je ma):
  {_REQUIRED_TAGS_HUMAN}.
- "kategoria": ZAWSZE dokladnie "{FIXED_KATEGORIA}". Nic innego.
- Pozostale wartosci faktograficzne - jesli nieznane, wpisz "Nieznana".

Schemat kazdego obiektu (WSZYSTKIE POLA WYMAGANE):
{{
  "plik": "<nazwa pliku, taka sama jak w liscie>",
  "tytul_polski": "<polski tytul obrazu (oficjalny, jesli istnieje)>",
  "tytul_orginalny": "<oryginalny tytul w jezyku artysty (np. dunski/niemiecki/francuski) lub 'Nieznana'>",
  "akapity": ["<AKAPIT 1>", "<AKAPIT 2>", "<AKAPIT 3>"] lub z opcjonalnym "<AKAPIT 4 ciekawostki>",
  "data_powstania": "<rok lub zakres lub 'Nieznana'>",
  "miejsce_powstania": "<miasto/kraj lub 'Nieznana'>",
  "technika": "<np. Olej na plotnie>",
  "gatunek": "<np. Pejzaz marynistyczny>",
  "nurt": "<np. Romantyzm/Realizm>",
  "forma": "<np. Malarstwo>",
  "tagi": ["<tag1>", "<tag2>", "..."],
  "kategoria": "{FIXED_KATEGORIA}",
  "tlumaczenia": {{
    "en": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "de": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "fr": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "es": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "nl": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "it": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }}
  }}
}}

{_AKAPITY_GUIDELINES}

{_TRANSLATIONS_GUIDELINES}

Zwracaj DOKLADNIE jedna tablice JSON z {n} obiektami (tyle, ile pozycji wyzej), nic wiecej.
"""


def _build_batch_prompt_gpt(items_block: str, n: int) -> str:
    return f"""SYSTEM / ROLA:
Jestes generatorem ustrukturyzowanych danych JSON dla galerii obrazow premium.
Jednoczesnie jestes ekspertem od sztuki i copywritingu.

TWARDE ZASADY FORMATU ODPOWIEDZI (MUSISZ ICH PRZESTRZEGAC):
1. Odpowiedz MUSI zaczynac sie od znaku '[' i konczyc znakiem ']'. Nic przed, nic po.
2. ZAKAZANE: markdown, bloki kodu ```json ... ```, jakiekolwiek komentarze (//, /* */).
3. ZAKAZANE: tekst wstepny typu "Oto JSON:", "Here is...", "Sure, ...".
4. Uzywaj WYLACZNIE podwojnych cudzyslowow ASCII (") do stringow.
   NIE uzywaj typograficznych \u201c \u201d \u201e \u00ab \u00bb.
5. Apostrofy i cudzyslowy WEWNATRZ tekstu (np. w akapitach) wymieniaj na polskie
   cudzyslowy drukarskie \u201e ... \u201d albo usuwaj - NIGDY surowy " w srodku stringu.
6. Kazda tablica musi byc zamknieta ']' zanim otworzysz kolejne pole.
   W szczegolnosci: po ostatnim akapicie (3 lub 4) domknij '[...]' NAWIASEM ']'
   zanim napiszesz "data_powstania". Po liscie tagow domknij ']' zanim napiszesz "kategoria".
7. Kazdy obiekt musi byc zamkniety '}}'. Tablica zewnetrzna musi byc zamknieta ']'.
8. Liczba obiektow w tablicy = DOKLADNIE {n} (tyle, ile pozycji ponizej — jedna na DZIELO).
9. Pole "plik" w kazdym obiekcie MUSI byc 1:1 rowne nazwie pliku z listy ponizej
   (bez sufiksow «(preview)» i «Full» — kopiuj doslownie).

ZADANIE MERYTORYCZNE:
Dla KAZDEJ pozycji ponizej utworz obiekt JSON wedlug schematu nizej (jeden obiekt = jedno dzielo).

Pozycje do opracowania (nazwa pliku bez preview/Full — ten sam obraz):
{items_block}

Wymagania merytoryczne dla kazdego obiektu:
- "tytul_polski":
  * jesli pozycja ma [jezyk: POLSKI] - przepisz tytul z pliku 1:1.
  * jesli [jezyk: OBCY (wymaga tlumaczenia na polski)] - PRZETLUMACZ na polski;
    NAJPIERW sprawdz czy istnieje OFICJALNE polskie tlumaczenie (Wikipedia PL, Culture.pl,
    katalogi muzeow) i UZYJ go dokladnie. Dopiero jesli brak - przetlumacz naturalnie.
- "tytul_orginalny" - WAZNE:
  * Tytul z nazwy pliku jest CZESTO po angielsku jako wersja popularna/handlowa, ale
    tytul ORYGINALNY moze byc w innym jezyku - dunskim, niemieckim, francuskim, wloskim,
    rosyjskim, norweskim, hiszpanskim, niderlandzkim - zaleznie od pochodzenia artysty.
  * Podaj tytul w JEZYKU ARTYSTY w jego natywnej pisowni (z diakrytykami).
  * Tylko gdy artysta tworzyl po angielsku (UK/USA itp.) - oryginalem moze byc tytul
    angielski z pliku.
  * Gdy oryginal naprawde nieznany - "Nieznana"; nie wpisuj wtedy mechanicznie tytulu z pliku.
- "akapity": MINIMUM 3 akapity opisu obrazu po polsku (+ opcjonalnie 4. z ciekawostkami) -
  trzymaj sie SZCZEGOLOWYCH WYTYCZNYCH dla pola "akapity" w dalszej czesci promptu.
- "tagi" (KRYTYCZNE - SEO sklepu PL): 25-35 pozycji po polsku, male litery, bez hashy,
  bez srednikow, bez duplikatow. Cel: maksymalny SEO PL pod klientow chcacych KUPIC obraz.
  Wymagane grupy:
    A) artysta + samo nazwisko;
    B) gatunek i nurt po polsku;
    C) technika ('olej na plotnie', 'akwarela', ...);
    D) motywy (np. 'morze', 'gory', 'kobieta', 'kwiaty', 'noc');
    E) 1-3 kolory dominujace po polsku;
    F) 1-3 STYLE WNETRZA tylko z whitelisty: {_STYLE_HUMAN};
    G) 1-3 POMIESZCZENIA tylko z whitelisty: {_ROOM_HUMAN};
    H) 1-3 OKAZJE/PREZENTY tylko z whitelisty: {_GIFT_HUMAN}.
  OBOWIAZKOWO dolacz wszystkie stale tagi (kazdy produkt sklepu je ma):
  {_REQUIRED_TAGS_HUMAN}.
- "kategoria": ZAWSZE dokladnie "{FIXED_KATEGORIA}". Nic innego (bez sciezek typu 'Sztuka > ...').
- Wartosci faktograficzne nieznane -> "Nieznana".

SCHEMAT KAZDEGO OBIEKTU (WSZYSTKIE POLA WYMAGANE, W PODANEJ KOLEJNOSCI):
{{
  "plik": "<nazwa pliku, taka sama jak w liscie>",
  "tytul_polski": "<polski tytul>",
  "tytul_orginalny": "<oryginalny tytul w jezyku artysty (dunski/niemiecki/francuski/...) lub 'Nieznana'>",
  "akapity": ["<AKAPIT 1>", "<AKAPIT 2>", "<AKAPIT 3>"] lub z opcjonalnym "<AKAPIT 4 ciekawostki>",
  "data_powstania": "<rok lub zakres lub 'Nieznana'>",
  "miejsce_powstania": "<miasto/kraj lub 'Nieznana'>",
  "technika": "<np. Olej na plotnie>",
  "gatunek": "<np. Pejzaz marynistyczny>",
  "nurt": "<np. Romantyzm/Realizm>",
  "forma": "<np. Malarstwo>",
  "tagi": ["<tag1>", "<tag2>", "..."],
  "kategoria": "{FIXED_KATEGORIA}",
  "tlumaczenia": {{
    "en": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "de": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "fr": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "es": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "nl": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }},
    "it": {{ "tytul_polski": "...", "akapity": ["...","...","..."], "seo_title": "...", "seo_description": "...", "alt_text": "..." }}
  }}
}}

{_AKAPITY_GUIDELINES}

{_TRANSLATIONS_GUIDELINES}

PRZED WYSLANIEM ODPOWIEDZI ZWERYFIKUJ:
  - czy odpowiedz zaczyna sie od '[' a konczy na ']',
  - czy liczba '[' rowna sie liczbie ']',
  - czy liczba '{{' rowna sie liczbie '}}',
  - czy NIE MA w odpowiedzi '```' ani slow w innym jezyku poza polskim (poza tytulami obcymi i blokami 'tlumaczenia'),
  - czy kazdy obiekt ma WSZYSTKIE 13 pol zgodnie ze schematem (lacznie z 'tlumaczenia' x 6 jezykow).

Zwroc TERAZ tylko tablice JSON z {n} obiektami. Nic wiecej.
"""


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_BLOCK = re.compile(r"\[.*\]", re.DOTALL)

_AKAPITY_MIN = 3
_AKAPITY_MAX = 4


def _normalize_akapity(akapity: Any) -> list[str]:
    """Waliduje i normalizuje 3-4 akapity (4. opcjonalny — ciekawostki)."""
    if not isinstance(akapity, list) or not all(isinstance(a, str) for a in akapity):
        raise ValueError(
            f"Pole 'akapity' musi byc lista {_AKAPITY_MIN} lub {_AKAPITY_MAX} stringow "
            f"(4. tylko gdy sa ciekawostki o obrazie)."
        )
    cleaned = [a.strip() for a in akapity if a.strip()]
    if len(cleaned) not in (_AKAPITY_MIN, _AKAPITY_MAX):
        raise ValueError(
            f"Pole 'akapity' musi miec {_AKAPITY_MIN} lub {_AKAPITY_MAX} niepustych elementow "
            f"(otrzymano {len(cleaned)})."
        )
    return cleaned


def _validate_item(data: dict[str, Any]) -> None:
    if "tytul_polski" not in data and "tytul_orginalny" in data:
        data["tytul_polski"] = data["tytul_orginalny"]
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Brakujace pola: {', '.join(missing)}")
    data["akapity"] = _normalize_akapity(data.get("akapity"))
    tagi = data.get("tagi")
    if not isinstance(tagi, list) or not all(isinstance(t, str) for t in tagi):
        raise ValueError("Pole 'tagi' musi byc lista stringow.")
    data["tagi"] = ensure_required_tags(tagi)
    force_fixed_kategoria(data)
    _normalize_translations(data)


def _normalize_translations(data: dict[str, Any]) -> None:
    """Sanityzuje pole 'tlumaczenia' (opcjonalne).

    Jesli LLM zwrocil go - sprawdzamy ze dla kazdego z TRANSLATION_LANGS sa pola
    TRANSLATION_KEYS (akapity: 3 lub 4 stringi). Niezgodne sa wycinane.
    Jesli LLM go pominal - tworzymy puste {} (caly produkt bedzie po polsku).
    """
    tr = data.get("tlumaczenia")
    if not isinstance(tr, dict):
        data["tlumaczenia"] = {}
        return
    cleaned: dict[str, dict[str, Any]] = {}
    for lang in TRANSLATION_LANGS:
        block = tr.get(lang)
        if not isinstance(block, dict):
            continue
        out: dict[str, Any] = {}
        for k in TRANSLATION_KEYS:
            v = block.get(k)
            if k == "akapity":
                try:
                    out[k] = _normalize_akapity(v)
                except ValueError:
                    pass
            else:
                if isinstance(v, str) and v.strip():
                    out[k] = v.strip()
        if out:
            cleaned[lang] = out
    data["tlumaczenia"] = cleaned


def merge_json_part_lists(
    parts_by_index: dict[int, list[dict[str, Any]]],
    *,
    total_parts: int,
) -> list[dict[str, Any]]:
    """Scala odpowiedzi z czesci 1..total_parts w jedna tablice (kolejnosc zachowana)."""
    merged: list[dict[str, Any]] = []
    for i in range(1, max(1, int(total_parts)) + 1):
        part = parts_by_index.get(i)
        if part:
            merged.extend(part)
    return merged


def format_merged_json(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2)


def parse_batch_response_json(text: str) -> list[dict[str, Any]]:
    """Wyciaga tablice JSON z odpowiedzi LLM i waliduje kazdy obiekt.

    Zwraca liste slownikow; kazdy slownik ma pole 'plik' (filename) sluzace do dopasowania.
    """
    text = text.strip()
    if not text:
        raise ValueError("Pusta odpowiedz od LLM.")
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = _JSON_ARRAY_BLOCK.search(text)
    if not m:
        raise ValueError("Nie znaleziono tablicy JSON w odpowiedzi (oczekiwano '[...]').")
    blob = m.group(0)
    data = _loads_json_array_blob(blob)

    if not isinstance(data, list):
        raise ValueError("Oczekiwano tablicy JSON (lista obiektow).")
    if not data:
        raise ValueError("Tablica jest pusta.")
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Pozycja #{i} nie jest obiektem JSON.")
        if not (item.get("plik") or "").strip():
            raise ValueError(f"Pozycja #{i} nie ma pola 'plik' (potrzebne do dopasowania pliku).")
        try:
            _validate_item(item)
        except ValueError as e:
            raise ValueError(f"Pozycja '{item.get('plik', f'#{i}')}': {e}") from e
    return data





def _fix_polish_open_close_quote_pairs(blob: str) -> str:
    """„Tytul lub „L'Allegro" — zamykajacy ASCII \" zamien na typograficzny (U+201D).

    Nie ruszaj cudzyslowu zamykajacego wartosc JSON (np. ...Tamenunds",\\n \"akapity\").
    """
    return re.sub(
        r"„((?:[^\"\\]|\\.)*?)\"(?!\s*,\s*\n\s*\")(?!\s*\n\s*])",
        lambda m: f"„{m.group(1)}\u201d",
        blob,
    )


def _loads_json_array_blob(blob: str) -> list[Any]:
    """json.loads z naprawa typowych bledow LLM (polskie cudzyslowy, apostrofy w tekscie)."""
    repairs = [
        lambda s: s,
        _fix_polish_open_close_quote_pairs,
        _strip_json_trailing_commas,
        _sanitize_control_chars_in_strings,
        _sanitize_polish_ascii_quotes,
        _sanitize_inner_quotes,
    ]
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s not in seen:
            seen.add(s)
            candidates.append(s)

    _add(blob)
    step = blob
    for fn in repairs[1:]:
        step = fn(step)
        _add(step)
    combo = _sanitize_inner_quotes(
        _sanitize_polish_ascii_quotes(
            _sanitize_control_chars_in_strings(
                _strip_json_trailing_commas(_fix_polish_open_close_quote_pairs(blob))
            )
        )
    )
    _add(combo)

    last_err: json.JSONDecodeError | None = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError as e:
            last_err = e
    assert last_err is not None
    hints: list[str] = []
    if "„" in blob or "\u201e" in blob:
        hints.append("polskie cudzyslowy „…\"")
    if re.search(r",\s*[\]}]", blob):
        hints.append("przecinek na koncu tablicy/obiektu")
    if re.search(r'"(?:[^"\\]|\\.)*[\x00-\x1f]', blob):
        hints.append("znaki nowej linii w tekscie (powinny byc w jednej linii)")
    hint = ""
    if hints:
        hint = " (" + "; ".join(hints) + " — popraw w LLM lub wklej ponownie)"
    raise ValueError(
        f"Niepoprawny JSON (tablica): {last_err.msg} (pozycja {last_err.pos}).{hint}"
    ) from last_err


def _loads_json_object_blob(blob: str) -> dict[str, Any]:
    """json.loads obiektu z naprawa typowych bledow LLM (cudzyslowy w tlumaczeniach)."""
    repairs = [
        lambda s: s,
        _fix_polish_open_close_quote_pairs,
        _strip_json_trailing_commas,
        _sanitize_control_chars_in_strings,
        _sanitize_polish_ascii_quotes,
        _sanitize_inner_quotes,
    ]
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s not in seen:
            seen.add(s)
            candidates.append(s)

    _add(blob)
    step = blob
    for fn in repairs[1:]:
        step = fn(step)
        _add(step)
    combo = _sanitize_inner_quotes(
        _sanitize_polish_ascii_quotes(
            _sanitize_control_chars_in_strings(
                _strip_json_trailing_commas(_fix_polish_open_close_quote_pairs(blob))
            )
        )
    )
    _add(combo)

    last_err: json.JSONDecodeError | None = None
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError as e:
            last_err = e
            continue
        if not isinstance(data, dict):
            raise ValueError("Oczekiwano obiektu JSON (slownik).")
        return data
    assert last_err is not None
    hints: list[str] = []
    if "„" in blob or "\u201e" in blob or '"' in blob:
        hints.append('cudzyslowy w tekscie (np. „Am Klavier")')
    if re.search(r",\s*[\]}]", blob):
        hints.append("przecinek na koncu obiektu")
    hint = ""
    if hints:
        hint = " (" + "; ".join(hints) + ")"
    raise ValueError(
        f"Niepoprawny JSON: {last_err.msg} (pozycja {last_err.pos}).{hint}"
    ) from last_err


def _strip_json_trailing_commas(blob: str) -> str:
    """Usuwa przecinki bezposrednio przed ] lub } (czesty blad LLM)."""
    out: list[str] = []
    in_string = False
    escape = False
    for i, ch in enumerate(blob):
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            continue
        if ch == ",":
            j = i + 1
            while j < len(blob) and blob[j] in " \t\n\r":
                j += 1
            if j < len(blob) and blob[j] in "]}":
                continue
        out.append(ch)
    return "".join(out)


def _sanitize_control_chars_in_strings(blob: str) -> str:
    """Nowe linie / znaki sterujace wewnatrz stringow JSON -> escape lub spacja."""
    out: list[str] = []
    in_string = False
    escape = False
    for ch in blob:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                out.append(ch)
                in_string = False
                continue
            if ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            elif ord(ch) < 32:
                out.append(" ")
            else:
                out.append(ch)
            continue
        out.append(ch)
        if ch == '"':
            in_string = True
    return "".join(out)


def _sanitize_polish_ascii_quotes(blob: str) -> str:
    """„cytat\" — zamykajacy ASCII \" w srodku stringu JSON zamien na typograficzny."""
    out: list[str] = []
    in_string = False
    seen_polish_open = False
    prev = ""
    for i, ch in enumerate(blob):
        if not in_string:
            out.append(ch)
            if ch == '"' and prev != "\\":
                in_string = True
                seen_polish_open = False
        else:
            if ch == "\u201e" or ch == "„":
                seen_polish_open = True
                out.append(ch)
            elif ch == '"' and prev != "\\":
                rest = blob[i + 1 :]
                looks_structural = bool(
                    re.match(r"\s*[,}\]:]", rest) or i == len(blob) - 1
                )
                if looks_structural:
                    out.append(ch)
                    in_string = False
                    seen_polish_open = False
                else:
                    out.append("\u201d")
                    seen_polish_open = False
            else:
                out.append(ch)
        prev = ch
    return "".join(out)


def _sanitize_inner_quotes(blob: str) -> str:
    """Zamienia niezescapowane ASCII cudzyslowy wewnatrz wartosci string na typograficzne (U+201D),
    tak aby LLM-owy tytul typu 'Babie lato' w srodku stringu nie lamal JSON-a.
    Zachowuje cudzyslowy strukturalne (otwierajace/zamykajace stringi i klucze).
    """
    out: list[str] = []
    in_string = False
    prev = ""
    for i, ch in enumerate(blob):
        if not in_string:
            out.append(ch)
            if ch == '"' and prev != "\\":
                in_string = True
        else:
            if ch == '"' and prev != "\\":
                rest = blob[i + 1 : i + 16]
                # struktura JSON po zamkniciu stringu: whitespace + jeden z: , } ] :
                if re.match(r"\s*[,}\]:]", rest) or i == len(blob) - 1:
                    out.append(ch)
                    in_string = False
                else:
                    out.append("\u201d")
            else:
                out.append(ch)
        prev = ch
    return "".join(out)


def parse_response_json(text: str) -> dict[str, Any]:
    """Wyciaga pierwszy obiekt JSON z odpowiedzi LLM i waliduje wymagane pola."""
    text = text.strip()
    if not text:
        raise ValueError("Pusta odpowiedz od LLM.")
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = _JSON_BLOCK.search(text)
    if not m:
        raise ValueError("Nie znaleziono bloku JSON w odpowiedzi.")
    blob = m.group(0)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        repaired = _sanitize_inner_quotes(blob)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Niepoprawny JSON: {e2.msg} (pozycja {e2.pos}). "
                "Sprobuj usunac cudzyslowy typograficzne/apostrofy wewnatrz stringow."
            ) from e2

    if not isinstance(data, dict):
        raise ValueError("Oczekiwano obiektu JSON (slownik).")

    if "tytul_polski" not in data and "tytul_orginalny" in data:
        data["tytul_polski"] = data["tytul_orginalny"]

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Brakujace pola: {', '.join(missing)}")

    data["akapity"] = _normalize_akapity(data.get("akapity"))

    tagi = data.get("tagi")
    if not isinstance(tagi, list) or not all(isinstance(t, str) for t in tagi):
        raise ValueError("Pole 'tagi' musi byc lista stringow.")
    data["tagi"] = ensure_required_tags(tagi)
    force_fixed_kategoria(data)
    _normalize_translations(data)

    return data
