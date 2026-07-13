# GF-M3 — F1 Brand Panel Extraction Contract

Status: **IMPLEMENTATION PENDING**

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

Create:

`cursor-api/giclee_app/ui/gicleeframe_view_brand.py`

Preferred shape:

- a narrow mixin named `GicleeFrameBrandPanelMixin`, with no `__init__`;
- methods moved byte-for-byte where practical;
- explicit type-only host attributes or a small Protocol only when it improves checking without runtime coupling;
- no import from `gicleeframe_view.py` to avoid a cycle;
- `GicleeFrameView` inherits the mixin before `ctk.CTkScrollableFrame`.

`gicleeframe_view.py` remains the public import location for `GicleeFrameView`.

## 3. Candidate ownership

Move only F1-brand-specific behavior, after verifying the exact current method set on the pinned base:

- F1 placeholder/full/deferred panel construction;
- F1 expand/collapse handling;
- brand variant and placement callbacks;
- brand plan clear action;
- brand dry-run action;
- brand readiness rendering that is not shared with page readiness.

Keep shared helpers in the main view unless discovery proves a smaller neutral shared boundary. In particular, do not move a helper merely because F1 calls it when it is also used by the F2 page readiness panel.

## 4. Imports expected to move

Move F1-only imports out of `gicleeframe_view.py` when they have no remaining consumer there, including relevant symbols from:

- `gicleeframe_brief`;
- `gicleeframe_draft_state`;
- `gicleeframe_dry_run`;
- the brand part of `gicleeframe_readiness`;
- UI helpers used exclusively by the brand panel.

Do not move F2/page-editor imports.

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

Several tests inspect `gicleeframe_view.py` directly. Update them only where the ownership genuinely moved.

Rules:

- do not satisfy source-text assertions with comments or dead aliases;
- point F1-specific assertions at `gicleeframe_view_brand.py` or at the combined source set;
- keep F2, selection, scheduler and lifecycle assertions pointed at `gicleeframe_view.py`;
- preserve meaningful assertions for the lazy F1 behavior and its event names;
- add an identity/MRO test proving the moved methods are provided by `GicleeFrameBrandPanelMixin` and available on `GicleeFrameView`.

## 7. New tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_brand.py`

Minimum coverage:

1. module imports without importing `Komponenty.*`;
2. no `open`, `write_text`, `requests`, `shutil`, subprocess or Shopify operations;
3. mixin has no `__init__` and does not subclass a Tk widget;
4. expected F1 methods are owned by the mixin and resolve on `GicleeFrameView`;
5. F1 labels and event markers remain present in the correct module;
6. brand dry-run and clear callbacks retain RAM-only behavior;
7. no boot, selection, page-context, cache, details-on-demand or lifecycle methods moved into the mixin.

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

Before push:

- compile changed production modules;
- new brand-boundary tests;
- `test_studio_gicleeframe_shell.py`;
- `test_studio_gicleeframe_lazy_shell_6g2.py`;
- `test_studio_gicleeframe_lifecycle.py`;
- relevant visual-ready/startup tests;
- `pytest -k gicleeframe`;
- runtime-write inventory test;
- `git diff --check`;
- exact changed-file allowlist review.

CI pipeline after push:

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
