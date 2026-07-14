# GF-M13 — Selection Orchestration, Priority Lane & Atomic Swap Contract

Status: **CONTRACT LOCKED — IMPLEMENTATION PENDING**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `d46e8f83c9cf5a27dc16bbe07c29ced147702cdc`  
Work branch: `gpt-work/gicleeframe-modularization-m13-selection-orchestration`

## 1. Objective

Extract the complete **Selection Orchestration** boundary from `GicleeFrameView` into a dedicated mixin.

This is intentionally a large subsystem boundary. It owns, as one cohesive unit:

- selection click timing and generation lifecycle;
- the `_select_element` orchestration entrypoint;
- cancellation and scheduling of selection-owned jobs;
- the selection-priority window and its end lifecycle;
- preemption/yielding of background work while selection is active;
- cancellation of an outstanding incremental section-list continuation when user selection takes priority;
- scheduling and execution of atomic editor population;
- stale-generation and stale-selected-ID guards;
- deferred populate telemetry and completion;
- atomic-swap row-visibility flushing;
- preservation/repopulation of an active selection after light inventory refresh.

This boundary deliberately does **not** absorb the editor implementation, details-on-demand implementation, page-context population, preview/layer/children rendering, inventory loading, section-list rendering, section-list interaction, persistence or Shopify operations.

## 2. Exact method boundary

Move exactly these 18 methods from `GicleeFrameView`:

1. `_since_selection_click_ms`
2. `_selection_priority_active`
3. `_open_selection_priority_window`
4. `_preempt_background_for_selection_priority`
5. `_cancel_section_list_batch_continuation`
6. `_end_selection_priority_window`
7. `_defer_background_for_selection`
8. `_should_run_immediate_selection_populate`
9. `_schedule_selection_populate`
10. `_ensure_preserved_selection_populate_after_inventory_light`
11. `_select_element`
12. `_schedule_atomic_swap_populate`
13. `_run_atomic_swap_populate`
14. `_flush_atomic_swap_row_visibility`
15. `_populate_editor_deferred`
16. `_merged_for_selection_generation`
17. `_cancel_selection_jobs`
18. `_schedule_selection_job`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_selection_orchestration.py`

Target owner:

```python
class GicleeFrameSelectionOrchestrationMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameSelectionOrchestrationMixin,
    method_name,
)
```

Do not leave wrappers or duplicate implementations in the host.

## 3. Boundary-owned constants

Move these exact constants from the host to the new selection module:

```python
_GF_ATOMIC_SWAP_STATUS_TEXT = "Przygotowuję sekcję…"
_GF_SELECT_POPULATE_DEFER_MS = 0
_GF_SELECTION_PRIORITY_WINDOW_MS = 200
_GF_SELECTION_PRIORITY_YIELD_DEFER_MS = 60
```

Do not retain duplicate definitions in `gicleeframe_view.py`.

Export the mixin and these four constants through explicit `__all__`.

Do not move editor-, details-, page-context-, preview- or shell-specific timing constants.

## 4. Required host adapter for progressive-boot policy

The current `_select_element` reads the host-global `_progressive_boot_enabled()` function for telemetry. The new module must not import `gicleeframe_view.py`.

Add exactly one behavior-preserving host adapter in `GicleeFrameView`:

```python
def _progressive_boot_enabled_for_selection(self) -> bool:
    return _progressive_boot_enabled()
```

The moved `_select_element` must call:

```python
self._progressive_boot_enabled_for_selection()
```

This adapter remains in `GicleeFrameView.__dict__` and must be covered by a direct delegation test. Do not duplicate the progressive-boot environment policy in the selection module and do not move unrelated environment helpers/constants.

## 5. Target MRO

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
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **eleven mixins** before `ctk.CTkScrollableFrame`.

The selection mixin follows the interaction mixin because:

- `_select_element` calls interaction-owned highlight, trigger and collapse methods through `self`;
- interaction-owned row clicks delegate to `_select_element` through `self`;
- renderer/shell/background methods may call selection-owned `_defer_background_for_selection` and `_cancel_section_list_batch_continuation` through `self`;
- there are no duplicate method names between these boundaries.

## 6. Mixin constraints

`GicleeFrameSelectionOrchestrationMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may use `after()`, `after_idle()` and `after_cancel()` only for selection scheduling, priority lifecycle, atomic swap and the moved renderer-continuation cancellation adapter;
- does not create or destroy editor widgets;
- does not own inventory loading or model-cache rebuilding;
- does not own `_populate_editor` implementation;
- does not own details-on-demand, page-context, preview, layer navigation or children rendering;
- does not own section-list row rendering or dropdown interaction;
- does not own persistence or writer behavior.

