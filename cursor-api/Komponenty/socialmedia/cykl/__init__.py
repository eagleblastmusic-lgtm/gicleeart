"""Cykl - 'Obraz na rano, popoludnie i wieczor'.

Subpackage komponentu socialmedia. Realizuje automatyczny harmonogram
publikacji 3 postow dziennie (08:00/14:00/20:00) w 4 kanalach:
- Facebook PL (GicleeArtPolska)
- Facebook EN (GicleeArtEurope)
- Instagram PL (gicleeart.polska)
- Instagram EN (gicleeart.europe)

Kolejka jest budowana z kolekcji artystow w Shopify (sortowanie alfabetyczne
po nazwisku). Dla kazdego obrazu: intro/outro na pierwszym/ostatnim obrazie
artysty, automatyczne wciskanie nowych artystow i nowych obrazow.

Tresc captions generowana przez Opus batchem na tydzien. Publikacja przez
Meta Graph API v19 (wymaga konfiguracji tokenow w meta_credentials.json).

Entry point dla widoku: cykl.view.build_view(parent, on_back).
"""
