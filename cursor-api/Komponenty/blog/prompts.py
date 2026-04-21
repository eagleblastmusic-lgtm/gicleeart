"""Buildery promptow dla Generatora tresci i Generatora tematow.

Dwa warianty promptow:
- Opus (Anthropic Claude) - luzniejsze instrukcje, model sam lepiej radzi sobie z kontekstem.
- GPT (OpenAI) - twardsze rygory formatu JSON, bo GPT lubi dodawac komentarze.

Oba prompty wymuszaja jeden format JSON:

### Generator tresci (jeden post w 7 jezykach):
{
  "topic": "Historia malarstwa romantycznego",
  "category": "historia sztuki",
  "image_hint": "Propozycja tematu obrazu do artykulu (opcjonalnie)",
  "languages": {
    "pl": { "title": "...", "summary_html": "...", "body_html": "<p>...</p>", "tags": [...], "seo_title": "...", "seo_description": "..." },
    "en": { ... },
    "de": { ... },
    "fr": { ... },
    "es": { ... },
    "nl": { ... },
    "it": { ... }
  }
}

### Generator tematow (10 propozycji):
{
  "proposals": [
    { "title": "...", "reason": "Dlaczego warto - 1-2 zdania", "keywords": ["..."] },
    ... (x10)
  ]
}
"""

from __future__ import annotations

import json
import re
from typing import Any

LANGUAGES = [
    ("pl", "polski"),
    ("en", "angielski"),
    ("de", "niemiecki"),
    ("fr", "francuski"),
    ("es", "hiszpanski"),
    ("nl", "holenderski"),
    ("it", "wloski"),
]

SHOP_CONTEXT = """\
Sklep: GicleeArt (gicleeart.eu) - sprzedaz wydrukow artystycznych technika giclee na plotnie.
Sklep dziala na 7 rynkach UE (PL bazowy, EN/EU, FR, DE, ES, NL, IT).

Sklep ma DWIE galezie dzialalnosci (oba produkty sprzedawane sa na tej samej stronie):

1) REPRODUKCJE KLASYKOW MALARSTWA - gotowe reprodukcje dziel mistrzow (Monet, Van Gogh,
   Vermeer, Klimt, polscy kolorysci, prerafaelici itd.) drukowane w wysokiej jakosci giclee na plotnie.
   Grupa docelowa: milosnicy sztuki, osoby dekorujace dom/biuro w stylu klasycznym,
   boho, skandynawskim, glamour; prezenty dla milosnikow sztuki.

2) WYDRUKI NA ZAMOWIENIE Z WLASNEGO ZDJECIA (custom print / foto na plotnie) -
   klient wgrywa wlasne zdjecie (fotografia rodzinna, slubna, portret, zdjecie
   z sesji, krajobraz z wakacji, zdjecie produktowe, logo, grafika) przez edytor
   na stronie, sam dopasowuje kadr w live mockupie (widzi podglad na scianie w pokoju),
   wybiera rozmiar i drukuje na tym samym plotnie giclee co reprodukcje.
   Grupa docelowa: klienci indywidualni (prezenty personalizowane, sesje slubne,
   zdjecia rodzinne, portrety dzieci, pamiatki z podrozy), fotografowie (wydruki
   dla klientow), male firmy (dekoracja biura, wlasna marka wizualna).

Ton komunikacji (obie galezie): elegancki, ciepy, merytoryczny, bez napuszenia -
edukujemy, opowiadamy historie, pokazujemy kontekst kulturowy lub emocjonalny.

WAZNE: Artykul NIE MA byc tylko reklama produktu. Ma dawac wartosc - wiedze,
inspiracje, opowiesc. Subtelnie nawiazujemy do produktu dopiero w ostatnim
akapicie (CTA), i to raczej jako naturalne zakonczenie niz tward sell.
Jesli temat dotyczy reprodukcji klasyki -> CTA o reprodukcjach giclee.
Jesli temat dotyczy wlasnych zdjec / fotografii / personalizacji -> CTA o wydruku wlasnego zdjecia
w edytorze z mockupem, z podkresleniem tej samej jakosci giclee co reprodukcje.
"""


# ---------------------------------------------------------------------------
# Generator tresci (content prompt)
# ---------------------------------------------------------------------------

