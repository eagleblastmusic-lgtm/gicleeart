"""Filtry wynikow wyszukiwania — m.in. bez rzezby, rysunkow i artefaktow."""

from __future__ import annotations

import re

from .types import ArtworkHit

_KEEP_OBJECT_TYPES = frozenset(
    {
        "painting",
        "paintings",
        "photograph",
        "photographs",
    },
)

_SCULPTURE_OBJECT_TYPES = frozenset(
    {
        "sculpture",
        "sculptures",
        "statue",
        "statues",
        "bust",
        "busts",
        "relief",
        "reliefs",
        "figurine",
        "figurines",
        "statuette",
        "statuettes",
        "herm",
        "herms",
        "rzeźba",
        "rzezba",
        "rzeźby",
        "rzezby",
        "beeld",
        "beelden",
        "beeldhouwwerk",
        "skulptur",
        "skulpturen",
    },
)

_DRAWING_OBJECT_TYPES = frozenset(
    {
        "drawing",
        "drawings",
        "architectural drawing",
        "architectural drawings",
        "design drawing",
        "index of american design",
        "rysunek",
        "rysunki",
        "tekening",
        "tekeningen",
        "dessin",
        "dessins",
        "croquis",
    },
)

_PRINT_OBJECT_TYPES = frozenset(
    {
        "print",
        "prints",
        "graphic",
        "graphics",
        "engraving",
        "engravings",
        "etching",
        "etchings",
        "lithograph",
        "lithographs",
        "woodcut",
        "woodcuts",
        "mezzotint",
        "mezzotints",
        "gravure",
        "gravures",
        "grafika",
        "grafiki",
        "druk",
        "druki",
    },
)

_ARCHAEOLOGICAL_OBJECT_TYPES = frozenset(
    {
        "decorative art",
        "decorative arts",
        "arms & armor",
        "arms and armor",
        "ceramics",
        "ceramic",
        "pottery",
        "coins & medals",
        "coin",
        "coins",
        "medal",
        "medals",
        "numismatics",
        "ivory & bone",
        "ivory and bone",
        "precious stones & gems",
        "precious stones and gems",
        "enamels",
        "enamel",
        "wood",
        "stone",
        "glasswares",
        "glassware",
        "glass",
        "lacquer & inlay",
        "lacquer and inlay",
        "textiles",
        "textile",
        "technical material",
        "volume",
        "volumes",
        "ephemera",
        "gold, silver & jewelry",
        "gold, silver and jewelry",
        "jewelry",
        "jewellery",
        "metal",
        "antiquities",
        "antiquity",
        "vessel",
        "vessels",
        "vase",
        "vases",
        "bowl",
        "bowls",
        "amphora",
        "amphorae",
        "urn",
        "urns",
        "fragment",
        "fragments",
        "sarcophagus",
        "amulet",
        "amulets",
        "weapon",
        "weapons",
        "helmet",
        "helmets",
        "shield",
        "shields",
        "tool",
        "tools",
        "utensil",
        "utensils",
        "seal",
        "seals",
        "ring",
        "rings",
        "bracelet",
        "bracelets",
        "fibula",
        "fibulae",
        "pendant",
        "pendants",
        "brooch",
        "brooches",
        "necklace",
        "necklaces",
        "dagger",
        "sword",
        "spear",
        "axe",
        "arrowhead",
        "tablet",
        "tablets",
        "beaker",
        "flask",
        "pitcher",
        "ewer",
        "chalice",
        "cup",
        "plate",
        "dish",
        "jar",
        "weight",
        "token",
    },
)

_PUBLICATION_OBJECT_TYPES = frozenset(
    {
        "book",
        "books",
        "biographies",
        "biography",
        "manuscript",
        "manuscripts",
        "manuscripts & rare books",
        "periodical",
        "periodicals",
        "publication",
        "publications",
        "catalog",
        "catalogs",
        "catalogue",
        "catalogues",
        "volume",
        "volumes",
        "serial",
        "serials",
        "journal",
        "journals",
        "magazine",
        "magazines",
        "bibliography",
        "bibliographies",
        "exhibitions (events)",
        "ephemera",
    },
)

_ALBUM_OBJECT_TYPES = frozenset(
    {
        "album",
        "albums",
        "portfolio",
        "portfolios",
        "folder",
        "folders",
    },
)

_ALBUM_IN_TITLE = re.compile(r"(?<![a-z])albums?(?![a-z])|\[folder\]", re.IGNORECASE)

_PUBLICATION_IN_TYPE = re.compile(
    r"(?<![a-z])(?:books?|biograph\w*|manuscripts?|periodicals?|publications?|"
    r"catalog(?:ue)?s?|volumes?|serials?|journals?|magazines?|bibliograph\w*|"
    r"exhibitions?\s*\(events\)|ephemera)(?![a-z])",
    re.IGNORECASE,
)

