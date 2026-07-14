# GF-M17 — Page Context & Inline Settings Engine Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `c9b38b4589f9307ba6c204eaf9e46a2e979fc30d`  
Work branch: `gpt-work/gicleeframe-modularization-m17-page-context-engine`

## 1. Objective

Extract the complete **Page Context & Inline Settings Engine** boundary from
`GicleeFrameView` into one dedicated mixin.

The boundary owns as one cohesive subsystem:

- page-context shell summary and visible shell state;
- immediate and progressive page-context routing;
- readonly row, divider-grid, setting-card and setting-widget caches;
- page-context visibility and pack/grid manager reuse;
- page-context job scheduling and cancellation;
- page-context row specification and precomputation;
- lazy divider groups and cancellable group batching;
- lightweight setting-summary rows;
- on-demand inline setting editor lifecycle;
- progressive stable defer, batching and immediate fallback rendering.

The boundary deliberately does **not** absorb:

- editor-shell/static-container construction from GF-M14;
- details-on-demand dispatch/cache from GF-M15;
- preview, layer-navigation or children rendering from GF-M16;
- selection orchestration;
- inventory loading/merge, lifecycle, progressive boot or atomic reveal;
- RAM draft mutation and `_apply_edit_to_draft`;
- writer, persistence, Shopify sync or deploy.

GF-M17 is RAM-only and behavior-preserving.

## 2. Exact method boundary

Move exactly these **39 methods** from `GicleeFrameView`.

### A. Shell summary and routing

1. `_page_context_shell_summary_lines`
2. `_show_page_context_shell_state`
3. `_schedule_or_fill_page_context`

### B. Shared row/widget helpers

4. `_pack_field_vertical`
5. `_pack_setting_field_row`
6. `_hide_page_context_rows`
7. `_show_page_context_row`
8. `_get_or_create_readonly_card`
9. `_get_or_create_page_context_row`
10. `_get_or_create_divider_grid`
11. `_get_or_create_divider_group`
12. `_update_setting_widget`
13. `_create_page_setting_widget`
14. `_get_or_create_page_setting_row`
15. `_get_or_create_setting_card`
16. `_reset_page_context_settings_on_layout_change`
17. `_edit_panel_pack_anchor`

### C. Scheduling, packing and loading compatibility

18. `_cancel_page_context_jobs`
19. `_schedule_page_context_job`
20. `_page_context_pack_kwargs`
21. `_clear_page_context_loading_label`
22. `_show_page_context_loading_state`

### D. Specs, lazy groups and inline editor

23. `_page_context_row_specs`
24. `_reset_page_context_lazy_group_visual_state`
25. `_make_page_setting_spec`
26. `_format_page_setting_value`
27. `_create_page_context_setting_summary_row`
28. `_close_active_setting_editor`
29. `_open_inline_setting_editor`
30. `_create_full_setting_editor_inside_row`
31. `_create_page_context_collapsed_group_row`
32. `_expand_page_context_group`
33. `_populate_page_context_group_batch`
34. `_precompute_page_context_specs_cache`

### E. Progressive and immediate population

