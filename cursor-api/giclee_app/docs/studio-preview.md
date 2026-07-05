# GicleeApp Studio Preview (F4.3a)

Hub: [`README.md`](README.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md) · tło: [`background-parity.md`](background-parity.md)

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

## F3.2 — inline polish (scope)

| Element | Stan |
|---------|------|
| Cross-nav `on_open_component` | callback z `InlineHostView` → `launcher_studio` |
| Stack powrotu | poprzedni inline albo hub źródłowy |
| `Esc` | back tylko poza polami tekstowymi |
| `inline_min_width/height` | bezpieczny zakres + restore minsize |
| Breadcrumb | `Kategoria / Komponent` lub `Kategoria / … / Aktualny` |
| Header | „Inline Studio” (bez etykiety F3 w UI) |

---

## F3 — inline embed + local Git/GPT (zachowane)

| Element | Stan |
|---------|------|
| Inline host (`ui/inline_host.py`) | `build_view(parent, on_back)` przez `tk.Frame` bridge |
| Routing inline | hub → `InlineHostView`, breadcrumb, back |
| Recent dla inline | tylko po udanym `build_view` |
| Error state | krótki komunikat w UI, bez traceback; log: typ + krótki opis |
| Launch subprocess / url | przez `launcher_delegate` (bez zmian F2) |
| Git status | local-only: `.git` w `cursor-api`, opcjonalnie `HEAD` short |
| GPT status | local-only: `Komponenty/integracjagpt/` + `.gpt_mirror/` (bez odczytu config) |
| Polling / sync / backup / deploy | **brak** (poza zakresem Studio; sync/backup = klasyczny launcher) |
| GitHub API / network / tokeny | **brak** |

---

## F4 — background parity foundation (F4.0 + F4.1)

| Element | Stan |
|---------|------|
| Audit mapa tła | [`background-parity.md`](background-parity.md) — Tier 1–4 |
| `studio/background_capabilities.py` | statyczna mapa `tldobio`, `stronaglowna` |
| Badge „Tło” na karcie huba | tylko komponenty z capability |
| Status read-only po kliknięciu | `Tło: <label> — <source_hint> (read-only)` |
| Zapis / Shopify / sync / deploy | **brak** |
| Panel tła / kreator | **F4.2** panel shell · **F4.3+** edycja |

Tier 3 (`katalog`, `kontakt`, `faq`, `stronablogu`) — udokumentowany w audycie, **bez badge w F4.1**.

---

## F4.2 — Background Panel Shell

| Element | Stan |
|---------|------|
| `ui/background_panel.py` | read-only panel: typ tła, źródło, kontekst inline, status |
| Wejście z huba | osobny przycisk **Tło** na karcie (`tldobio`, `stronaglowna`) |
| Klik karty | nadal otwiera inline komponent (bez zmian) |
| Badge „Tło” | dekoracyjny |
| Powrót | **Wróć** → hub tej samej kategorii (F3.2.1.1 lifecycle) |
| `Esc` | powrót z panelu gdy brak konfliktu z inline |
| Zapis / Shopify / sync | **brak** |
| F4.3+ | read-only state summary (F4.3b) — **poza F4.3a** |

---

## F4.3a — Background Safe Handoff

| Element | Stan |
|---------|------|
| Akcja w panelu | **Edytuj w komponencie** — nawigacja do istniejącego inline |
| Handoff | `tldobio` → Tło do Bio · `stronaglowna` → Strona główna |
| Panel | nadal read-only; brak zapisu |
| Powrót z inline | hub (nie panel tła) |
| Routing | `_handoff_background_to_inline` → `_show_inline_component` (niszczy background host) |
| F4.3b / F5 | **poza zakresem** |

Manual smoke F4.3a:

1. Hub → **Tło** → panel → **Edytuj w komponencie** → inline ładuje się
2. **Wróć do huba** → kafelki OK
3. Klik karty (bez panelu) — inline bez regresji

---

## F4.1.1 — inline smoke fixes

| Element | Stan |
|---------|------|
| `Komponenty/_shared/tkdnd_safe.py` | safe `register_drop_target` — brak crasha bez TkinterDnD root |
| `GICLEE_STUDIO_INLINE` | ustawiane w `inline_host` na czas mountu komponentu |
| Podglądy obrazów | local-first z `assets/`; w Studio bez fetch Shopify |
| Placeholder | `brak lokalnego podglądu` gdy brak pliku lokalnego |
| Klasyczny launcher | DnD na `TkinterDnD.Tk()` + CDN podgląd bez zmian |

---

## F3.2 inline smoke matrix (manual)

Checklista ręczna w Studio Preview — nie w CI.

| folder | mode | build_view | inline dims | result | notes |
|--------|------|------------|-------------|--------|-------|
| faq | inline | 2-arg | 1100×720 | pending | lekki |
| katalog | inline | 2-arg | 1100×720 | pending | lekki |
| kontakt | inline | 2-arg | 1100×720 | pending | lekki |
| losujobraz | inline | 2-arg | — | pending | lekki |
| filozofiamarki | inline | 2-arg | 1180×780 | pending | lekki |
| finanse | inline | 3-arg + cross-nav | — | pending | kpir/dnr via callback |
| stronaglowna | inline | 2-arg | — | pending | ciężki — theme editor |
| planer | inline | 2-arg | — | pending | ciężki |

**Known limitations:** crash w `Komponenty/*/view.py` = osobny micro-fix, nie F3.2.

---

## F2 — panel pracy (zachowane)

- Lokalny state: `giclee_app/logs/studio_state.json`
- Dashboard: statusy, pinned/recent, safe quick actions
- Hub: sort pinned → recent, filtr trybu, PPM, card cache

---

## Performance

- `discover_components()` — **1×** przy starcie
- Hub cache — bez regresji po wejściu/wyjściu z inline
- Inline host — **bez cache** (transient per wejście)
- **F3.1** — sanitized errors, `inspect.signature`, resize z `inline_width`/`inline_height`
- **F3.2** — cross-nav stack, `inline_min_*`, breadcrumb polish
- **F3.2.1** — powrót z inline do huba bez pustego contentu (lifecycle hub cache)
- **F3.2.1.1** — CTk: nie wołać `self.minsize()` bez argów (czyta `tk.Misc.minsize`); `_safe_geometry` przed resize/restore

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
| `ui/inline_host.py` | host inline + error states + cross-nav callback |
| `launcher_studio.py` | routing inline, stack, resize, Esc |
| `launcher_delegate.py` | subprocess/url only |
| `studio/status_providers.py` | local Git/GPT |
| `studio/state.py` | recent + pinned |
| `studio/background_capabilities.py` | read-only mapa tła (F4.1) |
| `ui/background_panel.py` | read-only panel shell tła (F4.2) |
| `Komponenty/_shared/tkdnd_safe.py` | safe DnD w embed Studio (F4.1.1) |
