# LC-7 — launcher navigation view cache

## Cel

Ograniczyć koszt przechodzenia między indeksem kategorii i ekranami komponentów bez zmiany istniejącego modelu nawigacji, renderera, DnD ani lifecycle widoków inline.

## Zakres

- `launcher_navigation_cache.py` definiuje neutralne klucze i sygnatury ekranów oraz mały cache bez zależności od Tk i I/O;
- `cached_navigation_launcher.py` przechowuje gotowe ramki Tk dla indeksu, pustych stanów i poszczególnych kategorii;
- kanoniczny `LauncherApp` wskazuje na `CachedNavigationGicleeApp`;
- dotychczasowy `DragDropCategoryGicleeApp` pozostaje niezmienioną warstwą bazową i zachowuje własny entrypoint.

## Zachowanie cache

- pierwszy dostęp do ekranu buduje widgety dotychczasowym rendererem;
- kolejny dostęp używa istniejącej ramki, odtwarza listę aktywnych celów DnD, tytuł okna i podtytuł;
- indeks kategorii jest unieważniany po zmianie dowolnej sekcji, kolejności albo metadanych widocznych komponentów;
- ekran pojedynczej kategorii jest unieważniany wyłącznie po zmianie tej kategorii;
- stara ramka jest niszczona przed przebudową, więc cache nie zachowuje nieaktualnych callbacków komponentów;
- puste stany mają osobne klucze i nie kolidują z indeksem ani kategoriami.

## Granice bezpieczeństwa

- brak zapisu danych, konfiguracji i stanu użytkownika;
- brak zmian w `launcher_layout.json`, komponentach, Shopify, deployu i usługach tła;
- brak cache widoków inline — ich istniejący lifecycle pozostaje bez zmian;
- brak zmiany przewijania LC-5/PR #140; etap ultra smooth pozostaje osobnym przyszłym zadaniem;
- cache działa wyłącznie w klasycznym launcherze; Studio Preview i profil produkcyjny Studio pozostają odseparowane.

## Inwalidacja

Sygnatura komponentu obejmuje folder, ścieżkę pakietu, nazwę, opis, ikonę, kolor, kolejność, tryb, URL, hidden, availability, stability i `extras`. Wartości zagnieżdżone są zamrażane do stabilnej postaci hashowalnej.

## Walidacja

Minimalny zestaw:

```powershell
python -m pytest -q tests/test_launcher_navigation_cache.py tests/test_cached_navigation_launcher.py tests/test_launcher_app_composition.py
python -m compileall -q giclee_app tests
```

Pełny Stage 2 CI pozostaje obowiązkową bramką przed merge.
