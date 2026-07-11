# Theme Page Editor — Writer Safety WS-1

## Kontrakt operacji

| Operacja | Wariant | Plik motywu | Assety | Shopify |
|---|---:|---:|---:|---:|
| Zapisz wersję | TAK | NIE | NIE | NIE |
| Zastosuj wersję do motywu… | NIE | TAK — bounded delta | jawne | NIE |
| Wdróż motyw… | NIE | NIE | NIE | TAK |

## Zapisz wersję

Zapis dotyczy wyłącznie aktualnego wariantu w `data/variants/<variant_id>/`.
Nieedytowane pola nie są ponownie serializowane. Dzięki temu zapis jednej kontrolki nie może:

- usuwać znaczników HTML z innych pól,
- dodawać domyślnych pól takich jak `image_object_y`,
- zmieniać pozostałych wariantów,
- zmieniać pliku motywu ani assetów.

Przed pierwszym zapisem powstaje osobna baza Apply w:

`data/variant_bases/<variant_id>/<template>.json`

Każdy zapis wariantu tworzy dokładny backup poprzedniej wersji i używa zapisu atomowego.

## Zastosuj wersję do motywu…

Apply nie kopiuje całego wariantu do motywu. Oblicza wyłącznie różnicę:

`variant_base -> aktualny wariant`

Następnie przenosi tę różnicę na świeżo odczytany plik motywu. Zachowane pozostają:

- niezarządzane sekcje,
- niezarządzane pola i bloki,
- kolejność elementów,
- formatowanie HTML w nieedytowanych polach,
- brakujące opcjonalne pola, których użytkownik nie zmienił.

Pusty asset efektów nie jest przepisywany tylko po to, aby zmienić identyfikator wariantu.

Apply pokazuje unified diff, wymaga frazy `ZASTOSUJ <variant_id>`, ponownie kontroluje hashe i tworzy dokładne backupy. Po poprawnym Apply baza wersji przesuwa się do aktualnego wariantu.

## Wdróż motyw…

Deploy wdraża wyłącznie stan plików znajdujących się już na dysku. Nie zapisuje wariantu i nie wykonuje Apply.

## Regresje wykryte podczas testów

### WS-1.1

Kontekst przycisków był rozwiązywany przed zakończeniem budowy UI. Poprawiono go na rozwiązywanie w chwili kliknięcia.

### WS-1.2

Pierwszy bounded preview pokazał, że pełne ponowne serializowanie wszystkich kontrolek powodowało dodatkowe zmiany HTML i domyślne `image_object_y`. Wprowadzono minimalny zapis kontrolki oraz Apply wyłącznie na podstawie delta wariantu.
