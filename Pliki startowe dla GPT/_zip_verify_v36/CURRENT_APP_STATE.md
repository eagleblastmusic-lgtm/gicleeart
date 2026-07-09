# Current GicleeApp State

Last updated: 2026-07-05 (post F3/F3.2.1.1)

## Current app version

GicleeApp version: `1.28.0`

## Current canonical commits

### gicleeapp

Repository: `eagleblastmusic-lgtm/gicleeapp`  
Branch: `main`  
Current canonical HEAD:

`92866eccc144044e4761e1791dd99479d910b39e`

Message:

`fix(studio): F3.2.1.1 CTk geometry restore on inline return`

### gicleeart monorepo

Repository: `eagleblastmusic-lgtm/gicleeart.git`  
Branch: `master`  
Current monorepo sync:

`de3cc14f80a1edef66138ae8e130eb3f2c7fc164`

The monorepo stores the app under:

`cursor-api/`

### gicleeart-gpt

Repository: `eagleblastmusic-lgtm/gicleeart-gpt`  
Purpose: Shopify theme review snapshot, not live production.

Important: `REVIEW_MANIFEST.snapshot_commit` can be orientational and may lag by one amend. The canonical review point is the GitHub commit SHA / push SHA / `git log -1`.

---

# GicleeApp Studio Preview

GicleeApp has a Studio Preview shell alongside the classic launcher.

Run classic launcher:

```powershell
python -m giclee_app
```

Run Studio Preview:

```powershell
python -m giclee_app.studio_preview
```

The classic launcher is still the safe production fallback.

---

# Studio phases completed

## F0/F1 — Studio Preview shell

CustomTkinter-based Studio Preview next to the old launcher.

Key rule:

* `python -m giclee_app` still opens the classic launcher.
* `python -m giclee_app.studio_preview` opens the new Studio Preview.

Important files:

* `giclee_app/studio_preview.py`
* `giclee_app/launcher_studio.py`
* `giclee_app/launcher_delegate.py`
* `giclee_app/ui/*`
* `giclee_app/studio/*`
* `giclee_app/data/studio_categories.json`
* `giclee_app/docs/studio-preview.md`

## F1.1 — Performance cache/debounce

* `StudioComponentIndex`, cached category mapping, cached component discovery
* `Component.hidden`, cached fonts, search debounce, lazy/warm Theme Dev status

## F1.2 — Fast tab switching

* view cache, cached dashboard/hub views, `grid()` / `grid_remove()`
* card cache, lazy batch rendering, sidebar re-click guard

## F1.3 — Instant first paint / skeleton prepaint

* skeleton grid, progressive card rendering, cached views skip skeleton on return

## F2 — Practical Studio Dashboard

* dashboard "what to do today", recent/pinned components, local Studio state
* read-only statuses, no deploys/syncs/polling/GitHub push from dashboard

## F3 Minimal — Inline embed

* inline embed, local Git/GPT, hub routing, transient host

## F3.1 — Error sanitizer + build_view signature

* sanitizer błędów, `inspect.signature` dla `build_view`, opcjonalny resize

## F3.1.1 — Security masking + geometry restore

* maskowanie Bearer/Authorization, restore geometrii tylko po resize

## CI — GitHub Actions

* Studio tests + Security / push workflow tests on push

## CI security fix

* `audit_repo_for_github_push()` skanuje sekrety przed `git fetch`

## F3.2 — Cross-navigation

* cross-nav, stack back, `inline_min_*`, breadcrumb, Esc

## F3.2.1 — Hub return fix

* powrót z inline do huba bez pustego contentu

## F3.2.1.1 — CTk geometry restore

* fix CTk geometry/minsize restore po inline resize

---

# Next phase

## F4 — Background parity

**Not started.** Do not begin F4 without explicit user command.

---

# Known non-blocking issue

`stronaglowna TclError` / mousewheel binding po destroy inline hosta — potencjalny F3.2.2 micro-fix. Nie blokuje F3/F3.2.1.1.

---

# Hard safety rules for future work

When working on GicleeApp Studio:

1. Do not modify `giclee_app/launcher.py` unless explicitly requested.
2. Do not modify `giclee_app/__main__.py` unless explicitly requested.
3. Do not modify `Komponenty/*/view.py` or `Komponenty/*/component.json` unless the task explicitly concerns a component.
4. Do not touch runtime state, logs, `gpt_config.json`, `.shopify_session.json`, backups.
5. Do not add polling, backup, sync, publisher, deploy, or GitHub push behavior to Studio.
6. Do not show tokens/secrets in UI.
7. Do not use `git add -A` or `git add .` — stage explicit files only.
8. Keep classic launcher as fallback.
9. Prefer targeted tests during iteration; full Studio + security suite before commit.

---

# Repository routing

## `gicleeapp`

Use for: Python app, launcher, Studio Preview, UI shell, local app workflows, push components, GPT integration tools, app tests.

Start review from: `README.md`, `GPT_README.md`, `REVIEW_MANIFEST.json`, `SYNC_NOTES.md`, `.gitignore`, `docs/UI_REDESIGN_PLAN.md`, `giclee_app/docs/studio-preview.md`

## `gicleeart-gpt`

Use for: Shopify theme review snapshot, Liquid/CSS/JS, frontend theme review.

Do not confuse `gicleeapp` with `gicleeart-gpt`.

---

# Testing expectations

Prefer Python 3.11 with working Tk/Tcl. Do not use broken Python 3.14 for GUI/Studio tests.

Targeted tests during debug (examples — see COMPACT v36 for full list):

```powershell
cd C:\Strona\pusty\cursor-api
py -3.11 -m pytest tests/test_studio_launcher_inline.py tests/test_studio_inline_host.py -q --tb=short -x
```

Full package before commit:

```powershell
cd C:\Strona\pusty\cursor-api
py -3.11 -m pytest tests/test_studio_* tests/test_status_providers.py tests/test_pushe.py tests/test_gicleeart_gpt_push.py tests/test_gicleeapp_push.py tests/test_integracjagpt.py -q
```

After push: verify GitHub Actions (Studio + Security workflows).
