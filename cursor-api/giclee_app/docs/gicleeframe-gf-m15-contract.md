# GF-M15 — Details-on-Demand Orchestrator & Cache Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `13e1607be62ab3d2d21dd5ea3d005e15eabb901e`  
Work branch: `gpt-work/gicleeframe-modularization-m15-details-on-demand`

## 1. Objective

Extract the complete **Details-on-Demand Orchestrator & Cache** boundary from `GicleeFrameView` into one dedicated mixin.

The boundary owns, as one cohesive subsystem:

- details request and CTA timing;
- stable media-details placeholder shell;
- details availability CTA and module-selection shell;
- per-module cache lookup, cache application and cache-save policy;
- preview, page-context, layer-nav and children module dispatch;
- generation/stale guards;
- details job scheduling and cancellation;
- children batching;
- preserved legacy full staged pipeline;
- legacy deferred media/detail population wrappers;
- the shared minimal/heavy `SectionVisualCacheEntry` save policy.

The boundary deliberately does **not** absorb the actual preview renderer, page-context engine, layer-navigation renderer or children renderer. Those remain host-owned adapters and future GF-M16+ candidates.

GF-M15 is RAM-only. It does not enable persistence, writer, Shopify sync or deploy.

## 2. Exact method boundary

Move exactly these **48 methods** from `GicleeFrameView`:

### A. Timing and shared performance telemetry

1. `_since_details_request_ms`
2. `_since_details_cta_ms`
3. `_log_perf_e_update_done`

### B. Stable shell and cache contracts

4. `_ensure_media_details_stable_shell`
5. `_hide_media_details_stable_shell`
6. `_details_cache_entry`
7. `_any_details_module_cached`
8. `_details_module_cache_hit`
9. `_cached_details_modules`
10. `_full_visual_cache_entry`
11. `_apply_cached_page_context_summary`
12. `_apply_cached_preview_module`
13. `_apply_cached_page_context_module`
14. `_apply_cached_layer_nav_module`
15. `_apply_cached_children_module`
16. `_apply_cached_media_details`

### C. Availability CTA and details shell

17. `_ensure_details_on_demand_block_built`
18. `_hide_details_on_demand_block`
19. `_show_details_on_demand_block`
20. `_on_details_on_demand_clicked`
21. `_ensure_details_shell_built`
22. `_show_details_shell`
23. `_hide_details_shell`
24. `_hide_details_container`
25. `_update_details_module_status`

### D. Module dispatch and batching

26. `_on_details_module_clicked`
27. `_apply_details_module_from_cache`
28. `_execute_details_module`
29. `_run_children_details_module_batched`
30. `_save_details_module_cache`

### E. Preserved legacy full staged pipeline

31. `_apply_details_cache_hit`
32. `_apply_heavy_details_on_demand`
33. `_details_stage_still_valid`
34. `_details_on_demand_stages_for`
35. `_begin_details_on_demand_stages`
36. `_schedule_next_details_stage`
37. `_execute_details_on_demand_stage`
38. `_run_children_details_stage_batched`
39. `_finalize_details_on_demand`

### F. Scheduler, shared cache and legacy deferred wrappers

