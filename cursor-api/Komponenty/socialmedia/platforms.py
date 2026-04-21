"""Definicje platform social media z ich regulami.

Kazda platforma ma:
- kod (stable id uzywany w storage)
- nazwa wyswietlana
- limity znakow (caption, title, hashtagi)
- rekomendowana liczba hashtagow
- orientacja zdjecia / format
- rekomendowany ton / dlugosc tekstu
- ikonka + kolor (dla GUI)
- guidance dla LLM (jak pisac pod te platforme)

Wszystko zebrane w jednym miejscu, zeby prompty i planer korzystaly z tych samych reguly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Platform:
    code: str                      # stable ID, np. "ig_feed"
    label: str                     # np. "Instagram Feed"
    icon: str                      # emoji
    color: str                     # hex
    caption_limit: int             # max znakow w caption
    hashtag_limit: int             # max liczba hashtagow
    recommended_hashtags: int      # ile sugerowac w generatorze
    recommended_words: tuple[int, int]  # (min, max) slow w caption
    format_hint: str               # np. "1:1 lub 4:5 (1080x1080 lub 1080x1350)"
    tone: str                      # krotki opis tonu dla LLM
    structure: str                 # struktura caption dla LLM


PLATFORMS: dict[str, Platform] = {
    "ig_feed": Platform(
        code="ig_feed",
        label="Instagram Feed",
        icon="📷",
        color="#e1306c",
        caption_limit=2200,
        hashtag_limit=30,
        recommended_hashtags=15,
        recommended_words=(60, 150),
        format_hint="Kwadrat 1:1 (1080x1080) lub pionowy 4:5 (1080x1350). Wysoka jakosc, estetyka wazna.",
        tone="Estetyczny, inspirujacy, osobisty, krotkie zdania, 1-2 emoji na akapit.",
        structure=(
            "1) Hook w 1. zdaniu - pytanie, stwierdzenie lub emocja zatrzymujaca scrollujacego. "
            "2) 2-3 krotkie akapity: historia, ciekawostka, kontekst obrazu/produktu. "
            "3) CTA (link w bio, komentarz, zapisanie). "
            "4) Na koncu BLOK hashtagow - 12-15 mieszanka marki + niszowe + popularne."
        ),
    ),
    "ig_stories": Platform(
        code="ig_stories",
        label="Instagram Stories",
        icon="✨",
        color="#fd79a8",
        caption_limit=200,       # tekst na sticker
        hashtag_limit=10,
        recommended_hashtags=3,
        recommended_words=(5, 25),
        format_hint="Pionowy 9:16 (1080x1920). Short-lived 24h.",
        tone="Bezposredni, live, emoji, pytania i polls, duza czcionka.",
        structure=(
            "1) Bardzo krotki hook (1 linia, max 8-10 slow). "
            "2) Opcjonalny CTA (swipe up / link / DM). "
            "3) Maks 3 hashtagi (mniej jest lepiej w Stories)."
        ),
    ),
    "ig_reels": Platform(
        code="ig_reels",
        label="Instagram Reels",
        icon="🎬",
        color="#a55eea",
        caption_limit=2200,
        hashtag_limit=30,
        recommended_hashtags=10,
        recommended_words=(30, 120),
        format_hint="Pionowy 9:16 (1080x1920), video 15-90s. Hook w pierwszych 3 sekundach!",
        tone="Dynamiczny, szybki, konwersacyjny, z zaskoczeniem albo 'reveal'.",
        structure=(
            "1) Scenariusz 3-5 ujec (opisz co widac w kazdym: hook, budowanie napiecia, reveal, CTA). "
            "2) On-screen text: 3-5 krotkich napisow do nalozenia na video. "
            "3) Caption pod video: krotki opis + CTA + 8-12 hashtagow. "
            "4) Propozycja trendujacego dzwieku (mozesz opisac stylem: 'spokojna fortepianowa melodia' itp.)."
        ),
    ),
    "fb": Platform(
        code="fb",
        label="Facebook",
        icon="📘",
        color="#1877f2",
        caption_limit=63206,
        hashtag_limit=10,
        recommended_hashtags=3,
        recommended_words=(100, 300),
        format_hint="Kwadrat 1:1 lub poziomy 1.91:1 (1200x628 dla linków).",
        tone="Dluzszy, bardziej edukacyjny niz IG. Mozna linkowac i rozwijac historie.",
        structure=(
            "1) Pierwsze 2-3 linie musza zachecic do kliknniecia 'zobacz wiecej'. "
            "2) Dluga tresc: historia, edukacja, kontekst. Mozna uzywac podzialow pustymi liniami. "
            "3) Pytanie na koncu zeby pobudzic komentarze. "
            "4) Link do produktu/bloga (FB karze posty z linkami, ale nadal warto). "
            "5) Maks 3-5 hashtagow (na FB maja slabszy efekt niz na IG)."
        ),
    ),
    "tiktok": Platform(
        code="tiktok",
        label="TikTok",
        icon="🎵",
        color="#000000",
        caption_limit=2200,
        hashtag_limit=30,
        recommended_hashtags=5,
        recommended_words=(10, 50),
        format_hint="Pionowy 9:16 (1080x1920), video 15-60s. Hook w 2 sekundach.",
        tone="Autentyczny, szorstki, viralowy, humor i zaskoczenie lubiane.",
        structure=(
            "1) Scenariusz 3-4 ujec video: hook (1s), dev (3-5s), reveal (5-10s), CTA (last 2s). "
            "2) On-screen text: 2-4 krotkie zdania. "
            "3) Caption krotki + CTA + 4-6 hashtagow (mieszanka niszowych i trend). "
            "4) Sugestia trendujacego dzwieku."
        ),
    ),
    "pinterest": Platform(
        code="pinterest",
        label="Pinterest",
        icon="📌",
        color="#e60023",
        caption_limit=500,         # description
        hashtag_limit=20,
        recommended_hashtags=0,    # Pinterest nie uzywa hashtagow - keywords w tytule/opisie
        recommended_words=(50, 100),
        format_hint="Pionowy 2:3 (1000x1500) lub 1:2.1. Jakosc wizualna krytyczna.",
        tone="SEO-friendly, keyword-rich, eleganckie nazewnictwo, brak emoji.",
        structure=(
            "1) Tytul pina (100 znakow): chwytliwy + slowa kluczowe ('Jak zaaranzowac salon w stylu...'). "
            "2) Description (300-500 znakow): 2-3 akapity z naturalnie wplecionymi keywords. "
            "3) URL docelowy (link do produktu lub artykulu bloga). "
            "4) 5-10 keywords / tagow (lowercase, long-tail). "
            "5) NIE uzywaj emoji - Pinterest ich nie lubi w wyszukiwarce."
        ),
    ),
}


PLATFORM_ORDER = ["ig_feed", "ig_stories", "ig_reels", "fb", "tiktok", "pinterest"]


def get(code: str) -> Platform | None:
    return PLATFORMS.get(code)


def all_platforms() -> list[Platform]:
    return [PLATFORMS[code] for code in PLATFORM_ORDER if code in PLATFORMS]


LANGUAGES: list[tuple[str, str]] = [
    ("pl", "polski"),
    ("en", "angielski"),
]


def lang_label(code: str) -> str:
    for c, label in LANGUAGES:
        if c == code:
            return label
    return code
