# Segregator plików (`segregatorplikow`)

Komponent subprocess GicleeApp do szybkiego sortowania plików — przeciągnięcie na kafelek reprezentujący folder docelowy.

## Uruchomienie

```bash
cd cursor-api
python -m Komponenty.segregatorplikow
```

Lub kafelek w launcherze (sekcja **Narzędzia pomocnicze**) / Studio (kategoria **System**).

## Konfiguracja

| Plik | Rola |
|------|------|
| `data/tiles.example.json` | **Szablon w repo** — pusta struktura `{ "version": 1, "tiles": [] }` |
| `data/tiles.json` | **Lokalna konfiguracja użytkownika** — tworzona przy pierwszym zapisie kafelka; **nie commitować** (zawiera prywatne ścieżki dysku) |

Przykładowa struktura `tiles.json` po skonfigurowaniu:

```json
{
  "version": 1,
  "tiles": [
    {
      "id": "uuid",
      "name": "Obrazy",
      "path": "D:/Giclee/Obrazy",
      "children": [
        {
          "id": "uuid",
          "name": "Do obróbki",
          "path": "D:/Giclee/Obrazy/Do obrobki",
          "children": []
        }
      ]
    }
  ]
}
```

- Kafelki główne (parent) + podkafelki max **1 poziom** głębokości.
- API zapisu: `storage.load_tiles()` / `storage.save_tiles()`.
- Gdy `tiles.json` nie istnieje, `load_tiles()` zwraca pusty store — aplikacja startuje normalnie.

## Przepływ operacji

1. Użytkownik przeciąga pliki na kafelek **lub** wybiera pliki i klika kafelek.
2. Foldery są odfiltrowywane (MVP — tylko pliki).
3. `move_service.plan_moves()` buduje plan (dry-run).
4. **Bez konfliktu nazw** w folderze docelowym: od razu `shutil.move` + toast.
5. **Konflikt nazw** (plik o tej samej nazwie już istnieje): dialog podglądu ze źródłem, celem, statusem i polityką duplikatów.
6. W dialogu dopiero klik **Przenieś** (+ potwierdzenie) wywołuje przeniesienie.

**Drop bez konfliktu nie pokazuje podglądu.**

## Duplikaty

Gdy plik docelowy istnieje:

| Polityka | Zachowanie |
|----------|------------|
| Zmień nazwę (domyślna) | `plik.jpg` → `plik (1).jpg` |
| Pomiń | Plik nie jest przenoszony |
| Anuluj | Cała operacja anulowana |
| Zastąp | **Wyłączone w MVP** (kolejna wersja) |

Brak automatycznego nadpisywania.

## Współdzielone moduły

| Moduł | Użycie |
|-------|--------|
| `_shared/tkdnd_safe.py` | `register_drop_target`, `parse_dnd_files` |
| `_shared/toast.py` | `show_toast` |
| `_shared/activity_log.py` | `append_activity` |
| `_shared/activity_log_ui.py` | globalny dziennik |
| `_shared/tk_scroll.py` | przewijanie siatki kafelków |

## Pliki

| Plik | Rola |
|------|------|
| `gui.py` | UI, kafelki, DnD, log sesji |
| `storage.py` | model i zapis `tiles.json` |
| `move_service.py` | planowanie i wykonanie move |
| `dialogs.py` | edycja kafelka, podgląd operacji |
| `component.json` | metadane launchera |

## Zależności

`requirements.txt`: `tkinterdnd2>=0.4.0` (opcjonalne — fallback bez DnD).

## Logi

- Sesja: panel w oknie komponentu.
- Globalny: `_shared/data/activity_log.jsonl` przez `append_activity`.
- Subprocess stdout: `cursor-api/logs/segregatorplikow.log`.
