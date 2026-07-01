"""Mapowanie URL zakladek uzytkownika na zrodla wyszukiwania."""



from __future__ import annotations



import re

from dataclasses import dataclass

from urllib.parse import urlparse



from ..storage import SiteEntry





@dataclass(frozen=True)

class SourceDef:

    source_id: str

    name: str

    patterns: tuple[str, ...]

    api: bool = True

    local: bool = False

    web_fallback: bool = True





SOURCES: tuple[SourceDef, ...] = (

    SourceDef("rijks", "Rijksmuseum", (r"rijksmuseum\.nl",)),

    SourceDef("met", "The Met", (r"metmuseum\.org",)),

    SourceDef("artic", "Art Institute of Chicago", (r"artic\.edu",)),

    SourceDef("nga", "National Gallery of Art", (r"nga\.gov",), local=True),

    SourceDef("getty", "Getty Museum", (r"getty\.edu",)),

    SourceDef("cleveland", "Cleveland Museum of Art", (r"clevelandart\.org",)),

    SourceDef("smithsonian", "Smithsonian Open Access", (r"si\.edu",)),

    SourceDef("yale", "Yale Center for British Art", (r"britishart\.yale\.edu",), api=False),

    SourceDef("walters", "Walters Art Museum", (r"thewalters\.org",), local=True),

    SourceDef("smk", "SMK (Dania)", (r"smk\.dk", r"open\.smk\.dk",)),

    SourceDef("belvedere", "Belvedere", (r"belvedere\.at",)),

    SourceDef("mia", "Minneapolis Institute of Art", (r"artsmia\.org",)),

    SourceDef("newfields", "Indianapolis / Newfields", (r"discovernewfields\.org",)),

    SourceDef("paris_musees", "Paris Musées", (r"parismuseescollections\.paris\.fr",)),

    SourceDef("fng", "Finnish National Gallery", (r"kansallisgalleria\.fi",)),

    SourceDef("nationalmuseum_se", "Nationalmuseum, Stockholm", (r"collection\.nationalmuseum\.se",), api=False),

    SourceDef("mauritshuis", "Mauritshuis", (r"mauritshuis\.nl",), api=False),

    SourceDef("dma", "Dallas Museum of Art", (r"dma\.org",), api=False),

    SourceDef("lacma", "LACMA", (r"collections\.lacma\.org", r"lacma\.org",), api=False),

    SourceDef("princeton", "Princeton University Art Museum", (r"artmuseum\.princeton\.edu",), api=False),

    SourceDef("clark", "Clark Art Institute", (r"clarkart\.edu",), api=False),

    SourceDef("barnes", "Barnes Foundation", (r"barnesfoundation\.org",), api=False),

    SourceDef("slam", "Saint Louis Art Museum", (r"slam\.org",), api=False),

    SourceDef("staedel", "Städel Museum", (r"staedelmuseum\.de",), api=False),

    SourceDef("mkg", "MK&G Hamburg", (r"mkg-hamburg\.de",), api=False),

    SourceDef("basel", "Kunstmuseum Basel", (r"kunstmuseumbasel\.ch",), api=False),

    SourceDef("albertina", "Albertina", (r"sammlungenonline\.albertina\.at",)),

    SourceDef("npm_tw", "National Palace Museum (Taiwan)", (r"digitalarchive\.npm\.gov\.tw",), api=False),

    SourceDef("mnk", "Muzeum Narodowe w Krakowie", (r"zbiory\.mnk\.pl", r"mnk\.pl",), api=False),

    SourceDef("yale_gallery", "Yale University Art Gallery", (r"artgallery\.yale\.edu",), api=False),

    SourceDef("philadelphia", "Philadelphia Museum of Art", (r"philamuseum\.org",), api=False),

    SourceDef("risd", "RISD Museum", (r"risdmuseum\.org",)),

    SourceDef("dia", "Detroit Institute of Arts", (r"dia\.org",), api=False),

    SourceDef("birmingham_moa", "Birmingham Museum of Art", (r"artsbma\.org",), api=False),

    SourceDef(
        "birmingham_trust",
        "Birmingham Museums Trust",
        (r"birminghammuseums\.org\.uk", r"dams\.birminghammuseums\.org\.uk"),
        api=True,
    ),

    SourceDef("ramm", "Royal Albert Memorial Museum & Art Gallery", (r"rammuseum\.org\.uk", r"collections\.rammuseum\.org\.uk",), api=False),

    SourceDef("nypl", "NYPL Digital Collections", (r"digitalcollections\.nypl\.org", r"nypl\.org",)),

    SourceDef("loc", "Library of Congress", (r"loc\.gov",)),

    SourceDef("wellcome", "Wellcome Collection", (r"wellcomecollection\.org",)),

    SourceDef("tepapa", "Museum of New Zealand Te Papa Tongarewa", (r"tepapa\.govt\.nz", r"collections\.tepapa\.govt\.nz",)),

    SourceDef("cooper_hewitt", "Cooper Hewitt Smithsonian Design Museum", (r"cooperhewitt\.org", r"collection\.cooperhewitt\.org",)),

    SourceDef("europeana", "Europeana", (r"europeana\.eu",)),

    SourceDef("pdia", "Public Domain Image Archive", (r"pdimagearchive\.org",), api=False),

)



_BY_ID: dict[str, SourceDef] = {s.source_id: s for s in SOURCES}





def source_for_url(url: str) -> SourceDef | None:

    host = (urlparse(url).netloc or "").lower().removeprefix("www.")

    if not host:

        return None

    for src in SOURCES:

        for pat in src.patterns:

            if re.search(pat, host):

                return src

    return None





def sources_for_sites(sites: list[SiteEntry]) -> list[SourceDef]:

    """Unikalne zrodla w kolejnosci pierwszego wystapienia w zakladkach."""

    out: list[SourceDef] = []

    seen: set[str] = set()

    for site in sites:

        src = source_for_url(site.url)

        if not src or src.source_id in seen:

            continue

        seen.add(src.source_id)

        out.append(src)

    return out





def get_source(source_id: str) -> SourceDef | None:

    return _BY_ID.get(source_id)

