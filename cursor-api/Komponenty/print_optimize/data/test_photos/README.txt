Pierwszy zestaw testowy — wrzuc tutaj wlasne zdjecia (JPG/PNG/WEBP).

W folderze sa juz 3 pliki startowe (01–03) do szybkiego testu pipeline;
do realnej kalibracji dodaj 8–12 **wlasnych** motywow z listy ponizej.

Cel: kalibracja optymalizacji vs Whitewall (pary original / ww70).

Zalecane 8–12 roznych motywow (po 1 pliku kazdego typu):

  1. Portret w swietle dziennym (twarz + tlo)
  2. Portret w sztucznym swietle (zolta poswiata)
  3. Pejzaz z niebem (moze lekko przeswietlone)
  4. Pejzaz z cieniami w lasie / gorskim
  5. Wnetrze (okno, kontrast w pomieszczeniu)
  6. Zdjecie telefonu (niska rozdzielczosc OK)
  7. Czarno-biale lub niska saturacja
  8. Jedzenie / still life (nasycone kolory)
  9. Zdjecie z mocnym kadrem / crop
 10. Stare zdjecie skan / niski kontrast

Nie uzywaj obrazow z cudzych zamowien Whitewall — tylko wlasne pliki.

Potem w GicleeApp: Optymalizacja druku → zakladka «Zestaw testowy»
→ «Zbierz pary z Whitewall» → zakladka «Kalibracja» → «Uruchom kalibracje».

Wymaganie Whitewall: **min. 700×700 px** (obie krawedzie). Mniejsze pliki
(miniaturki 260nw, zdjecia 500 px szerokosci) sa pomijane — patrz
`ww_pairs/collect_skipped.json`.
- Whitewall wymaga uploadu przez panel «SELECT PHOTO» → «UPLOAD PHOTOS» (Playwright robi to automatycznie).
- PNG/WEBP sa konwertowane do JPG przed wyslaniem.
- Pierwszy plik moze potrwac ~30–60 s; przy wielu plikach licz ok. 1 min / zdjecie.
- Na start wystarczy 3–5 roznych motywow (nie 30 naraz).

Wynik: data/ww_pairs/<nazwa>/original.jpg (WW enhancement=0, ten sam kadr co ww70),
ww70.jpg, ww100.jpg, manifest.json
oraz data/ww_pairs/calibration_report.json
