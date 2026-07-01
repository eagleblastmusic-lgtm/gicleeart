"""Prompt Gemini: analiza sceny i parametry korekcji pod druk."""

from __future__ import annotations

ANALYSIS_PROMPT = """Jestes kolorysta przygotowujacym zdjecie klienta do druku wielkoformatowego (papier fine art / akryl).

Przeanalizuj obraz i zaproponuj DELIKATNA korekcje pod druk — nie styl Instagram, nie HDR, nie oversaturacja skory.

Zasady:
- portret: niska saturacja (+0..+4%), ostroznie z cieniami i skora
- pejzaz: lekko wiecej saturacji i kontrastu w oddali OK
- wnetrze / sztuczne swiatlo: korekta balansu bieli (temperature_shift)
- zdjecie telefonu: czesto shadow_lift i lekka ekspozycja
- czarno-biale / minimalistyczne: saturacja ~1.0, subtelny kontrast

Zwrac TYLKO jeden obiekt JSON (bez markdown), pola:
{
  "scene": "krotki identyfikator sceny po angielsku, np. portrait_indoor",
  "exposure": liczba -0.35..0.35 (0 = bez zmiany jaśniej/ciemniej),
  "contrast": liczba 0.85..1.25 (1.0 = bez zmiany),
  "saturation": liczba 0.85..1.20 (1.0 = bez zmiany),
  "shadow_lift": liczba 0..0.35 (podbicie cieni),
  "highlight_recovery": liczba 0..0.25 (sciemnienie swiatel),
  "temperature_shift": liczba -0.15..0.15 (ujemne = chlodniej, dodatnie = cieplej),
  "tint_shift": liczba -0.10..0.10 (zielony/magenta),
  "confidence": liczba 0..1
}

Wartosci maja byc konserwatywne — lepiej za malo niz przesadzic."""
