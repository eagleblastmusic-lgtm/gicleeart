# GF-M18 — Lifecycle, Inventory & Final Host Boundary Contract

Status: **COMPLETED — FINAL HOST BOUNDARY INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `e3b91f564d15b2e3d0749c7461af8207e65c7238`  
Work branch: `gpt-work/gicleeframe-modularization-m18-lifecycle-inventory`

## 1. Objective

Extract the final cohesive **Lifecycle, Inventory & Shell Orchestration** boundary from
`GicleeFrameView` into one dedicated mixin.

The boundary owns:

- cached-view navigation lifecycle (`set_navigation`, show/hide);
- RAM model lookup/cache rebuilding;
- visual-session timing;
- loading overlay, perceived-ready and atomic-reveal orchestration;
- lazy/eager shell and workspace orchestration;
- deferred sections/control-column startup;
- bounded inventory reading, light/full refresh and draft merge orchestration;
- progressive section-list bootstrap and final-list completion;
- compatibility shell helpers that remain part of the current behavior.

The extraction is behavior-preserving. It must not change timings, telemetry, widget
layout, selection preservation, initial-selection policy, bounded inventory sources or
RAM-only guarantees.

The boundary deliberately does **not** absorb:

- `GicleeFrameView.__init__` or any state initialization;
- host adapters `_editor_micro_defer_ms` and
  `_progressive_boot_enabled_for_selection`;
- RAM draft mutation in `_apply_edit_to_draft`;
- any writer, persistence, file mutation, Shopify sync or deploy behavior;
- implementations already owned by GF-M3–GF-M17 mixins.

## 2. Exact method boundary

Move exactly these **58 methods** from `GicleeFrameView`.

### A. Public navigation and cached-view lifecycle

1. `set_navigation`
2. `_handle_back`
3. `on_show`
4. `on_hide`

### B. RAM model cache and timing

5. `_rebuild_page_model_cache`
6. `_set_merged`
7. `_since_visual_enter_ms`
8. `_queue_latency_since_ms`
9. `_begin_visual_session`

### C. Atomic reveal, loading overlay and readiness

10. `_ensure_atomic_reveal_overlay`
11. `_atomic_reveal_missing_gates`
12. `_ensure_atomic_reveal_prerequisites`
13. `_ensure_top_bar_actions_for_atomic_reveal`
14. `_schedule_atomic_reveal_check`
15. `_try_atomic_reveal`
16. `_ensure_loading_overlay`
17. `_show_loading_overlay`
18. `_hide_loading_overlay`
19. `_mark_idle_ready`
20. `_mark_visual_ready`
21. `_schedule_visual_ready`
22. `_log_visual_gate_ready`
23. `_try_mark_perceived_ready`

### D. Shell/workspace/control orchestration

24. `_build_shell`
25. `_build_page_editor_section_critical`
26. `_build_workspace_skeleton_column`
27. `_clear_column_children`
28. `_build_workspace_critical`
29. `_build_sections_column_deferred`
30. `_build_sections_column_extras_deferred`
31. `_log_visible_prewarm_suppressed`
32. `_should_suppress_visible_prewarm`
33. `_build_control_column_deferred`
34. `_micro_deferred_control_skeleton`
35. `_micro_deferred_control_structure`
36. `_schedule_control_late_build`
37. `_build_control_late_cards`
38. `_micro_deferred_control_readiness`
39. `_micro_deferred_control_safety`
40. `_build_page_editor_section`
41. `_build_page_workspace`
42. `_upgrade_section_list_scroll`
43. `_build_control_column`
44. `_build_page_top_bar`
45. `_build_toolbar_group`
46. `_toggle_f1_section`

### E. Inventory and progressive bootstrap

