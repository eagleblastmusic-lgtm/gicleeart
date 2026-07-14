# GF-M11 — Section List Rendering & Row Construction Contract

Status: **PLANNED — CONTRACT LOCKED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `22dacb8e332e1840c3af84a29200e043ea5cc1e3`  
Work branch: `gpt-work/gicleeframe-modularization-m11-section-list-rendering`

## 1. Objective

Extract the cohesive **Section List Rendering & Row Construction** boundary from `GicleeFrameView` into a dedicated mixin.

The package owns:

- full section-list rebuild orchestration;
- chunked full-list row creation;
- progressive/incremental list rendering;
- first and steady batch construction;
- continuation scheduling between batches;
- construction and callback wiring of individual section rows;
- the legacy `_render_section_menu` adapter that delegates to the renderer.

This boundary deliberately does **not** absorb dropdown open/close behavior, selection orchestration, drag/reorder mutation, inventory/model rebuilding, initial-selection policy, progressive lifecycle gates, editor population or atomic reveal.

## 2. Exact method boundary

Move exactly these 8 methods from `GicleeFrameView`:

1. `_render_section_list`
2. `_render_full_list_chunk`
3. `_render_section_list_incremental`
4. `_render_section_list_batch`
5. `_schedule_section_list_batch_continuation`
6. `_create_section_list_row`
7. `_build_section_row`
8. `_render_section_menu`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_section_list_rendering.py`

Target owner:

```python
class GicleeFrameSectionListRenderingMixin:
```

After integration:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameSectionListRenderingMixin,
    method_name,
)
```

Do **not** move `_finalize_full_list_render`. It owns the initial-selection/progressive-policy decision and remains an explicit host adapter called by `_render_full_list_chunk`.

## 3. Target MRO

```python
class GicleeFrameView(
    GicleeFrameBrandPanelMixin,
    GicleeFramePageReadinessMixin,
    GicleeFrameStructureDryRunMixin,
    GicleeFrameSafetyCardMixin,
    GicleeFrameReadinessRowMixin,
    GicleeFrameTopBarMixin,
    GicleeFrameRamVariantMixin,
    GicleeFrameSectionListShellMixin,
    GicleeFrameSectionListRenderingMixin,
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **nine mixins** before `ctk.CTkScrollableFrame`.

`GicleeFrameSectionListRenderingMixin` follows `GicleeFrameSectionListShellMixin` because the shell calls `_create_section_list_row` through `self`, while the rendering module may import shared first-batch/placeholder constants from the shell module.

## 4. Mixin constraints

`GicleeFrameSectionListRenderingMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify operations or deploy operations;
- may use `after()` and `after_idle()` only for renderer batching/continuations;
- does not own inventory loading or model-cache rebuilding;
- does not own selection generation, editor population or atomic-swap logic;
- does not own dropdown positioning/outside-click bindings;
- does not own drag/reorder mutation;
- does not own global progressive bootstrap/lifecycle gates.

Export the mixin and boundary-owned constants through an explicit `__all__`.

## 5. Boundary-owned constants

Move these 4 constants from the host to the new renderer module, preserving exact values:

```python
_SECTION_ROW_GRIP = "⋮"
_SECTION_ROW_HEIGHT = 64
_GF_SECTION_BATCH_SIZE = 8
_GF_SECTION_BATCH_DELAY_MS = 0
```

Do not retain duplicate definitions in `gicleeframe_view.py`.

The renderer imports these existing shell-owned constants from `gicleeframe_view_section_list_shell.py` instead of duplicating or moving them:

```python
_GF_SECTION_FIRST_BATCH_SIZE
_SECTION_PLACEHOLDER
```

Do not move:

```text
_GF_SECTION_FIRST_VISIBLE_DEFER_MS
_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS
_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS
_GF_SECTIONS_COLUMN_EARLY_DEFER_MS
_SECTION_LIST_WIDTH
_SECTION_LIST_HEIGHT
_SECTION_LIST_LOADING_TEXT
_SECTION_LABEL_MAX_CHARS
_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV
```

The first-visible scheduling constant and collapse-on-click policy remain host-owned because their schedulers/selection adapters remain in the host.

## 6. Required direct imports in the renderer

The new module may import its direct dependencies from neutral modules, including:

- `time`, `tkinter`, `customtkinter`;
- `SectionDropdownOption` from `gicleeframe_page_draft`;
- `log_event`, `span`;
- `theme`;
- `_ellipsize`, `_section_kind_copy` from `gicleeframe_view_models`;
- visual primitives/constants required by row construction;
- `_GF_SECTION_FIRST_BATCH_SIZE` and `_SECTION_PLACEHOLDER` from the section-list shell module.

It must not import the host module.

## 7. Host-owned adapters and state

The following remain in `GicleeFrameView.__dict__` and may be called by the mixin through `self`:

```text
__init__
_finalize_full_list_render
_rebuild_page_model_cache
_defer_background_for_selection
_show_editor_placeholder_state
_try_mark_progressive_full_ready
_precompute_page_context_specs_cache
_log_visual_gate_ready
_try_mark_perceived_ready
_schedule_atomic_reveal_check
_since_visual_enter_ms
_queue_latency_since_ms
_on_section_row_click
_start_section_drag
_finish_section_drag
_highlight_section_row
_highlight_section_rows
_select_element
_render_section_dropdown interaction methods
_upgrade_section_list_scroll
_schedule_section_list_incremental
_run_deferred_bootstrap
_try_mark_progressive_full_ready
```

All renderer-related state initialization remains in host `__init__`, including:

- `_section_list_scroll`;
- `_section_row_frames` and `_section_row_ids`;
- `_highlighted_section_id`;
- `_full_list_render_generation` when initialized dynamically;
- progressive flags/timestamps;
- selected ID and merged/model caches.

## 8. Behavioral contract

Preserve exactly:

### Full rebuild

- no-op when `_section_list_scroll` is missing;
- generation increment/cancellation behavior;
- destruction of existing children and clearing row caches;
- placeholder rendering when no merged elements exist;
- cache rebuild only through host adapter `_rebuild_page_model_cache`;
- exact `studio.gicleeframe.render_section_list` span and payload;
- delegation to `_render_full_list_chunk`.

### Full chunk rendering

- stale-generation and widget-existence guards;
- batch size `_GF_SECTION_BATCH_SIZE`;
- row order and use of `_build_section_row`;
- exact `after(_GF_SECTION_BATCH_DELAY_MS, ...)` continuation behavior;
- final delegation to host `_finalize_full_list_render`.

### Progressive rendering

- selection-priority deferral through host adapter `_defer_background_for_selection`;
- exact incremental enter/start/batch/done events and payloads;
- empty-list first-visible/perceived/full-ready behavior;
- model-cache rebuild through host adapter only;
- row-cache clearing and child destruction order;
- first batch uses `_GF_SECTION_FIRST_BATCH_SIZE`, subsequent batches use `_GF_SECTION_BATCH_SIZE`;
- first-visible event/state/gate order remains unchanged;
- continuation goes through `_schedule_section_list_batch_continuation`;
- final placeholder/selected-state behavior remains unchanged;
- `after_idle(self._precompute_page_context_specs_cache)` remains unchanged;
- full-ready remains a host adapter.

### Row construction

- exact frame geometry, radius, padding and height;
- static-lane rows omit drag grip;
- non-static rows wire grip press/release to host drag adapters;
- index pill formatting and layout;
- kind label and title typography/copy;
- title ellipsis behavior;
- all click targets call host `_on_section_row_click` with the same element ID;
- `_build_section_row` remains a thin adapter to `_create_section_list_row`.

### Section menu adapter

- `_render_section_menu` remains a one-line behavior-preserving delegation to `_render_section_list`.

## 9. Explicit exclusions

GF-M11 must not change or move:

- `_finalize_full_list_render` and initial-selection policy;
- `_selected_section_label`, `_update_section_list_trigger`;
- `_collapse_section_list`, `_open_section_dropdown`, `_toggle_section_list`;
- outside-click bind/unbind/widget ancestry logic;
- `_select_element`, selection generations, cache, atomic swap or editor population;
- `_highlight_section_row` / `_highlight_section_rows`;
- `_start_section_drag`, `_finish_section_drag`, `_section_row_index_at_root_y`;
- `reorder_page_blocks`, RAM draft mutation or inventory merge;
- `_upgrade_section_list_scroll`, shell/static-lane construction or scroll-upgrade scheduling;
- inventory loading/model ownership;
- perceived-ready, progressive-full-ready or atomic-reveal definitions;
- wording, dimensions, colors, timings, callback wiring, telemetry names or payload fields;
- writer, persistence, filesystem mutation, Shopify, sync or deploy;
- `.github`, workflows, versioning, starter files or ZIP archives.