## 7. Required direct imports

The new module may import direct dependencies from neutral modules:

- `time`;
- `tkinter as tk`;
- `Callable` from `collections.abc`;
- `MergedPageElement` from `gicleeframe_page_draft`;
- `log_event`, `span`.

It must not import the host module. All cross-boundary calls go through `self`.

## 8. Host-owned adapters and state

The following remain outside the selection mixin and may be called through `self`:

```text
__init__
_progressive_boot_enabled_for_selection
_cancel_details_on_demand_jobs
_cancel_page_context_jobs
_hide_details_container
_hide_details_shell
_hide_details_on_demand_block
_close_active_setting_editor
_highlight_section_row
_update_section_list_trigger
_minimal_cache_entry
_apply_minimal_cache
_show_editor_refresh_status
_hide_media_details_stable_shell
_show_editor_selection_stable_shell_state
_collapse_section_list
_populate_editor
_hide_editor_refresh_status
_set_row_visible
_queue_latency_since_ms
```

The following state remains initialized in host `__init__`:

```text
_selected_id
_merged_by_id
_selection_generation
_selection_after_ids
_selection_click_mono
_selection_populate_scheduled_mono
_selection_priority_generation
_selection_priority_until_mono
_selection_priority_end_after_id
_selection_visual_cache_applied
_section_visual_cache
_details_on_demand_expanded
_details_on_demand_active_element_id
_details_on_demand_request_mono
_details_cta_click_mono
_page_context_generation
_editor_has_ready_content
_editor_last_ready_element_id
_atomic_swap_suppress_visible
_atomic_swap_deferred_row_visibility
_section_list_batch_after_id
_media_deferred_done_after_id
_shell_editor_built
```

GF-M13 must not introduce a mixin `__init__` or move state initialization.

## 9. Behavioral contract

### Selection click timing

Preserve exactly:

- `None` when `_selection_click_mono` is absent;
- elapsed milliseconds based on `time.perf_counter()`;
- rounding to two decimal places.

### Selection-priority window

Preserve exactly:

- active state requires a non-expired deadline;
- optional generation check;
- cancellation of a previous priority-end callback with `tk.TclError` swallowed;
- exact `_GF_SELECTION_PRIORITY_WINDOW_MS = 200` deadline and callback scheduling;
- exact `studio.gicleeframe.selection.priority_start` event and payload;
- exact `studio.gicleeframe.selection.priority_end` event and payload;
- stale priority-end generations do not clear a newer window;
- `_selection_priority_end_after_id` lifecycle remains unchanged.

### Background preemption and yielding

Preserve exactly:

- selection priority preempts an outstanding incremental section-list batch continuation;
- `_cancel_section_list_batch_continuation` clears the stored ID before cancellation and swallows `tk.TclError`;
- preemption logs `studio.gicleeframe.background.deferred_for_selection` only when a continuation was cancelled;
- preemption payload keeps `reason="selection_priority_preempt"`, `delay_ms=0` and `job="section_list.incremental_batch"`;
- background jobs return `False` when priority is inactive;
- default yield delay is `_GF_SELECTION_PRIORITY_YIELD_DEFER_MS = 60`;
- caller-provided delay overrides the default;
- exact event name/payload and `after(delay, callback)` ordering remain unchanged.

### Selection job scheduling and cancellation

Preserve exactly:

- cancellation count equals the number of `_selection_after_ids` present before cancellation;
- all selection callback IDs are removed and cancelled;
- `tk.TclError` is swallowed;
- `_media_deferred_done_after_id` is independently cancelled and cleared;
- `_schedule_selection_job` appends the returned `after` ID;
- `_schedule_selection_populate` uses `_GF_SELECT_POPULATE_DEFER_MS = 0`, sets `_selection_populate_scheduled_mono`, schedules `_populate_editor_deferred` and preserves telemetry.

### Preserved selection after inventory light refresh

Preserve exactly:

