"""Orkiestrator: buduje produkt, wgrywa zdjecie, ustawia meta, kolekcje i publikuje."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from . import shopify_client as sc
from . import templates as variant_templates
from .body_i18n import translate_field_value_or_pl
from .html_template import build_artist_collection_body_html, build_body_html
from .image_analysis import analyze_image
from .options_i18n import (
    find_missing_option_translations,
    translate_option_name,
    translate_option_value,
)
from .parser import (
    FOLLOW_UP_KIND_F,
    FOLLOW_UP_KIND_I,
    IMAGE_ROLE_FULL,
    IMAGE_ROLE_MOCKUP,
    IMAGE_ROLE_PREVIEW,
    alt_is_catalog_preview,
    alt_is_gallery_full,
    artist_collection_title,
    compute_source_key,
    full_alt_text,
    installment_alt_text,
    mockup_alt_text,
    preview_alt_text,
    slugify,
    source_key_tag,
    surname_only,
)
from .prompt_builder import dedupe_queue_items_by_work, lookup_llm_entry
from .tags_taxonomy import collection_blueprints_for_tags
from .tags_taxonomy_i18n import LOCALE_DISPLAY

# Historyczny ID produktu referencyjnego w Shopify - uzywany tylko przy
# pierwszym uruchomieniu (bootstrap szablonu 'Podstawowy' w templates.py).
# Apka dzialajaca na swiezej instalacji zaciaga go raz, zapisuje lokalnie,
# i od tej pory dziala z lokalnego snapshota.
REFERENCE_PRODUCT_ID = variant_templates.REFERENCE_PRODUCT_ID
VENDOR = "Giclee Art"
PRODUCT_TYPE = "Obraz"

# Menu nawigacji: kolekcje artystow wisza jako dzieci pozycji 'ARTYŚCI'
# w menu glownym 'main-menu' (patrz SHOP_KNOWLEDGE.md sekcja 9).
ARTIST_MENU_HANDLE = "main-menu"
ARTIST_MENU_PARENT = "ARTYŚCI"

# Wspolny baner kolekcji artysty (jak u pozostalych artystow). To samo zdjecie
# (Andreas Achenbach - Raddampfer) jest ustawione jako image kolekcji u innych.
ARTIST_COLLECTION_BANNER_SRC = (
    "https://cdn.shopify.com/s/files/1/1011/0517/2828/collections/"
    "Andreas_Achenbach_-_Raddampfer_in_sturmischer_See.jpg"
)

Logger = Callable[[str], None]
BatchProgress = Callable[[int, int, str], None]
ProductReadyCallback = Callable[[dict[str, Any], dict[str, Any]], None]

# Cache zywy w pamieci procesu - zeby przy paczce N produktow nie pytac Shopify
# o te same kolekcje N razy. Klucz = handle smart-collection. Wartosc = dict z 'id'.
_SMART_COLLECTION_CACHE: dict[str, dict[str, Any]] = {}


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def build_seo(*, tytul: str, artysta: str, gatunek: str = "", nurt: str = "") -> tuple[str, str, str]:
    """Buduje (title_tag, meta_description, handle) dla pojedynczego produktu.

    Zoptymalizowane pod SEO PL: w title_tag pakujemy najmocniejsze frazy zakupowe
    ('obraz na plotnie', 'reprodukcja gicl\u00e9e'), w meta_desc dodajemy gatunek/nurt
    (gdy znane) zeby trafiac w long-tail.
    """
    title_tag = (
        f"{tytul} \u2013 {artysta} | Obraz na p\u0142\u00f3tnie, reprodukcja gicl\u00e9e"
    )
    bits: list[str] = [
        f"Reprodukcja obrazu \u201e{tytul}\u201d \u2013 {artysta}.",
    ]
    if (gatunek or "").strip() and (gatunek or "").strip().lower() != "nieznana":
        bits.append(f"Gatunek: {gatunek.strip()}.")
    if (nurt or "").strip() and (nurt or "").strip().lower() != "nieznana":
        bits.append(f"Nurt: {nurt.strip()}.")
    bits.append(
        "Wydruk gicl\u00e9e na p\u0142\u00f3tnie w jako\u015bci muzealnej \u2013 "
        "elegancka dekoracja \u015bciany do salonu, sypialni i gabinetu. "
        "Idealny pomys\u0142 na prezent."
    )
    meta_desc = " ".join(bits)
    handle = slugify(f"{artysta} {tytul}")
    return title_tag, meta_desc, handle


def build_image_alt(
    *,
    artysta: str,
    tytul: str,
    gatunek: str = "",
    nurt: str = "",
    technika: str = "",
) -> str:
    """Buduje SEO-loaded alt text dla zdjecia produktu (Google Images PL).

    Zasady:
      - <125 znakow (limit czytelnosci dla czytnikow ekranu / SEO),
      - zaczynamy od 'Artysta - Tytul' (najmocniejsza fraza),
      - dorzucamy 1-2 slowa kluczowe (gatunek/nurt/technika) jesli znane,
      - konczymy frazza zakupowa 'reprodukcja gicl\u00e9e na p\u0142\u00f3tnie'.
    """
    head = f"{artysta} \u2013 {tytul}"
    extras: list[str] = []
    for v in (gatunek, nurt, technika):
        s = (v or "").strip()
        if s and s.lower() != "nieznana":
            extras.append(s)
    extras_str = ", ".join(extras[:2])  # max 2 zeby nie rozmywac
    tail = "reprodukcja gicl\u00e9e na p\u0142\u00f3tnie"
    parts = [head]
    if extras_str:
        parts.append(extras_str)
    parts.append(tail)
    alt = " | ".join(parts)
    if len(alt) > 125:
        alt = alt[:122].rstrip() + "..."
    return alt


def push_product_translations(
    *,
    product_id: int,
    artist: str,
    translations: dict[str, dict[str, Any]],
    paragraphs_pl: list[str] | None = None,
    original_title: str = "",
    data_powstania: str = "",
    miejsce_powstania: str = "",
    technika: str = "",
    gatunek: str = "",
    nurt: str = "",
    forma: str = "",
    lifespan: str = "",
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Pushuje tlumaczenia produktu na 6 jezykow przez Shopify Translations API.

    Dla kazdego jezyka z `translations` (en/de/fr/es/nl/it) ustawia:
      - title          (tytul produktu '{Artysta} - {tlumaczenie tytulu}')
      - body_html      (caly szablon z 3-4 akapitami w jezyku docelowym + tabela szczegolow)
      - global.title_tag       (SEO title)
      - global.description_tag (SEO description)

    Wymaga scope: write_translations.
    """
    if not translations:
        _log(logger, "[i18n] Brak bloku 'tlumaczenia' w llm_data - pomijam push tlumaczen.")
        return {"pushed": [], "skipped": [], "errors": []}

    shop, token = sc.load_session()
    product_gid = sc.product_gid(product_id)
    pushed: list[str] = []
    errors: list[dict[str, str]] = []

    for lang, block in translations.items():
        if not isinstance(block, dict):
            continue
        translated_title = (block.get("tytul_polski") or "").strip()
        akapity_lang = block.get("akapity") or paragraphs_pl or []
        seo_title = (block.get("seo_title") or "").strip()
        seo_desc = (block.get("seo_description") or "").strip()
        if not translated_title and not akapity_lang and not seo_title:
            continue

        # 1) Pelny tytul produktu (Artysta - <tlum>)
        full_title = f"{artist} - {translated_title}" if translated_title else ""

        # 2) Wartosci faktograficzne sekcji 'SZCZEGOLY' w jezyku docelowym.
        #    Pierwsze zrodlo: blok 'tlumaczenia.<lang>' z LLM (gdy ma odpowiednie pole).
        #    Drugie zrodlo: statyczny slownik `body_i18n` (Olej na plotnie -> Huile sur toile,
        #    XIX wiek -> XIXe siecle, Düsseldorf / Ostenda -> Düsseldorf / Ostende, ...).
        #    Trzecie zrodlo: oryginalna polska wartosc (lepsze niz puste pole).
        def _facts_field(lang_block_key: str, pl_value: str) -> str:
            v = (block.get(lang_block_key) or "").strip()
            if v:
                return v
            return translate_field_value_or_pl(pl_value, lang)

        data_powstania_lang = _facts_field("data_powstania", data_powstania)
        miejsce_powstania_lang = _facts_field("miejsce_powstania", miejsce_powstania)
        technika_lang = _facts_field("technika", technika)
        gatunek_lang = _facts_field("gatunek", gatunek)
        nurt_lang = _facts_field("nurt", nurt)
        forma_lang = _facts_field("forma", forma)

        # 3) Pelny body_html w jezyku docelowym (kompletny szablon z lokalizowanym
        #    naglowkiem 'SZCZEGOLY' i etykietami pol - wszystko z body_i18n.body_labels(lang)).
        body_html_lang = ""
        if isinstance(akapity_lang, list) and 3 <= len([a for a in akapity_lang if (a or "").strip()]) <= 4:
            body_html_lang = build_body_html(
                tytul_obrazu=translated_title,
                artysta=artist,
                data=lifespan,
                akapity=akapity_lang,
                tytul_orginalny=original_title,
                data_powstania=data_powstania_lang,
                miejsce_powstania=miejsce_powstania_lang,
                technika=technika_lang,
                gatunek=gatunek_lang,
                nurt=nurt_lang,
                forma=forma_lang,
                lang=lang,
            )

        # Pola tlumaczone bezposrednio na zasobie Product: title, body_html
        # oraz - WAZNE - meta_title / meta_description (klucze SEO w Shopify
        # Translations API; metafieldy 'global.title_tag' / 'global.description_tag'
        # NIE sa tu uzywane - aplikacja Translate & Adapt czyta wlasnie te klucze).
        product_fields: dict[str, str] = {}
        if full_title:
            product_fields["title"] = full_title
        if body_html_lang:
            product_fields["body_html"] = body_html_lang
        if seo_title:
            product_fields["meta_title"] = seo_title
        if seo_desc:
            product_fields["meta_description"] = seo_desc

        if product_fields:
            try:
                sc.register_translations(
                    shop, token,
                    resource_gid=product_gid,
                    locale=lang,
                    fields=product_fields,
                )
                pushed_keys = sorted(product_fields.keys())
                _log(
                    logger,
                    f"[i18n] {lang.upper()} ({LOCALE_DISPLAY.get(lang, lang)}): "
                    f"product zarejestrowano keys={pushed_keys}.",
                )
            except sc.ShopifyError as e:
                errors.append({"lang": lang, "scope": "product", "error": str(e)})
                _log(logger, f"[i18n] {lang}: BLAD product translations: {e}")
                continue

        pushed.append(lang)

    # 3) Tlumaczenia opcji wariantow (Kolor/Rozmiar/Rodzaj drewna) i ich wartosci
    #    (Czarny/Brąz/Sosna/Dąb/M/L/XL/...). Statyczny slownik - bez LLM.
    try:
        opt_summary = push_option_translations(
            product_gid=product_gid,
            languages=list(translations.keys()) if translations else None,
            logger=logger,
        )
    except Exception as e:
        opt_summary = {"pushed": [], "errors": [str(e)]}
        _log(logger, f"[i18n] BLAD push tlumaczen opcji wariantow: {e}")

    return {
        "pushed": pushed,
        "skipped": [],
        "errors": errors,
        "options": opt_summary,
    }


