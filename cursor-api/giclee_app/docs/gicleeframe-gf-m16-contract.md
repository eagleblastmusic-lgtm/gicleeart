# GF-M16 — Visual Detail Renderers Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `544199b2acffe1194a3cb7754348b023a2facc86`  
Work branch: `gpt-work/gicleeframe-modularization-m16-visual-detail-renderers`

## 1. Objective

Extract the complete **Visual Detail Renderers** boundary from `GicleeFrameView` into one dedicated mixin.

The boundary owns, as one cohesive subsystem:

- tree-row lookup helpers used by visual detail rendering;
- preview-key selection, frame/widget caching and shell-bootstrap cleanup;
- divider, media-section, legacy, image, text and fallback preview renderers;
- section-preview update/reuse/stale-swap behavior;
- layer-navigation item derivation, tile cache, visibility synchronization and rendering;
- child-overview tile rendering and range/batch support.

The boundary deliberately does **not** absorb:

- details-on-demand orchestration/cache from GF-M15;
- editor shell/static containers from GF-M14;
- page-context specification, rows, batching, collapsed groups or inline setting editor;
- selection orchestration;
- lifecycle, inventory loading/merge or progressive boot.

GF-M16 is RAM-only. It does not enable persistence, writer, Shopify sync or deploy.

## 2. Exact method boundary

Move exactly these **40 methods** from `GicleeFrameView`.

### A. Shared visual lookup and labels

1. `_parent_row_for_element`
2. `_tree_row_for_element`
3. `_image_ref_label`

### B. Preview metadata helpers

4. `_preview_meta_lines`
5. `_apply_metadata_preview_content`
6. `_build_section_metadata_preview_structure`

### C. Layer-navigation renderer

7. `_selected_layer_items`
8. `_layer_nav_tile_signature`
9. `_sync_layer_nav_visibility`
10. `_hide_layer_nav_tiles`
11. `_show_layer_nav_tile`
12. `_get_or_create_layer_nav_header`
13. `_get_or_create_layer_nav_row`
14. `_get_or_create_layer_nav_tile`
15. `_update_layer_nav_tile`
16. `_update_layer_nav`

### D. Preview cache and frame lifecycle

17. `_preview_key_for_element`
18. `_hide_preview_frames`
19. `_show_preview_frame`
20. `_get_or_create_preview_frame`
21. `_get_or_create_preview_label`
22. `_clear_preview_shell_bootstrap_once`

### E. Type-aware preview structures and content

23. `_divider_preview_dimensions`
24. `_build_divider_preview_structure`
25. `_update_divider_preview_content`
26. `_build_media_section_preview_structure`
27. `_update_media_section_preview_content`
28. `_build_legacy_preview_structure`
29. `_update_legacy_preview_content`
30. `_build_default_preview_structure`
31. `_update_default_preview_content`
32. `_build_image_preview_structure`
33. `_update_image_preview_content`
34. `_build_text_preview_structure`
35. `_update_text_preview_content`
36. `_ensure_preview_structure`
37. `_update_preview_content`
38. `_update_section_preview`

### F. Children overview renderer

