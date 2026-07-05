# Pushe

Komponent GicleeApp: wdrożenia motywu Shopify (dev / live) oraz bezpieczna synchronizacja głównego monorepo na GitHub.

## Uruchomienie

- GicleeApp → kafelek **Pushe**
- CLI: `python -m Komponenty.pushe` (z `cursor-api/`)

## Gdzie co pushować

| Cel | Komponent | Repo / środowisko | Kiedy używać |
|-----|-----------|-------------------|--------------|
| Shopify dev | Pushe | development theme (piaskownica) | szybki test na dev |
| Shopify live | Pushe | live theme (produkcja) | świadomy deploy produkcji |
| Główne repo gicleeart | Pushe | `eagleblastmusic-lgtm/gicleeart.git` | backup / monorepo (motyw + cursor-api) |
| GicleeArt-GPT review | Integracja z GPT | `eagleblastmusic-lgtm/gicleeart-gpt` | snapshot motywu dla ChatGPT |
| GicleeApp review | Integracja z GPT | `eagleblastmusic-lgtm/gicleeapp` | snapshot aplikacji dla ChatGPT |

**Pushe GitHub** nie jest snapshotem review dla ChatGPT — do tego służy **Integracja z GPT**.

## Operacje Shopify

| Akcja | Co robi |
|-------|---------|
| **Push dev** | `shopify theme push --environment development` — motyw «GicleeApp dev» (ID `200713503068`) |
| **Push live** | `shopify theme push --environment live --allow-live` — opublikowany motyw (ID `197314249052`) |

Shopify CLI: ta sama ścieżka co w **Strona główna** (`Komponenty/stronaglowna/service.py` → `deploy_theme`).

Komponent **nie** zapisuje treści ze Strony głównej przed pushem — przed deployem Shopify upewnij się, że motyw lokalny jest aktualny.

## Operacja GitHub (gicleeart.git)

Bezpieczny flow (bez `git add -A`):

1. **Dry-run / audyt** — `git fetch`, analiza brancha, lista plików, skan sekretów i runtime denylist
2. Raport w logu GUI
3. Potwierdzenie (osobno: nowe, zmienione, **usunięte**)
4. Po potwierdzeniu: `git pull --ff-only` (gdy behind), `git add -- <explicit paths>`, commit, push

### Remote guard

Akceptowany tylko `eagleblastmusic-lgtm/gicleeart.git`. Blokada przy `gicleeart-gpt`, `gicleeapp` lub innym origin.

### Runtime denylist

Pliki spoza `commit_candidates` (m.in. `.env`, backupy Strony głównej, KPiR, faktury, zamówienia, `.gpt_mirror/`, `Pliki startowe dla GPT/`) są pomijane w audycie. Mogą pozostać lokalnie jako dirty — to zamierzone; nie trafiają do commita bez zmiany `.gitignore` (osobna faza).

### Usunięte pliki

W raporcie i dialogu osobna sekcja **Usunięte (N)**. Usunięcia nie są stage’owane automatycznie — wymagają wyraźnej akceptacji w drugim dialogu.

## Pliki

| Plik | Rola |
|------|------|
| `gui.py` | UI — Shopify dev/live, bezpieczny push gicleeart |
| `service.py` | `push_shopify_*`, `dry_run_github_push`, `commit_and_push_github`, audyt |
| `config.py` | URL GitHub, branch, Shopify, runtime denylist |

## Powiązane

- Snapshot review motywu / app: [`integracjagpt.md`](integracjagpt.md)
- Deploy motywu (engine): `Komponenty/stronaglowna/service.py` → `deploy_theme`

## Uwagi

- Push live wymaga potwierdzenia w UI.
- Testy: `pytest tests/test_pushe.py` (z katalogu `cursor-api/`).