def push_option_translations(
    *,
    product_gid: str,
    languages: list[str] | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Pushuje tlumaczenia nazw opcji wariantow (ProductOption) i ich wartosci
    (ProductOptionValue) na podane jezyki obce, korzystajac ze slownika
    `options_i18n.OPTION_NAME_TRANSLATIONS` / `OPTION_VALUE_TRANSLATIONS`.

    Wymaga scope: write_translations.

    languages: lista locali (np. ['en','de','fr','es','nl','it']); None = wszystkie obsl.
    """
    from .options_i18n import SUPPORTED_LANGS

    langs = [
        lg for lg in (languages or list(SUPPORTED_LANGS))
        if lg in SUPPORTED_LANGS
    ]
    if not langs:
        return {"pushed": [], "errors": []}

    shop, token = sc.load_session()
    options = sc.get_product_options_with_gids(shop, token, product_gid)
    if not options:
        _log(logger, "[i18n] Produkt nie ma opcji wariantow - pomijam tlumaczenia opcji.")
        return {"pushed": [], "errors": []}

    option_names_pl = [o.get("name") or "" for o in options]
    option_values_pl: list[str] = []
    for o in options:
        for v in (o.get("values") or []):
            n = (v or {}).get("name") or ""
            if n:
                option_values_pl.append(n)
    missing = find_missing_option_translations(option_names_pl, option_values_pl)
    if missing:
        for lg, items in missing.items():
            _log(
                logger,
                f"[i18n][opcje] BRAK tlumaczen w slowniku ({lg}): {items} "
                "-> dopisz do options_i18n.py",
            )

    pushed: list[str] = []
    errors: list[dict[str, str]] = []

    for lang in langs:
        # 3a) Tlumaczenie NAZW opcji (Kolor/Rozmiar/...)
        for opt in options:
            opt_gid = opt.get("id") or ""
            name_pl = opt.get("name") or ""
            translated = translate_option_name(name_pl, lang)
            if not opt_gid or not translated:
                continue
            try:
                sc.register_translations(
                    shop, token,
                    resource_gid=opt_gid,
                    locale=lang,
                    fields={"name": translated},
                )
            except sc.ShopifyError as e:
                errors.append({"lang": lang, "scope": f"option:{name_pl}", "error": str(e)})
                _log(logger, f"[i18n][opcje] {lang} '{name_pl}': BLAD: {e}")

        # 3b) Tlumaczenie WARTOSCI opcji (Czarny/Brąz/Sosna/Dąb/M/L/XL/...)
        for opt in options:
            for v in (opt.get("values") or []):
                v_gid = (v or {}).get("id") or ""
                v_pl = (v or {}).get("name") or ""
                translated_val = translate_option_value(v_pl, lang)
                if not v_gid or not translated_val:
                    continue
                try:
                    sc.register_translations(
                        shop, token,
                        resource_gid=v_gid,
                        locale=lang,
                        fields={"name": translated_val},
                    )
                except sc.ShopifyError as e:
                    errors.append({"lang": lang, "scope": f"value:{v_pl}", "error": str(e)})
                    _log(logger, f"[i18n][opcje] {lang} '{v_pl}': BLAD: {e}")

        pushed.append(lang)
        _log(
            logger,
            f"[i18n][opcje] {lang.upper()} ({LOCALE_DISPLAY.get(lang, lang)}): "
            f"opcje + wartosci wariantow zarejestrowane.",
        )

    return {"pushed": pushed, "errors": errors}


def ensure_smart_collections_from_tags(
    *,
    tags: list[str],
    logger: Logger | None = None,
    publish: bool = True,
) -> list[dict[str, Any]]:
    """Dla kazdego tagu z listy, ktory ma blueprint w tags_taxonomy.COLLECTION_RULES,
    znajduje istniejaca smart-collection (po handle/title) lub TWORZY nowa.

    Po utworzeniu - opcjonalnie publikuje na wszystkich kanalach i ustawia metapola SEO.
    Zwraca liste slownikow {'tag', 'id', 'handle', 'title', 'created'}.

    Idempotentne. Cache w pamieci sesji (proces) zeby nie spamowac API w petli batcha.
    """
    blueprints = collection_blueprints_for_tags(tags or [])
    if not blueprints:
        return []
    shop, token = sc.load_session()
    out: list[dict[str, Any]] = []
    for bp in blueprints:
        handle = bp["handle"]
        cached = _SMART_COLLECTION_CACHE.get(handle)
        if cached:
            out.append({**cached, "tag": bp["tag"], "created": False})
            continue
        try:
            coll, created = sc.upsert_smart_collection_for_tag(
                shop, token,
                title=bp["title"],
                handle=bp["handle"],
                tag=bp["tag"],
                body_html=bp.get("body_html"),
            )
        except sc.ShopifyError as e:
            _log(logger, f"[smart-coll] '{bp['title']}': BLAD - {e}")
            continue
        cid = int(coll.get("id") or 0)
        if not cid:
            _log(logger, f"[smart-coll] '{bp['title']}': brak id w odpowiedzi Shopify, pomijam.")
            continue
        record = {"id": cid, "handle": coll.get("handle") or handle, "title": coll.get("title") or bp["title"]}
        _SMART_COLLECTION_CACHE[record["handle"]] = record

        if created:
            _log(logger, f"[smart-coll] UTWORZONO id={cid} '{record['title']}' (rule: tag='{bp['tag']}').")
            try:
                sc.set_collection_seo_metafields(
                    shop, token, cid,
                    title_tag=bp["seo_title"], description_tag=bp["seo_description"],
                )
                _log(logger, f"[smart-coll] SEO metapola ustawione dla id={cid}.")
            except sc.ShopifyError as e:
                _log(logger, f"[smart-coll] SEO metapola id={cid}: {e}")
            if publish:
                try:
                    names = sc.publish_collection_everywhere(shop, token, sc.collection_gid(cid))
                    _log(
                        logger,
                        f"[smart-coll] Opublikowano kolekcje na kanalach: {', '.join(names) if names else '(brak)'}",
                    )
                except sc.ShopifyError as e:
                    _log(
                        logger,
                        f"[smart-coll] Publikacja kolekcji id={cid}: {e}\n"
                        "  -> Wymaga scope: write_publications.",
                    )
        else:
            _log(logger, f"[smart-coll] OK (istnieje) id={cid} '{record['title']}'.")
        out.append({**record, "tag": bp["tag"], "created": created})
    return out


def create_painting_product(
    *,
    image_path: Path,
    artist: str,
    title: str,
    llm_data: dict[str, Any],
    logger: Logger | None = None,
    template_id: str | None = None,
    image_role: str | None = None,
    base_title: str | None = None,
) -> dict[str, Any]:
    """Tworzy pelny produkt w Shopify. Zwraca podsumowanie.

    llm_data: dict z polami: tytul_polski, tytul_orginalny, akapity (list[3-4]),
              data_powstania, miejsce_powstania, technika, gatunek, nurt, forma,
              tagi (list[str]), kategoria.

    template_id: id szablonu wariantow (z `variant_templates.json`). Jesli None,
    uzywa szablonu domyslnego. Szablony sa snapshotem - nie pytamy Shopify.
    """
    polish_title = (llm_data.get("tytul_polski") or "").strip() or title
    original_title = (llm_data.get("tytul_orginalny") or "").strip() or title
    display_title = polish_title
    shop, token = sc.load_session()
    _log(logger, f"[shopify] Sesja: {shop}")

    # Wybierz szablon wariantow
    if template_id:
        template = variant_templates.get_by_id(template_id)
        if template is None:
            raise sc.ShopifyError(f"Szablon wariantow {template_id} nie istnieje.")
    else:
        template = variant_templates.get_default()
        if template is None:
            # Ostatnia szansa: sprobuj bootstrap
            template = variant_templates.bootstrap_default_if_missing(logger=logger)
        if template is None:
            raise sc.ShopifyError(
                "Brak szablonu wariantow. Otworz dialog 'Szablony...' i dodaj szablon."
            )

    options_payload, variants_payload = variant_templates.template_to_shopify_payload(template)
    _log(
        logger,
        f"[szablon] Uzywam szablonu '{template.name}' "
        f"({len(variants_payload)} wariantow, {len(options_payload)} opcji).",
    )

    coll_title = artist_collection_title(artist)
    _log(logger, f"[kolekcja] Szukam: '{coll_title}'...")
    collection = sc.find_artist_collection(shop, token, coll_title)
    if collection:
        _log(
            logger,
            f"[kolekcja] OK: id={collection['id']} kind={collection['kind']} "
            f"lifespan='{collection['lifespan']}'",
        )
    else:
        _log(logger, f"[kolekcja] NIE ZNALEZIONO '{coll_title}' - produkt powstanie bez przypisania.")

    lifespan = (collection or {}).get("lifespan") or ""

    body_html = build_body_html(
        tytul_obrazu=display_title,
        artysta=artist,
        data=lifespan,
        akapity=llm_data["akapity"],
        tytul_orginalny=original_title,
        data_powstania=llm_data["data_powstania"],
        miejsce_powstania=llm_data["miejsce_powstania"],
        technika=llm_data["technika"],
        gatunek=llm_data["gatunek"],
        nurt=llm_data["nurt"],
        forma=llm_data["forma"],
    )

    tags_list = [t.strip() for t in llm_data.get("tagi", []) if isinstance(t, str) and t.strip()]

    # Auto-tagi z analizy obrazu (PIL): orientacja + dominujacy kolor.
    # Te tagi sa dodawane do KAZDEGO produktu na podstawie samego pliku JPEG.
    try:
        analysis = analyze_image(image_path)
        for t in analysis["extra_tags"]:
            if t and t.lower() not in {x.lower() for x in tags_list}:
                tags_list.append(t)
        _log(
            logger,
            f"[analiza] {analysis['width']}x{analysis['height']} (aspect={analysis['aspect']:.2f}) "
            f"-> orientacja: {analysis['orientation_kind']}, kolor: {analysis['dominant_color_name']}.",
        )
    except Exception as e:
        _log(logger, f"[analiza] BLAD analizy obrazu (pomijam auto-tagi): {e}")

    base_for_key = (base_title or display_title).strip()
    source_key = compute_source_key(artist, base_for_key)
    src_tag = source_key_tag(source_key) if source_key else ""
    if src_tag and src_tag not in tags_list:
        tags_list.append(src_tag)
    tags_csv = ", ".join(tags_list)

    title_tag, meta_desc, handle = build_seo(
        tytul=display_title,
        artysta=artist,
        gatunek=llm_data.get("gatunek", ""),
        nurt=llm_data.get("nurt", ""),
    )
    if image_role == IMAGE_ROLE_FULL:
        image_alt = full_alt_text(artist, base_for_key)
    elif image_role == IMAGE_ROLE_PREVIEW:
        image_alt = preview_alt_text(artist, base_for_key)
    else:
        image_alt = build_image_alt(
            artysta=artist,
            tytul=display_title,
            gatunek=llm_data.get("gatunek", ""),
            nurt=llm_data.get("nurt", ""),
            technika=llm_data.get("technika", ""),
        )

    product_payload: dict[str, Any] = {
        "title": f"{artist} - {display_title}",
        "body_html": body_html,
        "vendor": VENDOR,
        "product_type": PRODUCT_TYPE,
        "status": "active",
        "handle": handle,
        "tags": tags_csv,
        "template_suffix": "",
        "options": options_payload or None,
        "variants": variants_payload or None,
    }
    product_payload = {k: v for k, v in product_payload.items() if v is not None}

    _log(logger, "[produkt] Tworze produkt w Shopify...")
    prod = sc.create_product(shop, token, product_payload)
    pid = int(prod.get("id"))
    _log(logger, f"[produkt] OK id={pid} handle={prod.get('handle')} source_key={source_key or '(brak)'}")

    _log(logger, f"[obraz] Wgrywam zdjecie: {image_path.name} (alt: '{image_alt}')")
    upload_pos = 1 if image_role == IMAGE_ROLE_FULL else None
    img = sc.upload_image(
        shop, token, pid, image_path, alt=image_alt, position=upload_pos, logger=logger
    )
    new_img_id = int(img.get("id") or 0)
    _log(logger, f"[obraz] OK image_id={new_img_id}")
    if image_role == IMAGE_ROLE_PREVIEW and new_img_id:
        try:
            sc.set_product_featured_image(shop, token, pid, new_img_id)
            _log(logger, "[obraz] Ustawiono (preview) jako zdjecie glowne (kolekcje/menu).")
        except sc.ShopifyError as e:
            _log(logger, f"[obraz] Nie ustawiono featured preview: {e}")
    elif image_role == IMAGE_ROLE_FULL and new_img_id:
        try:
            sc.set_image_position(shop, token, pid, new_img_id, 1)
        except sc.ShopifyError as e:
            _log(logger, f"[obraz] Nie ustawiono position=1 dla Full: {e}")

    _log(logger, "[seo] Metapola title_tag/description_tag...")
    sc.set_seo_metafields(shop, token, pid, title_tag=title_tag, description_tag=meta_desc)

    if source_key:
        try:
            sc.upsert_metafield(
                shop, token, pid,
                namespace="custom", key="source_key", value=source_key,
                ftype="single_line_text_field",
            )
            _log(logger, f"[meta] custom.source_key = '{source_key}'")
        except sc.ShopifyError as e:
            _log(logger, f"[meta] custom.source_key: {e}")

    kategoria = (llm_data.get("kategoria") or "").strip()
    if kategoria:
        _log(logger, f"[meta] custom.kategoria = '{kategoria}'")
        sc.set_custom_metafield(
            shop, token, pid,
            namespace="custom", key="kategoria", value=kategoria,
            ftype="single_line_text_field",
        )

    # Push tlumaczen na 6 jezykow (en/de/fr/es/nl/it). Wymaga scope: write_translations.
    translations_block = llm_data.get("tlumaczenia") or {}
    if translations_block:
        try:
            push_product_translations(
                product_id=pid,
                artist=artist,
                translations=translations_block,
                paragraphs_pl=llm_data.get("akapity"),
                original_title=original_title,
                data_powstania=llm_data.get("data_powstania", ""),
                miejsce_powstania=llm_data.get("miejsce_powstania", ""),
                technika=llm_data.get("technika", ""),
                gatunek=llm_data.get("gatunek", ""),
                nurt=llm_data.get("nurt", ""),
                forma=llm_data.get("forma", ""),
                lifespan=lifespan,
                logger=logger,
            )
        except Exception as e:
            _log(logger, f"[i18n] BLAD push tlumaczen: {e}")

    collection_assigned = False
    collection_assign_error: str | None = None
    if collection and collection.get("kind") == "custom":
        try:
            sc.add_to_collect(shop, token, pid, int(collection["id"]))
            collection_assigned = True
            _log(logger, f"[kolekcja] Dodano do custom collection id={collection['id']}.")
        except sc.ShopifyError as e:
            collection_assign_error = str(e)
            _log(logger, f"[kolekcja] Blad dodawania do kolekcji: {e}")
    elif collection and collection.get("kind") == "smart":
        _log(
            logger,
            "[kolekcja] Smart collection - produkt powinien sie dodac automatycznie na bazie regul (vendor/tagi).",
        )
        try:
            if sc.is_product_in_collection(
                shop,
                token,
                pid,
                int(collection["id"]),
                collection_kind="smart",
            ):
                collection_assigned = True
            else:
                collection_assign_error = "smart_rules_no_match"
        except sc.ShopifyError as e:
            collection_assign_error = str(e)
    elif not collection:
        collection_assign_error = "collection_not_found"

    # LAZY: tworzymy smart-collections (style/pomieszczenie/prezent/gatunek) na bazie tagow.
    # Idempotentne, cache w pamieci sesji - nie spamuje API w petli batcha.
    try:
        ensure_smart_collections_from_tags(tags=tags_list, logger=logger, publish=True)
    except Exception as e:
        _log(logger, f"[smart-coll] Niespodziewany blad upserrtu kolekcji: {e}")

    try:
        names = sc.publish_product_everywhere(shop, token, sc.product_gid(pid))
        _log(logger, f"[publikacje] Opublikowano na kanalach: {', '.join(names) if names else '(brak)'}")
    except sc.ShopifyError as e:
        _log(
            logger,
            f"[publikacje] Nie opublikowano na wszystkich kanalach (prawdopodobnie brak scope publications): {e}\n"
            "  -> Zaktualizuj .env: SCOPES=...,read_publications,write_publications i uruchom `npm run oauth`.",
        )

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{pid}"
    _log(logger, f"[gotowe] Produkt utworzony: {admin_url}")

    return {
        "product_id": pid,
        "handle": prod.get("handle"),
        "admin_url": admin_url,
        "artist": artist,
        "surname": surname_only(artist),
        "seo_title": title_tag,
        "seo_description": meta_desc,
        "lifespan": lifespan,
        "collection_id": (collection or {}).get("id"),
        "collection_kind": (collection or {}).get("kind"),
        "collection_title_expected": coll_title,
        "collection_assigned": collection_assigned,
        "collection_assign_error": collection_assign_error,
    }


class ProductNotFoundError(RuntimeError):
    """Bazowy produkt do dogrywania obrazu nie istnieje."""


def get_artist_products(artist: str, logger: Logger | None = None) -> list[dict[str, Any]]:
    """Zwraca liste produktow w kolekcji artysty (do recznego wskazania duplikatu).

    Pusta lista, jesli kolekcja artysty nie istnieje.
    """
    shop, token = sc.load_session()
    coll_title = artist_collection_title(artist)
    collection = sc.find_artist_collection(shop, token, coll_title)
    if not collection:
        _log(logger, f"[artist-products] Brak kolekcji '{coll_title}' - pomijam reczne wyszukiwanie.")
        return []
    try:
        return sc.iter_collection_products(shop, token, int(collection["id"]))
    except sc.ShopifyError as e:
        _log(logger, f"[artist-products] Blad pobierania kolekcji: {e}")
        return []


def find_existing_product_for_new(
    *,
    artist: str,
    filename_title: str,
    polish_title: str | None = None,
    logger: Logger | None = None,
) -> dict | None:
    """Zwraca produkt, jesli istnieje juz w Shopify, pasujacy do biezacego pliku.

    Kolejnosc dopasowania:
      1) po stabilnym kodzie zrodla ('src:<slug(artysta)>__<slug(tytul_bazowy)>') - tag.
      2) po tytule '{artist} - {filename_title}' i '{artist} - {polish_title}' (fallback).
    """
    shop, token = sc.load_session()

    base = (filename_title or "").strip()
    key = compute_source_key(artist, base)
    if key:
        tag = source_key_tag(key)
        try:
            matches = sc.find_products_by_tag(shop, token, tag)
        except sc.ShopifyError as e:
            _log(logger, f"[match] tag '{tag}': blad - {e}")
            matches = []
        if matches:
            _log(logger, f"[match] tag '{tag}' -> trafienie id={matches[0].get('id')}")
            return matches[0]
        _log(logger, f"[match] tag '{tag}' -> brak trafien, probuje po tytule...")

    tried: set[str] = set()
    for t in (base, polish_title):
        if not t:
            continue
        k = t.strip().lower()
        if k in tried:
            continue
        tried.add(k)
        prod = sc.find_product_by_title(shop, token, f"{artist} - {t}")
        if prod:
            _log(logger, f"[match] tytul '{artist} - {t}' -> trafienie id={prod.get('id')}")
            return prod
    _log(logger, "[match] nie znaleziono po kodzie ani po tytule.")
    return None


def _ensure_source_key(
    *,
    product: dict[str, Any],
    artist: str,
    base_title: str,
    logger: Logger | None = None,
) -> None:
    """Jezeli produkt nie ma jeszcze tagu src:<kod> / metapola custom.source_key - dopisuje je.

    'Lazy migration' - istniejace produkty dorabiaja sobie kod przy pierwszym kontakcie.
    """
    key = compute_source_key(artist, base_title)
    if not key:
        return
    tag = source_key_tag(key)

    raw_tags = product.get("tags") or ""
    tag_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
    has_any_src = any(t.startswith("src:") for t in tag_list)

    shop, token = sc.load_session()
    product_id = int(product["id"])

    if not has_any_src:
        tag_list.append(tag)
        try:
            sc.update_product(shop, token, product_id, {"tags": ", ".join(tag_list)})
            _log(logger, f"[backfill] Dopisano tag {tag} do produktu {product_id}.")
        except sc.ShopifyError as e:
            _log(logger, f"[backfill] Nie udalo sie dopisac tagu: {e}")

    try:
        existing_mf = sc.find_metafield(
            shop, token, product_id, namespace="custom", key="source_key"
        )
        if not existing_mf or (existing_mf.get("value") or "").strip() != key:
            sc.upsert_metafield(
                shop, token, product_id,
                namespace="custom", key="source_key", value=key,
                ftype="single_line_text_field",
            )
            _log(logger, f"[backfill] Ustawiono custom.source_key='{key}' na produkcie {product_id}.")
    except sc.ShopifyError as e:
        _log(logger, f"[backfill] custom.source_key: {e}")


def replace_primary_image(
    *,
    product_id: int,
    image_path: Path,
    artist: str,
    display_title: str,
    base_title: str | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Podmienia GLOWNE (position=1) zdjecie produktu na nowe.

    1) Pobiera istniejace zdjecia.
    2) Wgrywa nowe zdjecie (z position=1) jako nowe image_id.
    3) Ustawia pozycje 1 na nowym.
    4) Usuwa stare zdjecie, ktore bylo na pozycji 1.
    """
    shop, token = sc.load_session()
    _log(logger, f"[podmiana] Sesja: {shop}")

    try:
        prod = sc.get_product(shop, token, product_id)
    except sc.ShopifyError:
        prod = {"id": product_id, "tags": ""}
    _ensure_source_key(
        product=prod,
        artist=artist,
        base_title=(base_title or display_title),
        logger=logger,
    )

    existing = sc.list_product_images(shop, token, product_id)
    old_primary_id: int | None = None
    for img in existing:
        if int(img.get("position") or 0) == 1:
            old_primary_id = int(img["id"])
            break

    alt = build_image_alt(artysta=artist, tytul=display_title)
    _log(logger, f"[podmiana] Wgrywam nowe zdjecie glowne: {image_path.name} (alt: '{alt}')")
    img = sc.upload_image(shop, token, product_id, image_path, alt=alt, logger=logger)
    new_id = int(img.get("id"))
    try:
        sc.set_image_position(shop, token, product_id, new_id, 1)
        _log(logger, f"[podmiana] Ustawiono position=1 dla image_id={new_id}")
    except sc.ShopifyError as e:
        _log(logger, f"[podmiana] Nie udalo sie ustawic position=1: {e}")

    if old_primary_id and old_primary_id != new_id:
        try:
            sc.delete_product_image(shop, token, product_id, old_primary_id)
            _log(logger, f"[podmiana] Usunieto stare zdjecie glowne id={old_primary_id}")
        except sc.ShopifyError as e:
            _log(logger, f"[podmiana] Nie usunieto starego: {e}")

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    return {
        "product_id": product_id,
        "admin_url": admin_url,
        "image_id": new_id,
        "mode": "replace_image",
    }


