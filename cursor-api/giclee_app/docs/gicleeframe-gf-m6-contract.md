# GF-M6 — F2 Safety Card Extraction Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `477d1f49a854aed9c656455d13b9ee085702a278`
Work branch: `gpt-work/gicleeframe-modularization-m6-safety-card`

## 1. Discovery decision

GF-M6 extracts the smallest coherent F2 boundary remaining after GF-M5: the static **Safety Card** rendered at the bottom of the control column.

The boundary owns only the safety-card construction, safety copy and its local wraplength token. It does not own control-column composition, structure dry-run, page readiness, inventory, lifecycle, schedulers, selection, page context, preview, layer navigation, cache, editor population or RAM-variant actions.

Rejected for this stage:

- `_build_control_column`, because the host must remain the composition root for structure → readiness → safety;
- top-bar and command-bar, because they own staggered `after()` scheduling, telemetry and atomic-reveal gates;
- RAM-variant actions, because they cross inventory refresh, selection state, menus and editor population;
- editor and section-list boundaries, because they are larger and performance-sensitive.

## 2. Target architecture

Create:

`cursor-api/giclee_app/ui/gicleeframe_view_safety.py`

Preferred shape:

- a narrow mixin named `GicleeFrameSafetyCardMixin`;
- no `__init__`;
- no Tk/widget base class;
- no import from `gicleeframe_view.py`;
- no file writes, network, subprocess, dialogs or Shopify operations;
- `GicleeFrameView` inherits it after the existing brand, page-readiness and structure-dry-run mixins and before `ctk.CTkScrollableFrame`.

`gicleeframe_view.py` remains the public import location for `GicleeFrameView`.

## 3. Exact ownership boundary

Move exactly one method:

1. `_build_safety_card`

The new module owns:

- `_SAFETY_TITLE = "Bezpieczeństwo"`;
- `_SAFETY_CHECKLIST` with the existing four rows and unchanged Polish copy;
- `_SAFETY_ROW_WRAPLENGTH = 276`.

The wraplength preserves the current expression `_CONTROL_COL_MINSIZE - 44`, where the host control-column minimum remains 320.

## 4. Host-owned composition and shared behavior

The following remain in `gicleeframe_view.py`:

- `_build_control_column` — composes structure → readiness → safety;
- `_CONTROL_COL_MINSIZE` — still consumed by workspace grid and skeleton layout;
- all lifecycle, scheduler, telemetry, selection, inventory, page-context, preview, layer-nav, cache, editor and RAM-variant methods;
- `_pack_readiness_row` and all prior extracted boundaries.

The safety mixin may use the stateless primitive `_build_safety_row`, but must not duplicate it.

## 5. Compatibility contracts

Preserve exactly:

- `GicleeFrameView` public import path and class identity;
- MRO compatibility with `GicleeFrameBrandPanelMixin`, `GicleeFramePageReadinessMixin` and `GicleeFrameStructureDryRunMixin`;
- control-column order: structure → readiness → safety;
- safety title, checklist row order and all copy;
- card variant `panel_deep`, radius `16`, packing and padding;
- safety-row primitive usage and wraplength `276`;
- bottom spacer label height `4`;
- RAM-only informational behavior;
- no timing constants, `after()`, scheduler ownership, telemetry or performance-lane changes;
- no writer, persistence, sync, upload, publish, deploy or Shopify mutation.

## 6. Import ownership after extraction

Remove from `gicleeframe_view.py` only symbols with no remaining host consumer after extraction:

- `_SAFETY_TITLE`;
- `_SAFETY_CHECKLIST`;
- `_build_safety_row` import.

Retain `_CONTROL_COL_MINSIZE` in the host.

Retain `ctk`, `_CARD_PAD_X`, `_make_card_title`, `_make_gf_card` and other primitives/theme imports when they still have other host consumers. Cleanup must be consumer-proven, not assumed.

## 7. Source-text tests

`test_studio_gicleeframe_shell.py` ownership-sensitive assertions were updated after MRO wiring:

- `_build_safety_card`, `_SAFETY_TITLE`, `_SAFETY_CHECKLIST`, `_build_safety_row` usage and safety-only copy live in `gicleeframe_view_safety.py`;
- `_build_control_column`, `_CONTROL_COL_MINSIZE` and control-column ordering remain host assertions;
- no-write/no-network/no-scheduler guardrails added for the safety module.

Page-readiness and structure-dry-run host-ownership tests no longer assert `_build_safety_card` in `GicleeFrameView.__dict__`.

## 8. Tests

`cursor-api/tests/test_studio_gicleeframe_view_safety.py` covers:

1. module imports without `Komponenty.*`;
2. no writes, network, subprocess, dialogs, Shopify or scheduler ownership;
3. mixin has no `__init__` and no Tk base;
4. exact one-method ownership;
5. exact safety title, checklist and row order;
6. `_SAFETY_ROW_WRAPLENGTH == 276`;
7. rendering calls the existing safety-row primitive four times with unchanged title/detail pairs and wraplength;
8. card variant, radius, packing and bottom spacer are preserved;
9. MRO contains all four mixins;
10. `_build_safety_card` resolves from `GicleeFrameSafetyCardMixin` and is absent from `GicleeFrameView.__dict__`;
11. `_build_control_column` remains host-owned.

## 9. Exact durable allowlist

Maximum durable scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_safety.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_safety.py`
4. `cursor-api/tests/test_studio_gicleeframe_shell.py`
5. directly affected existing Giclée Frame ownership tests, only where `_build_safety_card` host ownership is now obsolete
6. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
7. this contract document

No `.github`, workflow, version, starter-file or ZIP changes.

## 10. Required validation

Before push of the integration commit:

- `py_compile` for host and all four mixin modules;
- new safety boundary tests;
- brand, page-readiness and structure-dry-run MRO tests;
- shell, lifecycle, lazy-shell and progressive-boot tests;
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
- no structure-dry-run or page-readiness refactor;
- no inventory or RAM-variant action extraction;
- no top-bar/command-bar extraction;
- no timing, scheduler, performance or telemetry changes;
- no editor, section-list, preview, page-context, layer-nav or cache changes;
- no primitive duplication or redesign;
- no writer, persistence or Shopify operation;
- no starter-file update in this PR;
- no ZIP generation.