_CONTENT_JSON_SKELETON = """\
{
  "topic": "...",
  "category": "...",
  "image_hint": "",
  "languages": {
    "pl": {
      "title": "",
      "summary_html": "",
      "body_html": "",
      "tags": [],
      "seo_title": "",
      "seo_description": ""
    },
    "en": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" },
    "de": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" },
    "fr": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" },
    "es": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" },
    "nl": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" },
    "it": { "title": "", "summary_html": "", "body_html": "", "tags": [], "seo_title": "", "seo_description": "" }
  }
}
"""


def _content_rules(variant: str) -> str:
    base_rules = """\
ZASADY TWORZENIA ARTYKULU:
1. Dlugosc kazdej wersji jezykowej: 700-1100 slow w `body_html` (same slowa, bez HTML).
2. `body_html`: czysty HTML, dozwolone tagi: <p>, <h2>, <h3>, <strong>, <em>, <ul>, <ol>, <li>, <blockquote>, <a>, <br>. NIE uzywaj <div>, <span>, <img>, <script>, <style>, inline CSS.
3. Struktura: lead (1 akapit - zaciekawienie), 2-3 naglowki H2 z rozwinieciem tematu, ostatni akapit CTA z naturalnym nawiazaniem do GicleeArt (max 1-2 zdania).
4. `summary_html`: 1 krotki akapit <p>...</p> (80-140 slow) - to zajawka pokazywana na liscie postow.
5. `seo_title`: 55-60 znakow, zawiera glowne slowo kluczowe + brand jeli sie miesci.
6. `seo_description`: 140-158 znakow, zachecajaca meta-desc z call-to-action.
7. `tags`: 5-8 tagow - fraz kluczowych po polsku (dla PL) / po angielsku (EN) / lokalnie dla pozostalych. Duze litery pierwszej litery. Przykady PL: "Sztuka klasyczna", "Reprodukcja", "Dekoracja wnetrz", "Foto na plotnie", "Prezent personalizowany".
8. TLUMACZENIA: wszystkie 7 wersji maja miec ten sam PRZEKAZ, ale NIE sa doslownym tumaczeniem. Uwzgledniaj kontekst kulturowy (np. niemieckie traktowanie klasyki, francuska precyzja, wloska emocjonalnosc).
9. `category`: jedna z: "historia sztuki", "technika", "kierunki i style", "artysci", "aranzacja wnetrz", "porady zakupowe", "custom print", "foto na plotnie".
10. `image_hint`: krotka (1 zdanie) sugestia co powinno znalezc sie na zdjeciu do tego artykulu.
11. DOPASOWANIE CTA do galezi:
    - Temat o klasyce/artystach/reprodukcjach -> CTA odwolujaca sie do reprodukcji mistrzow w GicleeArt.
    - Temat o fotografii wlasnej / personalizacji / sesjach / prezentach ze zdjeciem -> CTA odwolujaca sie do funkcji wgrania
      wlasnego zdjecia w edytorze z live mockupem (klient widzi podglad na scianie), wyboru kadru i druku giclee.
    - Temat mostkujacy (np. fotografia vs malarstwo) -> CTA moze laczyc oba produkty, ale konkretnie i krotko.
    - NIGDY nie mieszaj CTA "przegladaj reprodukcje" w artykule praktycznie poswieconym wlasnym zdjeciom, i odwrotnie.
"""
    if variant == "gpt":
        return base_rules + """\

DODATKOWE RYGORY DLA GPT:
- ZWROC WYLACZNIE poprawny JSON - bez markdown code fences (```), bez komentarzy, bez tekstu przed ani po.
- Wszystkie stringi w JSON sa pojedynczej linii (uzyj \\n jesli MUSISZ miec nowa linie w HTML, ale najlepiej zostaw HTML jako ciag bez zbednych nowych linii).
- Nie obcinaj odpowiedzi - jesli widzisz ze zbliasz sie do limitu tokenow, skroc poszczegolne wersje jezykowe (zachowaj strukture), ale NIE obcinaj na srodku slowa.
- Cudzysowy wewnatrz HTML escape'uj jako \\" (standardowy JSON).
"""
    return base_rules + """\

DODATKOWE WSKAZOWKI DLA CLAUDE OPUS:
- Czytelnosc > objetosc. Mozesz przekroczyc 1100 slow jeli to ma sens merytoryczny, ale nie rozwadniaj.
- W PL - naturalny, literacki polski. Nie uzywaj amerykanizmow ani kalkowan.
- W EN/DE/FR/ES/NL/IT - native-level, pisane jakby przez rodzimego copywritera, nie tumacza.
- Odpowiedz zwroc w jednym bloku code fence ```json ... ``` (parser w aplikacji obsuguje oba warianty).
"""


