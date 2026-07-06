# GicleeApp UI Redesign Plan

**Status:** Faza 5.2 — Local draft selection.

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

## Roadmap (F0–F6)

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
| F5.2 | Local draft selection (in-memory) | **current** |
| F5.3 | Preview-only apply | planned |
| F5.4 | Controlled save via existing component API | planned — osobna akceptacja |
| F5.5 | Shopify / sync / deploy | planned — osobna decyzja |
| F5.6 | Przełącznik domyślny (`GICLEE_STUDIO_UI`) | planned |
| F6 | PyInstaller + CustomTkinter w `.exe` | planned |
| F7 | Sync / backup / cykl produkcyjny w Studio (osobna faza systemowa) | planned |

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

Dashboard, Strona/Motyw, Produkty, Zamówienia, Produkcja, Finanse, Content/AI, Review/GPT, System — mapowanie w `giclee_app/data/studio_categories.json`.

## Out of scope (initial repo phase)

- No refactor of `parents[N]` theme paths.
- No change to `launcher.py` until Studio preview is validated.
- No polling / backup / Shopify sync in Studio F1.

## Bezpieczeństwo

- Stary launcher = produkcja (polling, backup, inline).
- Studio Preview = UI + read-only statusy + launch subprocess/url + inline embed (F3).
- Inline w Studio: `InlineHostView` + `Komponenty.<folder>.view` — bez importu `launcher.py`.
- F2 state: `giclee_app/logs/studio_state.json` (gitignored).