39. `_fill_children_overview_buttons`
40. `_fill_children_overview_buttons_range`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_visual_detail_renderers.py`

Target owner:

```python
class GicleeFrameVisualDetailRenderersMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameVisualDetailRenderersMixin,
    method_name,
)
```

Do not leave host wrappers or duplicate implementations.

## 3. Constants and direct imports

GF-M16 introduces **no new boundary-owned timing or copy constants**.

The visual renderer module may directly import:

- `tkinter as tk`;
- `Any` from `typing`;
- `customtkinter as ctk`;
- `MergedPageElement`, `editor_title_for_element`, `parent_row_title` from the RAM-only page draft module;
- `log_event`, `span`;
- `theme`;
- `_ellipsize`, `_section_kind_copy` from `gicleeframe_view_models`;
- the required stateless tokens/helpers from `gicleeframe_view_primitives`;
- `_LAYER_NAV_TITLE` from `gicleeframe_view_editor_shell`.

`_LAYER_NAV_TITLE` remains owned and exported by the GF-M14 editor-shell module. Do not duplicate or relocate its value in GF-M16.

The new module must not import `gicleeframe_view.py`.

All runtime cross-boundary calls go through `self`.

## 4. Target MRO

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
    GicleeFrameSectionListInteractionMixin,
    GicleeFrameSelectionOrchestrationMixin,
    GicleeFrameEditorShellMixin,
    GicleeFrameDetailsOnDemandMixin,
    GicleeFrameVisualDetailRenderersMixin,
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **fourteen mixins** before `ctk.CTkScrollableFrame`.

The visual-renderer mixin follows details-on-demand because:

- GF-M15 dispatches preview, layer-nav and children renderer methods through `self`;
- GF-M15 cache apply/save calls the visual lookup helpers through `self`;
- the visual renderer calls editor-shell content-swap helpers through `self`;
- the visual renderer calls selection-owned `_select_element` and timing through `self`;
- no method name is duplicated across these boundaries.

## 5. Mixin constraints

`GicleeFrameVisualDetailRenderersMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may create/configure/hide only preview frames/widgets, layer-navigation widgets and children-overview tiles already owned by this boundary;
- does not initialize state;
- does not schedule background jobs or own `after()` queues;
- does not load or merge inventory;
- does not mutate the RAM page draft;
- does not own section selection or selection priority;
- does not own details CTA, cache policy or module scheduling;
- does not own editor-shell/static-container construction;
- does not implement page-context rows, settings, batching or inline editors;
- does not own persistence, writer or deployment behavior.

## 6. Host-owned adapters and exclusions

The following remain outside the visual renderer and may be called through `self`:

```text
__init__
_selected_id / _merged model state
_select_element
_since_selection_click_ms
_log_editor_content_swapped
_editor_last_ready_element_id
_section_preview_canvas
_section_preview_badge
_section_preview_card
_layer_nav_frame
_children_overview_buttons
```

The following ownership remains explicit:

- GF-M14 editor shell owns static preview/layer/children containers and `_LAYER_NAV_TITLE`;
- GF-M15 details-on-demand owns dispatch, cache, generation guards, batching orchestration and deferred wrappers;
- host owns all page-context methods and stateful setting-editor behavior;
- host owns lifecycle, inventory, progressive boot, perceived-ready and atomic reveal;
- selection mixin owns `_select_element`;
- writer, persistence, Shopify and deploy remain excluded.

Page-context methods must not move, including but not limited to:

```text
_page_context_shell_summary_lines
_show_page_context_shell_state
_schedule_or_fill_page_context
_hide_page_context_rows
_show_page_context_row
_get_or_create_readonly_card
_get_or_create_page_context_row
_get_or_create_divider_grid
_get_or_create_divider_group
_update_setting_widget
_create_page_setting_widget
_get_or_create_page_setting_row
_get_or_create_setting_card
_page_context_row_specs
_create_page_context_row_from_spec
_populate_page_context_batch
_populate_page_context_progressive_stable
_populate_page_context_progressive
_fill_page_context
_make_page_setting_spec
_format_page_setting_value
_create_page_context_setting_summary_row
_close_active_setting_editor
_open_inline_setting_editor
_create_full_setting_editor_inside_row
_create_page_context_collapsed_group_row
_expand_page_context_group
_populate_page_context_group_batch
_cancel_page_context_jobs
_schedule_page_context_job
```

## 7. Host-owned state

All state initialization remains in `GicleeFrameView.__init__`, including:

```text
_section_tree_rows_cache
_selected_id
_merged
_layer_nav_tile_cache
_layer_nav_title_widgets
_layer_nav_meta_widgets
_layer_nav_visible_keys
_layer_nav_row_frame
_layer_nav_header_label
_layer_nav_rendered_signatures
_layer_nav_bound_targets
_layer_nav_visible_order
_preview_frame_cache
_preview_value_widgets
_preview_active_key
_preview_shell_bootstrapped
_preview_bootstrap_panel
_preview_bootstrap_status_label
_section_preview_canvas
_section_preview_badge
_section_preview_line
_children_overview_buttons
_editor_last_ready_element_id
```

GF-M16 must not introduce a mixin `__init__` or move state initialization.

## 8. Behavioral contract

### Shared lookups

Preserve exactly:

- parent-row lookup across root rows and children;
- tree-row lookup semantics and `None` behavior;
- image reference normalization, Shopify-prefix stripping and final path-segment behavior.

### Layer navigation