def build_content_prompt_opus(topic: str, image_url: str = "", existing_titles: list[str] | None = None) -> str:
    return _build_content_prompt(topic, image_url, existing_titles, variant="opus")


def build_content_prompt_gpt(topic: str, image_url: str = "", existing_titles: list[str] | None = None) -> str:
    return _build_content_prompt(topic, image_url, existing_titles, variant="gpt")


def _build_content_prompt(
    topic: str,
    image_url: str,
    existing_titles: list[str] | None,
    *,
    variant: str,
) -> str:
    existing_block = ""
    if existing_titles:
        titles_sample = existing_titles[:20]
        existing_block = (
            "\nOBECNE POSTY NA BLOGU (zeby nie duplikowac tematyki):\n"
            + "\n".join(f"- {t}" for t in titles_sample)
            + "\n"
        )
    image_block = f"\nURL ZDJECIA GLOWNEGO (referencja wizualna, nie wstawiaj go do HTML): {image_url}\n" if image_url else ""

    return f"""\
Jestes copywriterem-ekspertem od sztuki i historii malarstwa, piszacym na blog sklepu GicleeArt
w siedmiu jezykach. Twoje zadanie: napisac JEDEN post na blog o podanym temacie w 7 wersjach jezykowych.

{SHOP_CONTEXT}
{existing_block}{image_block}
TEMAT POSTA:
"{topic}"

{_content_rules(variant)}

FORMAT ODPOWIEDZI - JSON dokladnie o tej strukturze (wypelnij KAZDE pole, zadnych placeholderow "..."):
{_CONTENT_JSON_SKELETON}

Kody jezykow w `languages`:
- pl = polski (BAZA)
- en = angielski (rynek EU)
- de = niemiecki
- fr = francuski
- es = hiszpanski
- nl = holenderski
- it = wloski
"""


# ---------------------------------------------------------------------------
# Generator tematow (topics prompt)
# ---------------------------------------------------------------------------

def build_topics_prompt_opus(existing_titles: list[str], planned_topics: list[str] | None = None) -> str:
    return _build_topics_prompt(existing_titles, planned_topics, variant="opus")


def build_topics_prompt_gpt(existing_titles: list[str], planned_topics: list[str] | None = None) -> str:
    return _build_topics_prompt(existing_titles, planned_topics, variant="gpt")