_PUBLICATION_URL = re.compile(
    r"siris-librar|/ipac20/|worldcat\.org|/catalog/|bibliograph|"
    r"books\.google|archive\.org/details",
    re.IGNORECASE,
)

_ARCHAEOLOGICAL_DEPARTMENTS = (
    "egyptian",
    "ancient near eastern",
    "greek and roman",
    "mesopotamian",
    "byzantine",
    "pre-columbian",
    "islamic art",
    "african art",
    "oceanic art",
    "asian art",
)

_SCULPTURE_IN_TEXT = re.compile(
    r"(?<![a-z])(?:sculptur\w*|statues?|statuettes?|figurines?|"
    r"rze[źz]b\w*|beeld(?:houw)?\w*|skulptur\w*|"
    r"\bbusts?\b|\breliefs?\b|\bherms?\b)(?![a-z])",
    re.IGNORECASE,
)

_DRAWING_IN_TEXT = re.compile(
    r"(?<![a-z])(?:architectural\s+drawings?|design\s+drawings?|drawings?|"
    r"rysunk\w*|tekening\w*|dessins?|croquis)(?![a-z])",
    re.IGNORECASE,
)

_PRINT_IN_TEXT = re.compile(
    r"(?<![a-z])(?:prints?|engravings?|etchings?|lithographs?|woodcuts?|"
    r"mezzotints?|gravures?|monotypes?|screenprints?|grafik\w*|druk\w*)(?![a-z])",
    re.IGNORECASE,
)

_PRINT_MEDIUM = re.compile(
    r"\b(?:mezzotint|engraving|etching|lithograph\w*|woodcut\w*|"
    r"aquatint|drypoint|linocut|screenprint\w*|silkscreen|"
    r"monotype|photogravure|helioengraving|giclee)\b",
    re.IGNORECASE,
)

_PAINTING_MEDIUM = re.compile(
    r"\boil on (?:canvas|panel|board|linen|copper)\b|"
    r"\bacrylic on\b|\btempera on\b",
    re.IGNORECASE,
)

_DRAWING_MEDIUM = re.compile(
    r"\bgraphite\b|\bcharcoal\b|\bchalk\b|\bpastel\b|"
    r"\bwatercolou?r\b|\bgouache\b|\bink on paper\b|"
    r"\bpen and ink\b|\bpencil\b|\bcrayon\b|\bsilverpoint\b|"
    r"\bblack chalk\b|\bred chalk\b|\bsanguine\b|"
    r"\bdrawing on paper\b",
    re.IGNORECASE,
)

_ARCHAEOLOGICAL_IN_TEXT = re.compile(
    r"(?<![a-z])(?:archaeolog\w*|antiqu(?:ity|ities)|"
    r"ceramic\w*|potter\w*|earthenware|stoneware|"
    r"coins?(?:\s*(?:&|and)\s*medals?)?|medallions?|numismatic\w*|"
    r"arms?\s*(?:&|and)\s*armou?r|"
    r"ivory\s*(?:&|and)\s*bone|"
    r"glasswares?|enamels?|textiles?|"
    r"amphor\w*|sarcophag\w*|"
    r"\bvases?\b|\bbowls?\b|\burns?\b|\bvessels?\b|"
    r"funerary|burial\b|"
    r"ancient\s+near\s+eastern|"
    r"decorative\s+art\w*|"
    r"precious\s+stones?\s*(?:&|and)\s*gems?)(?![a-z])",
    re.IGNORECASE,
)

