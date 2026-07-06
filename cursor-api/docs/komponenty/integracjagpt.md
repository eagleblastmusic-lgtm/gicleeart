# Komponent: integracjagpt

**Cel:** Integracja motywu GicleeArt z Custom GPT — lustro GitHub (bez `cursor-api/`), nagrania Playwright, paczka review, wiadomości do schowka.

| Plik | Rola |
|------|------|
| `gui.py` | Okno: konfiguracja, sesja review, nagranie, paczka, push, schowek |
| `config.py` | Allowlist ścieżek, `data/gpt_config.json` |
| `mirror.py` | Kopia motywu → `.gpt_mirror/`, `REVIEW_MANIFEST.json`, git push |
| `review_session.py` | Cel sesji, znane problemy, format commit `review: …` |
| `record.py` | Wrapper na `scripts/gpt-record-preview.mjs` |
| `obs_record.py` | Nagrywanie OBS (WebSocket StartRecord/StopRecord) → review-demos |
| `handoff.py` | Szablony wiadomości review / start rozmowy (na bazie plików w «Pliki startowe dla GPT») |
| `gicleeapp_push.py` | Bezpieczny push snapshotu `cursor-api` → staging → `eagleblastmusic-lgtm/gicleeapp` |
| `gicleeart_gpt_push.py` | Bezpieczny push snapshotu motywu → `.gpt_mirror` → `eagleblastmusic-lgtm/gicleeart-gpt` |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Push GicleeArt-GPT (motyw Shopify)

Osobny workflow w GUI **Integracja z GPT** — sekcja **Push GicleeArt-GPT (motyw Shopify)**.

| Etap | Działanie |
|------|-----------|
| A — dry-run | `sync_theme_to_mirror()` (allowlist motywu → `.gpt_mirror`), `git status` / diff, skan sekretów, raport: nowe / zmienione / usunięte / stale |
| B — push | Po potwierdzeniu: `git pull --ff-only` (jeśli behind), `git add -- <explicit paths>` (bez `-A`), commit `review: <cel> YYYY-MM-DD HH:MM`, **finalize + verify manifest SHA**, `git push origin main` |

**Nie dotyczy:** GicleeApp, `_gicleeapp_staging`, komponentu `pushe`, Shopify dev/live push.

Usuwanie przestarzałych plików w `.gpt_mirror` (stale) jest zamierzone — mirror = snapshot allowlisty. Usunięcia stage’owane jawnie po potwierdzeniu.

Fallback commit (gdy brak celu review): `Refresh GicleeArt-GPT theme snapshot`.

Po commicie obowiązkowo: `_finalize_manifest_snapshot_commit` + `_verify_manifest_snapshot_commit` (`REVIEW_MANIFEST.json` → `snapshot_commit` = HEAD).

## Push GicleeApp (aplikacja lokalna)

Osobny workflow w GUI **Integracja z GPT** — sekcja **Push GicleeApp (aplikacja lokalna)**.

| Etap | Działanie |
|------|-----------|
| A — dry-run | safe sync `cursor-api` → `C:\Strona\_gicleeapp_staging`, merge `.gitignore`, `git status` / diff, skan sekretów |
| B — push | Po potwierdzeniu: `git pull --ff-only` (jeśli behind), `git add -- <explicit paths>` (batch, bez `-A`), weryfikacja `git diff --cached`, commit, `git push origin main` |

**Nie dotyczy:** motywu Shopify, `.gpt_mirror/`, `gicleeart-gpt`, komponentu `pushe`.

Zachowuje 8 plików review-only (m.in. `GPT_README.md`, `docs/GPT_KNOWLEDGE_PACK.md`). Nie używa `git add -A`. Przy sekrecie lub pliku runtime w kandydatach — workflow zatrzymany.

**Runtime denylist (F3.2.1.2):** m.in. `documents/`, `notatki/`, `print_optimize/data/`, `stronaglowna/data/tmp/`, scratch root (`_tmp_*`, `czesc*.json`, `tmp_getty*`) — wykluczone z sync, audytu i commita. Przed commitem: `git diff --cached --name-only` musi zgadzać się z listą zaakceptowanych plików; inaczej push **przerwany** (hard stop).

Domyślny commit: `Refresh GicleeApp repository snapshot`.

## Repo GPT (lustro)

**Lustro motywu:** sync generuje `GPT_README.md`, `SYNC_NOTES.md`, `REVIEW_MANIFEST.json` z sekcją **Related repository: GicleeApp** (routing vs `eagleblastmusic-lgtm/gicleeapp`).

**Nie** trafia: `cursor-api/`, backupy, `.env`, cache CSV.

> Snapshot jest kopią **lokalnego working tree** motywu — nie musi odpowiadać głównemu repo ani live.

`GPT_README.md` (generowany w lustrze) zawiera sekcję **Jak interpretować snapshot** — semantyka `changed_files`, `snapshot_commit`, mediów i tras.

Lokalny clone lustra: `cursor-api/.gpt_mirror/` (gitignore).

## Faza A — paczka review

| Artefakt | Ścieżka |
|----------|---------|
| Indeks GPT | `REVIEW_MANIFEST.json` (w korzeniu lustra) |
| Notatki | `SYNC_NOTES.md` |
| Nagrania | `docs/review-demos/latest-desktop.webm`, `latest-mobile.webm` |
| Screenshoty | `docs/review-demos/latest-desktop.png`, `latest-mobile.png` |
| Konsola | `docs/review-demos/console-errors.txt` |

**GUI:** pole „Cel review / sesji”, opcjonalnie „Znane problemy”, checkbox „Nagrania w paczce”.

