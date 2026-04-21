"""Buildery promptow dla Generatora tresci social media + parser odpowiedzi.

Dwa warianty promptow (jak w blog):
- Opus (Claude) - luzniejsze, code fence ```json.
- GPT - twardsze rygory: zwroc WYLACZNIE JSON, bez tekstu dokleonego.

Tryby:
- single: jeden post.
- series: seria N postow na ten sam temat rozlozonych w czasie.

Format odpowiedzi single:
{
  "platform": "ig_feed",
  "language": "pl",
  "topic": "...",
  "post": {
    "title": "",                 // Pinterest / opcjonalne
    "caption": "glowny tekst",
    "on_screen_text": ["..."],   // Reels/TikTok
    "hashtags": ["#foo", "#bar"],
    "image_hint": "sugestia co pokazac na zdjeciu/video",
    "link": "",                  // URL docelowy (opcjonalnie)
    "music_hint": ""             // Reels/TikTok
  }
}

Format odpowiedzi series:
{
  "platform": "ig_feed",
  "language": "pl",
  "topic": "...",
  "series_meta": {
    "arc": "Krótki opis luku narracyjnego 3-5 postów",
    "cadence": "co 2 dni" | "codziennie przez tydzien" itp.
  },
  "posts": [ { ...struktura jak post single... }, ... ]
}
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import hashtag_library, platforms

SHOP_CONTEXT = """\
Sklep: GicleeArt (gicleeart.eu) - wydruki giclee na plotnie.
Dwie galezie produktu:

1) REPRODUKCJE KLASYKOW MALARSTWA (Monet, Van Gogh, Vermeer, Klimt, polscy kolorysci itd.)
   drukowane w wysokiej jakosci na plotnie giclee. Grupa: milosnicy sztuki, dekoracja
   wnetrz (klasyka, boho, skandynawski, glamour), prezenty.

2) CUSTOM PRINT - wydruk z wlasnego zdjecia klienta. Klient wgrywa zdjecie
   (rodzinne, slubne, portret, sesja, krajobraz, logo, zdjecie produktowe) przez
   edytor na stronie, sam dopasowuje kadr w live mockupie (podglad na scianie),
   wybiera rozmiar, drukujemy giclee. Grupa: klienci indywidualni (prezenty,
   sesje rodzinne/slubne, pamiatki z podrozy), fotografowie, male firmy.

Ton marki: elegancki, ciepy, merytoryczny, subtelnie aspiracyjny, bez napuszenia
i tard sellu. Uzywamy klasycznej estetyki - plotno, swiatlo, faktura, detal.
"""


# ---------------------------------------------------------------------------
# Generator tresci - single post
# ---------------------------------------------------------------------------

def build_post_prompt_opus(
    *,
    topic: str,
    platform_code: str,
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_post_prompt(
        topic=topic,
        platform_code=platform_code,
        language=language,
        extra_hint=extra_hint,
        link=link,
        variant="opus",
    )


def build_post_prompt_gpt(
    *,
    topic: str,
    platform_code: str,
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_post_prompt(
        topic=topic,
        platform_code=platform_code,
        language=language,
        extra_hint=extra_hint,
        link=link,
        variant="gpt",
    )


def _build_post_prompt(
    *,
    topic: str,
    platform_code: str,
    language: str,
    extra_hint: str,
    link: str,
    variant: str,
) -> str:
    p = platforms.get(platform_code)
    if p is None:
        raise ValueError(f"Nieznana platforma: {platform_code}")

    lang_label = platforms.lang_label(language)
    locked = hashtag_library.locked_for(language)
    suggested = hashtag_library.suggested_for(language)

    hint_block = f"\nDODATKOWY KONTEKST OD UZYTKOWNIKA:\n{extra_hint.strip()}\n" if extra_hint.strip() else ""
    link_block = f"\nLINK DOCELOWY (do wkleczenia w CTA tam gdzie ma sens): {link.strip()}\n" if link.strip() else ""

    format_json = """\
{
  "platform": "%PLATFORM%",
  "language": "%LANG%",
  "topic": "%TOPIC%",
  "post": {
    "title": "",
    "caption": "",
    "on_screen_text": [],
    "hashtags": [],
    "image_hint": "",
    "link": "",
    "music_hint": ""
  }
}
"""
    format_json = (
        format_json.replace("%PLATFORM%", p.code)
        .replace("%LANG%", language)
        .replace("%TOPIC%", topic.replace('"', "'"))
    )

    variant_note = _variant_note(variant)

    return f"""\
