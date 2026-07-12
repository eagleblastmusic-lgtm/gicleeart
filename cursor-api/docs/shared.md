# Moduły współdzielone (`Komponenty/_shared`)

Hub warstwy API: [`README.md`](README.md)

Folder: `cursor-api/Komponenty/_shared/`

---

## Pliki

| Moduł | Rola | Używany przez |
|-------|------|---------------|
| `auth.py` | Hasło startowe aplikacji | GicleeApp, komponenty wrażliwe |
| `activity_log.py` | Dziennik zdarzeń JSONL w zewnętrznym AppData | Wszystkie komponenty (log akcji) |
| `activity_log_ui.py` | Okno podglądu + kopiowanie | GicleeApp toolbar |
| `task_notify.py` | Dźwięk po zakończeniu batcha | `dodajobraz`, inne kolejki |
| `fx_rates.py` | Kursy NBP (cache 24h) | Dialog rynków w `dodajobraz` |
| `window_geometry.py` | Centrowanie okien Tk | GicleeApp, dialogi |
| `tile_grid.py` | Siatka kafelków (inline views) | `blog`, `socialmedia`, `zadania` |
| `help_dialog.py` | Okno pomocy | Komponenty z HELP_TEXT |
| `tree_sort.py` | Sortowanie Treeview | `produkcja`, planery |
| `toast.py`, `notifications.py` | Powiadomienia UI | Różne GUI |
| `backup.py` | Kopie zapasowe; nowe ZIP-y i stan harmonogramu w AppData | Launcher |

---

## Zewnętrzne ścieżki runtime

Wspólny resolver znajduje się w `giclee_app/app_paths.py`.

- dane i cache: `%LOCALAPPDATA%\GicleeArt\GicleeApp\data\`,
- logi: `%LOCALAPPDATA%\GicleeArt\GicleeApp\logs\`,
- backupy: `%LOCALAPPDATA%\GicleeArt\GicleeApp\backups\`,
- konfiguracja: `%APPDATA%\GicleeArt\GicleeApp\config\`.

Odczyt pozostaje kompatybilny z istniejącymi plikami przy kodzie, ale nowe zapisy nie mogą modyfikować legacy source tree. Testy mogą nadpisać korzenie przez `GICLEEAPP_LOCAL_ROOT` i `GICLEEAPP_ROAMING_ROOT`.

---

## activity_log

Format: JSONL, jedna linia = jedno zdarzenie.

```python
from Komponenty._shared.activity_log import append_activity
append_activity("dodajobraz", "Utworzono produkt", detail="Hans Dahl - Babie lato")
```

Przy pierwszym zapisie istniejący legacy `Komponenty/_shared/data/activity_log.jsonl` jest kopiowany jednokrotnie do zewnętrznego katalogu logów. Plik legacy pozostaje nietknięty.

Podgląd: GicleeApp → **Dziennik akcji**

---

## backup

Nowe archiwa i `.last_run.json` są zapisywane poza repozytorium. Lista backupów korzysta z legacy `cursor-api/backups/` tylko wtedy, gdy nie ma jeszcze zewnętrznych archiwów. Zakres zbieranych plików oraz kontrakt ręcznego restore nie zostały zmienione w tym etapie.

---

## fx_rates (NBP)

- API: https://api.nbp.pl (bez klucza)
- Cache: `data/fx_cache.json` (24h)
- Używane przy liczeniu cen rynkowych EUR/PLN w komponencie **zmienceny** (widok Rynki…)

Szczegóły rynków: [`../SHOP_KNOWLEDGE.md`](../SHOP_KNOWLEDGE.md) §2