- **Review package only** — sync lustra + opcjonalnie nagrania/PNG/console, **bez pusha** (sprawdź `.gpt_mirror/`).
- **Push GicleeArt-GPT do GitHub** — dry-run → audyt → potwierdzenie → bezpieczny commit + push (bez nagrań; nagrania na dysku trafiają do lustra allowlistą).
- **Pełny cykl** — nagrania (jeśli checkbox) → sync lustra → ten sam bezpieczny flow push (reuse świeżego sync, bez drugiego pełnego dry-run sync; wymaga potwierdzenia przed pushem).

Stary przycisk **Push → GPT GitHub** usunięty — zastąpiony sekcją **Push GicleeArt-GPT**.

## Workflow

1. Custom GPT (konektor GitHub) → plan + prompt do Cursor.
2. Cursor implementuje na dysku; opcjonalnie theme dev.
3. **Integracja z GPT** → wpisz cel review → Review package only (test) lub Pełny cykl.
4. Kopiuj wiadomość review → ChatGPT ocenia diff + `REVIEW_MANIFEST.json` + review-demos.

## Nagrania

Skrypt: `scripts/gpt-record-preview.mjs` — webm (desktop **1920×1080**, mobile 390×844), PNG po załadowaniu hero, mid-scroll PNG, `console-errors.txt`. Wideo = naturalne ładowanie strony (goto → boot hero/stack → scroll z postojami przy sekcjach stacka, ~30 s). Bez wstrzykiwania tła ani sztucznych pauz przed startem.

| Przycisk GUI | Cel | Folder |
|--------------|-----|--------|
| **Nagraj (OBS)** | Przełącznik start/stop → kopia do `latest-desktop.webm` | `docs/review-demos/` |
| **Nagraj podgląd** | `latest-*` pod paczkę review / push GPT | `docs/review-demos/` (w motywie, trafia do lustra) |
| **Utwórz wideo na dysku** | osobna sesja z timestampem (Playwright, opcjonalnie) | `Komponenty/integracjagpt/data/nagrania/…` |
| **Pełny cykl** (bez Playwright) | «Nagraj (OBS)» albo okno wyboru wideo → **`latest-desktop.webm`** / **`latest-mobile.webm`** | push GPT |

### OBS (zalecane)

1. **Theme dev…** — podgląd na localhost.
2. W OBS: scena z przechwytywaniem okna przeglądarki (Full HD).
3. **Nagraj (OBS)** — ten sam przycisk przełącza start/stop. Przy pierwszym uruchomieniu OBS startuje z `--startrecording`; jeśli OBS już działa — `StartRecord` przez WebSocket (z retry).
4. Przewiń stronę ręcznie.
5. **Zatrzymaj (OBS)** — ponowne kliknięcie tego przycisku.
6. **Pełny cykl** z odznaczonym «Nagrania w paczce (Playwright)» — bez ponownego wyboru pliku, jeśli wideo już w review-demos.

Przed każdym **Nagraj (OBS)** usuwane są tylko poprzednie pliki `review-demos/latest-*`. Katalog nagrań OBS **nie jest** czyszczony (uniknięcie przypadkowego skasowania np. całego `Videos`).

W OBS ustaw **dedykowany** folder wyjścia, np. `Videos\Giclee-OBS` (Ustawienia → Wyjście → Nagrywanie).

Zależność: `pip install obsws-python` (patrz `Komponenty/integracjagpt/requirements.txt`). Domyślna ścieżka OBS: `C:\Program Files\obs-studio\bin\64bit\obs64.exe` — override w `gpt_config.json` → `obs_executable`.

Scroll nagrania: **natywne animacje section-scroll** (`stepDown` = jak kółko myszy), ~4,5 s hero + ~4,2 s postój/sekcja. Przycisk «Utwórz wideo na dysku» nagrywa tylko desktop (Full HD).

Wymaga: `npm install`, `npx playwright install chromium`, theme dev (localhost) lub live URL.

**Hasło password page:** sklep za hasłem wymaga `--store-password` dla CLI. W GUI **Integracja z GPT** → pole **Hasło sklepu** → Zapisz (plik `.shopify-store-password.local`, gitignore).

**ZIP wiedzy + rozmowa z GPT:** **Okno rozmowy** → **Skopiuj .zip** buduje `giclee_cursor_architect_knowledge_v37.zip` z **19 aktywnych plików** manifestu `CLEAN_PACK v37` w `{THEME_ROOT}/Pliki startowe dla GPT/` (archiwalne `.md` na dysku są pomijane), kopiuje ZIP do schowka Windows, potem **Skopiuj Wiadomość początkową** (`Wiadomość początkowa.txt`). **Zmień wiadomość początkową** otwiera edytor i zapisuje `Wiadomość początkowa.txt` w tym samym folderze. Alternatywnie: **Załaduj zip do rozmowy** → kopia w `data/gpt_knowledge.zip`. Po **Pełnym cyklu** ZIP trafia do schowka; aktywuje się **Skopiuj prompt rozpoczęcia rozmowy**.

**Źródła paczki wiedzy (kanoniczne):** `C:\Strona\pusty\Pliki startowe dla GPT` — pliki `.md` i `Wiadomość początkowa.txt` w tym folderze są źródłem prawdy. **Wygenerowany ZIP** (`giclee_cursor_architect_knowledge_v37.zip`) to output generatora; edytuj źródła, potem przebuduj ZIP z GUI (Integracja z GPT), nie ręcznie archiwum ZIP.

## Konfiguracja

`Komponenty/integracjagpt/data/gpt_config.json` — `remote_url`, `branch`, czasy nagrania, `obs_*` (WebSocket OBS).

## Odłożone (Faza B/C)

Branch `review/<data>-<temat>`, PR flow, wiele tras, auto diff-summary, mostek Cursor↔GicleeApp.

→ [`README.md`](README.md)
