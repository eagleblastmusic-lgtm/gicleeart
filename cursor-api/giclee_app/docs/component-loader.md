# Component loader (`component_loader.py`)

Hub GicleeApp: [`README.md`](README.md)

---

## Reguła discovery

Komponent = podkatalog `Komponenty/<nazwa>/` z plikiem **`__main__.py`**.

Opcjonalny **`component.json`**:

```json
{
  "name": "Wyświetlana nazwa",
  "description": "Krótki opis",
  "icon": "🎨",
  "color": "#1e88e5",
  "order": 10,
  "mode": "subprocess",
  "url": ""
}
```

| Pole | Domyślnie |
|------|-----------|
| `name` | nazwa folderu |
| `description` | pierwsza linia docstring `__init__.py` |
| `mode` | `subprocess` |
| `order` | 1000 (sort w sekcji „Inne”) |

Tryby `mode`:

- **`subprocess`** — wymaga `__main__.py`
- **`inline`** — wymaga `view.py` z klasą/widokiem montowanym w launcherze
- **`url`** — wymaga `url` w JSON (otwiera przeglądarkę)

---

## Dodawanie komponentu (checklist)

1. `Komponenty/<nazwa>/__init__.py`
2. `Komponenty/<nazwa>/__main__.py` z `main()` (subprocess) **lub** `view.py` (inline)
3. Opcjonalnie `component.json`, `requirements.txt`
4. Odśwież launcher (auto co 3 s)

Przykład subprocess:

```python
from .gui import main

if __name__ == "__main__":
    main()
```

---

## Dlaczego kafelek się nie pojawia

| Przyczyna | Fix |
|-----------|-----|
| Brak `__main__.py` (subprocess) | Dodaj entry point |
| Brak `view.py` (inline) | Dodaj widok inline |
| Błąd importu przy skanowaniu | Sprawdź logi / uruchom `python -m Komponenty.<nazwa>` ręcznie |
| Folder poza `Komponenty/` | Musi być bezpośrednio pod `Komponenty/` |

→ [`troubleshooting.md`](troubleshooting.md)

---

## Powiązane

- Lista komponentów: [`README.md`](README.md)
- Szczegóły per komponent: [`../../docs/komponenty/README.md`](../../docs/komponenty/README.md)