Jestes copywriterem social media specjalizujacym sie w sztuce, fotografii i dekoracji wnetrz.
Piszesz DLA JEDNEGO POSTA na platformie **{p.label}** w jezyku **{lang_label}** dla sklepu GicleeArt.

{SHOP_CONTEXT}

TEMAT POSTA:
"{topic}"
{hint_block}{link_block}
PLATFORMA: {p.label}
- Caption limit znakow: {p.caption_limit}
- Rekomendowana liczba slow: {p.recommended_words[0]}-{p.recommended_words[1]}
- Rekomendowana liczba hashtagow: {p.recommended_hashtags} (limit platformy: {p.hashtag_limit})
- Format zdjecia/video: {p.format_hint}
- Ton: {p.tone}
- Struktura: {p.structure}

HASHTAGI:
- STALE hashtagi marki (dolacz je ZAWSZE na koncu): {' '.join(locked) if locked else '(brak - platforma nie uzywa hashtagow)'}
- Propozycje tematyczne do wyboru (wybierz ~5-8 pasujacych do tematu): {' '.join(suggested[:12])}
- Dodaj jeszcze 3-5 wlasnych niszowych hashtagow dopasowanych do TEMATU.
- Dla Pinterest: NIE uzywaj hashtagow - zwroc pusta liste `hashtags: []`, a slowa kluczowe wplec do `caption` i `title`.

CO WYGENEROWAC:
1. `title`: tylko dla Pinterest (100 znakow, keyword-rich). Dla innych platform zostaw pusty string.
2. `caption`: glowny tekst posta w jezyku **{lang_label}**. Trzymaj sie struktury platformy.
3. `on_screen_text`: TYLKO dla Instagram Reels i TikTok - 2-4 krotkie napisy do nalozenia na video.
   Dla innych platform zostaw pusta liste.
4. `hashtags`: lista hashtagow (Pinterest: pusta). Kazdy element zaczyna sie od '#'.
5. `image_hint`: jedno zdanie opisujace co powinno byc na zdjeciu/video (kompozycja, styl, kolorystyka).
6. `link`: jesli uzytkownik podal LINK DOCELOWY - wpisz go tu; inaczej pusty string.
7. `music_hint`: TYLKO dla Reels/TikTok - opisz rodzaj muzyki lub zaproponuj trend (np. 'spokojna fortepianowa melodia', 'aktualny trend lofi').

WAZNE:
- Pisz w jezyku **{lang_label}** - caly caption, on_screen_text, image_hint MUSZA byc w tym jezyku.
- Hashtagi w odpowiednim jezyku (polskie dla pl, angielskie dla en).
- NIE kopiuj dokladnie formulek - brzmij naturalnie, jakby pisal native copywriter.
- NIE stosuj twardego sellu - ton ma byc inspirujacy / edukujacy / emocjonalny.

{variant_note}
FORMAT ODPOWIEDZI - JSON:
{format_json}
"""


# ---------------------------------------------------------------------------
# Generator tresci - MULTI PLATFORM (jeden prompt -> N wersji postow)
# ---------------------------------------------------------------------------

def build_multi_post_prompt_opus(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_multi_post_prompt(
        topic=topic, platform_codes=platform_codes, language=language,
        extra_hint=extra_hint, link=link, variant="opus",
    )


def build_multi_post_prompt_gpt(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_multi_post_prompt(
        topic=topic, platform_codes=platform_codes, language=language,
        extra_hint=extra_hint, link=link, variant="gpt",
    )


def _build_multi_post_prompt(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str,
    link: str,
    variant: str,
) -> str:
    active: list[platforms.Platform] = []
    for code in platform_codes:
        p = platforms.get(code)
        if p is None:
            raise ValueError(f"Nieznana platforma: {code}")
        active.append(p)
    if not active:
        raise ValueError("Nie wybrano zadnej platformy.")

    lang_label = platforms.lang_label(language)
    locked = hashtag_library.locked_for(language)
    suggested = hashtag_library.suggested_for(language)

    hint_block = f"\nDODATKOWY KONTEKST OD UZYTKOWNIKA:\n{extra_hint.strip()}\n" if extra_hint.strip() else ""
    link_block = f"\nLINK DOCELOWY: {link.strip()}\n" if link.strip() else ""

    # Per-platforma guidelines
    plat_section = "\n".join(
        f"### {p.icon} {p.label} (`{p.code}`):\n"
        f"- Caption limit: {p.caption_limit} znakow, rekomendowane {p.recommended_words[0]}-{p.recommended_words[1]} slow.\n"
        f"- Hashtagi: ~{p.recommended_hashtags} (limit: {p.hashtag_limit}).\n"
        f"- Format: {p.format_hint}\n"
        f"- Ton: {p.tone}\n"
        f"- Struktura: {p.structure}"
        for p in active
    )

    # JSON skeleton
    platforms_skeleton = ",\n    ".join(
        f'"{p.code}": {{"post": {{"title": "", "caption": "", "on_screen_text": [], "hashtags": [], "image_hint": "", "link": "", "music_hint": ""}}}}'
        for p in active
    )
    codes_csv = ", ".join(p.code for p in active)

    variant_note = _variant_note(variant)

    return f"""\
