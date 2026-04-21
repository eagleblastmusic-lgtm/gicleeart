"""Buduje prompt do LLM (w Cursor/chat) i waliduje zwrocony JSON."""
from __future__ import annotations

import json
import re
from typing import Any

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
    "akapity",             # 3 akapity opisu w jezyku docelowym
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
Wytyczne do pola "akapity" (opis obrazu, DOKLADNIE 3 AKAPITY):
Napisz opis tego obrazu w jezyku polskim, w eleganckim, literackim stylu, ktory brzmi naturalnie, swiezo i interesujaco. Tekst ma budzic ciekawosc odbiorcy, zachecac do zatrzymania sie nad dzielem i sprawiac, ze klient bedzie chcial spojrzec na obraz dluzej.

Nie narzucaj sztywnej struktury ani schematu opisu. Pozwol, by tekst sam wynikal z charakteru obrazu i byl unikalny dla konkretnego dziela. Unikaj powtarzalnych formulek, szkolnego tonu i nadmiernie oczywistych sformulowan.

Opis powinien byc sugestywny, estetyczny i angazujacy, ale nie przesadnie patetyczny. Ma sprawiac wrazenie tekstu premium - takiego, ktory dobrze brzmi na stronie galerii, w ofercie dla klienta lub w katalogu sztuki. Opis ma miec 3 akapity.

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
  * "akapity"          -> 3 akapity opisu w jezyku docelowym (NATURALNIE,
                           nie doslowne tlumaczenie z polskiego - dopuszczalna
                           lekka swobodna adaptacja stylistyczna; zachowaj fakty.)
  * "seo_title"        -> title_tag (do meta) w jezyku docelowym, max ok. 70 znakow,
                           format: 'Tytul - Artysta | <fraza zakupowa>' (np. 'Wall art / Wandbild / Tableau mural').
  * "seo_description"  -> description_tag, 140-160 znakow, w jezyku docelowym.
  * "alt_text"         -> alt zdjecia, max 125 znakow, w jezyku docelowym.

