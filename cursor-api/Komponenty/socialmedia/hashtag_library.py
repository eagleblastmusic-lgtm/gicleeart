"""Biblioteka hashtagow - stale tagi GicleeArt + helpers dla generatora.

Stale (locked) hashtagi sa zawsze dolaczane do kazdego posta na IG/TikTok,
zeby budowac rozpoznawalnosc marki i usprawnic wyszukiwanie profilowe.

Osobna lista per jezyk (PL vs EN), bo hashtagi PL nie maja sensu w profilu EN
i odwrotnie.
"""

from __future__ import annotations

LOCKED_HASHTAGS_PL: list[str] = [
    "#gicleeart",
    "#reprodukcjagiclee",
    "#obrazynaplotnie",
    "#sztukawdomu",
    "#dekoracjascian",
]

LOCKED_HASHTAGS_EN: list[str] = [
    "#gicleeart",
    "#gicleeprint",
    "#canvasart",
    "#fineartprint",
    "#walldecor",
]

# Propozycje hashtagow dla generatora - pozwalaja zasugerowac LLM konkretne trendy.
SUGGESTED_THEMES_PL: list[str] = [
    "#sztukaklasyczna", "#malarstwo", "#monet", "#vangogh", "#klimt",
    "#wnetrzeartystyczne", "#aranzacjawnetrz", "#boho", "#glamour",
    "#salonskandynawski", "#obrazdosalonu", "#prezentpersonalizowany",
    "#fotonaplotnie", "#zdjecienaplotnie", "#rodzinneplotno",
    "#slubnaplotnie", "#pamiatkazepodrozy",
]

SUGGESTED_THEMES_EN: list[str] = [
    "#classicalart", "#painting", "#monet", "#vangogh", "#klimt",
    "#interiordesign", "#bohemian", "#glamour", "#scandinavianhome",
    "#livingroomdecor", "#personalizedgift", "#photocanvas",
    "#familyphotocanvas", "#weddingcanvas", "#travelmemories",
]


def locked_for(language: str) -> list[str]:
    lc = (language or "").lower()
    if lc == "en":
        return LOCKED_HASHTAGS_EN
    if lc == "oba":
        return merge_unique(LOCKED_HASHTAGS_PL, LOCKED_HASHTAGS_EN)
    return LOCKED_HASHTAGS_PL


def suggested_for(language: str) -> list[str]:
    lc = (language or "").lower()
    if lc == "en":
        return SUGGESTED_THEMES_EN
    if lc == "oba":
        return merge_unique(SUGGESTED_THEMES_PL, SUGGESTED_THEMES_EN)
    return SUGGESTED_THEMES_PL


def merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for tag in group:
            t = tag.strip()
            if not t:
                continue
            if not t.startswith("#"):
                t = "#" + t
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
    return out