def _build_topics_prompt(
    existing_titles: list[str],
    planned_topics: list[str] | None,
    *,
    variant: str,
) -> str:
    existing_block = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "(brak - blog jest pusty)"
    planned_block = ""
    if planned_topics:
        planned_block = (
            "\nTEMATY JUZ ZAPROPOZYCJONOWANE (do pominiecia / uniknij duplikatow):\n"
            + "\n".join(f"- {t}" for t in planned_topics)
            + "\n"
        )

    variant_note = ""
    if variant == "gpt":
        variant_note = (
            "\nZWROC WYLACZNIE JSON - bez code fences, bez komentarzy, bez tekstu doklejonego. "
            "Uwazaj na cudzyslowy w stringach - escape'uj jako \\\".\n"
        )
    else:
        variant_note = (
            "\nZwroc JSON w bloku ```json ... ```. Parser obsuguje oba warianty.\n"
        )

    return f"""\
Jestes strategiem contentowym bloga sklepu GicleeArt (wydruki giclee na plotnie, 7 rynkow UE).
Twoje zadanie: zaproponowac 10 NOWYCH tematow na bloga, ktore uzupelnia istniejacy content,
przyciagna ruch z Google (long-tail SEO) i zaciekawia OBIE grupy klientow sklepu.

{SHOP_CONTEXT}

OBECNE POSTY NA BLOGU (nie duplikuj tematyki, ale mozesz ja poglebic lub wzbogacic):
{existing_block}
{planned_block}
ZASADY:
1. 10 propozycji = MIESZANKA tematow z OBU galezi sklepu. Docelowa proporcja w zestawie 10 tematow:
   - ~4-5 tematow zwiazanych z reprodukcjami klasyki (historia sztuki, artysci, kierunki, technika giclee, aranzacja ze sztuka);
   - ~4-5 tematow zwiazanych z wydrukiem wlasnego zdjecia / personalizacja
     (np. "jak przygotowac zdjecie do druku na plotnie", "foto slubne na scianie - pomysly na galerie",
     "portret dziecka na plotnie jako prezent", "czy zdjecie z telefonu nadaje sie na duzy wydruk",
     "sesja rodzinna -> dekoracja salonu", "wydruki zdjec z podrozy - jak wybrac kadr",
     "czarno-biale zdjecia na plotnie - kiedy warto", "wydruki zdjec dla fotografow na sprzedaz klientom");
   - 1-2 tematy mostkujace (np. "dlaczego Twoje zdjecie zasluguje na plotno jak mistrzowie",
     "pejzaz w malarstwie a fotografia krajobrazu - co je laczy").
2. Rozne kategorie: historia sztuki, technika druku giclee, kierunki i style, sylwetki artystow,
   aranzacja wnetrz, porady zakupowe, sezonowosc (swieta, pory roku), personalizacja / foto na zamowienie,
   poradniki przygotowania wlasnych zdjec, prezenty personalizowane, workflow dla fotografow.
3. Tematy maja byc konkretne i SEO-friendly - tytul jak z Google ("5 sposobow...", "Historia X",
   "Jak wybrac Y", "Czym rozni sie A od B", "Jak przygotowac Z").
4. Rozne poziomy trudnosci - od wprowadzajacych po niszowe.
5. Uzasadnienie: 1-2 zdania po polsku dlaczego warto napisac ten post (jakie pytanie rozwiazuje,
   do kogo trafi - reprodukcje vs custom print, jakie frazy SEO).
6. `keywords`: 3-6 fraz kluczowych (po polsku, lowercase) - glownie long-tail.

{variant_note}
FORMAT ODPOWIEDZI:
{{
  "proposals": [
    {{
      "title": "Jak wybrac reprodukcje obrazu do salonu w stylu skandynawskim",
      "reason": "Konkretne pytanie uzytkownikow przygotowujacych mieszkanie; galaz: reprodukcje; dobry long-tail.",
      "keywords": ["obraz do salonu skandynawski", "reprodukcja w stylu nordyckim", "plakat skandynawski"]
    }},
    {{
      "title": "Jak przygotowac zdjecie z telefonu do druku na plotnie 100x70 cm",
      "reason": "Praktyczny poradnik rozwiazujacy obawe klienta o jakosc zdjecia z komorki; galaz: custom print; celuje w klientow rozwazajacych personalizowany prezent.",
      "keywords": ["zdjecie z telefonu na plotno", "druk zdjecia duzy format", "jakosc zdjecia do druku"]
    }},
    ... (dokladnie 10 obiektow)
  ]
}}
"""


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


def parse_content_response(raw: str) -> dict[str, Any]:
    """Parsuje odpowiedz Generatora tresci. Rzuca ValueError przy bledach."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Odpowiedz nie jest obiektem JSON.")
    langs = data.get("languages")
    if not isinstance(langs, dict):
        raise ValueError("Brak pola 'languages' (slownik z wersjami).")
    missing = [code for code, _ in LANGUAGES if code not in langs]
    if missing:
        raise ValueError(f"Brakuje wersji jezykowych: {', '.join(missing)}")
    for code, _ in LANGUAGES:
        entry = langs.get(code) or {}
        if not isinstance(entry, dict):
            raise ValueError(f"Wersja '{code}' nie jest obiektem.")
        for key in ("title", "body_html"):
            if not str(entry.get(key) or "").strip():
                raise ValueError(f"Wersja '{code}' - brak pola '{key}'.")
    return data


def parse_topics_response(raw: str) -> list[dict[str, Any]]:
    """Parsuje odpowiedz Generatora tematow. Zwraca liste propozycji."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e
    proposals = data.get("proposals") if isinstance(data, dict) else data
    if not isinstance(proposals, list):
        raise ValueError("Brak listy 'proposals'.")
    out: list[dict[str, Any]] = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        out.append({
            "title": title,
            "reason": str(item.get("reason") or "").strip(),
            "keywords": [str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()],
        })
    if not out:
        raise ValueError("Nie znaleziono zadnych poprawnych propozycji w odpowiedzi.")
    return out
