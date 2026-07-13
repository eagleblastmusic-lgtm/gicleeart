# GF-M4 — F2 Page Readiness Panel Extraction Contract

Status: **IMPLEMENTATION PENDING**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `3515d50419c20e168fc37ec5061ad073fe28ddd5`  
Work branch: `gpt-work/gicleeframe-modularization-m4-page-readiness`

## 1. Discovery decision

GF-M4 extracts the smallest coherent stateful F2 boundary remaining in `GicleeFrameView`: the **page readiness panel**.

The boundary is intentionally narrower than the surrounding control column. It owns only construction, expand/collapse, summary formatting and row population for page readiness. It does not own the structure dry-run, inventory refresh, shared readiness-row renderer, control-column composition, lifecycle, schedulers, selection, page context, preview or cache.

The top-bar and command-bar lane was rejected for GF-M4 because it owns staggered `after()` scheduling, suppression gates, atomic-reveal signaling and multiple telemetry contracts. The editor-fields and section-list lanes were also rejected because they are substantially larger and more performance-sensitive.

## 2. Target architecture

Create:

`cursor-api/giclee_app/ui/gicleeframe_view_page_readiness.py`

Preferred shape:

- a narrow mixin named `GicleeFramePageReadinessMixin`;
- no `__init__`;
- no Tk/widget base class;
- no import from `gicleeframe_view.py`;
- no writes, network, subprocess or Shopify operations;
- `GicleeFrameView` inherits it alongside `GicleeFrameBrandPanelMixin`, before `ctk.CTkScrollableFrame`.

`gicleeframe_view.py` remains the public import location for `GicleeFrameView`.

## 3. Exact ownership boundary

Move exactly four methods:

1. `_build_control_readiness_card`
2. `_toggle_page_readiness`
3. `_page_readiness_summary_text`
4. `_fill_page_readiness`

Move the page-readiness-only constant:

- `_PAGE_READINESS_TITLE`

The module may import `GicleeFramePageReadiness` at module scope instead of retaining the current local imports, provided behavior and import safety remain unchanged.

## 4. Host-owned adapters and shared behavior

The following remain in `gicleeframe_view.py`:

- `_build_control_column` — composes structure, readiness and safety cards;
- `_build_control_structure_card`;
- `_build_safety_card`;
- `_run_structure_dry_run` — owns inventory/dry-run orchestration and status updates;
- `_pack_readiness_row` — shared by F1 brand readiness and F2 page readiness;
- `_reset_structure_dry_run_display`;
- all lifecycle, scheduler, selection, page-context, preview, layer-nav, cache and editor methods.

The extracted mixin may call `self._pack_readiness_row(...)`. It must not duplicate or wrap that method.

## 5. Compatibility contracts

Preserve exactly:

- `GicleeFrameView` public import path and class identity;
- MRO compatibility with `GicleeFrameBrandPanelMixin`;
- readiness card layout, copy, colors, fonts, dimensions and packing order;
- initial collapsed state and arrow text;
- summary strings and row counts;
- hidden compatibility summary label;
- RAM-only behavior;
- `_run_structure_dry_run` calling `self._fill_page_readiness(ready)`;
- the control-column order: structure → readiness → safety;
- no changes to timing constants, `after()`, scheduler ownership, telemetry or performance lanes;
- no writer, persistence, sync, upload, publish, deploy or Shopify mutation.

## 6. Imports expected to move

Move from `gicleeframe_view.py` only imports with no remaining host consumer after extraction:

- `readiness_page_display_rows`, if fully page-readiness-only;
- any page-readiness-only type imported locally by the moved methods;
- page-readiness UI helpers only when no host use remains.

Do not move or remove:

- `evaluate_gicleeframe_page_readiness`;
- `format_page_readiness_block`;
- imports needed by `_run_structure_dry_run`;
- `status_color`, needed by host `_pack_readiness_row`;
- primitives still used elsewhere in the host.

## 7. Source-text tests

`test_studio_gicleeframe_shell.py` currently expects `_toggle_page_readiness` and `_PAGE_READINESS_TITLE` in the host source.

Update only the ownership-sensitive assertions:

- page-readiness definitions/copy move to `gicleeframe_view_page_readiness.py`;
- `_build_control_column`, `_build_safety_card`, `_run_structure_dry_run` and `_pack_readiness_row` remain asserted in `gicleeframe_view.py`;
- do not satisfy tests with comments, dead aliases or copied strings;
- add no-write/no-network guardrails for the new module.

## 8. New tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py`

Minimum coverage:

1. module imports without `Komponenty.*`;
2. no file writes, network, subprocess, dialogs or Shopify operations;
3. mixin has no `__init__` and no Tk base;
4. exact four-method ownership;
5. `_PAGE_READINESS_TITLE == "Readiness (strona)"`;
6. MRO contains both page-readiness and brand mixins;
7. moved methods resolve from `GicleeFramePageReadinessMixin` and are absent from `GicleeFrameView.__dict__`;
8. `_build_control_column`, `_run_structure_dry_run` and `_pack_readiness_row` remain host-owned;
9. summary formatting preserves ready/blocked counts for `None` and a real readiness object;
10. expand/collapse method preserves pack/forget and arrow-text contracts.

## 9. Exact durable allowlist

Maximum durable scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_page_readiness.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py`
4. `cursor-api/tests/test_studio_gicleeframe_shell.py`
5. only directly affected existing page-readiness tests, if proven necessary
6. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
7. this contract document

No `.github`, workflow, version, starter-file or ZIP changes.

## 10. Required validation

Before push of the integration commit:

- `py_compile` for the host and new module;
- new page-readiness boundary tests;
- brand boundary tests to protect multi-mixin MRO;
- shell, lifecycle, lazy-shell and progressive-boot tests;
- existing readiness tests;
- `pytest -q -k gicleeframe`;
- runtime-write inventory;
- `git diff --check`;
- exact changed-file allowlist review.

CI after push:

1. draft Hermetic;
2. artifact review;
3. ready only after Hermetic success;
4. Tk GUI smoke and Tcl/Tk probe;
5. full baseline;
6. inventory and parse-error artifact review;
7. exact-head final review;
8. squash merge with `expected_head_sha` only after the full contract passes.

## 11. Explicit exclusions

- no UI redesign or copy change;
- no structure dry-run refactor;
- no shared readiness-row extraction;
- no control-column extraction;
- no top-bar/command-bar extraction;
- no timing, scheduler, performance or telemetry changes;
- no editor, section-list, preview, page-context, layer-nav or cache changes;
- no writer, persistence or Shopify operation;
- no starter-file update in this PR;
- no ZIP generation.