def update_existing_product_content(
    *,
    product_id: int,
    image_path: Path,
    artist: str,
    title: str,
    llm_data: dict[str, Any],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Aktualizuje istniejacy produkt: nowy opis (body_html), tagi, SEO, kategoria + podmiana zdjecia glownego.

    NIE rusza: handle, vendor, product_type, wariantow, cen, kolekcji.
    """
    shop, token = sc.load_session()
    _log(logger, f"[update] Sesja: {shop}")

    prod = sc.get_product(shop, token, product_id)
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")

    _ensure_source_key(product=prod, artist=artist, base_title=title, logger=logger)

    polish_title = (llm_data.get("tytul_polski") or "").strip() or title
    original_title = (llm_data.get("tytul_orginalny") or "").strip() or title
    display_title = polish_title

    lifespan = ""
    coll_title = artist_collection_title(artist)
    collection = sc.find_artist_collection(shop, token, coll_title)
    if collection:
        lifespan = collection.get("lifespan") or ""

    body_html = build_body_html(
        tytul_obrazu=display_title,
        artysta=artist,
        data=lifespan,
        akapity=llm_data["akapity"],
        tytul_orginalny=original_title,
        data_powstania=llm_data["data_powstania"],
        miejsce_powstania=llm_data["miejsce_powstania"],
        technika=llm_data["technika"],
        gatunek=llm_data["gatunek"],
        nurt=llm_data["nurt"],
        forma=llm_data["forma"],
    )
    tags_list = [t.strip() for t in llm_data.get("tagi", []) if isinstance(t, str) and t.strip()]

    # Auto-tagi z analizy obrazu (PIL): orientacja + dominujacy kolor.
    try:
        analysis = analyze_image(image_path)
        for t in analysis["extra_tags"]:
            if t and t.lower() not in {x.lower() for x in tags_list}:
                tags_list.append(t)
        _log(
            logger,
            f"[update.analiza] {analysis['width']}x{analysis['height']} -> "
            f"orientacja: {analysis['orientation_kind']}, kolor: {analysis['dominant_color_name']}.",
        )
    except Exception as e:
        _log(logger, f"[update.analiza] BLAD analizy obrazu (pomijam auto-tagi): {e}")

    existing_tags = [t.strip() for t in (prod.get("tags") or "").split(",") if t.strip()]
    for t in existing_tags:
        if t.startswith("src:") and t not in tags_list:
            tags_list.append(t)
    key = compute_source_key(artist, title)
    if key:
        src_t = source_key_tag(key)
        if src_t not in tags_list:
            tags_list.append(src_t)
    tags_csv = ", ".join(tags_list)

    title_tag, meta_desc, _ = build_seo(
        tytul=display_title,
        artysta=artist,
        gatunek=llm_data.get("gatunek", ""),
        nurt=llm_data.get("nurt", ""),
    )

    new_title = f"{artist} - {display_title}"
    fields: dict[str, Any] = {
        "title": new_title,
        "body_html": body_html,
        "tags": tags_csv,
    }
    _log(logger, "[update] PUT /products/{id}.json (title, body_html, tags)...")
    sc.update_product(shop, token, product_id, fields)

    try:
        sc.upsert_metafield(
            shop, token, product_id,
            namespace="global", key="title_tag", value=title_tag, ftype="single_line_text_field",
        )
        sc.upsert_metafield(
            shop, token, product_id,
            namespace="global", key="description_tag", value=meta_desc, ftype="multi_line_text_field",
        )
        _log(logger, "[update] Zaktualizowano metapola SEO.")
    except sc.ShopifyError as e:
        _log(logger, f"[update] Metapola SEO: {e}")

    kategoria = (llm_data.get("kategoria") or "").strip()
    if kategoria:
        try:
            sc.upsert_metafield(
                shop, token, product_id,
                namespace="custom", key="kategoria", value=kategoria, ftype="single_line_text_field",
            )
            _log(logger, f"[update] custom.kategoria = '{kategoria}'")
        except sc.ShopifyError as e:
            _log(logger, f"[update] custom.kategoria: {e}")

    try:
        ensure_smart_collections_from_tags(tags=tags_list, logger=logger, publish=True)
    except Exception as e:
        _log(logger, f"[update] smart-coll: {e}")

    translations_block = llm_data.get("tlumaczenia") or {}
    if translations_block:
        try:
            push_product_translations(
                product_id=product_id,
                artist=artist,
                translations=translations_block,
                paragraphs_pl=llm_data.get("akapity"),
                original_title=original_title,
                data_powstania=llm_data.get("data_powstania", ""),
                miejsce_powstania=llm_data.get("miejsce_powstania", ""),
                technika=llm_data.get("technika", ""),
                gatunek=llm_data.get("gatunek", ""),
                nurt=llm_data.get("nurt", ""),
                forma=llm_data.get("forma", ""),
                lifespan=lifespan,
                logger=logger,
            )
        except Exception as e:
            _log(logger, f"[update.i18n] BLAD push tlumaczen: {e}")

    img_res = replace_primary_image(
        product_id=product_id,
        image_path=image_path,
        artist=artist,
        display_title=display_title,
        logger=logger,
    )

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    return {
        "product_id": product_id,
        "admin_url": admin_url,
        "image_id": img_res.get("image_id"),
        "mode": "replace_image_and_description",
    }


def audit_batch_collection_gaps(
    created: list[dict[str, Any]],
    *,
    logger: Logger | None = None,
) -> list[dict[str, Any]]:
    """Grupuje nowe produkty, ktore nie sa w kolekcji artysty (do poprawki nazwy kolekcji)."""
    try:
        shop, token = sc.load_session()
    except Exception as e:
        _log(logger, f"[kolekcja-audit] Pomijam (brak sesji Shopify): {e}")
        return []

    by_artist: dict[str, dict[str, Any]] = {}
    for row in created:
        mode = (row.get("mode") or "").strip()
        if mode in ("replace_image", "replace_image_and_description"):
            continue
        pid = row.get("product_id")
        artist = (row.get("artist") or "").strip()
        if not pid or not artist:
            continue
        expected = (row.get("collection_title_expected") or "").strip() or artist_collection_title(artist)
        coll_id = row.get("collection_id")
        coll_kind = row.get("collection_kind")
        in_coll = False
        if coll_id:
            try:
                in_coll = sc.is_product_in_collection(
                    shop,
                    token,
                    int(pid),
                    int(coll_id),
                    collection_kind=coll_kind,
                )
            except sc.ShopifyError as e:
                _log(logger, f"[kolekcja-audit] {row.get('file')}: {e}")
        if not in_coll:
            coll = sc.find_artist_collection(shop, token, expected)
            if coll:
                try:
                    in_coll = sc.is_product_in_collection(
                        shop,
                        token,
                        int(pid),
                        int(coll["id"]),
                        collection_kind=coll.get("kind"),
                    )
                except sc.ShopifyError:
                    pass
        if in_coll:
            continue
        grp = by_artist.setdefault(
            artist,
            {
                "artist": artist,
                "collection_title_default": expected,
                "products": [],
            },
        )
        grp["products"].append(
            {
                "product_id": int(pid),
                "file": row.get("file"),
                "admin_url": row.get("admin_url"),
                "reason": row.get("collection_assign_error") or "not_in_collection",
            }
        )
    out = list(by_artist.values())
    if out:
        total = sum(len(g["products"]) for g in out)
        _log(
            logger,
            f"[kolekcja-audit] {total} produkt(ow) poza kolekcja artysty — mozesz podac poprawna nazwe.",
        )
    return out


def assign_products_to_collection_title(
    *,
    collection_title: str,
    product_ids: list[int],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Przypisuje produkty do kolekcji custom po tytule (np. 'Monet, Claude')."""
    title = collection_title.strip()
    if not title:
        raise sc.ShopifyError("Pusta nazwa kolekcji.")
    shop, token = sc.load_session()
    from .collection_control import resolve_artist_collection_in_catalog

    catalog = sc.fetch_collection_catalog(shop, token)
    coll_meta = resolve_artist_collection_in_catalog(catalog, title)
    if coll_meta:
        coll = {
            "id": coll_meta["id"],
            "title": coll_meta["title"],
            "kind": coll_meta.get("kind") or "custom",
        }
    else:
        coll = sc.find_artist_collection(shop, token, title)
    if not coll:
        raise sc.ShopifyError(f"Nie znaleziono kolekcji o nazwie: {title!r}")
    cid = int(coll["id"])
    kind = (coll.get("kind") or "custom").strip().lower()
    added: list[int] = []
    already: list[int] = []
    failed: list[dict[str, Any]] = []
    for pid in product_ids:
        try:
            if sc.is_product_in_collection(shop, token, int(pid), cid, collection_kind=kind):
                already.append(int(pid))
                continue
            if kind == "custom":
                sc.add_to_collect(shop, token, int(pid), cid)
                added.append(int(pid))
                _log(logger, f"[kolekcja-fix] Dodano produkt id={pid} do '{title}'.")
            else:
                failed.append(
                    {
                        "product_id": int(pid),
                        "error": "Kolekcja smart — produkt musi spelniac reguly (tagi/vendor).",
                    }
                )
        except sc.ShopifyError as e:
            failed.append({"product_id": int(pid), "error": str(e)})
    return {
        "collection_id": cid,
        "collection_title": coll.get("title") or title,
        "collection_kind": kind,
        "added": added,
        "already": already,
        "failed": failed,
    }


def create_artist_collection_and_menu(
    *,
    collection_title: str,
    product_ids: list[int] | None = None,
    description: str | None = None,
    lifespan: str | None = None,
    portrait_path: "Path | str | None" = None,
    portrait_url: str | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Tworzy artyste "na wzor pozostalych": kolekcja custom + opis + zdjecie + menu + przypisanie.

    Krok po kroku:
      1. Znajduje lub tworzy custom-collection o tytule 'Nazwisko, Imie'.
      2. (jesli nowa) publikuje kolekcje na wszystkich kanalach (best-effort).
      3. Ustawia opis strony kolekcji (`body_html` jak u innych artystow):
         daty zycia (<h4>), okragly portret + akapity opisu. Portret jest
         wgrywany do Shopify Files (`portrait_path`). Nowej kolekcji ustawia
         tez wspolny baner (`image`).
      4. Dodaje pozycje do menu glownego pod 'ARTYŚCI' (wstawienie alfabetyczne).
      5. Przypisuje podane produkty do kolekcji (add_to_collect).

    Wymaga scope: write_products, write_publications, write_online_store_navigation,
    write_files (dla portretu). Zwraca dict z polami: collection_id, collection_title,
    created_collection, menu_added, menu_error, enrich_error, portrait_url, added,
    already, failed.
    """
    title = (collection_title or "").strip()
    if not title:
        raise sc.ShopifyError("Pusta nazwa artysty/kolekcji.")
    shop, token = sc.load_session()

    existing = sc.find_artist_collection(shop, token, title)
    if existing and (existing.get("kind") or "").lower() == "smart":
        raise sc.ShopifyError(
            f"'{title}' istnieje jako kolekcja SMART — nie tworze kolekcji custom artysty."
        )

    created_collection = False
    if existing:
        cid = int(existing["id"])
        _log(logger, f"[artysta] Kolekcja '{title}' juz istnieje (id={cid}).")
    else:
        created = sc.create_custom_collection(shop, token, title=title)
        cid = int(created.get("id") or 0)
        if not cid:
            raise sc.ShopifyError(f"Nie udalo sie utworzyc kolekcji '{title}'.")
        created_collection = True
        _log(logger, f"[artysta] Utworzono kolekcje custom '{title}' (id={cid}).")
        try:
            names = sc.publish_collection_everywhere(shop, token, sc.collection_gid(cid))
            _log(
                logger,
                f"[artysta] Opublikowano kolekcje na kanalach: "
                f"{', '.join(names) if names else '(brak)'}",
            )
        except sc.ShopifyError as e:
            _log(logger, f"[artysta] Publikacja kolekcji (pominieto): {e}")

    # Opis strony kolekcji + portret + baner (jak u pozostalych artystow).
    enrich_error: str | None = None
    resolved_portrait_url = (portrait_url or "").strip()
    want_body = bool(
        (description or "").strip()
        or portrait_path
        or resolved_portrait_url
        or (lifespan or "").strip()
    )
    try:
        if want_body:
            if portrait_path:
                _log(
                    logger,
                    f"[artysta] Wgrywam portret do Shopify Files: {Path(portrait_path).name}",
                )
                resolved_portrait_url = sc.upload_file_to_shopify_files(
                    Path(portrait_path), alt=title
                )
                _log(logger, f"[artysta] Portret (CDN): {resolved_portrait_url}")
            elif resolved_portrait_url:
                _log(logger, f"[artysta] Portret (gotowy CDN): {resolved_portrait_url}")
            body_html = build_artist_collection_body_html(
                title=title,
                description=description or "",
                lifespan=(lifespan or "").strip(),
                portrait_url=resolved_portrait_url,
            )
            sc.update_custom_collection(
                shop,
                token,
                cid,
                body_html=body_html,
                image_src=ARTIST_COLLECTION_BANNER_SRC if created_collection else None,
            )
            _log(
                logger,
                "[artysta] Zaktualizowano opis kolekcji"
                + (" + baner" if created_collection else "")
                + ".",
            )
        elif created_collection:
            sc.update_custom_collection(
                shop, token, cid, image_src=ARTIST_COLLECTION_BANNER_SRC
            )
            _log(logger, "[artysta] Ustawiono baner kolekcji.")
    except sc.ShopifyError as e:
        enrich_error = str(e)
        _log(logger, f"[artysta] Nie zaktualizowano opisu/zdjecia: {e}")

    menu_added = False
    menu_error: str | None = None
    try:
        res = sc.add_menu_child_collection(
            shop,
            token,
            parent_title=ARTIST_MENU_PARENT,
            child_title=title,
            collection_gid=sc.collection_gid(cid),
            menu_handle=ARTIST_MENU_HANDLE,
        )
        menu_added = bool(res.get("created"))
        if menu_added:
            _log(logger, f"[artysta] Dodano '{title}' do menu pod '{ARTIST_MENU_PARENT}'.")
        else:
            _log(logger, f"[artysta] '{title}' juz byl w menu pod '{ARTIST_MENU_PARENT}'.")
    except sc.ShopifyError as e:
        menu_error = str(e)
        _log(logger, f"[artysta] Menu (pominieto): {e}")

    added: list[int] = []
    already: list[int] = []
    failed: list[dict[str, Any]] = []
    for pid in product_ids or []:
        try:
            if sc.is_product_in_collection(
                shop, token, int(pid), cid, collection_kind="custom"
            ):
                already.append(int(pid))
                continue
            sc.add_to_collect(shop, token, int(pid), cid)
            added.append(int(pid))
            _log(logger, f"[artysta] Przypisano produkt id={pid} do '{title}'.")
        except sc.ShopifyError as e:
            failed.append({"product_id": int(pid), "error": str(e)})

    return {
        "collection_id": cid,
        "collection_title": title,
        "created_collection": created_collection,
        "menu_added": menu_added,
        "menu_error": menu_error,
        "enrich_error": enrich_error,
        "portrait_url": resolved_portrait_url,
        "added": added,
        "already": already,
        "failed": failed,
    }


def process_batch(
    *,
    items: list[dict[str, Any]],
    llm_items: list[dict[str, Any]] | None = None,
    logger: Logger | None = None,
    on_batch_progress: BatchProgress | None = None,
    on_product_ready: ProductReadyCallback | None = None,
) -> dict[str, Any]:
    """Przetwarza liste plikow (mieszanka: nowe produkty + dogrywki F2/F3).

    items: lista slownikow:
        {
          'path': Path,
          'artist': str,
          'title': str,              # raw z nazwy pliku
          'base_title': str,         # bez sufiksu F
          'follow_up_number': int|None,
          'title_is_polish': bool,
        }
    llm_items: lista slownikow zwrocona przez parse_batch_response_json (dla nowych produktow).
        Kazdy ma pole 'plik' do dopasowania po nazwie pliku.

    Kolejnosc: nowe produkty (LLM) -> (preview) -> (Full) bez LLM -> dogrywki F2+.
    Zwraca: { 'created': [...], 'followed_up': [...], 'errors': [{'file','error'}], 'skipped': [...] }.
    """
    llm_map: dict[str, dict[str, Any]] = {}
    for it in llm_items or []:
        key = (it.get("plik") or "").strip()
        if key:
            llm_map[key] = it

    preview_items = [
        it for it in items if it.get("image_role") == IMAGE_ROLE_PREVIEW
    ]
    new_items = dedupe_queue_items_by_work(
        [
            it
            for it in items
            if it.get("follow_up_number") is None
            and it.get("image_role")
            not in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_MOCKUP)
        ]
    )
    full_attach_items = [
        it
        for it in items
        if it.get("image_role") == IMAGE_ROLE_FULL
        and it.get("follow_up_number") is None
    ]
    followup_items = [
        it
        for it in items
        if it.get("follow_up_number") is not None or it.get("image_role") == IMAGE_ROLE_MOCKUP
    ]

    created: list[dict[str, Any]] = []
    followed_up: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    created_in_batch: set[str] = set()
    batch_done = 0
    batch_total = (
        len(new_items)
        + len(preview_items)
        + len(full_attach_items)
        + len(followup_items)
    )

    def _batch_tick(label: str) -> None:
        nonlocal batch_done
        batch_done += 1
        if on_batch_progress:
            on_batch_progress(batch_done, batch_total, label)

    def _ready(item: dict[str, Any], res: dict[str, Any]) -> None:
        if on_product_ready and res.get("product_id"):
            try:
                on_product_ready(item, res)
            except Exception:
                pass

    if new_items:
        _log(logger, f"\n[batch] Nowe produkty / podmiany: {len(new_items)} plik(ow)")
    for it in new_items:
        path = it["path"]
        fname = path.name
        action = (it.get("action") or "create").strip()
        existing_pid = it.get("existing_product_id")
        data = lookup_llm_entry(it, llm_map)

        if action == "skip":
            manual_pid = it.get("existing_product_id")
            role = it.get("image_role")
            if manual_pid and role == IMAGE_ROLE_FULL:
                try:
                    res = add_full_image(
                        image_path=path,
                        artist=it["artist"],
                        base_title=it["base_title"],
                        product_id=int(manual_pid),
                        logger=logger,
                    )
                    row = {"file": fname, **res, "follow_up_number": 0}
                    followed_up.append(row)
                    _ready(it, res)
                except Exception as e:
                    _log(logger, f"[batch] BLAD (full, reczne id) {fname}: {e}")
                    errors.append({"file": fname, "error": str(e)})
                _batch_tick(fname)
                continue
            if manual_pid and role == IMAGE_ROLE_PREVIEW:
                try:
                    res = add_preview_image(
                        image_path=path,
                        artist=it["artist"],
                        base_title=it["base_title"],
                        product_id=int(manual_pid),
                        logger=logger,
                    )
                    row = {"file": fname, **res}
                    followed_up.append(row)
                    _ready(it, res)
                except Exception as e:
                    _log(logger, f"[batch] BLAD (preview, reczne id) {fname}: {e}")
                    errors.append({"file": fname, "error": str(e)})
                _batch_tick(fname)
                continue
            _log(logger, f"[batch] POMINIETO {fname} (wybor uzytkownika).")
            skipped.append({"file": fname, "reason": "Uzytkownik wybral 'pomin'."})
            _batch_tick(fname)
            continue

        if action == "replace_image":
            if not existing_pid:
                _log(logger, f"[batch] BLAD {fname}: brak id istniejacego produktu do podmiany zdjecia.")
                errors.append({"file": fname, "error": "Brak id produktu do podmiany."})
                _batch_tick(fname)
                continue
            try:
                res = replace_primary_image(
                    product_id=int(existing_pid),
                    image_path=path,
                    artist=it["artist"],
                    display_title=it.get("base_title") or it["title"],
                    base_title=it.get("base_title") or it["title"],
                    logger=logger,
                )
                row = {"file": fname, "mode": "replace_image", **res, "follow_up_number": 0}
                followed_up.append(row)
                _ready(it, res)
            except Exception as e:
                _log(logger, f"[batch] BLAD (podmiana zdjecia) {fname}: {e}")
                errors.append({"file": fname, "error": str(e)})
            _batch_tick(fname)
            continue

        if action == "replace_image_and_description":
            if not existing_pid:
                _log(logger, f"[batch] BLAD {fname}: brak id istniejacego produktu do aktualizacji.")
                errors.append({"file": fname, "error": "Brak id produktu do aktualizacji."})
                _batch_tick(fname)
                continue
            if data is None:
                _log(
                    logger,
                    f"[batch] POMINIETO {fname}: akcja 'podmien obraz+opis' wymaga JSON-a z pola 'plik'.",
                )
                skipped.append({"file": fname, "reason": "Brak odpowiadajacego JSON dla 'obraz+opis'."})
                _batch_tick(fname)
                continue
            try:
                res = update_existing_product_content(
                    product_id=int(existing_pid),
                    image_path=path,
                    artist=it["artist"],
                    title=it["title"],
                    llm_data=data,
                    logger=logger,
                )
                row = {"file": fname, "mode": "replace_image_and_description", **res}
                created.append(row)
                _ready(it, res)
            except Exception as e:
                _log(logger, f"[batch] BLAD (podmiana obraz+opis) {fname}: {e}")
                errors.append({"file": fname, "error": str(e)})
            _batch_tick(fname)
            continue

        # action == "create" (default) lub "force_create"
        if data is None:
            _log(logger, f"[batch] POMINIETO {fname}: brak JSON-a dla tego pliku (pole 'plik').")
            skipped.append({"file": fname, "reason": "Brak odpowiadajacego obiektu JSON (pole 'plik')."})
            _batch_tick(fname)
            continue
        try:
            res = create_painting_product(
                image_path=path,
                artist=it["artist"],
                title=it["title"],
                llm_data=data,
                logger=logger,
                image_role=it.get("image_role"),
                base_title=it.get("base_title") or it["title"],
            )
            row = {"file": fname, **res}
            created.append(row)
            created_in_batch.add(fname)
            _ready(it, res)
        except Exception as e:
            _log(logger, f"[batch] BLAD (nowy) {fname}: {e}")
            errors.append({"file": fname, "error": str(e)})
        _batch_tick(fname)

    new_item_filenames = {it["path"].name for it in new_items}
    full_to_attach = [
        it
        for it in full_attach_items
        if it["path"].name not in created_in_batch
        and it["path"].name not in new_item_filenames
    ]
    if len(full_to_attach) != len(full_attach_items):
        batch_total = (
            len(new_items)
            + len(preview_items)
            + len(full_to_attach)
            + len(followup_items)
        )
        if on_batch_progress and batch_done <= batch_total:
            on_batch_progress(batch_done, batch_total, "")

    if preview_items:
        _log(logger, f"\n[batch] Podglad (preview): {len(preview_items)} plik(ow)")
    for it in preview_items:
        path = it["path"]
        try:
            res = add_preview_image(
                image_path=path,
                artist=it["artist"],
                base_title=it["base_title"],
                product_id=it.get("existing_product_id"),
                logger=logger,
            )
            row = {"file": path.name, **res}
            followed_up.append(row)
            _ready(it, res)
        except ProductNotFoundError as e:
            _log(logger, f"[batch] POMINIETO {path.name}: {e}")
            skipped.append({"file": path.name, "reason": str(e)})
        except Exception as e:
            _log(logger, f"[batch] BLAD (preview) {path.name}: {e}")
            errors.append({"file": path.name, "error": str(e)})
        _batch_tick(path.name)

    if full_to_attach:
        _log(logger, f"\n[batch] Full (dogrywka): {len(full_to_attach)} plik(ow)")
    for it in full_to_attach:
        path = it["path"]
        try:
            res = add_full_image(
                image_path=path,
                artist=it["artist"],
                base_title=it["base_title"],
                product_id=it.get("existing_product_id"),
                logger=logger,
            )
            row = {"file": path.name, **res}
            followed_up.append(row)
            _ready(it, res)
        except ProductNotFoundError as e:
            _log(logger, f"[batch] POMINIETO {path.name}: {e}")
            skipped.append({"file": path.name, "reason": str(e)})
        except Exception as e:
            _log(logger, f"[batch] BLAD (full) {path.name}: {e}")
            errors.append({"file": path.name, "error": str(e)})
        _batch_tick(path.name)

    if followup_items:
        _log(logger, f"\n[batch] Dogrywki F2+: {len(followup_items)} plik(ow)")
    for it in followup_items:
        path = it["path"]
        try:
            fkind = it.get("follow_up_kind") or FOLLOW_UP_KIND_F
            if it.get("image_role") == IMAGE_ROLE_MOCKUP:
                fkind = IMAGE_ROLE_MOCKUP
            res = add_follow_up_image(
                image_path=path,
                artist=it["artist"],
                base_title=it["base_title"],
                follow_up_number=int(it["follow_up_number"] or 0),
                follow_up_kind=fkind,
                product_id=it.get("existing_product_id"),
                logger=logger,
            )
            followed_up.append({"file": path.name, **res})
        except ProductNotFoundError as e:
            _log(logger, f"[batch] POMINIETO {path.name}: {e}")
            skipped.append({"file": path.name, "reason": str(e)})
        except Exception as e:
            _log(logger, f"[batch] BLAD (dogrywka) {path.name}: {e}")
            errors.append({"file": path.name, "error": str(e)})
        _batch_tick(path.name)

    if on_batch_progress and batch_total:
        on_batch_progress(batch_total, batch_total, "Gotowe")

    collection_gaps = audit_batch_collection_gaps(created, logger=logger)
    _log(
        logger,
        f"\n[batch] GOTOWE. Utworzono: {len(created)}, dograno: {len(followed_up)}, "
        f"pominieto: {len(skipped)}, bledow: {len(errors)}.",
    )
    return {
        "created": created,
        "followed_up": followed_up,
        "skipped": skipped,
        "errors": errors,
        "collection_gaps": collection_gaps,
    }


def _find_product_for_base(
    shop: str,
    token: str,
    artist: str,
    base_title: str,
    *,
    logger: Logger | None = None,
    log_prefix: str = "[obraz]",
) -> dict[str, Any]:
    """Szuka produktu po tagu src:... lub tytule '{artist} - {base_title}'."""
    key = compute_source_key(artist, base_title)
    prod: dict | None = None
    if key:
        _log(logger, f"{log_prefix} Szukam po kodzie: {source_key_tag(key)}")
        try:
            matches = sc.find_products_by_tag(shop, token, source_key_tag(key))
        except sc.ShopifyError:
            matches = []
        if matches:
            prod = matches[0]

    if not prod:
        target_title = f"{artist} - {base_title}"
        _log(logger, f"{log_prefix} Fallback po tytule: '{target_title}'")
        prod = sc.find_product_by_title(shop, token, target_title)

    if not prod:
        prod = _find_product_in_artist_collection(
            shop, token, artist, base_title, logger=logger, log_prefix=log_prefix
        )

    if not prod:
        tag_hint = source_key_tag(key) if key else "(brak kodu)"
        target_title = f"{artist} - {base_title}"
        raise ProductNotFoundError(
            f"Nie znaleziono produktu dla '{artist} - {base_title}'.\n"
            f"Szukany tag: {tag_hint}, tytul: '{target_title}'.\n"
            "Najpierw utworz produkt (plik Full + JSON) z TYM SAMYM tytulem bazowym w nazwie "
            "(np. «The Harvesters» w Full i w preview), potem wrzuc preview.\n"
            "Jesli produkt jest po polsku w sklepie, uzyj polskiego tytulu w obu nazwach plikow."
        )
    return prod


def _find_product_in_artist_collection(
    shop: str,
    token: str,
    artist: str,
    base_title: str,
    *,
    logger: Logger | None = None,
    log_prefix: str = "[match]",
) -> dict[str, Any] | None:
    """Fallback: produkt w kolekcji artysty po fragmencie handle / tagu src:...__<slug>."""
    base_slug = slugify(base_title)
    if not base_slug:
        return None
    try:
        products = get_artist_products(artist, logger=logger)
    except Exception:
        return None
    if not products:
        return None

    matches: list[dict[str, Any]] = []
    for p in products:
        handle = slugify(p.get("handle") or "")
        if handle.endswith(base_slug) or f"-{base_slug}" in handle:
            matches.append(p)
            continue
        for raw_tag in (p.get("tags") or "").split(","):
            tag = raw_tag.strip().lower()
            if tag.startswith("src:") and tag.endswith(f"__{base_slug}"):
                matches.append(p)
                break

    if len(matches) == 1:
        _log(
            logger,
            f"{log_prefix} Kolekcja artysty -> id={matches[0].get('id')} "
            f"(handle/tag pasuje do '{base_title}').",
        )
        return matches[0]
    if len(matches) > 1:
        _log(
            logger,
            f"{log_prefix} W kolekcji artysty jest {len(matches)} produktow pasujacych "
            f"do '{base_title}' — doprecyzuj tytul w nazwie pliku lub dodaj tag src:.",
        )
    return None


def _delete_images_matching(
    shop: str,
    token: str,
    product_id: int,
    *,
    predicate: Callable[[str | None], bool],
    logger: Logger | None = None,
) -> None:
    for im in sc.list_product_images(shop, token, product_id):
        if predicate(im.get("alt")):
            try:
                sc.delete_product_image(shop, token, product_id, int(im["id"]))
                _log(logger, f"[obraz] Usunieto stare id={im.get('id')} alt='{im.get('alt')}'")
            except sc.ShopifyError as e:
                _log(logger, f"[obraz] Nie usunieto id={im.get('id')}: {e}")


def _preview_image_id(images: list[dict]) -> int | None:
    for im in images:
        if alt_is_catalog_preview(im.get("alt")):
            try:
                return int(im["id"])
            except (TypeError, ValueError):
                continue
    return None


def _product_for_attach(
    shop: str,
    token: str,
    *,
    artist: str,
    base_title: str,
    product_id: int | None = None,
    logger: Logger | None = None,
    log_prefix: str = "[obraz]",
) -> dict[str, Any]:
    if product_id:
        prod = sc.get_product(shop, token, int(product_id))
        if not prod:
            raise ProductNotFoundError(f"Nie znaleziono produktu id={product_id}.")
        _log(logger, f"{log_prefix} Produkt reczny id={product_id} handle={prod.get('handle')}")
        return prod
    prod = _find_product_for_base(
        shop, token, artist, base_title, logger=logger, log_prefix=log_prefix
    )
    if not prod:
        raise ProductNotFoundError(
            f"Nie znaleziono produktu dla '{artist} - {base_title}'."
        )
    return prod


def add_preview_image(
    *,
    image_path: Path,
    artist: str,
    base_title: str,
    product_id: int | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Wgrywa (preview) — zdjecie glowne w kolekcjach/menu, ukryte w galerii PDP (motyw)."""
    shop, token = sc.load_session()
    _log(logger, f"[preview] Sesja: {shop}")
    prod = _product_for_attach(
        shop,
        token,
        artist=artist,
        base_title=base_title,
        product_id=product_id,
        logger=logger,
        log_prefix="[preview]",
    )
    pid = int(prod.get("id"))
    handle = prod.get("handle")
    _ensure_source_key(product=prod, artist=artist, base_title=base_title, logger=logger)

    _delete_images_matching(
        shop, token, pid, predicate=alt_is_catalog_preview, logger=logger
    )

    alt = preview_alt_text(artist, base_title)
    _log(logger, f"[preview] Wgrywam: {image_path.name} (alt: '{alt}')")
    img = sc.upload_image(shop, token, pid, image_path, alt=alt, position=2, logger=logger)
    new_id = int(img.get("id") or 0)
    if new_id:
        try:
            sc.set_product_featured_image(shop, token, pid, new_id)
            _log(logger, f"[preview] Ustawiono featured image_id={new_id}")
        except sc.ShopifyError as e:
            _log(logger, f"[preview] Nie ustawiono featured: {e}")

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{pid}"
    return {
        "product_id": pid,
        "handle": handle,
        "admin_url": admin_url,
        "image_id": new_id,
        "mode": "preview",
    }


def add_full_image(
    *,
    image_path: Path,
    artist: str,
    base_title: str,
    product_id: int | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Wgrywa (Full) — pierwsze w galerii PDP; featured zostaje (preview) jesli jest."""
    shop, token = sc.load_session()
    _log(logger, f"[full] Sesja: {shop}")
    prod = _product_for_attach(
        shop,
        token,
        artist=artist,
        base_title=base_title,
        product_id=product_id,
        logger=logger,
        log_prefix="[full]",
    )
    pid = int(prod.get("id"))
    handle = prod.get("handle")
    _ensure_source_key(product=prod, artist=artist, base_title=base_title, logger=logger)

    existing = sc.list_product_images(shop, token, pid)
    preview_id = _preview_image_id(existing)

    _delete_images_matching(
        shop, token, pid, predicate=alt_is_gallery_full, logger=logger
    )

    alt = full_alt_text(artist, base_title)
    _log(logger, f"[full] Wgrywam: {image_path.name} (alt: '{alt}')")
    img = sc.upload_image(shop, token, pid, image_path, alt=alt, position=1, logger=logger)
    new_id = int(img.get("id") or 0)
    if new_id:
        try:
            sc.set_image_position(shop, token, pid, new_id, 1)
        except sc.ShopifyError as e:
            _log(logger, f"[full] position=1: {e}")
        if preview_id:
            try:
                sc.set_product_featured_image(shop, token, pid, preview_id)
                _log(logger, f"[full] Featured pozostaje preview id={preview_id}")
            except sc.ShopifyError as e:
                _log(logger, f"[full] Nie przywrocono featured preview: {e}")

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{pid}"
    return {
        "product_id": pid,
        "handle": handle,
        "admin_url": admin_url,
        "image_id": new_id,
        "mode": "full",
    }


def add_follow_up_image(
    *,
    image_path: Path,
    artist: str,
    base_title: str,
    follow_up_number: int,
    follow_up_kind: str = FOLLOW_UP_KIND_F,
    mockup_name_suffix: str = "",
    product_id: int | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Dogrywa dodatkowe zdjecie do istniejacego produktu.

    follow_up_kind: 'F' (F2+), 'I' (I1, I2...), 'mockup' ((mockup) — widoczny w galerii PDP).
    """
    shop, token = sc.load_session()
    _log(logger, f"[shopify] Sesja: {shop}")

    prod = _product_for_attach(
        shop,
        token,
        artist=artist,
        base_title=base_title,
        product_id=product_id,
        logger=logger,
        log_prefix="[dogrywka]",
    )
    pid = int(prod.get("id"))
    handle = prod.get("handle")
    _log(logger, f"[dogrywka] OK baza: id={pid} handle={handle}")

    _ensure_source_key(product=prod, artist=artist, base_title=base_title, logger=logger)

    if follow_up_kind == IMAGE_ROLE_MOCKUP:
        alt = mockup_alt_text(artist, base_title, name_suffix=mockup_name_suffix)
        log_tag = "mockup"
    elif follow_up_kind == FOLLOW_UP_KIND_I:
        alt = installment_alt_text(artist, base_title, follow_up_number)
        log_tag = f"I{follow_up_number}"
    else:
        alt = f"{artist} - {base_title} (F{follow_up_number})"
        log_tag = f"F{follow_up_number}"
    _log(logger, f"[obraz] Dogrywam zdjecie {log_tag}: {image_path.name}")
    img = sc.upload_image(shop, token, pid, image_path, alt=alt, logger=logger)
    _log(logger, f"[obraz] OK image_id={img.get('id')}")

    try:
        total = sc.count_product_images(shop, token, pid)
        _log(logger, f"[dogrywka] Produkt ma teraz {total} zdjec.")
    except sc.ShopifyError:
        total = None

    admin_url = f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{pid}"
    return {
        "product_id": pid,
        "handle": handle,
        "admin_url": admin_url,
        "image_id": img.get("id"),
        "follow_up_number": follow_up_number,
        "follow_up_kind": follow_up_kind,
        "image_count": total,
        "mode": "follow_up" if follow_up_kind != IMAGE_ROLE_MOCKUP else "mockup",
    }


PRICE_DIALOG_SORT_ORDER = ("rodzaj drewna", "rozmiar", "kolor")

_SIZE_RANK = {
    "xxs": 0, "xs": 1, "s": 2, "m": 3, "l": 4, "xl": 5,
    "xxl": 6, "xxxl": 7, "3xl": 7, "4xl": 8, "5xl": 9,
}


def _size_sort_key(val: str) -> tuple[int, str]:
    v = (val or "").strip().lower()
    rank = _SIZE_RANK.get(v)
    if rank is not None:
        return (rank, v)
    return (999, v)


def _match_option_index(option_names: list[str], target: str) -> int | None:
    """Zwraca indeks (0-based) opcji, ktorej nazwa pasuje (case/diakrytyki-insensitive) do target.
    Pasuje tez fragmentem (np. 'rodzaj' znajdzie 'Rodzaj drewna')."""
    def norm(s: str) -> str:
        from .parser import _POLISH_MAP

        return (s or "").translate(_POLISH_MAP).strip().lower()

    tgt = norm(target)
    for i, name in enumerate(option_names):
        n = norm(name)
        if n == tgt or tgt in n or n in tgt:
            return i
    return None


def _variant_key_from_rest(v: dict[str, Any]) -> tuple[str, ...]:
    """Klucz dopasowania wariantu: tylko niepuste option1/2/3 (jak w szablonie)."""
    key_parts: list[str] = []
    for i in (1, 2, 3):
        val = v.get(f"option{i}")
        if val is not None and str(val).strip():
            key_parts.append(str(val).strip())
    return tuple(key_parts)


def _price_sort_key(p: str) -> tuple[int, float | str]:
    try:
        return (0, float(p.replace(",", ".").strip()))
    except ValueError:
        return (1, p)


def _fetch_live_prices_from_catalog(
    logger: Logger | None,
    *,
    product_type: str | None = PRODUCT_TYPE,
    on_catalog_progress: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[tuple[str, ...], str] | None:
    """Zbiera ceny wariantow ze wszystkich produktow danego typu (np. 'Obraz').

    Dla kazdego klucza (option1/2/3) zbiera unikalne ceny z calego katalogu.
    Gdy produkt referencyjny ze szablonu (shopify:ID) juz nie istnieje, nadal
    mamy poprawny podglad 'Obecna cena' w dialogu hurtowej zmiany.

    - Jedna unikalna cena w sklepie dla klucza -> wyswietlamy ja.
    - Wiecej niz jedna -> string 'rozne (N)' (jak w widoku grupowym GUI).
    """
    try:
        shop, token = sc.load_session()
    except (sc.ShopifyError, OSError, ValueError) as e:
        _log(logger, f"[ceny] Brak sesji — nie skanuje katalogu: {e}")
        return None

    _log(
        logger,
        f"[ceny] Skanuje ceny we wszystkich produktach (typ={product_type or 'dowolny'})...",
    )

    def _on_page(n: int) -> None:
        msg = f"[ceny] Pobrano {n} produktow ze sklepu (agregacja cen)..."
        _log(logger, msg)
        if on_catalog_progress:
            on_catalog_progress(msg)

    try:
        products = sc.fetch_all_products(
            shop,
            token,
            product_type=product_type,
            should_cancel=should_cancel,
            on_page_progress=_on_page,
        )
    except sc.OperationCancelled:
        _log(logger, "[ceny] Przerwano pobieranie katalogu — zostaja ceny z pliku szablonu.")
        return None
    except sc.ShopifyError as e:
        _log(logger, f"[ceny] Nie udalo sie pobrac katalogu: {e}")
        return None

    by_key: dict[tuple[str, ...], set[str]] = {}
    for prod in products:
        for v in prod.get("variants") or []:
            k = _variant_key_from_rest(v)
            if not k:
                continue
            raw = str(v.get("price") or "").strip()
            if not raw:
                continue
            by_key.setdefault(k, set()).add(raw)

    out: dict[tuple[str, ...], str] = {}
    for k, prices in by_key.items():
        uniq = sorted(prices, key=_price_sort_key)
        if len(uniq) == 1:
            out[k] = uniq[0]
        else:
            out[k] = f"rozne ({len(uniq)})"

    _log(
        logger,
        f"[ceny] Obecna cena = agregacja ze sklepu ({len(products)} prod., "
        f"{len(by_key)} roznych kluczy wariantow).",
    )
    return out


def get_reference_variant_rows(
    logger: Logger | None = None,
    *,
    template_id: str | None = None,
    on_catalog_progress: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[dict[str, Any]]:
    """Zwraca liste wariantow z lokalnego szablonu z polami:
      'key'    - krotka wartosci (option1, option2, option3) (do matchingu)
      'label'  - string 'Rodzaj drewna / Rozmiar / Kolor' w kolejnosci wyswietlania
      'price'  - obecna cena (string): **nadpisywana** przez agregacje cen z calego
                 katalogu produktow danego typu (domyslnie 'Obraz'); przy jednej
                 cenie dla klucza — ta cena, przy roznych — 'rozne (N)'. Jesli skan
                 sie nie uda, zostaje cena z pliku szablonu.

    Wiersze sa POSORTOWANE wedlug priorytetu: Rodzaj drewna -> Rozmiar -> Kolor.

    `template_id`: id szablonu (jesli None, uzywa domyslnego).
    """
    if template_id:
        template = variant_templates.get_by_id(template_id)
    else:
        template = variant_templates.get_default()
        if template is None:
            template = variant_templates.bootstrap_default_if_missing(logger=logger)
    if template is None:
        raise sc.ShopifyError(
            "Brak szablonu wariantow. Otworz 'Szablony...' aby dodac szablon."
        )

    _log(logger, f"[szablon] Pobieram warianty z szablonu '{template.name}'.")

    option_names = [(o.get("name") or "").strip() for o in template.options]
    while len(option_names) < 3:
        option_names.append("")

    display_order_idx: list[int] = []
    used: set[int] = set()
    for target in PRICE_DIALOG_SORT_ORDER:
        idx = _match_option_index(option_names, target)
        if idx is not None and idx not in used:
            display_order_idx.append(idx)
            used.add(idx)
    for i in range(len(option_names)):
        if i not in used and option_names[i]:
            display_order_idx.append(i)
            used.add(i)

    display_is_size = [
        "rozmiar" in (option_names[i] or "").lower() or "size" in (option_names[i] or "").lower()
        for i in display_order_idx
    ]

    rows: list[dict[str, Any]] = []
    for v_idx, v in enumerate(template.variants):
        key_parts: list[str] = []
        for i in (1, 2, 3):
            val = v.get(f"option{i}")
            if val is not None and str(val).strip():
                key_parts.append(str(val).strip())
        values = [v.get(f"option{i + 1}") for i in range(len(option_names))]
        display_parts = [
            str(values[i] or "").strip()
            for i in display_order_idx
            if i < len(values) and values[i] is not None
        ]
        sort_tuple: list[Any] = []
        for col_pos, opt_idx in enumerate(display_order_idx):
            raw = str(values[opt_idx] or "")
            if display_is_size[col_pos]:
                sort_tuple.append(_size_sort_key(raw))
            else:
                sort_tuple.append((0, raw.lower()))
        rows.append(
            {
                "key": tuple(key_parts),
                "label": " / ".join(display_parts) if display_parts else f"Wariant {v_idx + 1}",
                "price": str(v.get("price") or ""),
                "_sort": tuple(sort_tuple),
            }
        )

    rows.sort(key=lambda r: r["_sort"])
    for r in rows:
        r.pop("_sort", None)

    live_prices = _fetch_live_prices_from_catalog(
        logger,
        product_type=PRODUCT_TYPE,
        on_catalog_progress=on_catalog_progress,
        should_cancel=should_cancel,
    )
    if live_prices:
        for r in rows:
            k = r["key"]
            if k in live_prices:
                r["price"] = live_prices[k]

    return rows


def update_all_product_prices(
    *,
    option_values_to_price: dict[tuple[str, ...], str],
    product_type: str | None = PRODUCT_TYPE,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Aktualizuje ceny wszystkich wariantow pasujacych do mapy option_values -> price.

    Klucz: krotka wartosci option1/option2/option3 (pomija None). np. ('50x70', 'Papier').
    Wartosc: cena jako string ('129.00').

    Iteruje po wszystkich produktach (optional filter product_type).
    """
    shop, token = sc.load_session()
    _log(logger, f"[shopify] Sesja: {shop}")
    _log(logger, f"[ceny] Pobieram wszystkie produkty (typ={product_type or 'dowolny'})...")
    if on_progress:
        on_progress("Ladowanie katalogu produktow...")

    def _on_page(n: int) -> None:
        _log(logger, f"[ceny] Pobrano {n} produktow...")
        if on_progress:
            on_progress(f"Ladowanie katalogu: {n} produktow...")

    try:
        products = sc.fetch_all_products(
            shop,
            token,
            product_type=product_type,
            should_cancel=should_cancel,
            on_page_progress=_on_page,
        )
    except sc.OperationCancelled:
        _log(logger, "[ceny] Przerwano podczas pobierania katalogu.")
        raise

    _log(logger, f"[ceny] Znaleziono {len(products)} produktow.")

    updated = 0
    skipped = 0
    errors: list[str] = []
    p_total = len(products)
    for pi, prod in enumerate(products):
        if should_cancel and should_cancel():
            raise sc.OperationCancelled("Przerwano aktualizacje cen.")
        if on_progress and p_total and (pi % 3 == 0 or pi == p_total - 1):
            on_progress(f"Aktualizacja cen: produkt {pi + 1}/{p_total}...")
        ptitle = prod.get("title") or f"id={prod.get('id')}"
        for v in prod.get("variants") or []:
            key = tuple(
                (v.get(f"option{i}") or "").strip()
                for i in (1, 2, 3)
                if v.get(f"option{i}") is not None
            )
            new_price = option_values_to_price.get(key)
            if new_price is None:
                skipped += 1
                continue
            current = str(v.get("price") or "")
            if current == str(new_price):
                skipped += 1
                continue
            try:
                sc.update_variant_price(shop, token, int(v["id"]), str(new_price))
                updated += 1
                _log(logger, f"[ceny] OK {ptitle} / {' / '.join(key)} -> {new_price}")
            except sc.ShopifyError as e:
                errors.append(f"{ptitle} ({key}): {e}")
                _log(logger, f"[ceny] BLAD {ptitle} / {' / '.join(key)}: {e}")

    _log(logger, f"[ceny] Gotowe. Zaktualizowano: {updated}, pominieto: {skipped}, bledow: {len(errors)}.")
    return {
        "products_total": len(products),
        "variants_updated": updated,
        "variants_skipped": skipped,
        "errors": errors,
    }


def _split_artist_title(product_title: str, vendor: str | None) -> tuple[str, str]:
    """Z tytulu produktu Shopify wyciaga artyste i tytul obrazu.

    Tytul produktu w sklepie ma format 'Artysta - Tytul'. Jezeli separatora nie ma
    - jako artyste bierzemy 'vendor' (jesli != 'Giclee Art'), a tytul = caly napis.
    """
    raw = (product_title or "").strip()
    for sep in (" - ", " \u2013 ", " \u2014 "):
        if sep in raw:
            left, right = raw.split(sep, 1)
            return left.strip(), right.strip()
    fallback_artist = (vendor or "").strip()
    if fallback_artist.lower() in ("", "giclee art", "giclée art"):
        fallback_artist = ""
    return fallback_artist, raw


def _filename_from_image(image: dict | None) -> str:
    """Wyciaga z obiektu 'image' nazwe pliku (bez query / hashy CDN Shopify)."""
    if not image:
        return ""
    src = (image.get("src") or "").strip()
    if not src:
        return ""
    tail = src.rsplit("/", 1)[-1]
    tail = tail.split("?", 1)[0]
    return tail


def get_main_image_listing(
    *,
    product_type: str | None = PRODUCT_TYPE,
    logger: Logger | None = None,
) -> list[dict[str, Any]]:
    """Zwraca zestawienie 'glowne zdjecie' dla kazdego produktu (typ='Obraz').

    Kazdy element: {
      'id': int,
      'product_title': str,
      'artist': str,        # 'Hans Dahl' (z tytulu produktu, fallback: vendor)
      'surname': str,       # 'Dahl'
      'firstname': str,     # 'Hans'
      'painting_title': str,  # 'Babie lato'
      'main_image_filename': str,  # 'hans-dahl-babie-lato.jpg'
      'handle': str,
      'vendor': str,
    }
    """
    shop, token = sc.load_session()
    _log(logger, f"[shopify] Sesja: {shop}")
    _log(logger, f"[zestawienie] Pobieram produkty (typ={product_type or 'dowolny'})...")
    products = sc.iter_all_products(
        shop,
        token,
        product_type=product_type,
        fields="id,title,handle,vendor,image,product_type",
    )
    _log(logger, f"[zestawienie] Pobrano {len(products)} produktow.")

    rows: list[dict[str, Any]] = []
    for prod in products:
        artist, painting_title = _split_artist_title(prod.get("title") or "", prod.get("vendor"))
        parts = artist.split()
        surname = parts[-1] if parts else ""
        firstname = " ".join(parts[:-1]) if len(parts) > 1 else ""
        rows.append(
            {
                "id": int(prod.get("id") or 0),
                "product_title": (prod.get("title") or "").strip(),
                "artist": artist,
                "surname": surname,
                "firstname": firstname,
                "painting_title": painting_title,
                "main_image_filename": _filename_from_image(prod.get("image")),
                "handle": (prod.get("handle") or "").strip(),
                "vendor": (prod.get("vendor") or "").strip(),
            }
        )
    rows.sort(key=lambda r: ((r["surname"] or "\uffff").lower(), (r["firstname"] or "").lower()))
    return rows
