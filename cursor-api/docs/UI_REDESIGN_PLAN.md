# GicleeApp UI Redesign Plan

**Status:** Faza 1 — Studio Preview (CustomTkinter) obok klasycznego launchera.

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
| F1 | CTk shell preview (`studio_preview`) — bez pollingów | **current** |
| F2 | Dashboard read-only rozszerzony, recent, quick actions | planned |
| F3 | Inline embed w Studio | planned |
| F4 | Background parity (sync, backup, cykl) | planned |
| F5 | Przełącznik domyślny (`GICLEE_STUDIO_UI`) | planned |
| F6 | PyInstaller + CustomTkinter w `.exe` | planned |

## Architektura (F1)

```
giclee_app/
├── launcher.py              ← fallback (nietknięty)
├── launcher_studio.py       ← CTk shell
├── studio_preview.py        ← python -m giclee_app.studio_preview
├── launcher_delegate.py     ← subprocess/url only
├── ui/                      ← sidebar, topbar, dashboard, hub
├── studio/                  ← categories, status_providers
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
- Studio Preview = UI + read-only statusy + launch subprocess/url.
- Inline komponenty w F1: komunikat „Faza 2 — użyj klasycznego launchera”.
