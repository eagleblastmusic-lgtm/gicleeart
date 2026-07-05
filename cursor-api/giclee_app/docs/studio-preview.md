# GicleeApp Studio Preview (F1)

Hub: [`README.md`](README.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

**Studio Preview** to ciemny shell CustomTkinter obok klasycznego launchera. Nie zastępuje `launcher.py`.

---

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
pip install -r requirements-dev.txt
python -m giclee_app.studio_preview
```

Klasyczny launcher (bez zmian):

```powershell
python -m giclee_app
```

Brak `customtkinter` → komunikat:

```
Zainstaluj zależności dev: pip install -r requirements-dev.txt
```

---

## Co działa w F1

| Element | Stan |
|---------|------|
| Sidebar (9 kategorii) | działa |
| Dashboard — liczniki, wersja, activity log | read-only, realne |
| Dashboard — priorytety, alerty, GitHub, GPT | mock |
| Component hub — wyszukiwarka, karty | działa |
| Launch subprocess | działa (logi w `logs/`) |
| Launch url (np. sklep) | działa |
| Launch inline | komunikat F2 |
| Polling Shopify / backup / cykl | **brak** (tylko w klasycznym launcherze) |

---

## F1.2 — szybsze przełączanie zakładek

- **Cache widoków** — dashboard i huby kategorii są tworzone raz, potem `grid()` / `grid_remove()` zamiast destroy/create.
- **Lazy render kart** — pierwsze wejście w kategorię buduje karty partiami (`after(1)`), z komunikatem „Ładowanie komponentów…”.
- **Card cache** — wyszukiwarka filtruje istniejące karty przez `grid()` / `grid_remove()`, bez ponownego tworzenia widgetów.

---

## Ograniczenia

- Nie używać Studio jako jedynego okna do pracy produkcyjnej dopóki F4 nie zapewni parity pollingów.
- PyInstaller (`.exe`) — Studio **nie** jest w bundlu do Fazy 6.
- `__main__.py` nadal wskazuje na stary launcher.

---

## Pliki

| Plik | Rola |
|------|------|
| `studio_preview.py` | entrypoint |
| `launcher_studio.py` | okno CTk |
| `launcher_delegate.py` | uruchamianie subprocess/url |
| `ui/*` | layout |
| `studio/categories.py` | mapa kategorii |
| `studio/status_providers.py` | statusy read-only |
| `data/studio_categories.json` | folder → kategoria |
