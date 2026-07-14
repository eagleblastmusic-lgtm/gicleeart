# GF-M14 — Editor Shell, Prewarm & Minimal Population Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `c2dba2f61840533f4fa6b4e523ca9c9fef8fedfb`  
Work branch: `gpt-work/gicleeframe-modularization-m14-editor-shell-population`

## 1. Objective

Extract the complete **Editor Shell & Minimal Population** boundary from `GicleeFrameView` into one dedicated mixin.

This is intentionally the largest modularization package so far. It owns, as one cohesive subsystem:

- deferred editor-column startup and skeleton construction;
- identity-card placeholder, late build and prewarm lifecycle;
- basic editor-row prewarm lifecycle;
- eager/legacy editor-column construction;
- identity card, form shell and static containers for page context, children, layer navigation and preview;
- lazy construction of the basic editor fields;
- placeholder, refresh-status and stable-shell visual state;
- minimal visual-cache lookup/application;
- the main `_populate_editor` implementation for the lightweight editor path;
- atomic-swap-aware row visibility and basic field value setters;
- editor-ready/layout-shift/content-swap telemetry.

The boundary deliberately does **not** absorb the heavy engines that populate details-on-demand, page context, preview, layer navigation or children. Those remain host-owned adapters and future GF-M15+ candidates.

GF-M14 is RAM-only. It does not enable persistence, writer, Shopify sync or deploy.

## 2. Exact method boundary

Move exactly these **58 methods** from `GicleeFrameView`:

### A. Deferred shell, identity and prewarm lifecycle

1. `_build_editor_column_deferred`
2. `_micro_deferred_editor_skeleton`
3. `_build_section_identity_placeholder`
4. `_schedule_editor_identity_late_build`
5. `_schedule_editor_identity_prewarm_after_perceived`
6. `_schedule_editor_identity_prewarm`
7. `_run_editor_identity_prewarm`
8. `_schedule_editor_rows_prewarm`
9. `_editor_row_shell_flags`
10. `_editor_row_shells_already_built`
11. `_ensure_editor_row_shells_for_prewarm`
12. `_run_editor_rows_prewarm`
13. `_ensure_editor_identity_built`
14. `_build_editor_identity_late`
15. `_micro_deferred_editor_form_shell`
16. `_micro_deferred_editor_fields`
17. `_micro_deferred_editor_children`
18. `_micro_deferred_editor_page_context`

### B. Editor composition and static containers

19. `_build_section_identity_card`
20. `_build_action_dock`
21. `_build_editor_column`
22. `_build_setting_group_card`
23. `_build_edit_panel`
24. `_build_edit_panel_page_context`
25. `_ensure_page_context_shell_built`
26. `_build_edit_panel_fields`
27. `_ensure_title_row_built`
28. `_ensure_text_row_built`
29. `_ensure_alt_row_built`
30. `_ensure_image_ref_row_built`
31. `_ensure_notes_row_built`
32. `_build_edit_panel_children`
33. `_ensure_children_overview_built`
34. `_hide_editor_field_placeholder_if_needed`
35. `_ensure_editor_rows_for_fields`
36. `_ensure_minimal_editor_rows_for_fields`

### C. Minimal editor state, cache and population

