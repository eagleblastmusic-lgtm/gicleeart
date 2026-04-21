"""Buildery promptow dla generatora zadan marketingowych + parser odpowiedzi.

LLM dostaje:
- Kontekst sklepu (2 galezie: reprodukcje + custom print).
- Liste sygnalow Shopify (nowe produkty, nowi autorzy, kolekcje).
- Liste swiat/wydarzen z kalendarza na najblizsze N dni.
- Liste juz zaplanowanych zadan (zeby nie duplikowac).
- Liste platform social + blog.

Zadanie LLM: zbudowac plan ~15-20 zadan na kolejny miesiac, rozlozonych w czasie,
rozlozonych miedzy kanalami (nie 10 postow IG pod rzad!), dotykajacych roznych
galezi biznesu, wlaczajacy sie w nadchodzace swieta.

Output format (JSON, wersja 2 - multi-channel + multi-market):
{
  "period": "miesiac",
  "rationale": "1-2 zdania o ogolnym luku miesiaca",
  "tasks": [
    {
      "title": "Post IG + FB o Hansie Dahlu",
      "description": "Krotki opis po polsku - dla Ciebie do zrozumienia o co chodzi.",
      "description_translations": {
        "en": "Short EN description (REQUIRED jesli rynek inny niz tylko PL)",
        "de": "...",
        "es": "..."
      },
      "channels": ["ig_feed", "fb"],          // mozna 1+; LLM moze wrzucic to samo zadanie na kilka platform
      "languages": ["pl", "en"],              // jezyki contentu (2 profile: PL i EN)
      "target_markets": ["pl", "eu", "de"],   // ktore z 7 rynkow Shopify (pl/eu/fr/de/es/nl/it)
      "due_date": "2026-05-05",
      "priority": "low" | "normal" | "high" | "urgent",
      "source": "shopify" | "holiday" | "llm" | "evergreen",
      "source_ref": "np. 'Hans Dahl' albo 'Walentynki'",
      "suggested_topic": "Temat do wkleczenia w Generator tresci - po polsku, konkretny"
    },
    ... (15-20 zadan)
  ]
}
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

SHOP_CONTEXT = """\
Sklep: GicleeArt (gicleeart.eu) - wydruki giclee na plotnie.
Dwie galezie:
1) REPRODUKCJE KLASYKOW MALARSTWA - katalog gotowych produktow (Monet, Van Gogh, Vermeer, Klimt...).
2) CUSTOM PRINT z wlasnego zdjecia - edytor w sklepie, live mockup, personalizacja
   (zdjecia rodzinne, slubne, portrety, sesje, krajobrazy, logo firmy).
Rynki Shopify: pl (baza), eu, fr, de, es, nl, it. Social media: 2 profile - PL i EN.
"""

_CHANNEL_GUIDE = """\
KANALY (distribuuj zadania miedzy nimi, nie rob 10 postow IG pod rzad):
- ig_feed: post Instagram Feed (kwadrat/pionowy + dluzszy caption).
- ig_stories: Instagram Stories (24h, krotki, bezposredni).
- ig_reels: Instagram Reels (video 15-90s, hook + on-screen text).
- fb: Facebook (dluzszy post, mozna link).
- tiktok: TikTok (video 15-60s, hook w 2 sek).
- pinterest: Pinterest pin (SEO, keywords, link do produktu/blogu).
- blog: artykul na blogu sklepu (700-1100 slow, 7 jezykow automatycznie).
- newsletter: mail do subskrybentow.
- other: inne dzialania (reklama, konkurs, update w sklepie, fotosesja).

WAZNE - MULTI-CHANNEL:
Pole `channels` to LISTA. Jedno zadanie moze trafic na kilka platform jednoczesnie,
np. ten sam temat dla IG Feed + FB (rozne dlugosci captionu, ten sam motyw wizualny).
Jesli temat dobrze pasuje na 2-3 kanaly - daj liste, oszczedzaj zadania.
NIE laczy jednak ze soba kanalow o calkiem roznym formacie (np. blog + ig_stories).
Dobre kombinacje: [ig_feed, fb], [ig_reels, tiktok], [ig_feed, pinterest], [blog, newsletter].
"""

_MARKETS_GUIDE = """\
RYNKI (`target_markets` - lista, ktorych z 7 rynkow Shopify dotyczy zadanie):
- pl - rynek polski (priorytet, baza klientow). Tlumaczenie EN nie wymagane.
- eu - generalny rynek europejski (EN, lingua franca).
- fr, de, es, nl, it - konkretne kraje. Jesli targetujesz konkretny kraj,
  rozwaz tlumaczenie opisu na ten jezyk (description_translations).

JEZYKI (`languages` - lista, w jakich jezykach przygotowac content):
- pl, en (2 nasze profile social).
- Mozesz dolozyc de/fr/es/nl/it dla blog (Shopify autotranslate) lub kampanii konkretnego rynku.

