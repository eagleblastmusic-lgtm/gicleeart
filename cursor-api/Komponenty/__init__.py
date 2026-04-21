"""Folder z komponentami GicleeApp.

Kazdy podkatalog to osobny komponent (pakiet Pythona) z `__main__.py`.
GicleeApp dynamicznie wykrywa komponenty i wyswietla je jako kafelki.

Konwencja:
- folder z `__main__.py` = komponent uruchamiany przez `python -m Komponenty.<nazwa>`,
- opcjonalny `component.json` (manifest) z polami:
    {
      "name": "Wyswietlana nazwa",
      "description": "Krotki opis",
      "icon": "emoji albo sciezka do PNG",
      "color": "#1e88e5"
    }
- jesli brak `component.json`, GicleeApp uzywa nazwy folderu i pierwszej linijki
  docstring z `__init__.py`.
"""