37. `_show_editor_placeholder_state`
38. `_log_editor_skeleton_suppressed`
39. `_show_editor_refresh_status`
40. `_hide_editor_refresh_status`
41. `_mark_editor_content_ready`
42. `_log_editor_content_swapped`
43. `_minimal_cache_entry`
44. `_fields_from_cache_entry`
45. `_apply_section_visual_cache`
46. `_apply_minimal_cache`
47. `_log_minimal_editor_ready`
48. `_hide_heavy_editor_modules`
49. `_show_heavy_editor_modules`
50. `_mark_editor_stable_shell_ready`
51. `_maybe_log_layout_shift_guard`
52. `_show_editor_selection_stable_shell_state`
53. `_show_editor_selection_pending_state`
54. `_mark_editor_shell_ready_after_click`
55. `_populate_editor`
56. `_set_row_visible`
57. `_set_entry`
58. `_set_textbox`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_editor_shell.py`

Target owner:

```python
class GicleeFrameEditorShellMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameEditorShellMixin,
    method_name,
)
```

Do not leave wrappers or duplicate implementations in the host.

## 3. Boundary-owned constants

Move these exact **10 constants** from the host to the new editor module:

```python
_LEGACY_READONLY_MSG = (
    "Sekcja legacy — nie jest edytowana w Studio. "
    "Tylko notatka robocza opcjonalna."
)
_EDITOR_FORM_WIDTH = 760
_EDITOR_HERO_PREVIEW_HEIGHT = 118
_PREVIEW_SETTINGS_CAPTION = "Podgląd ustawień"
_LAYER_NAV_TITLE = "Warstwy sekcji"
_IMAGE_SOURCE_TITLE = "Źródło grafiki"
_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS = 80
_GF_EDITOR_IDENTITY_LATE_DEFER_MS = 160
_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT = "Podgląd sekcji pojawi się po wyborze…"
_EDITOR_PLACEHOLDER_TEXT = (
    "Wybierz sekcję po lewej stronie, aby załadować podgląd i ustawienia."
)
```

Do not retain duplicate definitions in `gicleeframe_view.py`.

Export the mixin and these ten constants through explicit `__all__`.

Do not move details-on-demand text/timing constants, page-context batching constants, preview-renderer constants or selection timing constants.

## 4. Required host adapter for shared micro-defer policy

The editor lifecycle currently uses host-global `_GF_MICRO_DEFER_MS = 16`, which is shared by non-editor startup/control code. The new editor module must not import `gicleeframe_view.py` and must not become owner of the shared global timing policy.

Add exactly one behavior-preserving host adapter in `GicleeFrameView`:

```python
def _editor_micro_defer_ms(self) -> int:
    return _GF_MICRO_DEFER_MS
```

Every moved editor method that currently uses `_GF_MICRO_DEFER_MS` must call:

```python
self._editor_micro_defer_ms()
```

The adapter remains in `GicleeFrameView.__dict__` and requires a direct delegation test. Do not duplicate the value `16` as a private editor constant.

## 5. Direct neutral imports

The new editor module may directly import:

- `time`;
- `tkinter as tk`;
- `customtkinter as ctk`;
- `MergedPageElement`, `EditorFieldVisibility`, `editor_context_rows`, `editor_field_visibility`, `editor_title_for_element`, `APPLY_RAM_DRAFT_LABEL`, `APPLY_RAM_MICROCOPY` from the RAM-only page draft module;
- `SectionVisualCacheEntry` from `gicleeframe_view_models`;
- `log_event`, `span`;
- `theme`;
- required stateless tokens/helpers from `gicleeframe_view_primitives`;
- `_SECTION_PLACEHOLDER` from `gicleeframe_view_section_list_shell`.

It must not import `gicleeframe_view.py`.

All runtime cross-boundary calls go through `self`.

## 6. Target MRO

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
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **twelve mixins** before `ctk.CTkScrollableFrame`.

The editor mixin follows selection orchestration because:

- selection-owned `_select_element` and atomic swap call editor-owned cache/state/population methods through `self`;
- editor-owned prewarm yields through selection-owned `_defer_background_for_selection`;
- editor-owned `_populate_editor` uses selection-owned timing/generation methods through `self`;
- interaction-owned `_selected_section_label` is called by editor methods through `self`;
- there are no duplicate method names between these boundaries.

## 7. Mixin constraints

`GicleeFrameEditorShellMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may create/configure/destroy only editor-shell widgets already owned by this boundary;
- may use `after()` only for the moved editor startup/prewarm lifecycle;
- does not load or merge inventory;
- does not mutate the RAM page draft directly;
- does not own selection generation or selection-job queues;
- does not own details-on-demand scheduling/execution;
- does not own page-context row specification, batching or setting-editor behavior;
- does not own preview content rendering;
- does not own layer-navigation tile rendering;
- does not own children-tile population;
- does not own persistence, writer or deployment behavior.

