# GicleeApp UI Redesign Plan

**Status:** Faza 6.2 — Asset Lab launch shell.

## Goal

Transform the current technical launcher into a **Premium Fine Art Control Center** (GicleeApp Studio).

## Current UI problems

- system-like Windows UI,
- too many raw cards,
- weak hierarchy,
- repeated small buttons,
- technical toolbar,
- inconsistent colors,
- limited status information,
- no premium visual identity.

## Target direction

- GicleeApp Studio / Fine Art Control Center,
- premium dashboard,
- calm dark or refined light theme,
- grouped components,
- search and filters,
- better cards,
- status badges,
- recent actions,
- clean toolbar,
- improved spacing,
- microinteractions,
- loading / success / error states.

## Design language

- museum editorial,
- Fine Art production studio,
- calm luxury,
- restrained Awwwards-inspired motion,
- no neon,
- no cyberpunk,
- no SaaS clutter.

## Repository

Future UI redesign of the GicleeApp launcher is implemented and reviewed in:

- **`eagleblastmusic-lgtm/gicleeapp`**

Not in **`eagleblastmusic-lgtm/gicleeart-gpt`** (theme snapshot only).

## Roadmap (F0–F8)

### Studio shell + Background Builder (F0–F5)

| Faza | Cel | Status |
|------|-----|--------|
| F0 | Dokumentacja, plan, mapa kategorii | done |
| F1 | CTk shell preview (`studio_preview`) — bez pollingów | done |
| F2 | Dashboard read-only, recent/pinned, hub sort/filter, safe quick actions | done |
| F2.1 | Polish: pin eviction, hub sort batch, dashboard refresh | done |
| F3 | Inline embed Studio, local-only Git/GPT status | done |
| F3.1 | Safer inline errors, build_view signature, optional resize | done |
| F3.1.1 | Bearer sanitizer, geometry restore polish | done |
| CI | GitHub Actions studio + security tests | done |
| F3.2 | Cross-nav, inline stack, inline_min_*, breadcrumb | done |
| F3.2.1.1 | CTk minsize / geometry restore po inline | done |
| F4 | Background parity foundation: audit + read-only Studio awareness | done |
| F4.1.1 | Inline DnD fallback + local thumbnails | done |
| F4.2 | Background Panel Shell — read-only panel tła w hubie | done |
| F4.3a | Safe handoff panel → existing inline editor | done |
| F4.3b | Read-only current background state summary | done |
| F5.0 | Background Builder UX contract / audit (docs-only) | done |
| F5.1 | Read-only asset browser shell (`stronaglowna`) | done |
| F5.1b | Bounded read-only asset list from active index | done |
| F5.2 | Local draft selection (in-memory) | done |
| F5.3 | Conceptual draft preview (panel mock) | done |
| F5.4a | Save contract + dry-run (Plan zapisu, zero I/O) | done |
| F5.4b | Controlled local write → aktywny index.json | planned — osobna akceptacja |
| F5.4c | Backup / rollback / validation hardening | planned |
| F5.5 | Shopify / sync / deploy | planned — osobna decyzja |
| F5.6 | Przełącznik domyślny (`GICLEE_STUDIO_UI`) | planned |

### Studio v2 redesign track (F6.x)

| Faza | Cel | Status |
|------|-----|--------|
| F6.0 | Component redesign audit — Keep / Merge / Legacy / Defer | done · accepted |
| F6.1 | Studio v2 workflow navigation map (docs-only) | done |
| F6.2 | Asset Lab shell — read-only / launch-only | done |
| F6.3 | Site Builder Tier 3 read-only shells | planned |

Mapa workflowów: [`giclee_app/docs/studio-v2-workflows.md`](../giclee_app/docs/studio-v2-workflows.md)

**Numeracja:** Track F6.x = Studio v2 redesign. Dawne „F6 PyInstaller” → **F8 packaging** (poniżej).

### System / packaging (F7–F8)

| Faza | Cel | Status |
|------|-----|--------|
| F7 | Sync / backup / cykl produkcyjny w Studio (osobna faza systemowa) | planned |
| F8 | PyInstaller + CustomTkinter w `.exe` (dawne F6) | planned |

## Architektura (F1)

```
giclee_app/
├── launcher.py              ← fallback (nietknięty)
├── launcher_studio.py       ← CTk shell
├── studio_preview.py        ← python -m giclee_app.studio_preview
├── launcher_delegate.py     ← subprocess/url only
├── ui/                      ← sidebar, topbar, dashboard, hub, inline_host, background_panel
├── studio/                  ← …, background_state, background_asset_types, background_asset_shell
└── data/studio_categories.json
```

- **`python -m giclee_app`** — klasyczny launcher (bez zmian).
- **`python -m giclee_app.studio_preview`** — Studio Preview (wymaga `requirements-dev.txt`).

Szczegóły uruchomienia: [`giclee_app/docs/studio-preview.md`](../giclee_app/docs/studio-preview.md).

## Kategorie sidebaru

**v1 (obecny kod):** Dashboard, Strona/Motyw, Produkty, Zamówienia, Produkcja, Finanse, Content/AI, Review/GPT, System — mapowanie w `giclee_app/data/studio_categories.json`.

**v2 (docelowy, F6.1 docs):** workflow-based — Site Builder, Asset Lab, Product Pipeline, Collections, Fulfillment, Content Hub, System (+ Finance Desk i Legacy Tools secondary). Szczegóły: [`studio-v2-workflows.md`](../giclee_app/docs/studio-v2-workflows.md). **Bez zmiany discovery do akceptacji implementacji F6.2+.**

## Out of scope (initial repo phase)

- No refactor of `parents[N]` theme paths.
- No change to `launcher.py` until Studio preview is validated.
- No polling / backup / Shopify sync in Studio F1.

## Bezpieczeństwo

- Stary launcher = produkcja (polling, backup, inline).
- Studio Preview = UI + read-only statusy + launch subprocess/url + inline embed (F3).
- Inline w Studio: `InlineHostView` + `Komponenty.<folder>.view` — bez importu `launcher.py`.
- F2 state: `giclee_app/logs/studio_state.json` (gitignored).
