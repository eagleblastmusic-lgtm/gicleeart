"""Centralna taksonomia tagow + mapowanie na smart-collections (Shopify).

Jedno miejsce, w ktorym definiujemy:
  * ALWAYS_TAGS         - tagi dolaczane do KAZDEGO produktu (branding sklepu, szerokie SEO).
  * STYLE_WHITELIST     - dopuszczalne style wnetrz (LLM ma wybierac stad, nie wymyslac).
  * ROOM_WHITELIST      - dopuszczalne pomieszczenia.
  * GIFT_WHITELIST      - dopuszczalne tagi okazji prezentowych.
  * GENRE_SYNONYMS_PL   - mapowanie 1:N: tag -> rownowazne tagi PL (poszerzanie SEO long-tail).
  * COLLECTION_RULES    - dla kazdego "kategoryzujacego" tagu opis odpowiadajacej smart-collection
                          (handle, title, body_html, seo title/description) - uzywane przez
                          ensure_smart_collections_from_tags() w create.py.

Konwencje:
  * Wszystkie tagi - male litery, polskie znaki dozwolone, separator: spacja.
  * Tagi oznaczajace pomieszczenie sa czlonem rzeczowym ('salon', 'sypialnia') - NIE
    'obraz do salonu' (to ma byc stalym tagiem szerokim, ale nie napedza kolekcji).
  * Stale tagi (ALWAYS_TAGS) sa **brandowe** i wystepuja w 100% produktow,
    wiec NIE generuja smart-collections (bylyby duplikatem 'wszystkich produktow').
  * Smart-collections tworzone sa LAZY: tylko gdy w bazie pojawi sie produkt z danym tagiem.

Konkurencja PL (wzorce zaobserwowane na czolowych sklepach typu galeriaobrazow.pl,
plakatobraz.pl, redro.pl, Allegro: kategoria 'Obrazy'):
  * Topowe frazy zakupowe: 'obraz na plotnie', 'obraz na sciane', 'obraz do salonu',
    'reprodukcja [artysta]', 'plakat na sciane', 'obraz nowoczesny'.
  * Sortowanie po stylu wnetrza i pomieszczeniu - dlatego sa kolekcjami, nie tylko tagami.
  * Prezenty - mocno konwertujaca podstrona, kazda okazja jako osobna kolekcja.

Przyszla wersja EN: dorobic siostrzany modul tags_taxonomy_en.py oraz funkcje
pl_to_en() konwertujaca slownik PL->EN; dorzucac drugi zestaw stalych tagow tylko gdy
sklep ma uruchomiona wersje EN.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1) ALWAYS-TAGS - dolaczane do kazdego produktu defensywnie po stronie aplikacji
#    (poza tym sa wymuszone w prompcie LLM).
# ---------------------------------------------------------------------------

ALWAYS_TAGS: tuple[str, ...] = (
    # Branding / kategoria sklepu
    "gicleeart",
    "giclee",
    "art",
    # Szerokie frazy zakupowe (dekoracja sciany, salon - najczestsze zapytania PL)
    "obraz na \u015bcian\u0119",
    "obraz do salonu",
    "obraz na p\u0142\u00f3tnie",
    "reprodukcja",
    "reprodukcja gicl\u00e9e",
    "wydruk gicl\u00e9e",
    "dekoracja wn\u0119trz",
    # Standardowe okazje prezentowe (dodane na wyrazne zyczenie wlasciciela sklepu)
    "prezent na rocznic\u0119",
    "prezent na \u015blub",
    # Dodatkowe pasujace okazje - bezpieczne dla 100% produktow w galerii sztuki
    "prezent dla niej",
    "prezent dla niego",
    "prezent na parapet\u00f3wk\u0119",
    "prezent na urodziny",
    "pomys\u0142 na prezent",
)


# ---------------------------------------------------------------------------
# 2) WHITELISTS - LLM wybiera 1-3 tagi z kazdej listy (jesli pasuja do obrazu).
# ---------------------------------------------------------------------------

STYLE_WHITELIST: tuple[str, ...] = (
    "nowoczesny",
    "klasyczny",
    "skandynawski",
    "boho",
    "glamour",
    "minimalistyczny",
    "vintage",
    "retro",
    "loft",
    "industrialny",
    "art deco",
    "prowansalski",
    "rustykalny",
    "elegancki",
)

ROOM_WHITELIST: tuple[str, ...] = (
    "salon",
    "sypialnia",
    "jadalnia",
    "kuchnia",
    "gabinet",
    "biuro",
    "\u0142azienka",
    "przedpok\u00f3j",
    "hol",
    "pok\u00f3j dziecka",
    "pok\u00f3j m\u0142odzie\u017cowy",
    "restauracja",
    "hotel",
)

GIFT_WHITELIST: tuple[str, ...] = (
    "prezent na rocznic\u0119",
    "prezent na \u015blub",
    "prezent na parapet\u00f3wk\u0119",
    "prezent na urodziny",
    "prezent na \u015bwi\u0119ta",
    "prezent dla niej",
    "prezent dla niego",
    "prezent dla rodzic\u00f3w",
    "prezent dla mamy",
    "prezent dla taty",
    "prezent dla dziadk\u00f3w",
    "prezent dla mi\u0142o\u015bnika sztuki",
    "pomys\u0142 na prezent",
)


# ---------------------------------------------------------------------------
# 3) GENRE_SYNONYMS_PL - po wygenerowaniu przez LLM, automatycznie dorzucamy
#    sprawdzone synonimy PL (long-tail SEO). Klucze case-insensitive.
# ---------------------------------------------------------------------------

GENRE_SYNONYMS_PL: dict[str, tuple[str, ...]] = {
    "krajobraz":          ("pejza\u017c", "obraz krajobrazowy"),
    "pejzaz":             ("krajobraz",),
    "pejza\u017c":        ("krajobraz",),
    "marynistyka":        ("morze", "obraz z morzem", "pejza\u017c marynistyczny"),
    "pejzaz marynistyczny": ("marynistyka", "morze"),
    "pejza\u017c marynistyczny": ("marynistyka", "morze"),
    "portret":            ("obraz portretowy",),
    "portret kobiety":    ("portret",),
    "portret m\u0119\u017cczyzny": ("portret",),
    "portret dziecka":    ("portret",),
    "akt":                ("akt kobiecy", "obraz aktowy"),
    "martwa natura":      ("still life",),
    "kwiaty":             ("obraz z kwiatami", "bukiet"),
    "bukiet":             ("kwiaty",),
    "konie":              ("obraz z koniem", "ko\u0144"),
    "psy":                ("obraz z psem", "pies"),
    "koty":               ("obraz z kotem", "kot"),
    "g\u00f3ry":          ("obraz g\u00f3ry", "krajobraz g\u00f3rski"),
    "las":                ("obraz z lasem", "le\u015bny krajobraz"),
    "miasto":             ("pejza\u017c miejski", "obraz miasta"),
    "wie\u015b":          ("pejza\u017c wiejski", "obraz wsi"),
    "religia":            ("obraz religijny", "sakralny"),
    "abstrakcja":         ("obraz abstrakcyjny", "abstrakcyjny"),
}


# ---------------------------------------------------------------------------
# 4) COLLECTION_RULES - dla kazdego "kategoryzujacego" tagu definicja smart-collection.
#    LAZY: kolekcja powstanie dopiero gdy do bazy trafi 1+ produkt z danym tagiem.
#    Stale tagi (ALWAYS_TAGS) NIE napedzaja kolekcji - byly to wszystkie produkty.
# ---------------------------------------------------------------------------

# Etykiety pomocnicze - znaki diakrytyczne unicode
_AOG = "\u0105"  # a z ogonkiem
_COA = "\u0107"  # c z kreska
_EOG = "\u0119"  # e z ogonkiem
_LSL = "\u0142"  # l z kreska
_NKR = "\u0144"  # n z kreska
_OKR = "\u00f3"  # o z kreska
_SKR = "\u015b"  # s z kreska
_ZKR = "\u017c"  # z z kropka

# typy tagow ktore napedzaja smart-collections (uzywane przez prompt do podpowiedzi
# i przez create.py do iterowania)
COLLECTION_DRIVING_KINDS: tuple[str, ...] = (
    "style", "room", "gift", "genre", "orientation", "color",
)

# Mapowanie nazw kolorow PL (z image_analysis.COLOR_PALETTE) na smart-collections
# - dorzucane do COLLECTION_RULES nizej.
COLOR_PALETTE_PL: tuple[str, ...] = (
    "czarny", "bia\u0142y", "szary",
    "be\u017cowy", "br\u0105zowy", "z\u0142oty",
    "czerwony", "r\u00f3\u017cowy", "pomara\u0144czowy", "\u017c\u00f3\u0142ty",
    "zielony", "niebieski", "granatowy", "fioletowy", "turkusowy",
)

# Tagi orientacji (musza pokrywac sie z image_analysis.ORIENTATION_TAGS)
ORIENTATION_TAG_DEFS: tuple[tuple[str, str, str], ...] = (
    ("format pionowy",     "Obrazy pionowe",
     "Reprodukcje obraz\u00f3w w formacie pionowym - idealne na waska \u015bciane "
     "obok regalu, kanapy lub w korytarzu."),
    ("format poziomy",     "Obrazy poziome",
     "Reprodukcje obraz\u00f3w w formacie poziomym - klasyczna forma idealna nad "
     "kanape, lozko lub komode."),
    ("format kwadratowy",  "Obrazy kwadratowe",
     "Reprodukcje obraz\u00f3w w formacie kwadratowym - eleganckie, harmonijne "
     "kompozycje pasuj\u0105ce do nowoczesnych wn\u0119trz."),
    ("panorama",           "Obrazy panoramiczne",
     "Reprodukcje obraz\u00f3w w formacie panoramicznym - rozlegle pejzaze, "
     "wodne horyzonty, gory - efektowne nad lozkiem czy kanapa."),
)


def _slug(text: str) -> str:
    """Slug zgodny z Shopify handle (ASCII, lowercase, dywiz)."""
    table = str.maketrans({
        _AOG: "a", _COA: "c", _EOG: "e", _LSL: "l", _NKR: "n",
        _OKR: "o", _SKR: "s", _ZKR: "z", "\u017a": "z",
    })
    s = (text or "").lower().translate(table)
    out = []
    prev_dash = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


# Odmiany potrzebne do poprawnej polszczyzny w nazwach/opisach kolekcji.
# Klucz = tag (mianownik, dokladnie jak w whitelist), wartosc = forma odmieniona.

# Style - narzednik (instrumentalis): "Obrazy w stylu <X>"
_STYLE_INSTR: dict[str, str] = {
    "nowoczesny":         "nowoczesnym",
    "klasyczny":          "klasycznym",
    "skandynawski":       "skandynawskim",
    "boho":               "boho",
    "glamour":            "glamour",
    "minimalistyczny":    "minimalistycznym",
    "vintage":            "vintage",
    "retro":              "retro",
    "loft":               "loft",
    "industrialny":       "industrialnym",
    "art deco":           "art deco",
    "prowansalski":       "prowansalskim",
    "rustykalny":         "rustykalnym",
    "elegancki":          "eleganckim",
}

# Pomieszczenia - dopelniacz (genitivus): "Obrazy do <X>"
_ROOM_GEN: dict[str, str] = {
    "salon":                  "salonu",
    "sypialnia":              "sypialni",
    "jadalnia":               "jadalni",
    "kuchnia":                "kuchni",
    "gabinet":                "gabinetu",
    "biuro":                  "biura",
    "\u0142azienka":          "\u0142azienki",
    "przedpok\u00f3j":        "przedpokoju",
    "hol":                    "holu",
    "pok\u00f3j dziecka":     "pokoju dziecka",
    "pok\u00f3j m\u0142odzie\u017cowy": "pokoju m\u0142odzie\u017cowego",
    "restauracja":            "restauracji",
    "hotel":                  "hotelu",
}

# Pomieszczenia - miejscownik (locativus): "dekoracja sciany w <X>"
_ROOM_LOC: dict[str, str] = {
    "salon":                  "salonie",
    "sypialnia":              "sypialni",
    "jadalnia":               "jadalni",
    "kuchnia":                "kuchni",
    "gabinet":                "gabinecie",
    "biuro":                  "biurze",
    "\u0142azienka":          "\u0142aziencie",
    "przedpok\u00f3j":        "przedpokoju",
    "hol":                    "holu",
    "pok\u00f3j dziecka":     "pokoju dziecka",
    "pok\u00f3j m\u0142odzie\u017cowy": "pokoju m\u0142odzie\u017cowym",
    "restauracja":            "restauracji",
    "hotel":                  "hotelu",
}


def _style_collection(tag: str) -> dict:
    instr = _STYLE_INSTR.get(tag, tag)
    title = f"Obrazy w stylu {instr}"
    seo_t = f"{title} \u2013 reprodukcje gicl\u00e9e na p\u0142\u00f3tnie"
    seo_d = (
        f"{title}: starannie dobrane reprodukcje obraz\u00f3w pasuj\u0105ce do wn\u0119trz "
        f"w stylu {instr}. Wydruk gicl\u00e9e na p\u0142\u00f3tnie, jako\u015b\u0107 muzealna."
    )
    body = (
        f"<p>Wybrane reprodukcje obraz\u00f3w idealne do wn\u0119trz "
        f"w stylu <strong>{instr}</strong>. Wszystkie wydruki w technice gicl\u00e9e "
        "na p\u0142\u00f3tnie najwy\u017cszej jako\u015bci.</p>"
    )
    return {
        "kind": "style",
        "tag": tag,
        "handle": _slug(title),
        "title": title,
        "body_html": body,
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


def _room_collection(tag: str) -> dict:
    gen = _ROOM_GEN.get(tag, tag)
    loc = _ROOM_LOC.get(tag, tag)
    title = f"Obrazy do {gen}"
    seo_t = f"{title} \u2013 reprodukcje gicl\u00e9e na \u015bcian\u0119"
    seo_d = (
        f"{title}: kolekcja reprodukcji obraz\u00f3w idealnych jako dekoracja "
        f"{gen}. Wydruki gicl\u00e9e na p\u0142\u00f3tnie, jako\u015b\u0107 muzealna."
    )
    body = (
        f"<p>Reprodukcje obraz\u00f3w polecane jako dekoracja \u015bciany w "
        f"<strong>{loc}</strong>. Wybierz dzie\u0142o, kt\u00f3re pasuje do "
        "Twojego wn\u0119trza i ciesz si\u0119 sztuk\u0105 na co dzie\u0144.</p>"
    )
    return {
        "kind": "room",
        "tag": tag,
        "handle": _slug(title),
        "title": title,
        "body_html": body,
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


def _gift_collection(tag: str) -> dict:
    title = tag[:1].upper() + tag[1:]
    seo_t = f"{title} \u2013 obraz jako prezent (reprodukcja gicl\u00e9e)"
    seo_d = (
        f"{title}: wyj\u0105tkowy upominek w postaci reprodukcji obrazu na p\u0142\u00f3tnie. "
        "Eleganckie opakowanie, jako\u015b\u0107 muzealna, gotowe do powieszenia."
    )
    body = (
        f"<p>Szukasz pomys\u0142u na <strong>{tag}</strong>? "
        "Reprodukcja obrazu na p\u0142\u00f3tnie to ponadczasowy, "
        "elegancki upominek - wyj\u0105tkowy i osobisty.</p>"
    )
    return {
        "kind": "gift",
        "tag": tag,
        "handle": _slug(title),
        "title": title,
        "body_html": body,
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


def _orientation_collection(tag: str, *, title: str, body: str) -> dict:
    seo_t = f"{title} \u2013 reprodukcje gicl\u00e9e na p\u0142\u00f3tnie"
    seo_d = (
        f"{title}: kolekcja reprodukcji obraz\u00f3w. Idealne na sciane "
        "do salonu, sypialni i gabinetu. Wydruk gicl\u00e9e w jako\u015bci muzealnej."
    )
    return {
        "kind": "orientation",
        "tag": tag,
        "handle": _slug(title),
        "title": title,
        "body_html": f"<p>{body}</p>",
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


def _color_collection(color_name: str) -> dict:
    """Smart-collection dla obrazow w danym dominujacym kolorze.

    Tag w produkcie: `obraz <kolor>` (np. 'obraz niebieski'). Plus produkt ma tez
    sam tag `<kolor>` ('niebieski'), ktory jest synonimem do filtrowania przez
    klientow szukajacych po prostu 'niebieski'.
    """
    title = f"Obrazy w kolorze: {color_name}"
    seo_t = f"Obrazy {color_name} \u2013 reprodukcje gicl\u00e9e na \u015bcian\u0119"
    seo_d = (
        f"Obrazy w kolorze {color_name}: starannie dobrane reprodukcje, w ktorych "
        f"przewaza barwa {color_name}. Pasuja do nowoczesnych i klasycznych wn\u0119trz."
    )
    body = (
        f"<p>Reprodukcje obraz\u00f3w, w kt\u00f3rych dominuje kolor "
        f"<strong>{color_name}</strong>. Pasuj\u0105 do wn\u0119trz, w kt\u00f3rych "
        "chcesz wprowadzi\u0107 spojny akcent kolorystyczny.</p>"
    )
    return {
        "kind": "color",
        "tag": f"obraz {color_name}",
        "handle": _slug(title),
        "title": title,
        "body_html": body,
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


def _genre_collection(tag: str, *, plural: str | None = None) -> dict:
    pl = plural or tag
    title = f"{pl[:1].upper()}{pl[1:]}"
    seo_t = f"{title} \u2013 reprodukcje obraz\u00f3w (gicl\u00e9e na p\u0142\u00f3tnie)"
    seo_d = (
        f"{title}: kolekcja klasycznych reprodukcji obraz\u00f3w. Wydruki gicl\u00e9e "
        "na p\u0142\u00f3tnie najwy\u017cszej jako\u015bci, gotowe na \u015bcian\u0119."
    )
    body = (
        f"<p>Reprodukcje obraz\u00f3w z kategorii <strong>{pl}</strong> "
        "w technice gicl\u00e9e na p\u0142\u00f3tnie. Najwy\u017csza jako\u015b\u0107 druku, "
        "klasyczne dzie\u0142a mistrz\u00f3w malarstwa.</p>"
    )
    return {
        "kind": "genre",
        "tag": tag,
        "handle": _slug(title),
        "title": title,
        "body_html": body,
        "seo_title": seo_t,
        "seo_description": seo_d,
    }


# Sciagnijmy w slownik docelowy. Klucz = TAG (lowercase, dokladnie taki, jaki ma
# trafic na produkt). Wartosc = blueprint smart-collection.

COLLECTION_RULES: dict[str, dict] = {}

for _t in STYLE_WHITELIST:
    COLLECTION_RULES[_t.lower()] = _style_collection(_t)

for _t in ROOM_WHITELIST:
    COLLECTION_RULES[_t.lower()] = _room_collection(_t)

for _t in GIFT_WHITELIST:
    COLLECTION_RULES[_t.lower()] = _gift_collection(_t)

# Orientacje (z image_analysis.py - tagi pojawiaja sie automatycznie po dodaniu pliku)
for _tag, _title, _body in ORIENTATION_TAG_DEFS:
    COLLECTION_RULES[_tag.lower()] = _orientation_collection(_tag, title=_title, body=_body)

# Kolory dominujace (15 z palety PL)
for _color in COLOR_PALETTE_PL:
    bp = _color_collection(_color)
    COLLECTION_RULES[bp["tag"].lower()] = bp

# Klasyczne gatunki/tematy (powszechnie wyszukiwane w PL)
for _tag, _plural in (
    ("pejza\u017c",          "pejza\u017ce"),
    ("krajobraz",            "krajobrazy"),
    ("marynistyka",          "marynistyka"),
    ("portret",              "portrety"),
    ("akt",                  "akty"),
    ("martwa natura",        "martwa natura"),
    ("kwiaty",               "obrazy z kwiatami"),
    ("konie",                "obrazy z ko\u0144mi"),
    ("psy",                  "obrazy z psami"),
    ("koty",                 "obrazy z kotami"),
    ("g\u00f3ry",            "obrazy g\u00f3rskie"),
    ("las",                  "obrazy z lasem"),
    ("miasto",               "pejza\u017ce miejskie"),
    ("wie\u015b",            "pejza\u017ce wiejskie"),
    ("religia",              "obrazy religijne"),
    ("abstrakcja",           "obrazy abstrakcyjne"),
):
    COLLECTION_RULES[_tag.lower()] = _genre_collection(_tag, plural=_plural)


# ---------------------------------------------------------------------------
# 5) Helpery uzywane przez prompt_builder.py i create.py
# ---------------------------------------------------------------------------

def expand_with_synonyms(tags: list[str]) -> list[str]:
    """Dla kazdego tagu z GENRE_SYNONYMS_PL dorzuca rownowazne synonimy PL.

    Bezpieczne (case-insensitive, deduplikuje). Zachowuje oryginalna kolejnosc
    pierwszych wystapien.
    """
    seen: set[str] = set()
    out: list[str] = []

    def _push(t: str) -> None:
        s = (t or "").strip()
        if not s:
            return
        k = s.lower()
        if k in seen:
            return
        seen.add(k)
        out.append(s)

    for t in tags or []:
        if not isinstance(t, str):
            continue
        _push(t)
        for syn in GENRE_SYNONYMS_PL.get(t.strip().lower(), ()):
            _push(syn)
    return out


def collection_blueprints_for_tags(tags: list[str]) -> list[dict]:
    """Zwraca listy blueprint'ow smart-collections do utworzenia dla podanego zestawu tagow.

    Pomija tagi nie majace mapowania w COLLECTION_RULES (czyli np. wolne tagi LLM,
    nazwiska artystow, kolory, stale brandowe tagi).
    """
    out: list[dict] = []
    seen: set[str] = set()
    for t in tags or []:
        if not isinstance(t, str):
            continue
        key = t.strip().lower()
        if not key or key in seen:
            continue
        bp = COLLECTION_RULES.get(key)
        if bp is None:
            continue
        seen.add(key)
        out.append(bp)
    return out