47. `_schedule_init_refresh_light`
48. `_run_init_refresh_light_deferred`
49. `_finish_init_refresh_light`
50. `_bootstrap_section_list_after_inventory_light`
51. `_flush_pending_section_list_if_needed`
52. `_schedule_section_list_incremental`
53. `_refresh_inventory_light`
54. `_show_section_list_loading_state`
55. `_run_deferred_bootstrap`
56. `_try_mark_progressive_full_ready`
57. `_refresh_inventory`
58. `_finalize_full_list_render`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_lifecycle_inventory.py`

Target owner:

```python
class GicleeFrameLifecycleInventoryMixin:
```

After integration, every moved method must be absent from
`GicleeFrameView.__dict__` and resolve by identity through the mixin. Do not leave
host wrappers or duplicate implementations.

## 3. Exact constants and helpers

Move exactly these **15 active constants** with unchanged values:

```python
_GF_LOADING_OVERLAY_TEXT = "Przygotowuję GICLÉE FRAME…"
_CONTROL_COL_MINSIZE = 320
_PROGRESSIVE_BOOT_ENV = "GICLEE_GF_PROGRESSIVE_BOOT"
_EAGER_BOOT_ENV = "GICLEE_GF_EAGER_BOOT"
_GF_SECTION_FIRST_VISIBLE_DEFER_MS = 0
_GF_INIT_REFRESH_LIGHT_DEFER_MS = 0
_GF_MICRO_DEFER_MS = 16
_GF_F1_DEFER_MS = 60
_GF_LAZY_SHELL_ENV = "GICLEE_GF_LAZY_SHELL"
_GF_SHELL_EDITOR_DEFER_MS = 16
_GF_SHELL_CONTROL_DEFER_MS = 30
_GF_CONTROL_LATE_BUILD_DEFER_MS = 120
_GF_SKELETON_SECTION_TEXT = "Ładowanie struktury sekcji…"
_GF_SKELETON_EDITOR_TEXT = "Wybierz sekcję po lewej stronie — edytor jest gotowy."
_GF_SKELETON_CONTROL_TEXT = "Kontrola i readiness pojawią się za chwilę."
```

Move exactly these module helpers:

```python
def _env_enabled(name: str, *, default: bool = False) -> bool:
    ...

def _progressive_boot_enabled() -> bool:
    ...

def _lazy_shell_enabled() -> bool:
    ...