Jestes copywriterem social media specjalizujacym sie w sztuce, fotografii i dekoracji wnetrz.
Piszesz {len(active)} WERSJE jednego posta - kazda dla innej platformy - w jezyku **{lang_label}**
dla sklepu GicleeArt. Platformy: {codes_csv}.

{SHOP_CONTEXT}

TEMAT:
"{topic}"
{hint_block}{link_block}
WYBRANE PLATFORMY - kazda ma swoje reguly (dostosuj tresc ODDZIELNIE!):

{plat_section}

WSPOLNE ZASADY DLA WSZYSTKICH WERSJI:
- Wszystkie posty dotycza tego samego tematu, ale sa napisane OSOBNO (nie kopiuj caption miedzy platformami!).
- IG Feed moze miec inspirujacy dluzszy caption; IG Stories bardzo krotki; Reels/TikTok scenariusz + on-screen.
- Pinterest: brak hashtagow (pusta lista), keywords w title + caption.
- Stale hashtagi marki (dolacz na koncu caption tam gdzie platforma ich uzywa): {' '.join(locked) if locked else '(brak)'}.
- Tematyczne hashtagi do wyboru: {' '.join(suggested[:12])} + wlasne niszowe.

CO WYGENEROWAC DLA KAZDEJ PLATFORMY:
1. `title`: tylko Pinterest (100 znakow, keyword-rich). Dla reszty pusty string.
2. `caption`: glowny tekst w jezyku **{lang_label}** dostosowany do platformy.
3. `on_screen_text`: TYLKO dla ig_reels i tiktok (2-4 krotkie napisy).
4. `hashtags`: lista (Pinterest: pusta). Kazdy element zaczyna sie od '#'.
5. `image_hint`: jedno zdanie opisujace co ma byc na zdjeciu/video.
6. `link`: jesli uzytkownik podal URL - umiesc go; inaczej pusty string.
7. `music_hint`: TYLKO reels/tiktok (opis/propozycja dzwieku).

{variant_note}

FORMAT ODPOWIEDZI - JSON:
{{
  "language": "{language}",
  "topic": "{topic.replace('"', chr(39))}",
  "platforms": {{
    {platforms_skeleton}
  }}
}}
"""


def parse_multi_post_response(raw: str) -> dict[str, Any]:
    """Parsuje odpowiedz multi-platform. Zwraca {language, topic, platforms: {code: {post: {...}}}}."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Odpowiedz nie jest obiektem JSON.")
    plats = data.get("platforms")
    if not isinstance(plats, dict) or not plats:
        raise ValueError("Brak pola 'platforms' w odpowiedzi (dict).")
    out_platforms: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for code, entry in plats.items():
        if not isinstance(entry, dict):
            errors.append(f"platform '{code}': nie jest obiektem")
            continue
        post_obj = entry.get("post") or entry  # niektore LLM zwracaja post bezposrednio
        try:
            out_platforms[str(code)] = {"post": _validate_post_obj(post_obj)}
        except ValueError as e:
            errors.append(f"platform '{code}': {e}")
    if not out_platforms:
        raise ValueError("Zadna platforma nie ma poprawnego posta: " + "; ".join(errors))
    return {
        "language": str(data.get("language") or "").strip(),
        "topic": str(data.get("topic") or "").strip(),
        "platforms": out_platforms,
    }


# ---------------------------------------------------------------------------
# Generator tresci - seria postow
# ---------------------------------------------------------------------------

