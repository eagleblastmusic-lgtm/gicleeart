# GicleeApp Studio Preview (F6.2)

Hub: [`README.md`](README.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md) · tło: [`background-parity.md`](background-parity.md) · F5: [`background-builder.md`](background-builder.md) · v2: [`studio-v2-workflows.md`](studio-v2-workflows.md)

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
| `ui/background_panel.py` | read-only panel: typ tła, źródło, **Aktualny stan**, kontekst inline, status |
| Wejście z huba | osobny przycisk **Tło** na karcie (`tldobio`, `stronaglowna`) |
| Klik karty | nadal otwiera inline komponent (bez zmian) |
| Badge „Tło” | dekoracyjny |
| Powrót | **Wróć** → hub tej samej kategorii (F3.2.1.1 lifecycle) |
| `Esc` | powrót z panelu gdy brak konfliktu z inline |
| Zapis / Shopify / sync | **brak** |

---

## F4.3b — Read-only background state summary

| Element | Stan |
|---------|------|
| Moduł | `studio/background_state.py` — `summarize_background_state(folder, package_path)` |
| Importy | **zero** `Komponenty.*`; tylko `Path.read_text` + `json.loads` |
| `tldobio` | cache `collections.json` — N kolekcji, M z tłem; bez URL-i w UI |
| `stronaglowna` | manifest + aktywny `index.json` — 5 stref, X/5 ustawione, obraz/wideo/brak |
| Fallback | nieczytelny JSON / brak pliku → komunikat zamiast crasha |
| Backup / write | **brak** — nie czyta `data/backups/*`, nie woła `load_manifest()` |

Manual smoke F4.3b:

1. Hub → **Tło** (`tldobio` / `stronaglowna`) → sekcja **Aktualny stan** widoczna
2. **Edytuj w komponencie** — handoff F4.3a bez regresji
3. **Wróć** → hub OK

---

## F5 — Premium Background Builder (plan)

Kontrakt i roadmapa: [`background-builder.md`](background-builder.md).

| Faza | Stan | Opis |
|------|------|------|
| F5.0 | done (docs) | UX contract — [`background-builder.md`](background-builder.md) |
| F5.1 | done | Read-only shell „Biblioteka / Assety” |
| F5.1b | done | Bounded lista przypisań z aktywnego wariantu |
| F5.2 | done | Lokalny draft wyboru strefy + typu (in-memory) |
| F5.3 | done | Conceptual draft preview — podgląd koncepcyjny · niezastosowany |
| F5.4a | done | Save contract + dry-run — **Plan zapisu**, zero I/O |
| F5.4b0 | done | Save readiness / ref policy — **Gotowość zapisu**, zero I/O |
| F5.4b1–F5.4c | planned | Writer + backup / rollback — osobna akceptacja |
| F5.4d | planned | Asset ref selection |
| F5.5 | planned | Shopify / sync / deploy — osobna akceptacja |

F5.4b0 **nie zapisuje** niczego — ocena gotowości i ref policy. Realny zapis = F5.4b1+.

Manual smoke F5.4b0: patrz sekcja poniżej.

---

## F6.2 — Asset Lab launch shell

| Element | Stan |
|---------|------|
| `studio/asset_lab_catalog.py` | 8 narzędzi — folder, summary, ryzyko N/M/H, sort order |
| `ui/asset_lab_view.py` | Workflow screen — klikalne karty (launch) |
| Sidebar | Nowa pozycja **Asset Lab** (NAV, bez zmiany `studio_categories.json`) |
| Launch | `launcher_delegate.launch(comp)` — jak hub subprocess |
| `record_launch` | Tak — standardowy `studio_state` (nie dane `Komponenty/*`) |
| Backend merge | **brak** — mockup/kolaz/squoosh/etc. bez zmian |
| Shopify w Studio layer | **brak** |
| Hub Produkty | Bez zmian — 14 kart nadal dostępne |
| F5.4 save | F5.4b0 done (readiness) · F5.4b1 not started |

Narzędzia (kolejność UI): `nazwijobraz`, `infoplikow`, `squoosh`, `print_optimize`, `przedpo`, `kolaz`, `mockup`, `pobierzobraz`.

Manual smoke F6.2:

1. Sidebar → **Asset Lab** → 8 kart z opisem, badge subprocess / ryzyko / legacy backend
2. Kliknij kartę (np. `nazwijobraz`) → subprocess lub bezpieczny błąd launch
3. Sidebar → Produkty / Strona główna → bez regresji
4. `python -m giclee_app` — klasyczny launcher OK

---

## F5.3 — Conceptual draft preview