Preserve exactly:

- parent/children ordering and labels;
- tile signatures and rendered-signature cache;
- visible-order and visible-key synchronization;
- hide/show idempotence and swallowed `tk.TclError`;
- header/row/tile lazy construction and cache reuse;
- title/meta/status styling and active-state colors;
- click binding to selection-owned `_select_element` for tile and nested widgets;
- bound-target reuse guard;
- empty-items behavior, including stale-content preservation;
- frame packing, delta/reuse/summary telemetry and payload fields;
- stale-refresh content-swap logging.

### Preview frame lifecycle

Preserve exactly:

- type-based preview keys, never element-ID-based keys;
- hide/show active-key behavior and Tcl fallbacks;
- frame and label cache reuse;
- exact widget-created/frame-created telemetry;
- one-time bootstrap cleanup, cached-frame preservation and destroy-fallback telemetry;
- no normal-path destruction of cached preview frames.

### Preview type renderers

Preserve exactly:

- divider thickness/width calculations and bounds;
- divider ghost/line structure and update behavior;
- media-section metadata heading/subtitle/fallback order;
- legacy metadata heading/subtitle;
- default/fallback metadata and `preview.fallback_used` telemetry;
- image preview structure, image-ref label and RAM/read-only copy;
- text preview structure and title/kind updates;
- exact preview-key dispatch in `_ensure_preview_structure` and `_update_preview_content`;
- labels, wording, dimensions, fonts, colors, packing and placement.

### Section preview update

Preserve exactly:

- canvas guard;
- `populate.preview` span payload;
- before/after child counts;
- badge copy through `_section_kind_copy`;
- structure-before-content ordering;
- stale-refresh behavior when preview key changes or remains equal;
- normal-path bootstrap clear → hide → show ordering;
- editor content-swap calls and payload;
- `preview.reuse` and `section_preview` telemetry;
- preview cache/widget counts.

### Children overview

Preserve exactly:

- tree-row lookup and zero-child telemetry;
- media-section-only rendering;
- full versus ranged rendering behavior;
- stale-refresh destruction with Tcl handling;
- grid reuse and creation;
- child ordering, column weights and tile layout;
- title/label/call-to-action copy;
- click binding for tile and nested children;
- completion telemetry and stale-refresh content-swap logging.

## 9. Explicit exclusions

GF-M16 must not move or modify:

- details-on-demand methods or constants from GF-M15;
- editor-shell methods or constants from GF-M14;
- page-context engine and inline setting editor;
- selection orchestration;
- section-list shell/rendering/interaction;
- inventory loading/merge and initial-selection policy;
- progressive/perceived/atomic-reveal lifecycle;
- RAM draft mutation and variant workflow;
- `.github`, workflows, versioning, Shopify/theme, writer, persistence, deploy, starter files or ZIP archives;
- wording, layout, timings, event names, payload fields, callback ordering or cache semantics.

Do not combine this extraction with cleanup/refactoring of the renderer algorithms. Move behavior 1:1.

## 10. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_visual_detail_renderers.py`

Minimum coverage:

1. exact 40-method ownership and identity;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no filesystem/network/subprocess/Shopify/deploy operations;
5. exact fourteen-mixin MRO;
6. no boundary-owned duplicate constants;
7. `_LAYER_NAV_TITLE` remains owned by editor shell and is imported without value duplication;
8. host ownership of page-context/lifecycle/inventory exclusions;
9. parent/tree lookup behavior;
10. image-ref normalization behavior;
11. metadata line construction;
12. metadata content apply and fallback telemetry;
13. selected layer-item ordering;
14. layer tile signature;
15. layer visibility synchronization and hide/show Tcl paths;
16. layer header/row/tile idempotent creation;
17. layer tile update skip/update/binding paths;
18. layer renderer empty, stale-empty and populated paths;
19. type-based preview key behavior;
20. preview hide/show idempotence and Tcl paths;
21. preview frame/label cache creation and reuse;
22. bootstrap cleanup cached-frame preservation and fallback telemetry;
23. divider dimensions bounds and invalid values;
24. divider structure/content update;
25. media-section preview renderer;
26. legacy preview renderer;
27. default/fallback preview renderer and event;
28. image preview renderer and normalized reference;
29. text preview renderer;
30. exact structure/content dispatch for all preview keys and fallback;
31. section preview normal update ordering;
32. section preview stale-swap same-key/different-key paths;
33. preview telemetry payloads and cache counts;
34. children zero/non-media/missing-parent paths;
35. children full/range rendering and grid reuse;
36. children stale-refresh cleanup and Tcl handling;
37. child tile copy and selection binding;
38. children completion telemetry/content-swap behavior;
39. no direct implementation of page-context/details/lifecycle engines.