The static page-context, children, preview and layer-nav **containers** created by editor-shell methods may move. Their engines remain excluded.

## 8. Host-owned adapters and policy

The following remain outside the editor mixin and may be called through `self`:

```text
__init__
_editor_micro_defer_ms
_clear_column_children
_since_visual_enter_ms
_queue_latency_since_ms
_log_visual_gate_ready
_try_mark_perceived_ready
_schedule_atomic_reveal_check
_defer_background_for_selection
_should_suppress_visible_prewarm
_log_visible_prewarm_suppressed
_selected_section_label
_apply_edit_to_draft
_since_selection_click_ms
_apply_cached_page_context_summary
_show_page_context_shell_state
_hide_page_context_rows
_clear_page_context_loading_label
_page_context_pack_kwargs
_get_or_create_readonly_card
_show_page_context_row
_get_or_create_page_context_row
_hide_media_details_stable_shell
_show_details_on_demand_block
_save_section_visual_cache
_hide_preview_frames
_fill_children_overview_buttons
_populate_editor_preview_deferred
_populate_editor_layer_nav_deferred
_populate_editor_children_deferred
_schedule_media_deferred_details
_populate_editor_media_details_batch
```

All details-on-demand methods, page-context engine methods, preview renderer methods, layer-nav renderer methods and children population methods remain host-owned.

The host also retains:

- `_build_page_editor_section` and `_build_page_workspace` because they compose all three workspace columns;
- control-column lifecycle and visible-prewarm policy shared with control cards;
- `_refresh_inventory`, `_refresh_inventory_light`, `_finalize_full_list_render`;
- progressive/perceived/atomic-reveal orchestration;
- `_apply_edit_to_draft` as the RAM draft mutation bridge.

## 9. Host-owned state

All state initialization remains in `GicleeFrameView.__init__`, including but not limited to:

```text
_editor_column
_identity_card
_editor_status_dot
_editor_section_subtitle
_editor_header_visible_row
_visible_var
_visible_row
_edit_panel
_legacy_msg_label
_editor_placeholder_label
_editor_form_shell_ready
_editor_identity_late_build_started
_editor_identity_late_build_done
_editor_identity_prewarm_scheduled
_editor_rows_prewarm_scheduled
_title_row
_text_row
_alt_row
_image_ref_row
_notes_row
_title_row_built
_text_row_built
_alt_row_built
_image_ref_row_built
_notes_row_built
_title_entry
_text_box
_alt_entry
_image_ref_entry
_notes_box
_notes_group_frame
_children_overview_row
_children_overview_buttons
_children_overview_built
_page_context_frame
_page_context_inner
_page_context_shell_built
_layer_nav_frame
_section_preview_card
_section_preview_canvas
_section_preview_badge
_preview_bootstrap_panel
_preview_bootstrap_status_label
_editor_refresh_status_frame
_editor_refresh_status_label
_editor_has_ready_content
_editor_last_ready_element_id
_editor_stable_shell_logged_for
_atomic_swap_suppress_visible
_atomic_swap_deferred_row_visibility
_section_visual_cache
_selection_generation
_selection_visual_cache_applied
_page_context_shell_shown_generation
_visual_bootstrap_complete
_shell_editor_built
```

GF-M14 must not introduce a mixin `__init__` or move state initialization.

## 10. Behavioral contract

### Deferred editor startup

Preserve exactly:

- widget-existence, already-built and missing-workspace guards;
- skeleton-enter queue-latency telemetry;
- existing-column reuse and `_clear_column_children` behavior;
- placeholder identity and legacy-label construction;
- shell/editor flags and exact event ordering;
- visual-gate/perceived-ready calls;
- identity-late scheduling before form-shell scheduling;
- placeholder state when no element is selected;
- exact shared micro-defer value through the host adapter.

### Identity placeholder, late build and prewarm

