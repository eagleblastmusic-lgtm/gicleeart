# GicleeApp Studio Preview (F3)

Hub: [`README.md`](README.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

**Studio Preview** to ciemny shell CustomTkinter obok klasycznego launchera. Nie zastępuje `launcher.py`.

---

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
pip install -r requirements-dev.txt
python -m giclee_app.studio_preview
```

Klasyczny launcher (bez zmian, fallback produkcyjny):

```powershell
python -m giclee_app
```

---

## F3 — inline embed + local Git/GPT (scope)

| Element | Stan |
|---------|------|
| Inline host (`ui/inline_host.py`) | `build_view(parent, on_back)` przez `tk.Frame` bridge |
| Routing inline | hub → `InlineHostView`, breadcrumb, „Wróć do huba” |
| Recent dla inline | tylko po udanym `build_view` |
| Error state | krótki komunikat w UI, bez traceback; log: typ + krótki opis |
| Launch subprocess / url | przez `launcher_delegate` (bez zmian F2) |
| Git status | local-only: `.git` w `cursor-api`, opcjonalnie `HEAD` short |
| GPT status | local-only: `Komponenty/integracjagpt/` + `.gpt_mirror/` (bez odczytu config) |
| Polling / sync / backup / deploy | **brak** (F4) |
| GitHub API / network / tokeny | **brak** |

---

## F2 — panel pracy (zachowane)

- Lokalny state: `giclee_app/logs/studio_state.json`
- Dashboard: statusy, pinned/recent, safe quick actions
- Hub: sort pinned → recent, filtr trybu, PPM, card cache

---

## Performance

- `discover_components()` — **1×** przy starcie
- Hub cache — bez regresji po wejściu/wyjściu z inline
- Inline host — **bez cache** (nowy host per wejście F3 Minimal)
- **F3.1** — sanitized error messages, `inspect.signature` dla `build_view`, opcjonalny resize z `inline_width`/`inline_height`

---

## Ograniczenia

- Stary launcher = produkcja (polling, backup, pełny inline z resize okna).
- Studio inline = `Komponenty.<folder>.view` tylko w shellu CTk; brak `launcher.GicleeApp`.
- Brak `.git` w `cursor-api` (np. monorepo) → Git pill `—` — to oczekiwane.
- PyInstaller — Studio nie w bundlu do F6.

---

## Pliki

| Plik | Rola |
|------|------|
| `ui/inline_host.py` | host inline + error states |
| `launcher_studio.py` | routing inline, transient host |
| `launcher_delegate.py` | subprocess/url only |
| `studio/status_providers.py` | local Git/GPT |
| `studio/state.py` | recent + pinned |
