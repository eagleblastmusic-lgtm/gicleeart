# GF-M3 — F1 Brand Panel Extraction Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `280258fe51dcf779b352e24417aa94740fb3a87a`  
Work branch: `gpt-work/gicleeframe-modularization-m3-brand-panel`

## 1. Discovery decision

GF-M3 extracts the self-contained **F1 brand planning panel** from the 8k+ line `GicleeFrameView` implementation.

The selection/performance lane, atomic reveal, boot scheduling, page-context scheduler, details-on-demand pipeline, section-list batching and lifecycle remain in `gicleeframe_view.py`. They are tightly coupled to timing, Tk `after()` ownership, telemetry and source-text regression tests and are explicitly outside this stage.

The F1 brand panel is the smallest coherent stateful UI boundary found by discovery:

- it owns the brand-only RAM draft flow;
- it is separate from the F2 page editor and page draft;
- it performs no file write, network operation or Shopify mutation;
- it does not own selection scheduling, performance lanes, cache or lifecycle;
- it can be moved without changing visible copy, layout or behavior.

## 2. Target architecture

Created:

`cursor-api/giclee_app/ui/gicleeframe_view_brand.py`

Shape:

- a narrow mixin named `GicleeFrameBrandPanelMixin`, with no `__init__`;
- no Tk/widget base class;
- methods moved byte-for-byte where practical;
- no import from `gicleeframe_view.py`, avoiding an import cycle;
- the host view retains lifecycle, scheduler and shared helper ownership;
- final integration requires `GicleeFrameView` to inherit the mixin before `ctk.CTkScrollableFrame`.

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

## 4. Imports expected to move during integration

Move F1-only imports out of `gicleeframe_view.py` when they have no remaining consumer there, including relevant symbols from:

- `gicleeframe_brief`;
- `gicleeframe_draft_state`;
- `gicleeframe_dry_run`;
- the brand part of `gicleeframe_readiness`;
- UI helpers used exclusively by the brand panel.

Keep imports required by the retained `_toggle_f1_section` adapter, F2 page readiness and shared helpers. Do not move F2/page-editor imports.

## 5. Compatibility contracts

The implementation must preserve:

- `GicleeFrameView` public import path and class identity;
- launcher routing;
- `set_navigation`, `on_show`, `on_hide` and all lifecycle behavior;
- exact F1 labels, status text, fonts, colors, packing order and initial collapsed state;
- exact lazy-shell behavior and existing event names;
- exact RAM-only draft semantics;
- no writer, F3/F4, save, sync, upload, publish or deploy capability;
- no change to selection, page-context, preview, layer-nav or details-on-demand flows;
- no change to timing constants, `after()` delays, scheduler ownership or cancellation;
- no change to performance telemetry outside import/module attribution required by the extraction.

## 6. Source-text tests

Several tests inspect `gicleeframe_view.py` directly. Update them only where ownership genuinely moved.

Rules:

- do not satisfy source-text assertions with comments or dead aliases;
- point moved F1 panel assertions at `gicleeframe_view_brand.py` or at the combined source set;
- keep the lazy/progressive expand adapter and its event assertion pointed at `gicleeframe_view.py`;
- keep F2, selection, scheduler and lifecycle assertions pointed at `gicleeframe_view.py`;
- preserve meaningful assertions for lazy F1 behavior and event names;
- add an identity/MRO test proving the moved methods are provided by `GicleeFrameBrandPanelMixin` and available on `GicleeFrameView` after integration.

## 7. New tests

Created:

`cursor-api/tests/test_studio_gicleeframe_view_brand.py`

Current boundary coverage:

1. module imports without importing `Komponenty.*`;
2. no `open`, `write_text`, `requests`, `shutil`, subprocess or Shopify operations;
3. mixin has no `__init__` and does not subclass a Tk widget;
4. exact ten-method ownership;
5. F1 labels and deferred event marker remain present;
6. expand/collapse adapter remains host-owned;
7. shared readiness-row renderer remains host-owned;
8. no boot, selection, page-context, cache, details-on-demand or lifecycle methods moved into the mixin.

Still required after wiring:

- assert the mixin is present in `GicleeFrameView.__mro__`;
- assert each moved method resolves from `GicleeFrameBrandPanelMixin` on `GicleeFrameView`;
- update directly affected source-text tests to inspect the correct owner.

## 8. Exact durable allowlist

Expected maximum durable scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_brand.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_brand.py`
4. only directly affected existing Giclée Frame source-text tests
5. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
6. this contract document

No `.github` changes. No workflow changes. No version bump unless an existing repository policy explicitly requires it for this refactor.

## 9. Required validation

Before push of the integration commit:

- compile changed production modules;
- new brand-boundary tests including final MRO assertions;
- `test_studio_gicleeframe_shell.py`;
- `test_studio_gicleeframe_lazy_shell_6g2.py`;
- `test_studio_gicleeframe_lifecycle.py`;
- relevant visual-ready/startup tests;
- `pytest -k gicleeframe`;
- runtime-write inventory test;
- `git diff --check`;
- exact changed-file allowlist review.

CI pipeline after integration push:

1. draft Hermetic;
2. artifact review;
3. mark ready only after Hermetic success;
4. Tk GUI smoke and Tcl/Tk probe;
5. full baseline;
6. inventory and parse-error artifact review;
7. exact-head final review;
8. squash merge with `expected_head_sha` only after the full contract passes.

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