Preserve exactly:

- placeholder copy, fonts, packing and reset of identity/preview/layer references;
- late-build started/done flags and event names;
- cancellation/yield behavior during selection priority;
- widget-existence and shell-ready guards;
- destruction/replacement of the placeholder identity card;
- selected element dot/subtitle restoration after late build;
- prewarm scheduling guards, timings, reasons and telemetry;
- prewarm skip paths (`already_built`, `shell_not_ready`, `form_shell_not_ready`);
- row-prewarm before/after flag telemetry;
- no visible prewarm after bootstrap completion.

### Editor identity card and form shell

Preserve exactly:

- card variants, dimensions, packing order and optional `pack_before` behavior;
- status dot, title, subtitle and visible checkbox;
- RAM action label/microcopy and command delegation to host `_apply_edit_to_draft`;
- hidden layer-navigation container;
- preview artboard/paper/mat/bootstrap shell and exact copy;
- form width, placeholder copy and editor-field lazy startup events;
- eager/legacy `_build_editor_column` behavior;
- page-context and children static-container creation without population-engine migration.

### Basic field construction

Preserve exactly:

- idempotent built flags;
- exact row/card labels, widget types, dimensions and readonly image-ref construction;
- notes styling and layout;
- field-visibility-driven construction;
- minimal path excluding children construction;
- placeholder hiding with `tk.TclError` swallowed;
- visible-row alias behavior.

### Placeholder, refresh and stable-shell state

Preserve exactly:

- placeholder dot/subtitle values and telemetry;
- refresh-status lazy construction, update, pack ordering and fallback;
- refresh-status hide behavior;
- editor content-ready state mutations;
- exact content-swapped, skeleton-suppressed, stable-shell, pending and shell-ready telemetry;
- from-cache status-dot coloring and normal pending gold color;
- one-time stable-shell logging behavior.

### Minimal cache

Preserve exactly:

- `_minimal_cache_entry` lookup by element ID;
- `EditorFieldVisibility` reconstruction from cached flags;
- legacy alias `_apply_section_visual_cache` delegation;
- cache-miss return path;
- identity/row shell construction before values are applied;
- exact dot/subtitle, row visibility, readonly and value-setting behavior;
- page-context summary, heavy-module hiding and details-on-demand delegation through host adapters;
- page-context generation marker, stable-shell/content-ready/refresh-status/minimal-ready ordering;
- return value semantics.

### Heavy shell visibility

Preserve exactly:

- preview-frame hide delegation;
- preview/layer/children static container hide/show behavior;
- pack arguments and `tk.TclError` handling;
- no heavy renderer or details engine moves into this boundary.

### Main `_populate_editor`

Preserve exactly:

- element-type field visibility, readonly policy, cache lookup and generation capture;
- identity and minimal-row ensure timing/event payloads;
- status dot and selected-label update;
- cached page-context summary versus shell-state versus hidden-frame branch;
- all existing spans and lightweight deferred-detail telemetry;
- legacy-message visibility and exact row ordering;
- image notes-row repack behavior;
- field value updates and readonly behavior;
- page-context shell readiness calculation and telemetry;
- shell-ready/stable-shell/heavy-hide/details-on-demand/refresh-hide ordering;
- visible-row count and layout-shift telemetry;
- host visual-cache save delegation with `media_details_built=False`;
- content-ready/minimal-ready and first-selection-ready telemetry;
- no direct heavy preview, layer-nav, children or details population.

### Atomic-swap-aware row and value helpers

Preserve exactly:

- suppression queues `(row, visible)` without immediate widget mutation;
- visible row packing, notes-group packing and hidden row behavior;
- entry/textbox state transitions, clear/insert order and final readonly state;
- compatibility with selection-owned `_flush_atomic_swap_row_visibility`.

## 11. Explicit exclusions

GF-M14 must not move or modify:

- details-on-demand shell, scheduler, stage execution, caching or module actions;
- `_ensure_media_details_stable_shell` / `_hide_media_details_stable_shell`;
- `_details_cache_entry`, details-cache helpers or cached details application;
- `_save_section_visual_cache` because it spans minimal and heavy details cache policy;
- page-context specification, row caching, grouping, batching, setting widgets or inline editors;
- `_apply_cached_page_context_summary` and `_show_page_context_shell_state`;
- preview structure/content/rendering/update methods;
- layer-navigation tile/cache/rendering/update methods;
- children tile population methods;
- selection orchestration methods from GF-M13;
- section-list shell/rendering/interaction methods from GF-M10–M12;
- inventory loading/merge and initial-selection policy;
- progressive/perceived/atomic-reveal policy;
- RAM variant workflow and `_apply_edit_to_draft`;
- writer, persistence, filesystem mutation, Shopify, sync or deploy;
- `.github`, workflows, versioning, starter files or ZIP archives;
- wording, layout, timings, event names, payload fields or callback ordering.

## 12. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py`

Minimum coverage:

1. exact 58-method ownership;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no filesystem/network/subprocess/Shopify/deploy operations;
5. complete twelve-mixin MRO and ordering;
6. method identity for all 58 methods;
7. exact values and ownership of ten constants;
8. host ownership of all exclusions/adapters;
9. exact `_editor_micro_defer_ms` host delegation;
10. deferred editor-column guards and skeleton entry;
11. skeleton new-column and reuse/clear paths;
12. identity placeholder construction and state reset;
13. skeleton flags, events, visual gate and scheduling order;
14. late identity scheduling idempotence and exact delay;
15. perceived prewarm scheduling idempotence and exact delay;
16. identity prewarm active-selection defer path;
17. identity prewarm invalid-widget, already-built, shell-not-ready and build paths;
18. row prewarm scheduling idempotence;
19. row shell flag snapshots and all-built policy;
20. row prewarm visible-suppression and selection-defer paths;
21. row prewarm shell/form guards and build telemetry;
22. identity late-build defer, guard, replacement and selected-state paths;
23. form-shell construction, width, placeholder and reveal scheduling;
24. legacy micro-deferred fields/children/page-context chaining;
25. identity card pack-before and normal pack paths;
26. visible checkbox and RAM action wiring;
27. static layer-nav and preview-container construction;
28. eager editor-column construction;
29. setting-group card construction;
30. edit-panel composition ordering;
31. page-context static shell idempotence;
32. title/text/alt/image-ref/notes row idempotence and widget contracts;
33. children static shell idempotence;
34. placeholder hide paths including `tk.TclError`;
35. full and minimal field-driven row construction differences;
36. placeholder-state UI and telemetry;
37. skeleton-suppressed telemetry;
38. refresh-status create/update/pack/fallback/hide paths;
39. content-ready state mutation;
40. content-swapped telemetry;
41. minimal-cache lookup and field reconstruction;
42. legacy cache alias delegation;
43. minimal-cache miss path;
44. minimal-cache hit field/visibility/readonly/value behavior;
45. minimal-cache host-adapter ordering and completion;
46. minimal-ready telemetry;
47. heavy-module hide/show behavior and Tcl handling;
48. stable-shell one-time and from-cache behavior;
49. layout-shift telemetry;
50. selection stable/pending states;
51. shell-ready-after-click behavior;
52. `_populate_editor` identity/row ensure ordering;
53. `_populate_editor` cache/page-context branches;
54. `_populate_editor` legacy and image-row behavior;
55. `_populate_editor` field values and visibility;
56. `_populate_editor` deferred-detail telemetry without heavy population;
57. `_populate_editor` final host-adapter ordering and cache save arguments;
58. first-selection telemetry guarded by bootstrap state;
59. atomic-swap row visibility queue and direct paths;
60. entry/textbox readonly state transitions;
61. no inventory loading, persistence or heavy-engine implementation in editor module.

Use fake widgets/state and monkeypatching where practical. Do not require a live display outside canonical Tk smoke.

