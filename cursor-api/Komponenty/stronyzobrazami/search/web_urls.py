"""Linki wyszukiwania w przeglądarce (fallback gdy brak API)."""



from __future__ import annotations



import urllib.parse



from .types import ArtworkHit





def build_web_search_url(source_id: str, *, artist: str, title: str) -> str:

    q = " ".join(x for x in (artist, title) if x).strip()

    enc = urllib.parse.quote(q)

    builders: dict[str, str] = {

        "rijks": f"https://www.rijksmuseum.nl/en/search?q={enc}",

        "met": f"https://www.metmuseum.org/art/collection/search?q={enc}",

        "artic": f"https://www.artic.edu/collection?q={enc}",

        "nga": f"https://www.nga.gov/collection-search-result.html?search={enc}",

        "getty": f"https://www.getty.edu/art/collection/search/?q={enc}",

        "cleveland": f"https://www.clevelandart.org/art/collection/search?q={enc}",

        "smithsonian": f"https://www.si.edu/search/collection?q={enc}",

        "yale": f"https://collections.britishart.yale.edu/catalog?q={enc}",

        "walters": f"https://art.thewalters.org/search/?q={enc}",

        "smk": f"https://open.smk.dk/en/search?q={enc}",

        "belvedere": f"https://sammlung.belvedere.at/en/search?q={enc}",

        "mia": f"https://collections.artsmia.org/search/{enc}",

        "newfields": f"https://collections.discovernewfields.org/search?q={enc}",

        "paris_musees": (

            "https://www.parismuseescollections.paris.fr/en/recherche/type/oeuvre"

            f"?search_api_fulltext={enc}"

        ),

        "fng": f"https://www.kansallisgalleria.fi/en/search?query={enc}",

        "nationalmuseum_se": f"https://collection.nationalmuseum.se/en/search?q={enc}",

        "mauritshuis": f"https://www.mauritshuis.nl/en/search?query={enc}",

        "dma": f"https://dma.org/art/collection/search?searchText={enc}",

        "lacma": f"https://collections.lacma.org/search?q={enc}",

        "princeton": f"https://artmuseum.princeton.edu/collection/search?keyword={enc}",

        "clark": f"https://www.clarkart.edu/Collection/Search?q={enc}",

        "barnes": f"https://collection.barnesfoundation.org/search?q={enc}",

        "slam": f"https://www.slam.org/collection-search/?q={enc}",

        "staedel": f"https://sammlung.staedelmuseum.de/en/search?q={enc}",

        "mkg": f"https://www.mkg-hamburg.de/en/collection/search?q={enc}",

        "basel": f"https://download.kunstmuseumbasel.ch/en/search?q={enc}",

        "albertina": f"https://sammlungenonline.albertina.at/en/search?q={enc}",

        "npm_tw": f"https://digitalarchive.npm.gov.tw/en/search?keyword={enc}",

        "mnk": f"https://zbiory.mnk.pl/en/search-result?q={enc}",

        "yale_gallery": f"https://artgallery.yale.edu/collection/search?keyword={enc}",

        "philadelphia": f"https://philamuseum.org/collection/search?query={enc}",

        "risd": f"https://risdmuseum.org/art-design/collection?search_api_fulltext={enc}",

        "dia": f"https://dia.org/search/collection?query={enc}",

        "birmingham_moa": f"https://www.artsbma.org/collection/?s={enc}",

        "birmingham_trust": (
            "https://dams.birminghammuseums.org.uk/assetbank-birminghammuseums/action/search"
            f"?keywords={enc}"
        ),

        "ramm": f"https://collections.rammuseum.org.uk/search.html?q={enc}",

        "nypl": f"https://digitalcollections.nypl.org/search/index?q={enc}&search_scope=default",

        "loc": f"https://www.loc.gov/search/?q={enc}&fa=online-format:image",

        "wellcome": f"https://wellcomecollection.org/search/works?query={enc}",

        "tepapa": f"https://collections.tepapa.govt.nz/search?q={enc}",

        "cooper_hewitt": f"https://collection.cooperhewitt.org/search/{enc}",

        "europeana": f"https://www.europeana.eu/en/search?query={enc}&qf=TYPE:IMAGE",

        "pdia": f"https://pdimagearchive.org/search/?q={enc}",

    }

    return builders.get(source_id, "")





def web_fallback_hits(

    source_id: str,

    source_name: str,

    *,

    artist: str,

    title: str,

) -> list[ArtworkHit]:

    url = build_web_search_url(source_id, artist=artist, title=title)

    if not url:

        return []

    label = " ".join(x for x in (artist, title) if x).strip() or "wyszukiwanie"

    return [

        ArtworkHit(

            source_id=source_id,

            source_name=source_name,

            title=f"Otwórz wyszukiwanie: {label}",

            artist=artist,

            object_url=url,

            search_mode="web",

            score=0.1,

        ),

    ]