35. `_create_page_context_row_from_spec`
36. `_populate_page_context_batch`
37. `_populate_page_context_progressive_stable`
38. `_populate_page_context_progressive`
39. `_fill_page_context`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_page_context.py`

Target owner:

```python
class GicleeFramePageContextMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFramePageContextMixin,
    method_name,
)
```

Do not leave host wrappers or duplicate implementations.

## 3. Exact constants and module helper

Move exactly these **10 constants** with unchanged values:

```text
_F2_FIELD_LABEL_WIDTH = 88
_GF_PROGRESSIVE_PAGE_CONTEXT_ENV = "GICLEE_GF_PROGRESSIVE_PAGE_CONTEXT"
_GF_PAGE_CONTEXT_BATCH_SIZE = 8
_GF_PAGE_CONTEXT_BATCH_DELAY_MS = 0
_GF_PAGE_CONTEXT_DEFER_MS = 10
_GF_PAGE_CONTEXT_STABLE_DEFER_MS = 80
_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT = "Ustawienia sekcji są aktualizowane…"
_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE = 1
_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS = 0
_DIVIDER_LAZY_GROUPS = {
    "line": ("Linia", ("thickness", "width_percent", "alignment_horizontal")),
    "layout": ("Układ", ("section_width", "padding-block-start", "padding-block-end")),
    "style": ("Styl", ("color_scheme", "corner_radius")),
}
```

Move the module helper:

```python
def _progressive_page_context_enabled() -> bool:
```

Preserve the existing environment semantics:

- missing env → enabled;
- `1`, `true`, `yes`, `on`, `debug` → enabled;
- any other explicit value → disabled.

The new module may implement this helper directly with `os.environ`; it must not
reverse-import `_env_enabled` or `gicleeframe_view.py`.

Export explicitly:

```python
__all__ = (
    "GicleeFramePageContextMixin",
    "_F2_FIELD_LABEL_WIDTH",
    "_GF_PROGRESSIVE_PAGE_CONTEXT_ENV",
    "_GF_PAGE_CONTEXT_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_BATCH_DELAY_MS",
    "_GF_PAGE_CONTEXT_DEFER_MS",
    "_GF_PAGE_CONTEXT_STABLE_DEFER_MS",
    "_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS",
    "_DIVIDER_LAZY_GROUPS",
    "_progressive_page_context_enabled",
)
```

## 4. Direct imports

The new module may directly import:

- `os`, `time`, `tkinter as tk`;
- `Callable` from `collections.abc`;
- `Any` from `typing`;
- `customtkinter as ctk`;
- `MergedPageElement`, `editor_context_rows`, `editor_field_visibility`;
- `PageSettingField`, `divider_setting_groups`;
- `log_event`, `span`;
- `theme`;
- `PageContextRowSpec`;
- `_f2_entry_kwargs`, `_f2_menu_kwargs`, `_make_gf_card`.

All runtime cross-boundary calls go through `self`.

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
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **fifteen mixins** before
`ctk.CTkScrollableFrame`.

The page-context mixin follows visual detail renderers because:

- GF-M15 dispatches page-context work through `self`;
- GF-M14 owns the static page-context shell called by this boundary;
- GF-M17 calls editor-shell, selection and lifecycle adapters through `self`;
- no method name is duplicated across these boundaries.

## 6. Mixin constraints

`GicleeFramePageContextMixin`:

- has no `__init__`;
- has no Tk/CTK base class;
- does not initialize state;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may create/configure/hide only page-context rows, setting widgets, lazy-group
  widgets and inline-editor widgets owned by this boundary;
- may schedule/cancel only IDs stored in `_page_context_after_ids`;
- does not load or merge inventory;
- does not mutate the RAM page draft;
- does not own section selection, selection priority or generation increments;
- does not own editor-shell/static-container construction;
- does not own details CTA/module dispatch or visual detail renderers;
- does not own persistence, writer or deployment behavior.

## 7. Host-owned state

All state initialization remains in `GicleeFrameView.__init__`, including:

```text
_page_context_frame
_page_context_inner
_page_setting_widgets
_page_context_row_cache
_page_context_value_widgets
_page_context_visible_keys
_page_context_row_managers
_page_context_settings_layout
_page_context_last_signature
_page_context_readonly_body
_page_context_divider_group_bodies
_page_context_divider_group_grid_opts
_page_context_setting_card_bodies
_page_context_after_ids
_page_context_generation
_page_context_loading_label
_page_context_shell_shown_generation
_page_context_specs_cache
_page_context_collapsed_group_rows
_page_context_collapsed_group_bodies
_page_context_collapsed_group_buttons
_page_context_expanded_group_ids
_active_setting_editor_row
_active_setting_editor_key
_page_context_summary_rows
_page_context_summary_value_labels
```

Selection/lifecycle state also remains host-owned:

```text
_selected_id
_selection_generation
_selection_visual_cache_applied
_atomic_swap_suppress_visible
_merged
_notes_row
_image_ref_row
_edit_panel
```

GF-M17 must not introduce a mixin `__init__`.

## 8. Host adapters and exclusions

The following remain outside GF-M17 and may be called through `self`:

```text
_build_setting_group_card
_since_selection_click_ms
_defer_background_for_selection
_ensure_page_context_shell_built
_apply_cached_page_context_summary
_save_section_visual_cache
_show_details_on_demand_block
_schedule_selection_job
_select_element
after
after_cancel
winfo_exists
```

The following remain explicitly host-owned:

```text
__init__
_build_page_editor_section
_build_page_workspace
_apply_edit_to_draft
_refresh_inventory
_refresh_inventory_light
_set_merged
_run_deferred_bootstrap
on_show
```

The following remain owned by earlier mixins:

- GF-M14 editor shell: static page-context container/shell construction;
- GF-M15 details on demand: dispatch, visual cache and module orchestration;
- GF-M16 visual detail renderers: preview/layer/children;
- GF-M13 selection orchestration: selection jobs, generations and priority;
- earlier mixins: section list, top bar, readiness, safety and RAM variants.

## 9. Behavioral contract

### Shell and routing

Preserve exactly:

- atomic-swap visible suppression;
- shell row hiding/loading-label cleanup;
- readonly shell summary order and labels;
- `shell_summary:{label}` keys;
- shell generation marker;
- `page_context.shell_ready` telemetry and payload;
- progressive versus immediate routing;
- stable defer timing and callback generation capture;
- hidden page-context path.

### Row/cache lifecycle

Preserve exactly:

- pack/grid manager-aware hide/show;
- swallowed `tk.TclError`;
- readonly-card, row, divider-grid/group and setting-card cache keys;
- idempotent widget reuse;
- label widths, fonts, colors, layout and copy;
- `page_context.row_created` event names and `kind` payloads;
- setting widget select/entry behavior and fallback value selection;
- `_page_setting_widgets` compatibility.

### Layout changes

Preserve exactly:

- divider/flat layout detection;
- selective cached-key destruction;
- Tcl fallback;
- clearing all lazy-group/summary/setting caches;
- active editor close;
- `page_context.destroy_fallback` payload.

### Scheduling

Preserve exactly:

- `_page_context_after_ids` append/pop behavior;
- cancellation count;
- swallowed `tk.TclError`;
- delay constants;
- pack anchor ordering;
- loading-state compatibility alias and both telemetry events.

### Specs and lazy groups

Preserve exactly:

- readonly and setting spec order;
- divider lazy-group IDs/titles/settings;
- flat setting cards;
- precomputed specs cache filtering;
- collapsed placeholder copy and cache reuse;
- stale expansion guards;
- expansion button copy;
- one-setting batches at zero delay;
- selection-priority deferral;
- group batch telemetry fields and order.

### Inline setting editor

Preserve exactly:

- selected-element stale guard;
- one active editor at a time;
- cleanup of inline child widgets;
- setting widget cache removal;
- editor key format;
- `span` and opened telemetry;
- full setting widget creation inside the summary row.

### Progressive population

Preserve exactly:

- spec cache hit/miss behavior;
- selection/generation stale guards and telemetry;
- selection-priority deferral;
- shell loading cleanup;
- hidden/empty behavior;
- layout reset ordering;
- frame packing and signature;
- batch size/delay;
- final telemetry payloads;
- immediate `_fill_page_context` fallback behavior, cache reuse and no normal-path
  destruction.

## 10. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_page_context.py`