## 13. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_lazy_editor_fields_6g5a.py
cursor-api/tests/test_studio_gicleeframe_control_late_cards_6g5b.py
cursor-api/tests/test_studio_gicleeframe_selection_polish_6g5c.py
cursor-api/tests/test_studio_gicleeframe_startup_hotspot_spans_6g5d.py
cursor-api/tests/test_studio_gicleeframe_identity_card_diet_6g5e.py
cursor-api/tests/test_studio_gicleeframe_first_visible_sections_6g5f.py
cursor-api/tests/test_studio_gicleeframe_top_bar_lazy_actions_6g5g.py
cursor-api/tests/test_studio_gicleeframe_top_bar_late_split_6g5h.py
cursor-api/tests/test_studio_gicleeframe_section_list_diagnostics_6g5i.py
cursor-api/tests/test_studio_gicleeframe_section_list_fast_lane_6g5j.py
cursor-api/tests/test_studio_gicleeframe_sections_column_early_lane_6g5k.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s1.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2a.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_selection_diag_6g5s.py
cursor-api/tests/test_studio_gicleeframe_visual_ready.py
cursor-api/tests/test_studio_gicleeframe_progressive_page_context.py
cursor-api/tests/test_studio_gicleeframe_shell.py
cursor-api/tests/test_studio_gicleeframe_view_selection_orchestration.py
```

Complete-MRO tests may receive only membership/order of `GicleeFrameEditorShellMixin` where they already assert the complete MRO:

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
```

Rules:

- moved methods/constants/events must be read or patched from the new editor module;
- host-owned heavy engines continue to be asserted against the host;
- tests patching module-level `log_event` for moved methods must patch `gicleeframe_view_editor_shell.log_event`;
- live Tk tests continue to invoke methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks;
- centralize all 58 identity assertions in the new boundary test;
- cross-boundary ordering tests may use combined host/editor/selection source text but must preserve exact markers and ordering intent;
- any additional changed test requires a concrete direct source-ownership or complete-MRO dependency and explicit justification in the implementation report.

## 14. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m14-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_editor_shell.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_editor_shell.py`
6. directly affected tests listed in section 13;
7. complete-MRO tests listed in section 13, with membership/order-only changes.

Any additional changed test requires a concrete direct dependency and explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage the exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract editor shell and population`

The PR remains draft after the implementation push.

## 15. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M14 to `gicleeframe-planning.md`;
- add `ui/gicleeframe_view_editor_shell.py` to the file table;
- preserve GF-M3–GF-M13 as historical checkpoints;
- change actual future pointers from `GF-M14+` to `GF-M15+`;
- document exactly twelve mixins after GF-M14;
- document that details-on-demand, page-context engine, preview renderer, layer-navigation renderer and children population remain host-owned candidates for GF-M15+.

## 16. Required local validation

- `py_compile` for host, new editor module and all existing mixins;
- new editor boundary tests;
- all directly changed editor startup/prewarm/lazy-field tests;
- fast-selection, selection diagnostics and all selection-stability suites;
- visual-ready and atomic-swap suites;
- progressive-page-context suites;
- selection, interaction, rendering and shell boundary suites;
- all changed complete-MRO suites;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review versus the contract head.

A local Tcl/Tk environment failure or flake must be reported separately. Do not add skips, weaken tests or change canonical CI requirements.

## 17. Commit, push and report

After validation:

- stage only approved files;
- commit exactly:
  `refactor(gicleeframe): extract editor shell and population`;
- push to the existing branch;
- keep the PR draft;
- do not merge and do not mark ready.

The final Cursor report must include:

- exact starting and final SHA;
- clean worktree and remote tracking confirmation;
- complete changed-file list and numstat;
- justification for every file outside the expected base list;
- exact 58/58 method ownership and ten constants;
- `_editor_micro_defer_ms` adapter confirmation;
- final twelve-mixin MRO;
- host adapter/exclusion list;
- behavior-parity checklist;
- all local test results;
- commit/push confirmation;
- any deviations from this contract.
