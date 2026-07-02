"""Definicje 4 kanalow cyklu + sloty czasowe.

Kazdy kanal = jedna strona/profil Meta + jezyk.

URL-e stron (CTA, hint w UI). Dla Facebooka w UI preferujemy link
`https://www.facebook.com/{page_id}` (staly, z creds) — vanity URL bywa nieaktualny.
- FB PL:   page_id w meta_credentials (np. …330579) -> facebook.com/{id}
- FB EN:   j.w.
- IG PL:   https://www.instagram.com/gicleeart.polska/
- IG EN:   https://www.instagram.com/gicleeart.europe/
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    code: str           # "fb_pl" | "fb_en" | "ig_pl" | "ig_en"
    label: str          # "Facebook PL"
    icon: str           # emoji
    color: str          # hex
    language: str       # "pl" | "en"
    platform: str       # "fb" | "ig"
    page_url: str       # publiczny URL profilu/strony
    store_url: str      # docelowy URL sklepu dla tego jezyka (storefront)


CHANNELS: dict[str, Channel] = {
    "fb_pl": Channel(
        code="fb_pl", label="Facebook PL", icon="F", color="#1877f2",
        language="pl", platform="fb",
        page_url="https://www.facebook.com/518592191330579",
        store_url="https://gicleeart.eu",
    ),
    "fb_en": Channel(
        code="fb_en", label="Facebook EN", icon="F", color="#1877f2",
        language="en", platform="fb",
        page_url="https://www.facebook.com/1120189217838817",
        store_url="https://gicleeart.eu/en-eu",
    ),
    "ig_pl": Channel(
        code="ig_pl", label="Instagram PL", icon="I", color="#e1306c",
        language="pl", platform="ig",
        page_url="https://www.instagram.com/gicleeart.polska/",
        store_url="https://gicleeart.eu",
    ),
    "ig_en": Channel(
        code="ig_en", label="Instagram EN", icon="I", color="#e1306c",
        language="en", platform="ig",
        page_url="https://www.instagram.com/gicleeart.europe/",
        store_url="https://gicleeart.eu/en-eu",
    ),
}

CHANNEL_ORDER = ["fb_pl", "fb_en", "ig_pl", "ig_en"]


def all_channels() -> list[Channel]:
    return [CHANNELS[c] for c in CHANNEL_ORDER if c in CHANNELS]


def get(code: str) -> Channel | None:
    return CHANNELS.get(code)


def public_profile_url(channel_code: str, creds: dict) -> str:
    """Publiczny URL profilu do otwarcia w przegladarce.

    FB: jesli w creds jest numeryczny page_id, uzyj facebook.com/{id}
    (stabilniejsze niz vanity). IG: `page_url` z kanalu (URL oparty o @username).
    """
    ch = CHANNELS.get(channel_code)
    if ch is None:
        return ""
    if ch.platform == "fb":
        pid = str(creds.get("page_id") or "").strip()
        if pid.isdigit():
            return f"https://www.facebook.com/{pid}"
        return ch.page_url
    return ch.page_url


def by_language(language: str) -> list[Channel]:
    return [c for c in all_channels() if c.language == language]


# ---------------------------------------------------------------------------
# Sloty czasowe
# ---------------------------------------------------------------------------

SLOT_CODES = ("morning", "afternoon", "evening")

DEFAULT_SLOT_TIMES: dict[str, str] = {
    "morning": "08:00",
    "afternoon": "14:00",
    "evening": "20:00",
}

SLOT_LABEL_PL: dict[str, str] = {
    "morning": "Rano",
    "afternoon": "Popoludnie",
    "evening": "Wieczor",
}


# Limity caption przejete z Komponenty/socialmedia/platforms.py
# (dla publishera uzywamy ich do obcinania / walidacji)
CAPTION_LIMITS: dict[str, int] = {
    "fb": 63206,    # de facto nieograniczone
    "ig": 2200,
}

# Rekomendowane dlugosci captions (do walidatora)
RECOMMENDED_LEN: dict[str, tuple[int, int]] = {
    "fb": (400, 900),      # FB lubi dluzsze storytelling
    "ig": (350, 1300),     # IG feed - srednio dluzsze z hashtagami na koncu
}


# Limity hashtagow
HASHTAG_LIMITS: dict[str, int] = {
    "fb": 10,
    "ig": 30,
}

HASHTAG_RECOMMENDED: dict[str, int] = {
    "fb": 5,
    "ig": 15,
}