| Element | Stan |
|---------|------|
| `background_draft_preview.py` | pure: `format_preview_body()`, placeholders tekstowe |
| `background_panel.py` | sekcja **Podgląd draftu** po „Draft wyboru” |
| Draft pusty | „Podgląd pojawi się po wyborze strefy i typu” |
| Draft ustawiony | badge `niezastosowany` + strefa + typ + placeholder CTkFrame |
| Apply / zapis / pliki | **brak** |

Manual smoke F5.3:

1. Hub → **Tło** → **Strona główna**
2. Draft pusty → preview empty copy
3. Wybór strefy + typu → preview aktualizuje się (`niezastosowany`)
4. **Aktualny stan** i **Biblioteka / Assety** bez zmian
5. **Wyczyść draft** → preview wraca do empty
6. Brak Zastosuj / Zapisz / Upload / file picker
7. **Tło do Bio** — brak preview
8. Brak zmian w `Komponenty/stronaglowna/data/*`

---

## F5.4a — Save contract + dry-run

| Element | Stan |
|---------|------|
| `background_save_contract.py` | pure: validate + dry-run + format summary |
| `background_panel.py` | sekcja **Plan zapisu** po „Podgląd draftu” |
| Akcja | **Sprawdź zapis** — jedyna akcja zapisu |
| Copy | `dry-run · nic nie zapisano` — stale widoczne |
| Zapis / apply / pliki | **brak** — zero `write_text` |
| video_collage | odrzucone — poza section_background F5.4 |

Manual smoke F5.4a:

1. `python -m giclee_app.studio_preview` → **Strona główna** → **Tło**
2. Wybierz strefę + typ (obraz lub wideo)
3. Kliknij **Sprawdź zapis**
4. Pojawia się `dry-run · nic nie zapisano` + semantic diff
5. **Aktualny stan** i **Biblioteka / Assety** bez zmian
6. Brak **Zapisz lokalnie** / **Zapisz** / **Zastosuj**
7. Brak zmian w `Komponenty/stronaglowna/data/*`
8. **Tło do Bio** — brak sekcji Plan zapisu
9. **Asset Lab** — bez regresji
10. `python -m giclee_app` — klasyczny launcher OK

---

## F5.4b0 — Save readiness / ref policy

| Element | Stan |
|---------|------|
| `background_save_readiness.py` | pure: `evaluate_save_readiness()`, `SaveOperation` |
| `background_panel.py` | **Gotowość zapisu** po dry-run w Plan zapisu |
| Checkbox | Plan wyczyść tło — readiness only, bez writera |
| Copy | `F5.4b0 nadal nic nie zapisuje` · F5.4b1 = realny zapis |
| Zapis / backup / writer | **brak** |

Manual smoke F5.4b0:

1. Studio → **Strona główna** → **Tło**
2. Wybierz strefę + typ **inny** niż obecny → **Sprawdź zapis**
3. Gotowość: **zablokowane** / wymaga wyboru assetu
4. Brak **Zapisz lokalnie**
5. Wybierz typ **zgodny** z obecnym stanem → Gotowość: **bez zmian** / noop
6. Opcjonalnie: checkbox plan clear przy istniejącym tle → gotowe (plan F5.4b1)
7. **Aktualny stan** / **Biblioteka** bez zmian · brak mutacji `data/*`
8. **Tło do Bio** — brak readiness
9. Asset Lab + klasyczny launcher OK

---

## F4.3a — Background Safe Handoff

| Element | Stan |
|---------|------|
| Akcja w panelu | **Edytuj w komponencie** — nawigacja do istniejącego inline |
| Handoff | `tldobio` → Tło do Bio · `stronaglowna` → Strona główna |
| Panel | nadal read-only; brak zapisu |
| Powrót z inline | hub (nie panel tła) |
| Routing | `_handoff_background_to_inline` → `_show_inline_component` (niszczy background host) |
| F4.3b / F5 | edytor w Studio (**F5**) — **poza F4.3b** |

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
| `studio/background_state.py` | read-only summary lokalnego stanu tła (F4.3b) |
| `studio/background_asset_types.py` | typy assetów shell (F5.1) |
| `studio/background_asset_shell.py` | read-only shell biblioteki (F5.1) |
| `studio/background_draft_state.py` | lokalny draft wyboru (F5.2) |
| `studio/background_draft_preview.py` | koncepcyjny podgląd draftu (F5.3) |
| `studio/background_save_contract.py` | save contract + dry-run (F5.4a) |
| `studio/background_save_readiness.py` | save readiness / ref policy (F5.4b0) |
| `studio/asset_lab_catalog.py` | katalog Asset Lab — 8 narzędzi (F6.2) |
| `ui/background_panel.py` | read-only panel shell tła (F4.2) |
| `ui/asset_lab_view.py` | Asset Lab launch shell (F6.2) |
| `Komponenty/_shared/tkdnd_safe.py` | safe DnD w embed Studio (F4.1.1) |