Minimum coverage:

1. exact 39-method ownership and identity;
2. exact 10 constants and helper semantics;
3. object-only mixin with no `__init__`;
4. no reverse host import;
5. no filesystem/network/subprocess/Shopify/deploy operations;
6. exact fifteen-mixin MRO;
7. host ownership of state, lifecycle, inventory and draft mutation;
8. page-context shell summary values;
9. atomic-swap suppression and missing-shell guards;
10. shell summary row creation/reuse and exact event payload;
11. progressive/immediate/hidden routing;
12. vertical field packing;
13. legacy `_pack_setting_field_row` select/entry paths;
14. hide/show pack and grid paths;
15. hide/show Tcl errors;
16. readonly-card idempotence;
17. readonly-row idempotence and copy;
18. divider-grid/group idempotence and grid options;
19. option-menu and entry widget update;
20. setting-widget creation/reuse;
21. setting-row and setting-card reuse;
22. layout reset selective destruction and cache clearing;
23. edit-panel anchor behavior;
24. job scheduling/cancellation and Tcl errors;
25. pack-anchor selection;
26. loading-label cleanup and alias telemetry;
27. row specs for hidden/empty/readonly/divider/flat;
28. lazy-group visual reset;
29. page-setting spec hit/miss;
30. setting-value formatting;
31. setting-summary creation/reuse/callback;
32. active editor close;
33. stale/current inline-editor open;
34. full inline editor creation;
35. collapsed-group create/reuse;
36. stale/already-expanded/new expansion;
37. group batch priority/stale/batch/reschedule paths;
38. specs precompute disabled/missing-widget/cache paths;
39. row-from-spec dispatch for every kind;
40. main batch priority/stale/partial/final paths;
41. stable defer stale/current paths and exact telemetry;
42. progressive population guard/empty/layout/cache paths;
43. immediate fill hidden/empty/readonly/divider/flat paths;
44. no normal-path destruction in immediate fill;
45. no direct implementation of selection/details/visual/lifecycle/inventory engines.