## 10. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py`

Minimum coverage:

1. exact 8-method ownership;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no write/network/subprocess/Shopify/deploy operations;
5. only renderer-owned `after()` / `after_idle()` usage;
6. complete nine-mixin MRO;
7. identity for all 8 methods;
8. host ownership of excluded adapters;
9. exact values and ownership of the 4 moved constants;
10. shell constants imported without duplication;
11. full rebuild empty and populated paths;
12. stale full-render generation guard;
13. full chunk continuation and finalizer delegation;
14. incremental empty path;
15. first-batch versus steady-batch sizes;
16. first-visible event/state/adapter order;
17. selection-priority deferral path;
18. continuation scheduling;
19. final incremental completion adapters;
20. static versus non-static row construction;
21. click callback wiring;
22. drag callback wiring only for non-static rows;
23. `_build_section_row` and `_render_section_menu` delegation.

Use fake widgets and monkeypatching where practical. Do not require a live display outside existing canonical Tk smoke tests.

## 11. Existing tests requiring source-ownership migration

Directly inspect and update only when affected:

```text
cursor-api/tests/test_studio_gicleeframe_progressive_boot.py
cursor-api/tests/test_studio_gicleeframe_section_list_fast_lane_6g5j.py
cursor-api/tests/test_studio_gicleeframe_first_visible_sections_6g5f.py
cursor-api/tests/test_studio_gicleeframe_section_list_diagnostics_6g5i.py
cursor-api/tests/test_studio_gicleeframe_micro_batches_6g3.py
cursor-api/tests/test_studio_gicleeframe_perceived_responsiveness_6g4.py
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_shell.py
```

Complete-MRO tests may receive only membership of `GicleeFrameSectionListRenderingMixin` where they already assert the complete MRO:

```text
cursor-api/tests/test_studio_gicleeframe_view_brand.py
cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py
cursor-api/tests/test_studio_gicleeframe_view_readiness_row.py
cursor-api/tests/test_studio_gicleeframe_view_safety.py
cursor-api/tests/test_studio_gicleeframe_view_top_bar.py
cursor-api/tests/test_studio_gicleeframe_view_ram_variants.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
```

Rules:

- moved methods/constants/events must be read from the new renderer module;
- host-owned adapters continue to be asserted against the host;
- cross-boundary ordering tests may use combined host/shell/renderer source text but must preserve exact markers and ordering intent;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks;
- centralize all 8 identity assertions in the new boundary test;
- update the shell boundary host-ownership set by removing only the 8 methods now owned by the renderer;
- add the renderer path to shell/no-write guardrails, but do not add it to `_NEW_PLANNING_MODULES`.

## 12. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m11-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_section_list_rendering.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py`
6. directly affected tests listed in section 11;
7. complete-MRO tests listed in section 11, with membership-only changes.

Any additional changed test requires a concrete direct source-ownership dependency and explicit justification in the implementation report.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage the exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract section list rendering`

The PR remains draft after the implementation push.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M11 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M10 as historical checkpoints;
- change actual future pointers from `GF-M11+` to `GF-M12+`;
- document exactly nine mixins after GF-M11;
- document that dropdown interaction, selection/highlighting and drag/reorder remain host-owned candidates for GF-M12+.

## 14. Required local validation

- `py_compile` for host, the new renderer and all existing mixins;
- new boundary tests;
- all directly affected rendering/progressive/fast-lane/diagnostic tests;
- section-list shell boundary tests;
- fast-selection and selection-stability tests;
- all existing `test_studio_gicleeframe_selection_stability_6g5s*.py` tests;
- perceived/visual gate suites;
- `pytest -q -k gicleeframe`;
- runtime-write inventory;
- `git diff --check`;
- exact changed-file allowlist review.

## 15. CI and merge contract

1. Cursor pushes the implementation to the existing branch and leaves the PR draft.
2. Run draft Hermetic on the exact final head.
3. Review the exact diff and artifact before ready.
4. Mark ready only after exact-head Hermetic success.
5. Require canonical Hermetic, Tk GUI smoke and full pytest baseline on the same exact head.
6. Review JUnit, Tcl/Tk patchlevel and runtime-write inventory artifacts.
7. Confirm `behind_by=0`, mergeable state, exact changed files and no unresolved review threads.
8. Squash merge using `expected_head_sha=<exact final head>`.
9. Confirm PR merged and `master` identical to the resulting merge SHA.
