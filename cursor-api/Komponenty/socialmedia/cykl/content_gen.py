"""Generator tresci cyklu - batch tygodniowy przez Opus.

Flow:
1. build_week_prompt(items) -> duzy prompt tekstowy, do skopiowania do Opus chatu.
2. User wkleja prompt w Cursor chat (model: Claude Opus).
3. Opus zwraca JSON w bloku ```json ... ```.
4. parse_week_response(raw) -> dict {item_id: ItemContent}.
5. apply_to_queue(queue, content_map) -> wpisuje tresc do pol CykleItem.caption_pl etc.

Prompt zawiera:
- SHOP_CONTEXT (reuse z Komponenty/socialmedia/prompts.SHOP_CONTEXT)
- URL-e 4 kanalow Meta + storefront PL/EN
- LOCKED_HASHTAGS_PL / EN (ktorych prompt wymusza)
- Zasady: intro przy is_first_of_artist, outro przy is_last_of_artist,
  specjalne intro dla is_new_artist ('na stronie pojawil sie nowy artysta'),
  specjalne intro dla is_new_painting ('nowy obraz w kolekcji X').
- 21 blokow 'painting' (tytuly PL/EN + 3 akapity opis PL/EN + flagi).

Wynik JSON:
{
  "items": [
    {
      "id": "<uuid>",
      "pl": {
        "caption_fb": "...",    // 400-900 slow, eleganckie, CTA
        "caption_ig": "...",    // 350-1300 znakow z hashtagami na koncu
        "hashtags": ["#..."],   // 10-15 wspolnych
        "zoom_hints": ["..."]   // 3-5 sugestii co pokazac w zoomach
      },
      "en": { ... ten sam schemat ... }
    },
    ...
  ]
}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .. import hashtag_library
from ..prompts import SHOP_CONTEXT
from . import platforms_cykl as _cp
from . import storage


# Liczba pozycji ktore mieszcza sie w jednym batchu Opusa (bezpiecznie ~21 = 7 dni)
DEFAULT_BATCH_SIZE = 21


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_week_prompt(
    items: list[storage.CykleItem],
    *,
    variant: str = "opus",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> str:
    """Buduje prompt dla Opusa na `batch_size` kolejnych pozycji (zwykle 7 dni x 3 sloty).

    Pomijamy pozycje ktore juz maja tresc (caption_pl + caption_en) chyba ze
    manual_override=False i user tego sobie zazyczy (na razie: skip gdy pelne).
    """
    batch = _select_batch(items, batch_size)
    if not batch:
        raise ValueError("Brak pozycji do wygenerowania (wszystkie maja juz tresc).")

    locked_pl = ", ".join(hashtag_library.LOCKED_HASHTAGS_PL)
    locked_en = ", ".join(hashtag_library.LOCKED_HASHTAGS_EN)

    channels_block = "\n".join(
        f"  - {c.label}: {c.page_url} (jezyk: {c.language}, platforma: {c.platform})"
        for c in _cp.all_channels()
    )

    paintings_block = "\n\n".join(_format_item_block(it, i + 1) for i, it in enumerate(batch))

    rigor = (
        "Zwroc WYLACZNIE jeden blok ```json {...} ``` bez dodatkowego tekstu."
        if variant == "gpt"
        else "Odpowiedz w bloku ```json ... ```."
    )

    prompt = f"""# GENERATOR TRESCI CYKLU "Obraz na rano, popoludnie i wieczor"

{SHOP_CONTEXT}

## Kanaly social cyklu (4 profile Meta + 2 storefronty):

{channels_block}

- Storefront PL: https://gicleeart.eu
- Storefront EN: https://gicleeart.eu/en-eu

## Twoje zadanie

Wygeneruj tresc do {len(batch)} postow na cykl social media. KAZDY post dotyczy JEDNEGO obrazu i jest publikowany JEDNOCZESNIE na 4 kanalach:
- Facebook PL + Instagram PL (tresc po POLSKU)
- Facebook EN + Instagram EN (tresc po ANGIELSKU)

