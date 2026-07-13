# GF-M5 — F2 Structure Dry-Run Panel Extraction Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `9287842a0fdf11eec15f11efe463deec28269f9b`
Work branch: `gpt-work/gicleeframe-modularization-m5-structure-dry-run`

## 1. Discovery decision

GF-M5 extracts the smallest coherent F2 boundary remaining after GF-M4: the **structure dry-run panel**.

The boundary owns the structure-card construction, empty-state reset and synchronous RAM-only dry-run action. It does not own control-column composition, safety, page-readiness rendering, inventory implementation, lifecycle, schedulers, selection, page context, preview, layer navigation, cache or editor population.

Rejected for this stage:

- top-bar and command-bar, because they own staggered `after()` scheduling, suppression gates, atomic-reveal signaling and telemetry;
- section list and editor fields, because they are larger and performance-sensitive;
- RAM-variant actions, because they cross inventory refresh, selection state, menus and editor population;
- safety card, because it is independent static copy and does not belong to the structure workflow.

## 2. Target architecture

Create:

`cursor-api/giclee_app/ui/gicleeframe_view_structure_dry_run.py`

Preferred shape:

- a narrow mixin named `GicleeFrameStructureDryRunMixin`;
- no `__init__`;
- no Tk/widget base class;
- no import from `gicleeframe_view.py`;
- no file writes, network, subprocess, dialogs or Shopify operations;
- `GicleeFrameView` inherits it after the existing brand and page-readiness mixins and before `ctk.CTkScrollableFrame`.

`gicleeframe_view.py` remains the public import location for `GicleeFrameView`.

## 3. Exact ownership boundary

Move exactly three methods:

1. `_build_control_structure_card`
2. `_reset_structure_dry_run_display`
3. `_run_structure_dry_run`

The new module owns a narrow layout token:

- `_STRUCTURE_DRY_RUN_WRAPLENGTH = 292`

This value preserves the current expression `_CONTROL_COL_MINSIZE - 28`, where the host control-column minimum remains 320. `_CONTROL_COL_MINSIZE` itself must remain in the host because workspace grid and skeleton layout consume it.

## 4. Host-owned composition and shared behavior

The following remain in `gicleeframe_view.py`:

- `_build_control_column` — composes structure → readiness → safety;
- `_build_safety_card`;
- `_CONTROL_COL_MINSIZE`;
- `_SAFETY_TITLE` and `_SAFETY_CHECKLIST`;
- all lifecycle, scheduler, selection, inventory implementation, page-context, preview, layer-nav, cache and editor methods.

The extracted mixin may call:

- `self._refresh_inventory(warn_if_draft=False)`;
- `self._fill_page_readiness(ready)` supplied by `GicleeFramePageReadinessMixin`;
- `self._on_status(...)`.

It must not duplicate or wrap these host/mixin dependencies.

## 5. Compatibility contracts

Preserve exactly:

- `GicleeFrameView` public import path and class identity;
- MRO compatibility with `GicleeFrameBrandPanelMixin` and `GicleeFramePageReadinessMixin`;
- structure card copy, layout, colors, dimensions and packing order;
- button label and callback;
- empty-state copy, wrap length and muted color;
- inventory refresh only when inventory is absent;
- dry-run construction, readiness evaluation and combined summary formatting;
- update of the structure label, page-readiness panel and status callback;
- control-column order: structure → readiness → safety;
- RAM-only behavior;
- no changes to timing constants, `after()`, scheduler ownership, telemetry or performance lanes;
- no writer, persistence, sync, upload, publish, deploy or Shopify mutation.

## 6. Import ownership after extraction

Move from `gicleeframe_view.py` only symbols with no remaining host consumer after extraction:

- `STRUCTURE_EMPTY_STATE`;
- `build_page_structure_dry_run`;
- `format_structure_dry_run_summary`;
- `evaluate_gicleeframe_page_readiness`;
- `format_page_readiness_block`.

Retain `CHECK_STRUCTURE_LABEL` in `gicleeframe_view.py`, because the host-owned command bar still uses it for the structure-check action after the method implementation moves to the mixin.

Retain all primitives and theme imports still consumed elsewhere in the host. In particular, do not remove `_make_gf_card`, `_make_card_title`, `_make_secondary_button`, `_make_empty_state` or `theme` solely because the moved methods use them.

## 7. Source-text tests

`test_studio_gicleeframe_shell.py` currently expects structure-dry-run definitions and copy in the host source.

Update only ownership-sensitive assertions:

- structure-card, reset, action and structure-only copy move to `gicleeframe_view_structure_dry_run.py`;
- `CHECK_STRUCTURE_LABEL`, `_build_control_column`, `_build_safety_card`, `_CONTROL_COL_MINSIZE` and safety assertions remain in `gicleeframe_view.py`;
- do not satisfy tests with comments, dead aliases or copied strings;
- add no-write/no-network/no-scheduler guardrails for the new module.

## 8. New tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_structure_dry_run.py`

Minimum coverage:

1. module imports without `Komponenty.*`;
2. no writes, network, subprocess, dialogs, Shopify or scheduler ownership;
3. mixin has no `__init__` and no Tk base;
4. exact three-method ownership;
5. `_STRUCTURE_DRY_RUN_WRAPLENGTH == 292`;
6. MRO contains brand, page-readiness and structure-dry-run mixins;
7. moved methods resolve from `GicleeFrameStructureDryRunMixin` and are absent from `GicleeFrameView.__dict__` after wiring;
8. `_build_control_column`, `_build_safety_card` and inventory implementation remain host-owned;
9. reset preserves empty-state copy and muted color;
10. dry-run preserves refresh-if-missing, label update, readiness handoff and status callback.

## 9. Exact durable allowlist

Maximum durable scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_structure_dry_run.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_structure_dry_run.py`
4. `cursor-api/tests/test_studio_gicleeframe_shell.py`
5. only directly affected existing Giclée Frame source-text tests, if proven necessary
6. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
7. this contract document

No `.github`, workflow, version, starter-file or ZIP changes.

## 10. Required validation

Before push of the integration commit:

- `py_compile` for host, structure module, page-readiness module and brand module;
- new structure boundary tests;
- page-readiness and brand boundary/MRO tests;
- shell, lifecycle, lazy-shell and progressive-boot tests;
- existing page dry-run and readiness tests;
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
- no control-column extraction;
- no safety-card extraction;
- no page-readiness refactor;
- no inventory implementation refactor;
- no RAM-variant action extraction;
- no top-bar/command-bar extraction;
- no timing, scheduler, performance or telemetry changes;
- no editor, section-list, preview, page-context, layer-nav or cache changes;
- no writer, persistence or Shopify operation;
- no starter-file update in this PR;
- no ZIP generation.
