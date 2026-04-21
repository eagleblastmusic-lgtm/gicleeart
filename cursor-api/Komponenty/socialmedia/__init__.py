"""Komponent Social Media - generator treści i planer postów.

Dwie główne funkcje:
- Generator treści: temat + platforma + język -> prompt do Opus/GPT -> wklejona odpowiedź
  -> podgląd -> zapis do planera.
- Planer postów: kolejka zaplanowanych postów ze statusami (pending/in_progress/done),
  edycja, kopiowanie caption, otwieranie obrazka, eksport CSV.

Obsługiwane platformy: Instagram Feed, Instagram Stories, Instagram Reels,
Facebook, TikTok, Pinterest. Dwa profile językowe: PL i EN.
"""