Dla KAZDEGO obrazu potrzebujesz przygotowac 4 wersje captions (2 jezyki x 2 platformy):
- FB = dluzszy, storytelling, 400-900 slow, moze miec pytania do odbiorcow.
- IG = krotszy ale z mocnym hookiem w 1. zdaniu, 350-1300 znakow, na koncu blok hashtagow.

### Zasady wspolne

1) Ton: elegancki, ciepy, merytoryczny, bez marketingowego pedu. Szanujemy sztuke i czytelnika.
2) ZAWSZE dolaczaj locked hashtagi marki (i pozniej mozesz dodac inne):
   - PL: {locked_pl}
   - EN: {locked_en}
3) Hashtagi: 10-15 lacznie dla IG (w tym locked). Dla FB 3-5 nie wiecej.
4) Nie uzywaj twardej sprzedazy typu "Kup teraz!". Lepiej: "zobacz w naszym sklepie", "dostepne jako giclee na plotnie w naszej galerii".
5) CTA (link w bio / opis): kierujemy na storefront w jezyku posta.

### Zasady kontekstowe (flagi pozycji)

Dla kazdego obrazu masz flagi `is_first_of_artist`, `is_last_of_artist`, `is_new_artist`, `is_new_painting`. Zastosuj:

- `is_first_of_artist=true` i `is_new_artist=false`:
  INTRO. Zaczynamy od zdania w stylu: "Rozpoczynamy nasz cykl z obrazami <ARTYSTA> - malarza/malarki <epoka/szkola>." Potem 1-2 zdania o artyscie (dlaczego warto go poznac), dopiero pozniej wchodzimy w konkretny obraz.

- `is_last_of_artist=true`:
  OUTRO. Na koncu captiona dodaj akapit: "To ostatni obraz <ARTYSTA> w naszej biezacej prezentacji. W kolejnym poscie pokazemy <NEXT_ARTIST>." (uzyj pola `next_artist`). Jesli next_artist jest pusty - napisz "w kolejnym poscie pokazemy nowego artyste".

- `is_new_artist=true`:
  DZWONEK. Zaczynamy od: "Na stronie pojawil sie nowy artysta: <ARTYSTA>. Witamy <JEGO PRAC/JEJ PRAC> w naszej galerii!" Potem 1-2 zdania o artyscie i wchodzimy w obraz. (Flaga zastepuje is_first_of_artist - nie powielaj obu intro).

- `is_new_painting=true` (u istniejacego artysty):
  KOMUNIKAT: "Dolozylismy nowy obraz do naszej kolekcji <ARTYSTA>: <TYTUL>." Potem normalny opis obrazu.

- Gdy zaden z powyzszych flag - normalny post o obrazie.

### Struktura captions

- **FB**: 1. hook (1-2 zdania), 2. historia obrazu / kontekst artystyczny (2-3 akapity, bazuj na podanych 3 akapitach opisu), 3. propozycja aranzacji (gdzie powiesic, do jakiego wnetrza), 4. CTA + link do storefront, 5. 3-5 hashtagow na koncu.

- **IG**: 1. hook (1 zdanie), 2. 2-3 krotkie akapity historia + faktura/detal, 3. CTA "link w bio / zapisz / komentarz", 4. blok hashtagow (10-15) na koncu.

### Zoom hints

Dla kazdego obrazu zaproponuj 3-5 sugestii (po polsku), JAKIE FRAGMENTY warto pokazac w IG karuzeli jako zblizenia. Przyklady: "faktura plotna przy dluzszym oceanie", "detal twarzy postaci z lewej", "refleksy swiatla na falach", "bogata paleta zolci i ugrow w tle".

## Pozycje (obrazy do opisania)

{paintings_block}

## Wynik

{rigor} Schemat:

```json
{{
  "items": [
    {{
      "id": "<uuid z listy powyzej>",
      "pl": {{
        "caption_fb": "...",
        "caption_ig": "...",
        "hashtags": ["#gicleeart", "#..."],
        "zoom_hints": ["...", "...", "..."]
      }},
      "en": {{
        "caption_fb": "...",
        "caption_ig": "...",
        "hashtags": ["#gicleeart", "#..."],
        "zoom_hints": ["...", "...", "..."]
      }}
    }}
  ]
}}
```