40. `_cancel_details_on_demand_jobs`
41. `_schedule_details_on_demand_job`
42. `_save_section_visual_cache`
43. `_should_defer_editor_detail_populate`
44. `_populate_editor_preview_deferred`
45. `_populate_editor_layer_nav_deferred`
46. `_populate_editor_children_deferred`
47. `_schedule_media_deferred_details`
48. `_populate_editor_media_details_batch`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_details_on_demand.py`

Target owner:

```python
class GicleeFrameDetailsOnDemandMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameDetailsOnDemandMixin,
    method_name,
)
```

Do not leave wrappers or duplicate implementations in the host.

## 3. Boundary-owned constants

Move these exact **32 constants** to the new details module:

```python
_GF_DETAILS_ON_DEMAND_TEXT = "Szczegóły sekcji są dostępne na żądanie."
_GF_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły"
_GF_MEDIA_DETAILS_ON_DEMAND_TEXT = (
    "Szczegóły mediów, warstwy i podgląd są dostępne na żądanie."
)
_GF_MEDIA_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły mediów"
_GF_DETAILS_ON_DEMAND_LOADING_TEXT = "Ładowanie szczegółów…"
_GF_DETAILS_SHELL_TITLE = "Szczegóły sekcji"
_GF_DETAILS_SHELL_SUBTEXT = "Wybierz, które szczegóły chcesz wczytać."
_GF_MEDIA_DETAILS_SHELL_SUBTEXT = (
    "Podgląd, warstwy i elementy mediów są dostępne osobno, żeby nie spowalniać edytora."
)
_GF_DETAILS_CACHE_HIT_STATUS = "Szczegóły załadowane"
_GF_DETAILS_MODULE_PREVIEW_TITLE = "Podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE = "Ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_TITLE = "Warstwy"
_GF_DETAILS_MODULE_CHILDREN_TITLE = "Elementy"
_GF_DETAILS_MODULE_PREVIEW_BUTTON = "Wczytaj podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON = "Wczytaj ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_BUTTON = "Wczytaj warstwy"
_GF_DETAILS_MODULE_CHILDREN_BUTTON = "Wczytaj elementy"
_GF_DETAILS_MODULE_IDLE_STATUS = "—"
_GF_DETAILS_MODULE_LOADED_STATUS = "Gotowe"
_GF_DETAILS_MODULE_LOADING_STATUS = "Ładowanie…"
_GF_DETAILS_STAGE_GAP_MS = 16
_GF_DETAILS_CHILDREN_BATCH_SIZE = 2
_GF_DETAILS_CONTAINER_HEIGHT = 148
_GF_MEDIA_PREVIEW_AFTER_SHELL_MS = 20
_GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS = 40
_GF_MEDIA_CHILDREN_AFTER_SHELL_MS = 80
_GF_MEDIA_DETAILS_STATUS_TEXT = "Szczegóły mediów zostaną zaktualizowane…"
_GF_MEDIA_DETAILS_STABLE_HEIGHT = 88
_GF_SELECTION_LAYER_NAV_DEFER_MS = 16
_GF_SELECTION_CHILDREN_DEFER_MS = 32
_GF_SELECTION_CHILDREN_LATE_DEFER_MS = 80
_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS = 16
```

Do not retain duplicate definitions in `gicleeframe_view.py`.

Export the mixin and all 32 constants through explicit `__all__`.

If a constant is still referenced by host-owned legacy code after extraction, the host may import it from the new details module. Do not duplicate its value.

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
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **thirteen mixins** before `ctk.CTkScrollableFrame`.

The details mixin follows editor shell because:

- editor-owned `_populate_editor` exposes the details CTA and saves minimal cache through `self`;
- selection-owned `_select_element` cancels details jobs and hides details shells through `self`;
- details methods call editor-owned stable-shell/content/cache helpers through `self`;
- details methods call selection-owned generation, scheduler and timing helpers through `self`;
- there are no duplicate method names between these boundaries.

## 5. Direct neutral imports

The new details module may directly import:

- `time`;
- `tkinter as tk`;
- `Callable` from `collections.abc`;
- `customtkinter as ctk`;
- `MergedPageElement`, `EditorFieldVisibility`, `editor_field_visibility`, `editor_title_for_element` from the RAM-only page draft module;
- `SectionVisualCacheEntry` from `gicleeframe_view_models`;
- `log_event`, `span`;
- `theme`;
- required stateless tokens from `gicleeframe_view_primitives`.

It must not import `gicleeframe_view.py`.

All runtime cross-boundary calls go through `self`.

## 6. Mixin constraints

`GicleeFrameDetailsOnDemandMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may create/configure/hide only the details CTA, details module shell and stable details shell owned by this boundary;
- may use `after()` only for details/deferred jobs already owned by this boundary;
- does not initialize state;
- does not load or merge inventory;
- does not mutate the RAM page draft;
- does not own section selection or selection priority;
- does not implement preview rendering;
- does not implement page-context row specification, setting widgets or batching;
- does not implement layer-navigation tile rendering;
- does not implement children tile/button rendering;
- does not own persistence, writer or deployment behavior.

## 7. Host-owned adapters and exclusions

The following remain outside the details mixin and may be called through `self`:

```text
__init__
winfo_exists
after
after_cancel
_selected_id / _merged_by_id model state
_selection_generation / selection priority state
_merged_for_selection_generation
_schedule_selection_job
_since_selection_click_ms
_set_row_visible
_fields_from_cache_entry
_show_heavy_editor_modules
_hide_heavy_editor_modules
_hide_editor_refresh_status
_mark_editor_content_ready
_editor_has_ready_content
_editor_last_ready_element_id
_editor_section_subtitle
_page_context_shell_summary_lines
_ensure_page_context_shell_built
_hide_page_context_rows
_clear_page_context_loading_label
_page_context_pack_kwargs
_get_or_create_readonly_card
_show_page_context_row
_get_or_create_page_context_row
_ensure_preview_structure
_show_preview_frame
_preview_key_for_element
_update_section_preview
_fill_page_context
_update_layer_nav
_fill_children_overview_buttons
_fill_children_overview_buttons_range
_tree_row_for_element
_selected_layer_items
_get_or_create_layer_nav_header
_get_or_create_layer_nav_row
_update_layer_nav_tile
_sync_layer_nav_visibility
```

Explicitly remain host-owned for GF-M16+:

- all preview structure/content/frame/render/update methods;
- all page-context row/spec/cache/group/batching/setting-editor methods;
- all layer-navigation tile/cache/render/update methods;
- all children overview button/tile population methods;
- inventory loading/merge and model-cache ownership;
- selection orchestration from GF-M13;
- editor shell/minimal population from GF-M14;
- progressive boot, perceived-ready and atomic-reveal lifecycle;
- RAM draft mutation and variant workflow;
- writer, persistence, Shopify and deploy.

## 8. Host-owned state

All state initialization remains in `GicleeFrameView.__init__`, including:

```text
_section_visual_cache
_media_details_stable_frame
_media_details_status_label
_media_details_stable_built
_details_on_demand_frame
_details_on_demand_hint_label
_details_on_demand_button
_details_on_demand_status_label
_details_on_demand_built
_details_on_demand_element_id
_details_on_demand_expanded
_details_on_demand_after_ids
_details_on_demand_generation
_details_on_demand_request_mono
_details_cta_click_mono
_details_on_demand_active_element_id
_details_container_frame
_details_container_built
_details_container_title_label
_details_container_subtext_label
_details_module_rows
_details_module_buttons
_details_module_status_labels
_media_deferred_done_after_id
```

GF-M15 must not introduce a mixin `__init__` or move state initialization.

## 9. Behavioral contract

### Timing and cancellation

Preserve exactly:

- request/CTA elapsed calculation and `None` behavior;
- round-to-two-decimals behavior;
- job list ownership, pop-before-cancel order and swallowed `tk.TclError`;
- scheduler append behavior;
- generation increments and active-element assignment;
- cancellation before starting a new CTA/module request.

### Availability CTA

Preserve exactly:

- atomic-swap suppression;
- expanded-state hide behavior;
- media/non-media text and button copy;
- cache summary count and status-label packing;
- pack-before preview/layer-nav behavior and Tcl fallbacks;
- exact telemetry names, payloads and ordering.

### Details shell

Preserve exactly:

- lazy idempotent construction;
- title/subtext, module order, two-line row layout and button wiring;
- module visibility from `EditorFieldVisibility`;
- cached/idle status selection;
- shell pack-before behavior and Tcl fallbacks;
- legacy hide alias behavior.

### Module execution and cache

Preserve exactly:

- cache-hit dispatch for preview/page-context/layer-nav/children;
- module-specific host renderer calls;
- loading/loaded status transitions;
- children batching with batch size 2 and 16 ms gap;
- generation and stale guards;
- exact ready/applied/cache-hit telemetry;
- preservation of previous module cache flags when saving one module;
- preview key, layer-nav titles/visibility and page-context summary semantics.

### Shared visual cache policy

Preserve exactly:

- minimal save versus full-details save behavior;
- previous heavy cache preservation on minimal saves;
- media-details built accumulation;
- preview/layer-nav/page-context/children flags;
- subtitle fallback;
- exact `selection.visual_cache_saved` payload fields;
- compatibility with editor-shell `_apply_minimal_cache` and `_populate_editor`.

### Legacy staged pipeline

Preserve exactly:

- full-stage ordering: summary, preview, optional page_context, layer_nav, optional children;
- per-stage scheduling and generation guards;
- children staged batching and continuation;
- final cache save, content-ready and telemetry ordering;
- legacy methods remain behaviorally available even though shell CTA does not auto-start the full chain.

### Legacy deferred detail wrappers

Preserve exactly:

- selection-generation guards;
- no work on minimal-cache hit;
- scheduled timings and event payloads;
- renderer delegation through `self`;
- media batch preview → layer-nav → children order;
- stable-shell/refresh hide, cache save and content-ready ordering.

## 10. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_details_on_demand.py`

Minimum coverage:

1. exact 48-method ownership and identity;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no filesystem/network/subprocess/Shopify/deploy operations;
5. exact thirteen-mixin MRO;
6. exact values and ownership of all 32 constants;
7. host ownership of all excluded renderer/engine methods;
8. request and CTA timing `None`/elapsed behavior;
9. stable-shell build/hide/ordering behavior;
10. details-cache entry and module-cache helpers;
11. cached module list order;
12. cached preview/page-context/layer-nav/children adapters;
13. details availability CTA build/show/hide/media-copy/cache-copy/pack paths;
14. CTA click guards, generation, cancellation and telemetry ordering;
15. details shell idempotent construction and module wiring;
16. shell visibility by field contract and cached status;
17. shell hide and legacy alias;
18. module click guards, cache hit and scheduled execution paths;
19. cached module application and telemetry;
20. direct module execution for all four module types;
21. children module batching continuation/finalization;
22. module cache save preserving previous flags;
23. full details cache hit path;
24. stale/generation validity guards;
25. legacy stage list construction;
26. legacy stage scheduling and execution;
27. legacy children staged batching;
28. legacy finalization ordering and telemetry;
29. details scheduler/cancel including `tk.TclError`;
30. shared visual-cache minimal/full behavior;
31. deferred preview/layer-nav/children wrappers;
32. media deferred scheduling and media batch ordering;
33. no direct implementation of preview/page-context/layer-nav/children engines.

Use neutral fake widgets/state and monkeypatching. Do not require a live display outside canonical Tk smoke.

## 11. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_perceived_responsiveness_6g4.py
cursor-api/tests/test_studio_gicleeframe_selection_diag_6g5s.py
cursor-api/tests/test_studio_gicleeframe_selection_polish_6g5c.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2a.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_view_selection_orchestration.py
cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py
```

Complete-MRO tests may receive only membership/order of `GicleeFrameDetailsOnDemandMixin` where they already assert the complete MRO:

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
```

Rules:

- moved methods/constants/events must be read or patched from the new details module;
- host-owned renderers continue to be asserted against the host;
- patch `log_event` in the module that owns the method;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks or combined host+module text when ownership matters;
- centralize all 48 identity assertions in the new boundary test;
- any additional changed test requires a direct source-ownership or complete-MRO dependency and explicit justification.

## 12. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m15-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_details_on_demand.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_details_on_demand.py`
6. directly affected tests listed in section 11;
7. complete-MRO tests listed in section 11, with membership/order-only changes.

Any additional changed test requires a concrete direct dependency and explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage the exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract details on demand`

The PR remains draft after the implementation push.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M15 to `gicleeframe-planning.md`;
- add `ui/gicleeframe_view_details_on_demand.py` to the file table;
- preserve GF-M1–GF-M14 as historical checkpoints;
- change actual future pointers from `GF-M15+` to `GF-M16+`;
- document exactly thirteen mixins after GF-M15;
- document that preview renderer, page-context engine, layer-navigation renderer, children renderer, lifecycle and inventory remain host-owned candidates for GF-M16+.

## 14. Required local validation

- `py_compile` for host, new details module and all existing mixins;
- new details boundary tests;
- all directly changed details/selection/editor tests;
- fast-selection and visual-ready suites;
- all selection diagnostics/stability suites;
- selection and editor-shell boundary suites;
- all changed complete-MRO suites;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review versus the contract head.

A local Tcl/Tk environment failure or flake must be reported separately. Do not add skips, retries, weaken tests or change canonical CI requirements.

## 15. Commit, push and report

After validation:

- stage only approved files;
- commit exactly:
  `refactor(gicleeframe): extract details on demand`;
- push to the existing branch;
- keep the PR draft;
- do not merge and do not mark ready.

The final Cursor report must include:

- exact starting and final SHA;
- clean worktree and remote tracking confirmation;
- complete changed-file list and numstat;
- justification for every file outside the expected base list;
- exact 48/48 method ownership and 32 constants;
- final thirteen-mixin MRO;
- host adapter/exclusion list;
- behavior-parity checklist;
- all local test results;
- commit/push confirmation;
- any deviations from this contract.