Use neutral fake widgets/state and monkeypatching. Do not create `ctk.CTk()` or
require a live display in the new boundary suite. Do not add skips or retries.

## 11. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_page_context_reuse.py
cursor-api/tests/test_studio_gicleeframe_progressive_page_context.py
cursor-api/tests/test_studio_gicleeframe_lazy_divider_groups.py
cursor-api/tests/test_studio_gicleeframe_lightweight_setting_rows.py
cursor-api/tests/test_studio_gicleeframe_responsive_selection.py
cursor-api/tests/test_studio_gicleeframe_lazy_editor_fields_6g5a.py
cursor-api/tests/test_studio_gicleeframe_selection_diag_6g5s.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2a.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_shell.py
cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py
cursor-api/tests/test_studio_gicleeframe_view_details_on_demand.py
cursor-api/tests/test_studio_gicleeframe_view_visual_detail_renderers.py
```

Complete-MRO tests may receive only membership/order changes for
`GicleeFramePageContextMixin` where they already assert the complete MRO:

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
cursor-api/tests/test_studio_gicleeframe_view_visual_detail_renderers.py
```

Rules:

- moved methods/events/constants must be read or patched from the new module;
- host-owned state/lifecycle/inventory/draft mutation remain asserted against host;
- patch `log_event` and `span` in the module owning the method;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise ownership assertions with broad `hasattr` or combined
  host+module text;
- centralize all 39 identity assertions in the new boundary test;
- any additional changed test requires direct ownership/MRO dependency and
  explicit justification.

## 12. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m17-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_page_context.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_page_context.py`
6. directly affected tests listed in section 11;
7. complete-MRO tests listed in section 11 with membership/order-only changes.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy,
starter-file or ZIP changes.

Do not use `git add -A`; stage exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract page context engine`

The PR remains draft after implementation push.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M17 to `gicleeframe-planning.md`;
- add `ui/gicleeframe_view_page_context.py` to the file table;
- preserve GF-M1–GF-M16 as historical checkpoints;
- change actual future pointers from `GF-M17+` to `GF-M18+`;
- document exactly fifteen mixins after GF-M17;
- document that lifecycle/inventory remain host-owned candidates for GF-M18.

## 14. Required local validation

- `py_compile` for host, new module and all existing mixins;
- new page-context boundary tests;
- page-context reuse/progressive suites;
- lazy divider and lightweight setting suites;
- directly changed selection/visual/editor/details suites;
- all changed complete-MRO suites;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review versus contract head.

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

## 15. Commit, push and report

After validation:

- stage only approved files;
- commit exactly:
  `refactor(gicleeframe): extract page context engine`;
- push to the existing branch;
- keep the PR draft;
- do not merge and do not mark ready.

The final Cursor report must include:

- exact starting and final SHA;
- clean worktree and remote tracking confirmation;
- complete changed-file list and numstat;
- justification for every file outside the expected base list;
- exact 39/39 method ownership;
- exact 10 constants and helper ownership;
- final fifteen-mixin MRO;
- host adapter/exclusion list;
- behavior-parity checklist;
- all local test results;
- commit/push confirmation;
- any deviations from this contract.
