# Karuzela Theme Writer Safety

## Status

Runtime Foundation / Writer Export Safety dla `Komponenty/karuzela`.

Base:

`master` @ `468fd381b708ee2c01832ac9b7b6695438c3e7fc`

Inventory przed etapem: **10**.

Oczekiwana delta: **10 → 8**.

## Klasyfikacja

`assets/giclee-carousel-config.js` jest śledzonym plikiem źródłowym motywu Shopify.

Zmiana tego pliku jest intencjonalnym writerem źródłowym, lecz nie może być skutkiem ubocznym zwykłego zapisu ustawień ani otwarcia podglądu.

Writer lokalnego pliku motywu nie jest:

- deployem Shopify,
- mutacją Admin API,
- synchronizacją live theme,
- automatyczną publikacją.

## Problem przed etapem

`save_karuzela_settings()` oraz pojedyncze settery zapisywały ustawienia aplikacji i natychmiast wywoływały `write_theme_config()`.

`write_theme_config()`:

- tworzył source-derived katalog `assets`,
- bezpośrednio nadpisywał `giclee-carousel-config.js`,
- nie pokazywał diffu,
- nie sprawdzał stale-state,
- nie wymagał osobnej zgody,
- nie tworzył zewnętrznej kopii bezpieczeństwa.

W rezultacie przyciski **Zapisz** i **Otwórz podgląd** mogły zmieniać śledzony plik motywu.

## Kontrakt po etapie

1. `save_settings()`, `save_karuzela_settings()` i pojedyncze settery zapisują wyłącznie ustawienia aplikacji.
2. **Zapisz** nie zmienia motywu.
3. **Otwórz podgląd** nie zmienia motywu.
4. Motyw zmienia tylko osobna akcja **Zastosuj do motywu…**.
5. Plan writer-a:
   - ma jeden bounded target,
   - zawiera bytes przed i po,
   - zawiera SHA-256 przed i po,
   - zawiera unified diff,
   - nie wykonuje zapisu.
6. Apply wymaga frazy `ZASTOSUJ KARUZELĘ`.
7. Apply ponownie rozwiązuje jedyny dozwolony target i odrzuca retargeted plan.
8. Apply porównuje bieżący hash z hashem z preview i blokuje stale-state.
9. Wersja „przed” jest kopiowana dokładnie do Local AppData `backups/Komponenty/karuzela/theme_config/`.
10. Zapis jest atomowy i po zapisie weryfikowany końcowym SHA.
11. Brak zmian nie tworzy backupu i nie przepisuje pliku.
12. Etap nie wykonuje deployu ani Shopify mutation.

## Zakres

- `cursor-api/Komponenty/karuzela/service.py`
- `cursor-api/Komponenty/karuzela/gui.py`
- `cursor-api/tests/test_karuzela_writer_safety.py`
- `cursor-api/docs/komponenty/karuzela.md`
- `cursor-api/docs/repository_safety/KARUZELA_THEME_WRITER_SAFETY.md`

## Testy

Testy kontraktu obejmują:

- zwykły zapis ustawień bez zmiany motywu;
- pojedyncze settery bez zmiany motywu;
- read-only plan i deterministyczny diff;
- błędną frazę potwierdzającą;
- stale-state;
- exact-target lock;
- udany atomowy zapis;
- backup poza repo;
- no-op bez backupu;
- rozdzielone akcje GUI;
- brak findingów analizatora dla `Komponenty/karuzela/service.py`.

## Rollback

Rollback kodu odbywa się przez rewert merge commita etapu.

Jeżeli lokalny asset został wcześniej zastosowany przez writer, backup dokładnych bytes „przed” pozostaje w Local AppData. Przywrócenie pliku jest oddzielną, świadomą operacją — rollback kodu nie nadpisuje automatycznie motywu.