ZASADA:
- Jesli `target_markets` zawiera tylko `pl` -> opis po polsku wystarczy.
- Jesli zawiera EU lub konkretny zagraniczny rynek -> WYMAGANE
  `description_translations.en` (i ewentualnie pasujacy jezyk rynku, np. de dla DE).
- Tlumaczenie ma byc krotkie (1-2 zdania) i klarowne - to dla operatora marketingu, zeby
  szybko zrozumial o czym jest zadanie kierowane na rynek zagraniczny.
"""


def build_tasks_prompt_opus(
    *,
    signals_text: str,
    holidays_text: str,
    planned_text: str,
    target_count: int = 18,
    period_label: str = "kolejny miesiac",
) -> str:
    return _build_tasks_prompt(
        signals_text=signals_text,
        holidays_text=holidays_text,
        planned_text=planned_text,
        target_count=target_count,
        period_label=period_label,
        variant="opus",
    )


def build_tasks_prompt_gpt(
    *,
    signals_text: str,
    holidays_text: str,
    planned_text: str,
    target_count: int = 18,
    period_label: str = "kolejny miesiac",
) -> str:
    return _build_tasks_prompt(
        signals_text=signals_text,
        holidays_text=holidays_text,
        planned_text=planned_text,
        target_count=target_count,
        period_label=period_label,
        variant="gpt",
    )


def _build_tasks_prompt(
    *,
    signals_text: str,
    holidays_text: str,
    planned_text: str,
    target_count: int,
    period_label: str,
    variant: str,
) -> str:
    today_str = date.today().isoformat()
    n = max(5, min(target_count, 40))

    planned_block = (
        f"\nZADANIA JUZ ZAPLANOWANE (nie duplikuj; mozesz sie odwolac, ale nie powtarzaj):\n{planned_text}\n"
        if planned_text.strip()
        else ""
    )

    variant_note = (
        "ZWROC WYLACZNIE JSON - bez code fences ```, bez komentarzy, bez tekstu przed/po."
        if variant == "gpt"
        else "Odpowiedz zwroc w bloku ```json ... ``` (parser obsluguje oba warianty)."
    )

    return f"""\
Jestes strategiem marketingu sklepu GicleeArt. Twoje zadanie: zaplanowac {n} KONKRETNYCH zadan
marketingowych na {period_label}. Dzis jest {today_str}.

{SHOP_CONTEXT}

{_CHANNEL_GUIDE}

{_MARKETS_GUIDE}

AKTUALNE SYGNALY Z SKLEPU (Shopify):
{signals_text}

NADCHODZACE SWIETA / WYDARZENIA (uwzgledniaj lead_time_days - kampanie zaczynaj wczesniej!):
{holidays_text}
{planned_block}
ZASADY PLANOWANIA:
1. Rozlozenie w czasie: zadania powinny byc rozsiane rownomiernie - 2-4 zadania tygodniowo,
   nie wszystkie w 1 dniu. `due_date` w formacie YYYY-MM-DD.
2. Rozloz miedzy kanalami: uwazaj zeby nie byo 10 postow IG pod rzad. Optymalna mieszanka
   w 18-20 zadaniach: ~5-6 IG Feed, 2-3 IG Stories, 2-3 Reels/TikTok, 2-3 FB, 1-2 Pinterest,
   1-2 blog, 1 newsletter, 1 other. Multi-channel zadania liczysz wg pierwszego kanalu.
3. Obie galezie: ~50% zadan o reprodukcjach klasyki, ~40% o custom print / personalizacja,
   ~10% bridge/edukacja uniwersalna.
4. Jezyk i rynek: wiekszosc PL (rynek bazowy), ale 25-35% celuj w EU/EN i konkretne rynki.
   Mozesz tez dac `languages: ["pl","en"]` + `target_markets: ["pl","eu"]` dla zadan dual.
5. Swieta: kampanie zaczynaj DZIEN `data_swieta - lead_time_days`, konczaj dzien przed.
   Np. Walentynki 14.02 z lead_time 21d -> kampanie 24.01 - 13.02 (4-5 zadan rozlozonych).
6. Nowi autorzy z sygnalow -> specjalny post prezentacyjny (IG Feed lub blog).
7. Nowe kolekcje -> post na IG/Pinterest + newsletter (mozna jako multi-channel).
8. Produkty bez obrazka / nieopublikowane -> zadanie administracyjne 'other' priority=urgent.
9. 'Suggested_topic' MUSI byc konkretny i gotowy do wklejenia w Generator tresci
   (np. 'Hans Dahl - norweski mistrz swiatla morza - nowy autor w GicleeArt', a nie 'post o autorze').
10. `description` ZAWSZE po polsku (to dla Ciebie - operatora). `description_translations`
    DODAJ jesli `target_markets` zawiera rynek inny niz `pl` - klucz 'en' i ewentualnie
    pasujacy do rynku ('de' dla DE, 'fr' dla FR, 'es' dla ES, 'nl' dla NL, 'it' dla IT).
