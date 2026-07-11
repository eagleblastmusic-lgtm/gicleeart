# GICLÉE HOME FLOW — Etap 1

## Cel

`GICLÉE HOME FLOW` jest wspólną osią identyfikacji sekcji oraz faz przejść strony głównej.
Nazwy użytkowe są zapisane per wariant w:

```text
Komponenty/stronaglowna/data/variants/<variant_id>/home_flow.json
```

Zmiana nazwy nie modyfikuje `templates/index.json`, `config/settings_data.json` ani motywu Shopify.

## Stabilne identyfikatory

Sekcje i fazy używają trwałych ID, np.:

```text
section:prehero
phase:portal
phase:hero-rise
section:hero
phase:hero-hold
phase:sound-consent
phase:horizontal-curtain
section:intro
phase:intro-hold
```

Kody prezentacyjne `GH-00`, `GH-01`, `GH-T01` itd. nie są zapisywane. Są wyliczane przy każdym odczycie z aktualnej kolejności. Dodanie nowej sekcji do modelu automatycznie przesuwa numery kolejnych pozycji bez zmiany technicznych ID.

## Interfejs

Komponent ma przycisk `GICLÉE HOME FLOW…`, który otwiera pełną oś z kolumnami:

- kod i nazwa,
- typ: sekcja lub faza,
- stabilne ID techniczne,
- położenie fazy względem sekcji.

Lewy panel `Sekcje strony głównej` korzysta z `Treeview`. Sekcje są wierszami głównymi, a fazy są pokazane pod sekcją, do której należą. Istniejący edytor po prawej nadal jest sterowany przez oryginalny, ukryty `Listbox`, dzięki czemu Etap 1 nie zmienia logiki zapisu treści sekcji.

## Generator pre-Hero

Wersja 1.48.0 rozszerza generator o pełny aktualny zestaw assetów:

- scrub i chrome pre-Hero,
- portal i wjazd Hero,
- poziomą kurtynę,
- live intro,
- centrowanie i matte Hero,
- utility bar,
- pytanie o dźwięk i bramkę odtwarzania,
- synchronizację efektów sekcji Giclée Art.

Generator eksportuje również `introHoldVh`. Dzięki temu główny przycisk `Zapisz` nie powinien usuwać późniejszych faz sekwencji ani ich assetów.

## Granice Etapu 1

Etap 1 pozwala edytować nazwy i identyfikować fazy. Nie zmienia kolejności sekcji Shopify i nie udostępnia jeszcze drag-and-drop. Przesuwanie oraz dodawanie nowych sekcji do `templates/index.json` należy do Etapu 3 i wymaga osobnej walidacji zależności.