```

Preserve exact env semantics:

- missing progressive env → progressive boot enabled;
- explicit eager env truthy → progressive boot disabled;
- truthy values are `1`, `true`, `yes`, `on`, `debug` after strip/lower;
- lazy shell missing env → enabled;
- every other explicit value → disabled.

Delete these **six declaration-only legacy constants** after an AST/name-use assertion
confirms zero `Load` occurrences on the exact base:

```text
_SECTION_LABEL_MAX_CHARS
_GF_BOOT_DEFER_MS
_GF_SHELL_SECTIONS_DEFER_MS
_GF_WORKSPACE_LOADING_TEXT
_GF_EDITOR_STALE_REFRESH_STATUS_TEXT
_GF_PERCEIVED_READY_DEFER_MS
```

They must not be copied to the new module.

Export explicitly the mixin, all 15 active constants and all three helpers.

## 4. Direct imports

The new module may directly import only dependencies required by the 58 methods,
including:

- `os`, `time`, `tkinter as tk`;
- `Callable` from `collections.abc`;
- `customtkinter as ctk`;
- `find_components_dir`, `run_async`, `log_event`, `span`;
- `MergedPageElement`, `merge_inventory_with_draft`, `section_dropdown_options`,
  `section_tree_rows`, `SectionDropdownOption`;
- `build_gicleeframe_page_inventory`;
- `theme`;
- `_GF_SECTION_FIRST_BATCH_SIZE`, `_SECTION_LIST_LOADING_TEXT`,
  `_SECTION_LIST_WIDTH` from the section-list shell boundary;
- `_make_gf_card`, `_make_secondary_button` from primitives.

All calls into GF-M3–GF-M17 boundaries go through `self`.

The new module must not import `gicleeframe_view.py`.

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
    GicleeFrameEditorShellMixin,
    GicleeFrameDetailsOnDemandMixin,
    GicleeFrameVisualDetailRenderersMixin,
    GicleeFramePageContextMixin,
    GicleeFrameLifecycleInventoryMixin,
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **sixteen mixins** before
`ctk.CTkScrollableFrame`. Lifecycle/inventory follows all feature boundaries because
it orchestrates them through `self`.

## 6. Mixin constraints

`GicleeFrameLifecycleInventoryMixin`:

- has no `__init__`;
- has no Tk/CTK base class;
- initializes no state;
- may use `after()`, `after_idle()`, `run_async()` and bounded inventory reads;
- may create/configure/hide only loading, skeleton and orchestration-owned widgets;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or
  deploy;
- does not mutate `GicleeFramePageDraft`;
- does not implement `_apply_edit_to_draft`;
- does not duplicate feature methods already extracted in GF-M3–GF-M17;
- does not reverse-import the host.

## 7. Host-owned composition root

`GicleeFrameView` remains the composition root and retains exactly these behavioral
methods:

```text
__init__
_editor_micro_defer_ms
_progressive_boot_enabled_for_selection
_apply_edit_to_draft
```

It also retains `uses_async_first_paint = True` and all state initialization.

The host imports `_GF_MICRO_DEFER_MS` and `_progressive_boot_enabled` from the new
module for its two adapters and startup decision. The host must not duplicate their
values or policy.

`__init__` preserves:

- `super().__init__` ordering;
- every existing state attribute and initial value;
- runtime marker inspection and telemetry;
- initial visual-enter timestamp/event;
- shell build call;
- progressive/eager inventory startup routing;
- atomic-reveal setup.

`_apply_edit_to_draft` remains RAM-only and calls `_set_merged` through MRO.

## 8. Behavioral contract

Preserve exactly:

### Cached-view lifecycle

- dynamic back-button behavior;
- cached `on_show` visual session behavior;
- no inventory refresh from `on_show`;
- `on_hide` cancellation of selection, page-context and details jobs;
- lifecycle telemetry payloads.

### Model cache and inventory

- `_merged_by_id`, tree-row and dropdown-option rebuild order;
- `set_merged` delegation;
- bounded inventory loading via `find_components_dir()`;
- light/full merge through `merge_inventory_with_draft`;
- selected-element preserve/clear policy;
- progressive initial-selection skip;
- eager initial-selection behavior;
- top-bar, section-list, readiness and editor updates;
- exact inventory telemetry names and payloads.

### Atomic reveal and visual readiness

- all readiness gates and their order;
- overlay creation, place/lift/forget behavior and Tcl fallback;
- top-bar actions materialized before reveal;
- minimal-ready, ready, revealed, visible-ready and idle-ready events;
- no double logging after flags are set;
- `after_idle` scheduling behavior.

### Shell/workspace/control orchestration

- lazy/eager shell routing;
- exact column widths, grid weights, labels and pack/grid options;
- deferred sections/editor/control delays;
- skeleton/structure/late-card sequencing;
- selection-priority defer for control late cards;
- prewarm suppression after visible bootstrap;
- scroll-upgrade behavior and Tcl fallback;
- F1 deferred build-on-expand behavior;
- legacy toolbar compatibility hooks.

### Progressive bootstrap

- async light-refresh success/error paths;
- widget-existence and Tcl guards;
- first-visible scheduling and telemetry;
- pending section-list flush behavior;
- deferred-bootstrap priority guard;
- progressive-full-ready prerequisites and single logging.

## 9. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_lifecycle_inventory.py`

Minimum coverage:

1. exact 58-method ownership and identity;
2. exact 15 active constants and three helpers;
3. AST proof that the six removed constants had no `Load` uses on the frozen base;
4. object-only mixin with no `__init__` or widget base;
5. no reverse host import;
6. no writes/network/subprocess/Shopify/deploy operations;
7. exact sixteen-mixin MRO;
8. host ownership of `__init__`, both adapters and `_apply_edit_to_draft`;
9. complete host state initialization remains present;
10. env helper truth table and eager override;
11. navigation/back and show/hide behavior;
12. model-cache rebuild and set-merged behavior;
13. timing helpers;
14. atomic-reveal gate calculation and prerequisites;
15. exact reveal telemetry order/payload and idempotence;
16. loading overlay create/show/hide and Tcl path;
17. lazy/eager shell routing and exact delays;
18. skeleton workspace layout and child-clear Tcl path;
19. perceived-ready missing/ready paths;
20. async light inventory success/error/destroyed-widget paths;
21. preserved/cleared selection after light inventory;
22. sections/control deferred build guards and order;
23. prewarm suppression and priority defer;
24. section-list incremental scheduling and pending flush;
25. eager workspace/control compatibility paths;
26. section-list scroll upgrade paths;
27. F1 toggle lazy-build paths;
28. full inventory refresh telemetry and rendering;
29. final-list progressive/eager initial-selection behavior;
30. progressive-full-ready guard and idempotence;
31. no page-draft mutation in the mixin;
32. no duplicate implementation in the host.