def build_series_prompt_opus(
    *,
    topic: str,
    platform_code: str,
    language: str,
    count: int = 5,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_series_prompt(
        topic=topic,
        platform_code=platform_code,
        language=language,
        count=count,
        extra_hint=extra_hint,
        link=link,
        variant="opus",
    )


def build_series_prompt_gpt(
    *,
    topic: str,
    platform_code: str,
    language: str,
    count: int = 5,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_series_prompt(
        topic=topic,
        platform_code=platform_code,
        language=language,
        count=count,
        extra_hint=extra_hint,
        link=link,
        variant="gpt",
    )


# ---------------------------------------------------------------------------
# Generator tresci - multi-platform (jeden temat, N platform)
# ---------------------------------------------------------------------------

def build_multi_platform_prompt_opus(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_multi_platform_prompt(
        topic=topic,
        platform_codes=platform_codes,
        language=language,
        extra_hint=extra_hint,
        link=link,
        variant="opus",
    )


def build_multi_platform_prompt_gpt(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str = "",
    link: str = "",
) -> str:
    return _build_multi_platform_prompt(
        topic=topic,
        platform_codes=platform_codes,
        language=language,
        extra_hint=extra_hint,
        link=link,
        variant="gpt",
    )


def _build_multi_platform_prompt(
    *,
    topic: str,
    platform_codes: list[str],
    language: str,
    extra_hint: str,
    link: str,
    variant: str,
) -> str:
    """Prompt generujacy ten sam temat zaadaptowany na kilka platform jednoczesnie."""
    plats: list[platforms.Platform] = []
    for code in platform_codes:
        p = platforms.get(code)
        if p is None:
            raise ValueError(f"Nieznana platforma: {code}")
        plats.append(p)
    if not plats:
        raise ValueError("Lista platform jest pusta.")

    lang_label = platforms.lang_label(language)
    locked = hashtag_library.locked_for(language)
    suggested = hashtag_library.suggested_for(language)

    hint_block = f"\nDODATKOWY KONTEKST OD UZYTKOWNIKA:\n{extra_hint.strip()}\n" if extra_hint.strip() else ""
    link_block = f"\nLINK DOCELOWY: {link.strip()}\n" if link.strip() else ""

    plat_specs = []
    for p in plats:
        plat_specs.append(
            f"### {p.icon} {p.label}  ({p.code})\n"
            f"- Caption limit: {p.caption_limit} znakow ({p.recommended_words[0]}-{p.recommended_words[1]} slow)\n"
            f"- Hashtagi: {p.recommended_hashtags} (limit {p.hashtag_limit})\n"
            f"- Format: {p.format_hint}\n"
            f"- Ton: {p.tone}\n"
            f"- Struktura: {p.structure}\n"
        )
    plats_block = "\n".join(plat_specs)

    posts_template_lines = []
    for p in plats:
        posts_template_lines.append(
            f"""    {{
      "platform": "{p.code}",
      "title": "",
      "caption": "",
      "on_screen_text": [],
      "hashtags": [],
      "image_hint": "",
      "link": "",
      "music_hint": ""
    }}"""
        )
    posts_template = ",\n".join(posts_template_lines)

    variant_note = _variant_note(variant)

    return f"""\
Jestes copywriterem social media specjalizujacym sie w sztuce, fotografii i dekoracji wnetrz.
Twoje zadanie: na ten sam TEMAT przygotuj {len(plats)} ROZNYCH wersji posta - po jednej na kazda
z wymienionych platform - tak zeby kazda byla idealnie dopasowana do specyfiki danej platformy
(dlugosc, ton, format), ale wszystkie buduja spojny komunikat marki GicleeArt w jezyku **{lang_label}**.

{SHOP_CONTEXT}

TEMAT (wspolny dla wszystkich platform):
"{topic}"
{hint_block}{link_block}
PLATFORMY DOCELOWE ({len(plats)}):
{plats_block}

WAZNE - NIE rob copy-paste tej samej tresci na rozne platformy. Kazda wersja:
- Wykorzystuje rownie ten sam motyw / hook / ciekawostke, ale ujmuje inaczej.
- Trzyma sie ZASAD danej platformy (dlugosc, hashtagi, struktura).
- Reels/TikTok dostaja `on_screen_text` i `music_hint`. Pinterest dostaje `title`
  i NIE dostaje hashtagow (keywords w `caption`/`title`). FB moze byc znacznie dluzsze.

HASHTAGI:
- STALE hashtagi marki (dolacz na kazdej platformie ktora ich uzywa): {' '.join(locked) if locked else '(brak)'}
- Propozycje tematyczne (wybieraj 4-8 dopasowanych do platformy z puli): {' '.join(suggested[:12])}

{variant_note}
FORMAT ODPOWIEDZI - JSON:
{{
  "language": "{language}",
  "topic": "{topic.replace('"', chr(39))}",
  "posts": [
{posts_template}
  ]
}}

Zwroc DOKLADNIE {len(plats)} obiektow w `posts`, jeden per platforma, w tej kolejnosci:
{', '.join(p.code for p in plats)}.
"""


def parse_multi_platform_response(raw: str) -> dict[str, Any]:
    """Parsuje odpowiedz multi-platform. Zwraca {language, topic, posts: [{platform, ...}, ...]}."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Odpowiedz nie jest obiektem JSON.")
    posts_raw = data.get("posts")
    if not isinstance(posts_raw, list) or not posts_raw:
        raise ValueError("Brak listy 'posts' lub jest pusta.")
    out_posts: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, p in enumerate(posts_raw, 1):
        if not isinstance(p, dict):
            errors.append(f"post #{i}: nie jest obiektem")
            continue
        platform_code = str(p.get("platform") or "").strip()
        if not platform_code:
            errors.append(f"post #{i}: brak pola 'platform'")
            continue
        try:
            validated = _validate_post_obj(p)
        except ValueError as e:
            errors.append(f"post #{i} ({platform_code}): {e}")
            continue
        validated["platform"] = platform_code
        out_posts.append(validated)
    if not out_posts:
        raise ValueError("Zaden post w multi-platform nie jest poprawny: " + "; ".join(errors))
    return {
        "language": str(data.get("language") or "").strip(),
        "topic": str(data.get("topic") or "").strip(),
        "posts": out_posts,
    }


def _build_series_prompt(
    *,
    topic: str,
    platform_code: str,
    language: str,
    count: int,
    extra_hint: str,
    link: str,
    variant: str,
) -> str:
    p = platforms.get(platform_code)
    if p is None:
        raise ValueError(f"Nieznana platforma: {platform_code}")

    n = max(2, min(count, 7))
    lang_label = platforms.lang_label(language)
    locked = hashtag_library.locked_for(language)
    suggested = hashtag_library.suggested_for(language)

    hint_block = f"\nDODATKOWY KONTEKST OD UZYTKOWNIKA:\n{extra_hint.strip()}\n" if extra_hint.strip() else ""
    link_block = f"\nLINK DOCELOWY: {link.strip()}\n" if link.strip() else ""

    variant_note = _variant_note(variant)

    return f"""\
Jestes copywriterem social media specjalizujacym sie w sztuce, fotografii i dekoracji wnetrz.
Twoje zadanie: zaprojektuj SERIE {n} POSTOW na platforme **{p.label}** w jezyku **{lang_label}**
dla sklepu GicleeArt, ktore razem buduja spojna narracje wokol JEDNEGO tematu.

{SHOP_CONTEXT}

TEMAT SERII:
"{topic}"
{hint_block}{link_block}
PLATFORMA: {p.label}
- Caption limit: {p.caption_limit} znakow
- Rekomendowana dlugosc kazdego posta: {p.recommended_words[0]}-{p.recommended_words[1]} slow
- Format: {p.format_hint}
- Ton: {p.tone}
- Struktura pojedynczego posta: {p.structure}

ZAPLANUJ LUK NARRACYJNY na {n} postow - klasyczny schemat:
1. HOOK / teaser (post 1) - zasygnalizuj temat, zostaw pytanie otwarte.
2. ROZWINIECIE / kontekst (posty 2 do {n - 2}) - eduikuj, pokaz detale, opowiedz historie.
3. REVEAL / zoom (post {n - 1}) - pokaz klucz tematu: konkretny obraz, detal, porada.
4. CTA (post {n}) - klarownie zachec do akcji (zakup, odwiedzenie bloga, zapisanie w kolekcji).

Kazdy post MUSI:
- Miec caption w jezyku **{lang_label}**.
- Miec wlasny hook i wlasne haslo kluczowe.
- Roznic sie wizualnie od pozostalych (image_hint pokazuje ze to cala seria, nie 5x to samo).
- Dolaczac STALE hashtagi marki: {' '.join(locked) if locked else '(pusto)'}.
- Wybrac 3-5 hashtagow tematycznych z puli: {' '.join(suggested[:10])} + wlasne niszowe.
- Dla Pinterest: hashtagi puste, keywords w `title` i `caption`.
- Dla Reels/TikTok: wypelnic `on_screen_text` i `music_hint`.

{variant_note}
FORMAT ODPOWIEDZI - JSON:
{{
  "platform": "{p.code}",
  "language": "{language}",
  "topic": "{topic.replace('"', chr(39))}",
  "series_meta": {{
    "arc": "1-2 zdania opisujace luk narracyjny calosci",
    "cadence": "np. 'co 2 dni przez 10 dni' albo 'codziennie przez tydzien'"
  }},
  "posts": [
    {{
      "title": "",
      "caption": "",
      "on_screen_text": [],
      "hashtags": [],
      "image_hint": "",
      "link": "",
      "music_hint": ""
    }},
    ... (dokladnie {n} obiektow)
  ]
}}
"""


def _variant_note(variant: str) -> str:
    if variant == "gpt":
        return (
            "DODATKOWE RYGORY DLA GPT:\n"
            "- Zwroc WYLACZNIE poprawny JSON - bez markdown code fences (```), "
            "bez komentarzy, bez tekstu przed ani po.\n"
            "- Cudzyslowy wewnatrz stringow JSON escape'uj jako \\\".\n"
            "- Uzyj \\n jesli potrzebujesz nowej linii w caption.\n"
        )
    return (
        "WSKAZOWKA DLA CLAUDE OPUS:\n"
        "- Pisz naturalnie, jakby native copywriter.\n"
        "- Odpowiedz zwroc w bloku code fence ```json ... ``` (parser obsluguje oba warianty).\n"
    )


# ---------------------------------------------------------------------------
# Parsery odpowiedzi LLM
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json_block(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    m = _CODE_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        return text[first : last + 1]
    return text


def _validate_post_obj(post: Any) -> dict[str, Any]:
    if not isinstance(post, dict):
        raise ValueError("Post nie jest obiektem JSON.")
    caption = str(post.get("caption") or "").strip()
    if not caption:
        raise ValueError("Post nie ma pola 'caption'.")
    return {
        "title": str(post.get("title") or "").strip(),
        "caption": caption,
        "on_screen_text": [str(s).strip() for s in (post.get("on_screen_text") or []) if str(s).strip()],
        "hashtags": [str(h).strip() for h in (post.get("hashtags") or []) if str(h).strip()],
        "image_hint": str(post.get("image_hint") or "").strip(),
        "link": str(post.get("link") or "").strip(),
        "music_hint": str(post.get("music_hint") or "").strip(),
    }


def parse_post_response(raw: str) -> dict[str, Any]:
    """Parsuje odpowiedz single-post. Zwraca {platform, language, topic, post}."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Odpowiedz nie jest obiektem JSON.")
    post = data.get("post")
    if post is None:
        raise ValueError("Brak pola 'post' w odpowiedzi.")
    return {
        "platform": str(data.get("platform") or "").strip(),
        "language": str(data.get("language") or "").strip(),
        "topic": str(data.get("topic") or "").strip(),
        "post": _validate_post_obj(post),
    }


def parse_series_response(raw: str) -> dict[str, Any]:
    """Parsuje odpowiedz serii. Zwraca {platform, language, topic, series_meta, posts}."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Odpowiedz nie jest obiektem JSON.")
    posts_raw = data.get("posts")
    if not isinstance(posts_raw, list) or not posts_raw:
        raise ValueError("Brak listy 'posts' lub jest pusta.")
    posts = []
    errors: list[str] = []
    for i, p in enumerate(posts_raw, 1):
        try:
            posts.append(_validate_post_obj(p))
        except ValueError as e:
            errors.append(f"post #{i}: {e}")
    if not posts:
        raise ValueError("Zaden post w serii nie jest poprawny: " + "; ".join(errors))
    meta = data.get("series_meta") if isinstance(data.get("series_meta"), dict) else {}
    return {
        "platform": str(data.get("platform") or "").strip(),
        "language": str(data.get("language") or "").strip(),
        "topic": str(data.get("topic") or "").strip(),
        "series_meta": {
            "arc": str(meta.get("arc") or "").strip(),
            "cadence": str(meta.get("cadence") or "").strip(),
        },
        "posts": posts,
    }