Use neutral fake widgets/state and monkeypatching. Do not create `ctk.CTk()` or require a live display in the new boundary suite. Do not add skips or retries.

## 11. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_preview_reuse.py
cursor-api/tests/test_studio_gicleeframe_preview_correctness.py
cursor-api/tests/test_studio_gicleeframe_layer_nav_reuse.py
cursor-api/tests/test_studio_gicleeframe_layer_nav_delta.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_shell.py
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2a.py
cursor-api/tests/test_studio_gicleeframe_lazy_editor_fields_6g5a.py
cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py
cursor-api/tests/test_studio_gicleeframe_view_details_on_demand.py
```

Complete-MRO tests may receive only membership/order of `GicleeFrameVisualDetailRenderersMixin` where they already assert the complete MRO:

```text
cursor-api/tests/test_studio_gicleeframe_view_brand.py
cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py
cursor-api/tests/test_studio_gicleeframe_view_readiness_row.py
cursor-api/tests/test_studio_gicleeframe_view_safety.py
cursor-api/tests/test_studio_gicleeframe_view_top_bar.py
cursor-api/tests/test_studio_gicleeframe_view_ram_variants.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_interaction.py
cursor-api/tests/test_studio_gicleeframe_view_selection_orchestration.py
cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py
cursor-api/tests/test_studio_gicleeframe_view_details_on_demand.py
```

Rules:

- moved methods/events must be read or patched from the new visual-renderer module;
- host-owned page-context/lifecycle methods continue to be asserted against the host;
- patch `log_event` in the module that owns the method;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks or combined host+module text when ownership matters;
- centralize all 40 identity assertions in the new boundary test;
- any additional changed test requires direct source-ownership or complete-MRO dependency and explicit justification.

## 12. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m16-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_visual_detail_renderers.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_visual_detail_renderers.py`
6. directly affected tests listed in section 11;
7. complete-MRO tests listed in section 11, with membership/order-only changes.

Any additional changed test requires a concrete direct dependency and explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract visual detail renderers`

The PR remains draft after the implementation push.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M16 to `gicleeframe-planning.md`;
- add `ui/gicleeframe_view_visual_detail_renderers.py` to the file table;
- preserve GF-M1–GF-M15 as historical checkpoints;
- change actual future pointers from `GF-M16+` to `GF-M17+`;
- document exactly fourteen mixins after GF-M16;
- document that page-context engine plus lifecycle/inventory remain host-owned candidates for GF-M17+.

## 14. Required local validation

- `py_compile` for host, new visual-renderer module and all existing mixins;
- new visual-renderer boundary tests;
- preview reuse/correctness suites;
- layer-navigation reuse/delta suites;
- children/fast-selection/visual-ready suites directly changed;
- selection stability suites directly changed;
- editor-shell and details boundary suites;
- all changed complete-MRO suites;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review versus the contract head.

A local Tcl/Tk environment failure or flake must be reported separately. Do not add skips, retries, weaken tests or change canonical CI requirements.

For PowerShell `py_compile`, collect files with `Get-ChildItem`; do not pass an unexpanded wildcard directly to Python.

## 15. Commit, push and report

After validation:

- stage only approved files;
- commit exactly:
  `refactor(gicleeframe): extract visual detail renderers`;
- push to the existing branch;
- keep the PR draft;
- do not merge and do not mark ready.

The final Cursor report must include:

- exact starting and final SHA;
- clean worktree and remote tracking confirmation;
- complete changed-file list and numstat;
- justification for every file outside the expected base list;
- exact 40/40 method ownership;
- final fourteen-mixin MRO;
- confirmation that `_LAYER_NAV_TITLE` remains editor-shell-owned;
- host adapter/exclusion list;
- behavior-parity checklist;
- all local test results;
- commit/push confirmation;
- any deviations from this contract.
