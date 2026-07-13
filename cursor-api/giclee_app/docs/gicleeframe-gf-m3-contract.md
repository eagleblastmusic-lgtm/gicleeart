# GF-M3 — F1 Brand Panel Extraction Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `280258fe51dcf779b352e24417aa94740fb3a87a`  
Work branch: `gpt-work/gicleeframe-modularization-m3-brand-panel`  
Integration commit SHA: `3ba73fdfdcaa3fb3d942bfaa0c14e3586713d526`

## 1. Discovery decision

GF-M3 extracts the self-contained **F1 brand planning panel** from the 8k+ line `GicleeFrameView` implementation.

The selection/performance lane, atomic reveal, boot scheduling, page-context scheduler, details-on-demand pipeline, section-list batching and lifecycle remain in `gicleeframe_view.py`. They are tightly coupled to timing, Tk `after()` ownership, telemetry and source-text regression tests and are explicitly outside this stage.

The F1 brand panel is the smallest coherent stateful UI boundary found by discovery:

- it owns the brand-only RAM draft flow;
- it is separate from the F2 page editor and page draft;
- it performs no file write, network operation or Shopify mutation;
- it does not own selection scheduling, performance lanes, cache or lifecycle;
- it was moved without changing visible copy, layout or behavior.

## 2. Resulting architecture

Created:

`cursor-api/giclee_app/ui/gicleeframe_view_brand.py`

Shape:

- a narrow mixin named `GicleeFrameBrandPanelMixin`, with no `__init__`;
- no Tk/widget base class;
- methods moved byte-for-byte where practical;
- no import from `gicleeframe_view.py`, avoiding an import cycle;
- the host view retains lifecycle, scheduler and shared helper ownership;
- `GicleeFrameView` inherits the mixin before `ctk.CTkScrollableFrame`.

`gicleeframe_view.py` remains the public import location for `GicleeFrameView`.

## 3. Exact ownership boundary

The mixin owns exactly:

1. `_build_f1_brand_section_placeholder`
2. `_build_f1_brand_section_deferred`
3. `_build_f1_brand_section_full`
4. `_build_f1_brand_section_panel_content`
5. `_build_rules_section`
6. `_clear_brand_plan`
7. `_fill_brand_readiness`
8. `_on_brand_variant`
9. `_on_brand_placement`
10. `_run_brand_dry_run`

The adapter `_toggle_f1_section` remains in `gicleeframe_view.py`. Discovery showed that it directly owns the lazy/progressive boot gate and the `studio.gicleeframe.f1.build_on_expand` event. Keeping that adapter in the host prevents boot-policy duplication and preserves scheduler/telemetry ownership.

The shared `_pack_readiness_row` also remains in the host because both F1 brand readiness and F2 page readiness consume it.

## 4. Imports moved during integration

F1-only imports were removed from `gicleeframe_view.py` after their consumers moved to the new module, including relevant symbols from:

- `gicleeframe_brief`;
- `gicleeframe_draft_state`;
- `gicleeframe_dry_run`;
- the brand part of `gicleeframe_readiness`;
- `SectionHeader`, which is now consumed by the brand panel module.

Imports required by the retained `_toggle_f1_section` adapter, F2 page readiness and shared helpers remain in the host. No unrelated F2/page-editor imports were moved.

## 5. Compatibility contracts

The implementation preserves:

- `GicleeFrameView` public import path and class identity;
- launcher routing;
- `set_navigation`, `on_show`, `on_hide` and all lifecycle behavior;
- exact F1 labels, status text, fonts, colors, packing order and initial collapsed state;
- exact lazy-shell behavior and existing event names;
- exact RAM-only draft semantics;
- no writer, F3/F4, save, sync, upload, publish or deploy capability;
- no change to selection, page-context, preview, layer-nav or details-on-demand flows;
- no change to timing constants, `after()` delays, scheduler ownership or cancellation;
- no change to performance telemetry outside module attribution required by the extraction.

## 6. Source-text tests

Several tests inspect `gicleeframe_view.py` directly. Only assertions whose ownership genuinely moved were updated.

Rules retained:

- no comments or dead aliases were added to satisfy source-text assertions;
- moved F1 panel assertions read `gicleeframe_view_brand.py`;
- the lazy/progressive expand adapter and its event assertion remain pointed at `gicleeframe_view.py`;
- F2, selection, scheduler and lifecycle assertions remain pointed at `gicleeframe_view.py`;
- identity/MRO tests prove that moved methods are provided by `GicleeFrameBrandPanelMixin` and resolve on `GicleeFrameView`.

## 7. Tests added and completed

Created:

`cursor-api/tests/test_studio_gicleeframe_view_brand.py`

Coverage:

1. module imports without importing `Komponenty.*`;
2. no `open`, `write_text`, `requests`, `shutil`, subprocess or Shopify operations;
3. mixin has no `__init__` and does not subclass a Tk widget;
4. exact ten-method ownership;
5. F1 labels and deferred event marker remain present;
6. expand/collapse adapter remains host-owned;
7. shared readiness-row renderer remains host-owned;
8. no boot, selection, page-context, cache, details-on-demand or lifecycle methods moved into the mixin;
9. mixin is present in `GicleeFrameView.__mro__`;
10. each moved method resolves from `GicleeFrameBrandPanelMixin` and is absent from `GicleeFrameView.__dict__`;
11. directly affected source-text tests inspect the correct owner.

## 8. Exact durable allowlist

Final durable scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_brand.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_brand.py`
4. `cursor-api/tests/test_studio_gicleeframe_shell.py`
5. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
6. this contract document

No `.github` changes. No workflow changes. No version bump.

## 9. Validation evidence

Local integration validation reported on commit `3ba73fdfdcaa3fb3d942bfaa0c14e3586713d526`:

- `py_compile`: PASS;
- boundary/shell/lazy-shell/progressive-boot/lifecycle: `37 passed`;
- `pytest -q -k gicleeframe`: `344 passed, 1479 deselected`;
- runtime-write inventory: `12 passed`;
- `git diff --check`: PASS;
- worktree: clean;
- `gicleeframe_view.py`: `6 insertions, 262 deletions` in the integration commit;
- no deploy, Shopify mutation or workflow changes.

Required CI pipeline before merge:

1. exact-head Hermetic smoke and artifact review;
2. Tk GUI smoke and Tcl/Tk probe;
3. full baseline;
4. runtime-write inventory and parse-error artifact review;
5. exact-head final review;
6. squash merge with `expected_head_sha` only after the full contract passes.

## 10. Explicit exclusions

- no UI redesign;
- no copy changes;
- no layout changes;
- no timing or scheduler changes;
- no performance tuning;
- no cache changes;
- no page-draft or inventory changes;
- no writer or persistence;
- no Shopify operation;
- no starter-file update in this implementation PR;
- no ZIP generation.