- generation, selected-ID and existing-pending-job guards;
- lookup through `_merged_by_id`;
- immediate path when `_should_run_immediate_selection_populate` returns true;
- scheduled fallback path otherwise;
- exact `selection.populate_priority_scheduled` and `selection.repopulate_after_inventory_scheduled` events/payloads;
- no inventory loading or merge logic moves into this boundary.

### `_select_element` orchestration

Preserve exactly:

- previous-ID capture, generation increment and timing order;
- exact `selection.start` and `select_element.user_or_programmatic` events/payloads;
- progressive-boot telemetry through the host adapter;
- cancellation order: selection jobs, details jobs, page-context generation increment, page-context jobs;
- exact jobs-cancelled and details-cancelled telemetry;
- details-shell/reset behavior when details jobs are cancelled;
- active inline setting editor close before changing the selected ID;
- missing element log/return path;
- immediate interaction-owned highlight and trigger update;
- minimal-cache lookup and visual-cache flag;
- details shell/on-demand hiding order;
- exact minimal-cache hit, partial-hit and miss events;
- stale-content status versus stable-shell pending behavior;
- optional list collapse through interaction-owned `_collapse_section_list`;
- exact immediate-ready telemetry;
- priority window opening after immediate UI readiness;
- minimal-cache hit returns without scheduling population;
- cache miss schedules atomic swap with exact telemetry and timestamps;
- no direct `_populate_editor` call from `_select_element`;
- no section-list rerender from `_select_element`.

### Atomic swap

Preserve exactly:

- scheduling through `after_idle`;
- stale-generation event and return;
- missing/stale-selected-ID return;
- exact `selection.atomic_swap.ready` event;
- stale editor content determines `_atomic_swap_suppress_visible`;
- deferred row visibility is cleared before population;
- `_populate_editor(m, atomic_swap=True)` remains a host adapter call;
- stale-content row visibility flush occurs only when required;
- `finally` always clears suppression and deferred state;
- applied/populate-done telemetry only for the still-current generation and selected ID;
- editor refresh status is hidden only after successful current application.

### Deferred populate and generation guard

Preserve exactly:

- queue latency calculation through host `_queue_latency_since_ms`;
- stale-generation and missing/stale-selected-ID logs/returns;
- exact populate enter/start/done events and payloads;
- host `_populate_editor` invocation with `visual_cache_refresh`;
- completion telemetry only for the current generation and selected ID;
- `_merged_for_selection_generation` exact stale-generation, stale-selected and missing event suffixes;
- host deferred preview/layer/children methods continue to use the moved generation guard through `self`.

### Atomic row-visibility flush

Preserve exactly:

- copied deferred list before mutation;
- clearing queue and disabling suppression before applying rows;
- row order and visibility values;
- delegation to host `_set_row_visible`.

## 10. Explicit exclusions

GF-M13 must not move or modify:

- `_populate_editor` and its editor-field/layout implementation;
- `_populate_editor_preview_deferred`;
- `_populate_editor_layer_nav_deferred`;
- `_populate_editor_children_deferred`;
- `_schedule_media_deferred_details`;
- `_populate_editor_media_details_batch`;
- details-on-demand methods and details cache implementation;
- page-context methods and page-context schedulers/cancellation;
- preview, layer-navigation or children rendering;
- `_refresh_inventory_light` and inventory preservation/clear policy;
- `_finalize_full_list_render` and initial-selection policy;
- renderer methods from GF-M11;
- interaction methods from GF-M12;
- shell/static-lane/scroll-upgrade methods from GF-M10;
- RAM variant management;
- writer, persistence, filesystem mutation, Shopify, sync or deploy;
- `.github`, workflows, versioning, starter files or ZIP archives;
- wording, timings, event names, payload fields or callback ordering.

## 11. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_selection_orchestration.py`

Minimum coverage:

1. exact 18-method ownership;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no filesystem/network/subprocess/Shopify/deploy operations;
5. complete eleven-mixin MRO;
6. method identity for all 18 methods;
7. exact values and ownership of the four moved constants;
8. host ownership of excluded adapters;
9. exact progressive-boot host adapter delegation;
10. selection-click timing absent and elapsed paths;
11. priority active inactive/expired/generation paths;
12. previous priority callback cancellation;
13. priority start scheduling, deadline and telemetry;
14. stale and current priority-end paths;
15. renderer-continuation cancellation absent/present/TclError paths;
16. priority preemption no-cancel and cancel telemetry paths;
17. background defer inactive/default/custom delay paths;
18. selection job cancellation count and TclError handling;
19. media-deferred callback cancellation and clearing;
20. selection job scheduling stores callback ID;
21. selection-populate scheduling and exact telemetry;
22. immediate-populate policy remains true;
23. preserved-selection generation/selected/pending guards;
24. preserved-selection immediate path;
25. preserved-selection fallback scheduling path;
26. `_select_element` missing-element path;
27. `_select_element` cancellation order and generation increment;
28. details-cancel reset path;
29. immediate highlight/trigger and collapse behavior;
30. minimal-cache hit path and no populate scheduling;
31. partial-cache/miss stable-content path;
32. cache-miss no-ready-content stable-shell path;
33. exact immediate and scheduling telemetry;
34. progressive-boot adapter usage;
35. atomic-swap scheduling through `after_idle`;
36. atomic-swap stale-generation and stale-selected paths;
37. atomic-swap current path without stale content;
38. atomic-swap current path with stale content and row flush;
39. atomic-swap `finally` cleanup when host populate raises;
40. atomic-swap completion telemetry/current-generation guard;
41. deferred populate stale-generation path;
42. deferred populate missing/stale-selected path;
43. deferred populate current path and exact telemetry;
44. generation helper stale/current/missing paths;
45. atomic row-visibility flush order and host delegation;
46. no direct editor implementation, inventory loading or persistence in selection module.

Use fake widgets/state and monkeypatching where practical. Do not require a live display outside canonical Tk smoke.

## 12. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_responsive_selection.py
cursor-api/tests/test_studio_gicleeframe_selection_diag_6g5s.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_interaction.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_shell.py
```

Complete-MRO tests may receive only membership/order of `GicleeFrameSelectionOrchestrationMixin` where they already assert the complete MRO:

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
```

Rules:

- moved methods/constants/events must be read or patched from the new selection module;
- host-owned editor/details/page-context adapters continue to be asserted against the host;
- tests patching module-level `log_event` for moved methods must patch `gicleeframe_view_selection_orchestration.log_event`;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks;
- centralize all 18 identity assertions in the new boundary test;
- update renderer boundary ownership for `_defer_background_for_selection` and `_cancel_section_list_batch_continuation` without weakening renderer behavior assertions;
- cross-boundary ordering tests may use combined host/selection/renderer/interaction source text but must preserve exact markers and ordering intent;
- any additional changed test requires a concrete direct source-ownership or complete-MRO dependency and explicit justification in the implementation report.

## 13. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m13-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_selection_orchestration.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_selection_orchestration.py`
6. directly affected tests listed in section 12;
7. complete-MRO tests listed in section 12, with membership/order-only changes.

Any additional changed test requires a concrete direct dependency and explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage the exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract selection orchestration`

The PR remains draft after the implementation push.

## 14. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M13 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M12 as historical checkpoints;
- change actual future pointers from `GF-M13+` to `GF-M14+`;
- document exactly eleven mixins after GF-M13;
- document that editor shell/population, details-on-demand, page-context, preview and layer navigation remain host-owned candidates for GF-M14+.

## 15. Required local validation

- `py_compile` for host, the new selection module and all existing mixins;
- new selection boundary tests;
- fast-selection, responsive-selection and selection diagnostic suites;
- all `test_studio_gicleeframe_selection_stability_6g5s*.py` suites;
- visual-ready and atomic-swap related suites;
- renderer, interaction and shell boundary suites;
- all changed complete-MRO suites;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file review versus the contract head.

A local Tcl/Tk environment failure must be reported separately. Do not add skips, weaken tests or change canonical CI requirements.

## 16. Commit, push and report

After validation:

- stage only the approved files;
- commit exactly:
  `refactor(gicleeframe): extract selection orchestration`;
- push to the existing branch;
- keep the PR draft;
- do not merge and do not mark ready.

The final Cursor report must include:

- exact starting and final SHA;
- clean worktree and remote tracking confirmation;
- complete changed-file list and numstat;
- justification for every file outside the expected base list;
- exact 18/18 method ownership and four constants;
- progressive-boot adapter confirmation;
- final eleven-mixin MRO;
- host adapter list;
- behavior-parity checklist;
- all local test results;
- commit/push confirmation;
- any deviations from this contract.