Use neutral fakes and monkeypatching. Do not create `ctk.CTk()` in the new boundary
suite. Do not add skips or retries.

## 10. Existing tests requiring migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_lifecycle.py
cursor-api/tests/test_studio_gicleeframe_progressive_boot.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_perceived_responsiveness_6g4.py
cursor-api/tests/test_studio_gicleeframe_control_late_cards_6g5b.py
cursor-api/tests/test_studio_gicleeframe_first_visible_sections_6g5f.py
cursor-api/tests/test_studio_gicleeframe_top_bar_lazy_actions_6g5g.py
cursor-api/tests/test_studio_gicleeframe_top_bar_late_split_6g5h.py
cursor-api/tests/test_studio_gicleeframe_section_list_diagnostics_6g5i.py
cursor-api/tests/test_studio_gicleeframe_section_list_fast_lane_6g5j.py
cursor-api/tests/test_studio_gicleeframe_sections_column_early_lane_6g5k.py
cursor-api/tests/test_studio_gicleeframe_sections_column_early_lane_queue_6g5m.py
cursor-api/tests/test_studio_gicleeframe_sections_column_static_lane_6g5q.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2a.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_shell.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_interaction.py
```

Rules:

- moved methods/events/constants are asserted in the new module;
- host state and RAM draft mutation remain asserted against the host;
- patch `log_event`, `span`, `run_async` and inventory builders in the owning module;
- live Tk tests continue through `GicleeFrameView` MRO;
- complete-MRO tests receive membership/order-only changes from 15 to 16 mixins;
- do not weaken precise assertions into broad `hasattr` checks.

## 11. Durable allowlist

Expected scope:

1. this contract;
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`;
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`;
4. `cursor-api/giclee_app/ui/gicleeframe_view_lifecycle_inventory.py`;
5. the new boundary suite;
6. directly affected tests listed in section 10;
7. complete-MRO tests with membership/order-only changes.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy,
starter-file or ZIP changes.

Do not use `git add -A`; stage exact approved files.

## 12. Documentation

After green local validation:

- set this contract to `COMPLETED — FINAL HOST BOUNDARY INTEGRATED`;
- add GF-M18 and the new module to `gicleeframe-planning.md`;
- document exactly sixteen mixins;
- document that the host retains only composition/state, two adapters and RAM draft
  mutation;
- mark GF-M1–GF-M18 modularization complete;
- point the next activity to the final GICLÉE FRAME audit, not GF-M19.

## 13. Required local validation

- `py_compile` for host and every `gicleeframe_view*.py` module;
- the new lifecycle/inventory boundary suite;
- every directly changed lifecycle, progressive, visual, section-list and selection
  suite;
- every changed complete-MRO suite;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review versus this contract head.

For PowerShell:

```powershell
$uiFiles = Get-ChildItem `
  -LiteralPath "giclee_app/ui" `
  -Filter "gicleeframe_view*.py" `
  -File |
  Select-Object -ExpandProperty FullName

python -m py_compile $uiFiles
if ($LASTEXITCODE -ne 0) {
    throw "py_compile zakończył się błędem."
}
```

A local Tcl/Tk failure must be reported separately. Do not add skips, retries,
weaken tests or change canonical CI requirements.

## 14. Commit, push and report

Expected implementation commit:

`refactor(gicleeframe): extract lifecycle inventory boundary`

After implementation validation:

- stage only approved files;
- push to the existing branch;
- keep the PR draft;
- do not mark ready or merge before independent exact-head review.

The implementation report must include:

- exact starting and final SHA;
- clean worktree/tracking confirmation;
- complete changed-file list and numstat;
- exact 58/58 method ownership;
- exact 15 active constants, three helpers and six removed dead constants;
- final sixteen-mixin MRO;
- retained host method list;
- behavior-parity checklist;
- all test results;
- any deviation from this contract.