WAZNE:
- Pole "id" MUSI dokladnie odpowiadac id-om z listy pozycji (dokladne dopasowanie).
- Kazda pozycja musi miec 4 captions (pl.caption_fb, pl.caption_ig, en.caption_fb, en.caption_ig).
- Zoom hints po polsku dla obu jezykow (to tylko instrukcja dla mnie co sfotografowac).
"""
    return prompt


def _select_batch(
    items: list[storage.CykleItem],
    batch_size: int,
) -> list[storage.CykleItem]:
    """Pobiera kolejne {batch_size} pozycji bez tresci (lub z niekompletna)."""
    out: list[storage.CykleItem] = []
    for it in items:
        if it.status in ("done", "skipped"):
            continue
        if it.manual_override:
            continue
        # Pelna tresc = oba jezyki dla obu platform
        has_pl = bool(it.caption_fb_pl or it.caption_ig_pl or it.caption_pl)
        has_en = bool(it.caption_fb_en or it.caption_ig_en or it.caption_en)
        if has_pl and has_en:
            continue
        out.append(it)
        if len(out) >= batch_size:
            break
    return out


def _format_item_block(item: storage.CykleItem, idx: int) -> str:
    flags = []
    if item.is_first_of_artist:
        flags.append("is_first_of_artist=true")
    if item.is_last_of_artist:
        flags.append("is_last_of_artist=true")
    if item.is_new_artist:
        flags.append("is_new_artist=true")
    if item.is_new_painting:
        flags.append("is_new_painting=true")
    flags_text = " | ".join(flags) if flags else "(pozycja zwykla)"

    return f"""### Pozycja {idx}

- id: `{item.id}`
- Artysta: {item.artist} (pozycja {item.artist_position}/{item.artist_total})
- Tytul PL: {item.painting_title_pl}
- Tytul EN: {item.painting_title_en}
- Flagi: {flags_text}
- next_artist: {item.next_artist or "(brak)"}
- Data publikacji: {item.scheduled_at} (slot: {item.slot})

Opis PL (3 akapity z opisu produktu):
{item.description_pl or "(brak - bazuj tylko na tytule i artyscie)"}