Format JSON:
"tlumaczenia": {
  "en": { "tytul_polski": "...", "akapity": ["...","...","..."],
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
    "<AKAPIT 3 opisu>"
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


BATCH_PROMPT_MODELS = ("opus", "gpt")


def build_batch_prompt(items: list[dict[str, Any]], *, model: str = "opus") -> str:
    """Buduje jeden prompt dla N obrazow na raz.

    items: lista slownikow { 'artist', 'title', 'filename', 'title_is_polish' (bool) }.
    model: 'opus' - wariant dla Claude (krotszy, bez nadmiernych rygorow),
           'gpt'  - wariant dla GPT (wzmocniony: zero code-fence, zero prozy, sprawdz nawiasy).
    """
    model_norm = (model or "opus").strip().lower()
    lines: list[str] = []
    for i, it in enumerate(items, start=1):
        lang = "POLSKI" if it.get("title_is_polish", True) else "OBCY (wymaga tlumaczenia na polski)"
        lines.append(
            f"{i}. plik: {it['filename']}\n"
            f"   artysta: {it['artist']}\n"
            f"   tytul: {it['title']}   [jezyk: {lang}]"
        )
    items_block = "\n".join(lines) if lines else "(brak pozycji)"

    if model_norm == "gpt":
        return _build_batch_prompt_gpt(items_block, len(items))
    return _build_batch_prompt_opus(items_block)


def _build_batch_prompt_opus(items_block: str) -> str:
    return f"""Jestes ekspertem od sztuki i copywritingu premium dla galerii obrazow.
Dla KAZDEGO z dziel ponizej przygotuj OPIS + komplet danych faktograficznych.
Zwroc WYLACZNIE jedna tablice JSON (bez komentarzy, bez code-fence markdown, bez tekstu dookola).
Tablica ma tyle obiektow, ile pozycji ponizej - jeden obiekt na jeden plik.

Pozycje do opracowania:
{items_block}

Wymagania wspolne dla KAZDEGO obiektu:
- Pole "plik" MUSI dokladnie odpowiadac nazwie pliku z listy powyzej (do dopasowania po stronie aplikacji).
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
- "akapity": DOKLADNIE 3 akapity opisu obrazu po polsku - trzymaj sie SZCZEGOLOWYCH WYTYCZNYCH
  dla pola "akapity" podanych w dalszej czesci promptu (sekcja 'Wytyczne do pola "akapity"').
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
  "akapity": ["<AKAPIT 1>", "<AKAPIT 2>", "<AKAPIT 3>"],
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

Zwracaj DOKLADNIE jedna tablice JSON z N obiektami (N = liczba pozycji wyzej), nic wiecej.
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
   W szczegolnosci: po 3 akapitach domknij '[...]' NAWIASEM ']' zanim napiszesz
   "data_powstania". Po liscie tagow domknij ']' zanim napiszesz "kategoria".
7. Kazdy obiekt musi byc zamkniety '}}'. Tablica zewnetrzna musi byc zamknieta ']'.
8. Liczba obiektow w tablicy = DOKLADNIE {n} (tyle, ile pozycji ponizej).
9. Pole "plik" w kazdym obiekcie MUSI byc 1:1 rowne nazwie pliku z listy ponizej
   (z podkresleniami, spacjami i rozszerzeniem - kopiuj doslownie).

ZADANIE MERYTORYCZNE:
Dla KAZDEJ pozycji ponizej utworz obiekt JSON wedlug schematu nizej.

Pozycje do opracowania:
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
- "akapity": DOKLADNIE 3 akapity opisu obrazu po polsku - trzymaj sie SZCZEGOLOWYCH WYTYCZNYCH
  dla pola "akapity" podanych w dalszej czesci promptu (sekcja 'Wytyczne do pola "akapity"').
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
  "akapity": ["<AKAPIT 1>", "<AKAPIT 2>", "<AKAPIT 3>"],
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


def _validate_item(data: dict[str, Any]) -> None:
    if "tytul_polski" not in data and "tytul_orginalny" in data:
        data["tytul_polski"] = data["tytul_orginalny"]
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Brakujace pola: {', '.join(missing)}")
    akapity = data.get("akapity")
    if not isinstance(akapity, list) or len(akapity) != 3 or not all(isinstance(a, str) for a in akapity):
        raise ValueError("Pole 'akapity' musi byc lista 3 stringow.")
    tagi = data.get("tagi")
    if not isinstance(tagi, list) or not all(isinstance(t, str) for t in tagi):
        raise ValueError("Pole 'tagi' musi byc lista stringow.")
    data["tagi"] = ensure_required_tags(tagi)
    force_fixed_kategoria(data)
    _normalize_translations(data)


def _normalize_translations(data: dict[str, Any]) -> None:
    """Sanityzuje pole 'tlumaczenia' (opcjonalne).

    Jesli LLM zwrocil go - sprawdzamy ze dla kazdego z TRANSLATION_LANGS sa pola
    TRANSLATION_KEYS (akapity musi byc lista 3 stringow). Niezgodne sa wycinane.
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
                if isinstance(v, list) and len(v) == 3 and all(isinstance(a, str) for a in v):
                    out[k] = [s.strip() for s in v]
            else:
                if isinstance(v, str) and v.strip():
                    out[k] = v.strip()
        if out:
            cleaned[lang] = out
    data["tlumaczenia"] = cleaned


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
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        repaired = _sanitize_inner_quotes(blob)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Niepoprawny JSON (tablica): {e2.msg} (pozycja {e2.pos})."
            ) from e2

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

    akapity = data.get("akapity")
    if not isinstance(akapity, list) or len(akapity) != 3 or not all(isinstance(a, str) for a in akapity):
        raise ValueError("Pole 'akapity' musi byc lista 3 stringow.")

    tagi = data.get("tagi")
    if not isinstance(tagi, list) or not all(isinstance(t, str) for t in tagi):
        raise ValueError("Pole 'tagi' musi byc lista stringow.")
    data["tagi"] = ensure_required_tags(tagi)
    force_fixed_kategoria(data)
    _normalize_translations(data)

    return data
