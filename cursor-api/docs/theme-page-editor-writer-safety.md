# Theme Page Editor — Writer Safety WS-1

## Cel

WS-1 rozdziela trzy wcześniej połączone operacje wspólnego edytora stron:

| Operacja | Wariant | Plik motywu | Asset efektów | Shopify |
|---|---:|---:|---:|---:|
| **Zapisz wersję** | TAK | NIE | NIE | NIE |
| **Zastosuj wersję do motywu…** | NIE | TAK, bounded | TAK, jawnie | NIE |
| **Wdróż motyw…** | NIE | NIE | NIE | TAK |

## Zapisz wersję

Przycisk zapisuje wyłącznie:

`Komponenty/<komponent>/data/variants/<variant_id>/<plik>.json`

Zapis:

- dotyczy tylko aktualnie wybranej wersji,
- tworzy dokładną kopię poprzedniego pliku wariantu,
- używa SHA-256 do wykrywania zmian wykonanych poza edytorem,
- zapisuje przez plik tymczasowy i `os.replace`,
- nie zmienia pliku motywu,
- nie generuje assetów,
- nie uruchamia deployu.

Kopie wariantów trafiają do:

`data/variant_backups/<variant_id>/`

## Przełączanie i dodawanie wersji

Przełączenie wersji wczytuje wyłącznie jej dane i aktualizuje lokalny manifest
komponentu. Nie stosuje wersji do motywu.

`Dodaj nową…` tworzy niezależną kopię katalogu aktualnej wersji. Późniejsze
zmiany nowej kopii nie modyfikują wersji źródłowej.

Zmiana nazwy modyfikuje wyłącznie etykietę w `manifest.json`.

## Zastosuj wersję do motywu…

Operacja zawsze zaczyna od świeżego pliku motywu odczytanego z dysku.

Następnie:

1. wczytuje zapisaną wersję,
2. stosuje tylko pola zadeklarowane w `config.zones`,
3. zachowuje niezarządzane sekcje, bloki, pola i kolejność,
4. pokazuje pełny unified diff,
5. wymaga frazy `ZASTOSUJ <variant_id>`,
6. ponownie sprawdza hash każdego celu,
7. tworzy dokładne kopie bajtowe,
8. zapisuje atomowo,
9. nie uruchamia Shopify ani deployu.

Kopie zastosowania trafiają do:

`data/apply_backups/<variant_id>/`

Jeżeli komponent ma efekty sekcji, asset efektów jest pokazany w tym samym
podglądzie i objęty tą samą kontrolą hashów. Komponenty `settings_only` nie
generują pustego assetu efektów.

## Wdróż motyw…

Deploy wykorzystuje wyłącznie stan plików motywu znajdujących się już na dysku.

Nie zapisuje wersji, nie stosuje wersji i nie generuje assetów. Przed wyborem
środowiska pokazuje jawne ostrzeżenie, że niezapisane dane edytora nie zostaną
uwzględnione.

## Giclée Frame

Dla `Komponenty/gicleeframe`:

- `Wersja 1` i `Wersja 2` pozostają niezależne,
- `Zapisz wersję` zmienia tylko `data/variants/gfX/page.giclee-frame.json`,
- `Zastosuj wersję do motywu…` zmienia tylko pola Giclée Frame w
  `templates/page.giclee-frame.json`,
- niezarządzane sekcje i ustawienia tego pliku pozostają zachowane.