Opis EN (3 akapity z tlumaczenia EN):
{item.description_en or "(brak - bazuj na PL, przetlumacz)"}
"""


# ---------------------------------------------------------------------------
# Parser odpowiedzi
# ---------------------------------------------------------------------------

@dataclass
class LangContent:
    caption_fb: str = ""
    caption_ig: str = ""
    hashtags: list[str] = field(default_factory=list)
    zoom_hints: list[str] = field(default_factory=list)


@dataclass
class ItemContent:
    id: str
    pl: LangContent = field(default_factory=LangContent)
    en: LangContent = field(default_factory=LangContent)


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Pusta odpowiedz.")
    # Wyciagnij blok ```json``` jesli jest
    m = _CODE_FENCE_RE.search(raw)
    candidate = m.group(1).strip() if m else raw
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        # Sprobuj znalezc pierwszy balanced {...}
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(candidate[start:end + 1])
            except json.JSONDecodeError:
                raise ValueError(f"Nie udalo sie sparsowac JSON: {e}") from e
        else:
            raise ValueError(f"Brak JSON w odpowiedzi: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("Odpowiedz nie jest slownikiem JSON.")
    return parsed


def _normalize_hashtags(raw: list[Any], locked: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for entry in (list(raw or []) + list(locked)):
        s = str(entry or "").strip()
        if not s:
            continue
        if not s.startswith("#"):
            s = "#" + s
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def parse_week_response(
    raw: str,
    expected_ids: list[str],
) -> dict[str, ItemContent]:
    """Parsuje odpowiedz Opusa na slownik {id: ItemContent}.

    Rzuca ValueError jesli:
    - brak pola items
    - id nie pasuje do expected_ids
    - brakuje captions w ktorym jezyku.
    """
    data = _extract_json(raw)
    items_raw = data.get("items")
    if not isinstance(items_raw, list):
        raise ValueError("Brak pola 'items' (lista) w odpowiedzi.")
    expected_set = set(expected_ids)

    out: dict[str, ItemContent] = {}
    missing_ids: list[str] = []

    for raw_item in items_raw:
        if not isinstance(raw_item, dict):
            continue
        iid = str(raw_item.get("id") or "").strip()
        if not iid:
            continue
        if iid not in expected_set:
            continue  # ignoruj nieznane id
        pl_raw = raw_item.get("pl") if isinstance(raw_item.get("pl"), dict) else {}
        en_raw = raw_item.get("en") if isinstance(raw_item.get("en"), dict) else {}
        pl = LangContent(
            caption_fb=str(pl_raw.get("caption_fb") or "").strip(),
            caption_ig=str(pl_raw.get("caption_ig") or "").strip(),
            hashtags=_normalize_hashtags(
                pl_raw.get("hashtags") or [],
                hashtag_library.LOCKED_HASHTAGS_PL,
            ),
            zoom_hints=[str(x).strip() for x in (pl_raw.get("zoom_hints") or []) if str(x).strip()],
        )
        en = LangContent(
            caption_fb=str(en_raw.get("caption_fb") or "").strip(),
            caption_ig=str(en_raw.get("caption_ig") or "").strip(),
            hashtags=_normalize_hashtags(
                en_raw.get("hashtags") or [],
                hashtag_library.LOCKED_HASHTAGS_EN,
            ),
            zoom_hints=[str(x).strip() for x in (en_raw.get("zoom_hints") or []) if str(x).strip()],
        )
        if not (pl.caption_fb and pl.caption_ig and en.caption_fb and en.caption_ig):
            missing_ids.append(iid)
            continue
        out[iid] = ItemContent(id=iid, pl=pl, en=en)

    not_found = [eid for eid in expected_ids if eid not in out]
    if missing_ids:
        raise ValueError(
            "Brakuje captions (fb/ig) dla pozycji: " + ", ".join(missing_ids[:5])
            + (f" (+{len(missing_ids) - 5})" if len(missing_ids) > 5 else "")
        )
    if not_found:
        raise ValueError(
            f"Brak tresci dla {len(not_found)} pozycji (spodziewane {len(expected_ids)}, "
            f"otrzymane {len(out)}). Przykladowe brakujace id: {', '.join(not_found[:3])}."
        )
    return out


def apply_to_queue(
    queue: list[storage.CykleItem],
    content_map: dict[str, ItemContent],
) -> int:
    """Wpisuje tresci z content_map do odpowiadajacych pozycji w queue.

    Zwraca liczbe zaktualizowanych pozycji. Pomija pozycje z manual_override=True
    (zeby nie nadpisac recznie edytowanej tresci).
    """
    count = 0
    for it in queue:
        if it.manual_override:
            continue
        c = content_map.get(it.id)
        if c is None:
            continue
        it.caption_fb_pl = c.pl.caption_fb
        it.caption_ig_pl = c.pl.caption_ig
        it.caption_fb_en = c.en.caption_fb
        it.caption_ig_en = c.en.caption_ig
        it.caption_pl = c.pl.caption_fb  # baza PL (uzywana w manual paste)
        it.caption_en = c.en.caption_fb
        it.hashtags_pl = c.pl.hashtags
        it.hashtags_en = c.en.hashtags
        # Merge zoom_hints z PL + EN (unikalne)
        hints_set: list[str] = []
        seen_h: set[str] = set()
        for h in (c.pl.zoom_hints + c.en.zoom_hints):
            k = h.strip().lower()
            if k and k not in seen_h:
                seen_h.add(k)
                hints_set.append(h.strip())
        it.zoom_hints = hints_set[:5]
        if it.status == "pending":
            it.status = "ready"
        count += 1
    return count