_ARCHAEOLOGICAL_MEDIUM = re.compile(
    r"\b(?:terracotta|earthenware|stoneware|faience|porcelain)\b|"
    r"\b(?:bronze|copper|iron|gold|silver)\s+(?:vessel|bowl|cup|coin|ring|fibula)\b|"
    r"\b(?:stone|marble)\s+(?:vessel|bowl|tablet|stela|steles?)\b",
    re.IGNORECASE,
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def is_sculpture_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik wyglada na rzezbe (typ, dzial, material)."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in _SCULPTURE_OBJECT_TYPES:
        return True
    if ot.startswith("sculpture") or "sculpture" in ot:
        return True

    dep = _norm(hit.department)
    if "sculpture" in dep or "sculptures" in dep:
        return True

    blob = " ".join(x for x in (hit.object_type, hit.department, hit.medium) if x)
    if _SCULPTURE_IN_TEXT.search(blob):
        return True

    return False


def _is_drawing_medium(medium: str) -> bool:
    med = medium or ""
    if _PAINTING_MEDIUM.search(med):
        return False
    return bool(_DRAWING_MEDIUM.search(med))


def is_drawing_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik wyglada na rysunek (typ, dzial, material)."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in ("painting", "paintings"):
        return False

    if ot in _DRAWING_OBJECT_TYPES:
        return True

    if ot == "painting & drawing":
        return _is_drawing_medium(hit.medium)

    if ot and "drawing" in ot:
        return True

    dep = _norm(hit.department)
    if "drawings" in dep or dep.endswith(" drawing"):
        if ot.startswith("print"):
            return False
        if not ot or "draw" in ot or ot in _DRAWING_OBJECT_TYPES:
            return True

    blob = " ".join(x for x in (hit.object_type, hit.department) if x)
    if _DRAWING_IN_TEXT.search(blob):
        if _PAINTING_MEDIUM.search(hit.medium or ""):
            return False
        return True

    if _is_drawing_medium(hit.medium) and ot not in ("print", "prints", "photograph", "photographs"):
        return True

    return False


def is_print_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik wyglada na grafike / druk (ryt, litografia, mezzotinta itd.)."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in ("painting", "paintings"):
        return False

    if ot in _PRINT_OBJECT_TYPES:
        return True
    if ot.startswith("print"):
        return True

    dep = _norm(hit.department)
    if "prints" in dep or dep.endswith(" print") or "drawings and prints" in dep:
        if ot in ("photograph", "photographs"):
            return False
        if not ot or ot in _PRINT_OBJECT_TYPES or ot.startswith("print"):
            return True

    blob = " ".join(x for x in (hit.object_type, hit.department) if x)
    if _PRINT_IN_TEXT.search(blob):
        if _PAINTING_MEDIUM.search(hit.medium or ""):
            return False
        return True

    if _PRINT_MEDIUM.search(hit.medium or ""):
        return True

    return False


def _in_ancient_department(department: str) -> bool:
    dep = _norm(department)
    return any(marker in dep for marker in _ARCHAEOLOGICAL_DEPARTMENTS)


def is_archaeological_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik wyglada na artefakt / obiekt archeologiczny."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in _KEEP_OBJECT_TYPES:
        return False
    if _PAINTING_MEDIUM.search(hit.medium or ""):
        return False

    if ot in _ARCHAEOLOGICAL_OBJECT_TYPES:
        return True

    core = " ".join(x for x in (hit.object_type, hit.department, hit.medium) if x)
    if _ARCHAEOLOGICAL_IN_TEXT.search(core):
        return True

    if _ARCHAEOLOGICAL_MEDIUM.search(hit.medium or ""):
        return True

    if _in_ancient_department(hit.department):
        if ot in _ARCHAEOLOGICAL_OBJECT_TYPES:
            return True
        if not ot:
            return True
        return ot not in _KEEP_OBJECT_TYPES

    return False


def is_album_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik to album / portfolio (zbior z wielu kart, nie pojedyncze dzielo)."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in ("painting", "paintings"):
        return False
    if ot in _ALBUM_OBJECT_TYPES:
        return True
    if _ALBUM_IN_TITLE.search(hit.title or ""):
        return True
    return False


def is_publication_hit(hit: ArtworkHit) -> bool:
    """True gdy wynik to ksiazka, katalog, biografia, rekord biblioteczny itp."""
    if hit.search_mode == "web":
        return False

    ot = _norm(hit.object_type)
    if ot in ("painting", "paintings", "photograph", "photographs"):
        return False
    if ot in _PUBLICATION_OBJECT_TYPES:
        return True
    if _PUBLICATION_IN_TYPE.search(hit.object_type or ""):
        return True
    if "rare book" in ot or "manuscript" in ot:
        return True

    if _PUBLICATION_URL.search(hit.object_url or ""):
        return True

    return False


def should_skip_hit(hit: ArtworkHit) -> bool:
    return (
        is_sculpture_hit(hit)
        or is_drawing_hit(hit)
        or is_print_hit(hit)
        or is_album_hit(hit)
        or is_archaeological_hit(hit)
        or is_publication_hit(hit)
    )


def scan_cap(limit: int, *, factor: int = 8, minimum: int = 30) -> int:
    """Ile kandydatow pobrac, gdy czesc wynikow odfiltrujemy."""
    return max(minimum, limit * factor)


def maybe_add_hit(hits: list[ArtworkHit], hit: ArtworkHit, *, limit: int) -> bool:
    """Dodaje wynik jesli nie jest odfiltrowany i miesci sie w limicie."""
    if should_skip_hit(hit):
        return False
    if len(hits) >= limit:
        return False
    hits.append(hit)
    return True


def filter_hits(hits: list[ArtworkHit]) -> list[ArtworkHit]:
    return [h for h in hits if not should_skip_hit(h)]


# Zachowaj stara nazwe dla importow wewnatrz pakietu.
filter_sculptures = filter_hits