11. Priorytety:
    - urgent: produkty bez obrazka / krytyczne terminy (<3 dni).
    - high: Black Friday, Boze Narodzenie, Walentynki, swieta w ciagu 2 tyg.
    - normal: standardowe zadania.
    - low: evergreen, zapasowe.

{variant_note}

FORMAT ODPOWIEDZI - JSON:
{{
  "period": "{period_label}",
  "rationale": "1-2 zdania o glownym luku narracyjnym miesiaca",
  "tasks": [
    {{
      "title": "Post IG + FB o Hansie Dahlu - norweski mistrz swiatla",
      "description": "Wprowadzenie nowego autora w katalogu. Skupienie na swietle i morzu.",
      "description_translations": {{
        "en": "Introducing a new artist - Norwegian master of marine light"
      }},
      "channels": ["ig_feed", "fb"],
      "languages": ["pl", "en"],
      "target_markets": ["pl", "eu"],
      "due_date": "2026-05-08",
      "priority": "normal",
      "source": "shopify",
      "source_ref": "Hans Dahl",
      "suggested_topic": "Hans Dahl - norweski mistrz swiatla morza - przedstawienie nowego autora w katalogu GicleeArt"
    }},
    ... (dokladnie {n} obiektow)
  ]
}}
"""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_VALID_CHANNELS = {
    "ig_feed", "ig_stories", "ig_reels", "fb", "tiktok", "pinterest",
    "blog", "newsletter", "other",
}
_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
_VALID_SOURCES = {"shopify", "holiday", "llm", "manual", "evergreen"}
_VALID_LANGS = {"pl", "en", "de", "fr", "es", "nl", "it", "both"}
_VALID_MARKETS = {"pl", "eu", "fr", "de", "es", "nl", "it"}


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


def _coerce_str_list(raw: Any, valid: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return out
    for x in raw:
        s = str(x or "").strip().lower()
        if s in valid and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def parse_tasks_response(raw: str) -> list[dict[str, Any]]:
    """Parsuje odpowiedz generatora zadan. Zwraca liste zadan (lub rzuca ValueError)."""
    payload = _extract_json_block(raw)
    if not payload:
        raise ValueError("Pusta odpowiedz z modelu.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Bledny JSON: {e}") from e

    tasks_raw: list[Any]
    if isinstance(data, dict):
        tasks_raw = data.get("tasks") or []
    elif isinstance(data, list):
        tasks_raw = data
    else:
        raise ValueError("Odpowiedz nie zawiera listy 'tasks'.")

    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ValueError("Lista 'tasks' jest pusta lub nie jest lista.")

    out: list[dict[str, Any]] = []
    for item in tasks_raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue

        # channels - obsluguje 'channels' (list) i 'channel' (string, backcompat)
        channels = _coerce_str_list(item.get("channels"), _VALID_CHANNELS)
        if not channels:
            single = str(item.get("channel") or "other").strip().lower()
            channels = [single] if single in _VALID_CHANNELS else ["other"]

        # languages - obsluguje 'languages' i 'language'
        languages = _coerce_str_list(item.get("languages"), _VALID_LANGS)
        if not languages:
            single_l = str(item.get("language") or "pl").strip().lower()
            if single_l == "both":
                languages = ["pl", "en"]
            elif single_l in _VALID_LANGS:
                languages = [single_l]
            else:
                languages = ["pl"]

        # target_markets - jesli puste, infer z language: pl->pl, en->eu
        markets = _coerce_str_list(item.get("target_markets"), _VALID_MARKETS)
        if not markets:
            if "pl" in languages and ("en" in languages or len(languages) > 1):
                markets = ["pl", "eu"]
            elif "en" in languages:
                markets = ["eu"]
            else:
                markets = ["pl"]

        # description_translations - tylko valid languages, niepuste, klucz != pl/both
        translations: dict[str, str] = {}
        raw_tr = item.get("description_translations") or {}
        if isinstance(raw_tr, dict):
            for k, v in raw_tr.items():
                k_str = str(k or "").strip().lower()
                v_str = str(v or "").strip()
                if k_str in _VALID_LANGS and k_str not in ("pl", "both") and v_str:
                    translations[k_str] = v_str

        priority = str(item.get("priority") or "normal").strip().lower()
        if priority not in _VALID_PRIORITIES:
            priority = "normal"
        source = str(item.get("source") or "llm").strip().lower()
        if source not in _VALID_SOURCES:
            source = "llm"

        out.append({
            "title": title,
            "description": str(item.get("description") or "").strip(),
            "description_translations": translations,
            "channels": channels,
            "languages": languages,
            "target_markets": markets,
            "due_date": str(item.get("due_date") or "").strip(),
            "priority": priority,
            "source": source,
            "source_ref": str(item.get("source_ref") or "").strip(),
            "suggested_topic": str(item.get("suggested_topic") or "").strip(),
        })
    if not out:
        raise ValueError("Zaden wpis w 'tasks' nie ma tytulu.")
    return out
