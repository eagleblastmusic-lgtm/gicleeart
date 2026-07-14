# GF-M12 — Section List Interaction, Highlight & RAM Reorder Contract

Status: **CONTRACT LOCKED — IMPLEMENTATION PENDING**

Repository: `eagleblastmusic-lgtm/gicleeart`  
Base branch: `master`  
Exact base SHA: `c5f1ccacb95ae0838d27a0d6ef9adc0eae310a21`  
Work branch: `gpt-work/gicleeframe-modularization-m12-section-list-interaction`

## 1. Objective

Extract the complete **Section List Interaction** boundary from `GicleeFrameView` into a dedicated mixin.

This is intentionally a larger subsystem boundary. It owns, as one cohesive unit:

- selected-section label and trigger copy;
- dropdown opening, positioning, collapsing and toggling;
- popup-row reuse/rebuild decisions;
- outside-click bind/unbind and widget ancestry checks;
- row-click telemetry and delegation into host selection orchestration;
- mapping child/media elements to the visible top-level row;
- incremental and full row highlighting;
- drag start, drop hit-testing and RAM-only reorder completion;
- post-reorder rerender, selected-element restoration and status feedback.

This boundary deliberately does **not** absorb the selection/editor pipeline, inventory loading, renderer implementation, shell construction, initial-selection policy, persistence or Shopify operations.

## 2. Exact method boundary

Move exactly these 19 methods from `GicleeFrameView`:

1. `_selected_section_label`
2. `_update_section_list_trigger`
3. `_collapse_section_list`
4. `_ensure_section_dropdown_rows`
5. `_open_section_dropdown`
6. `_widget_in_section_dropdown`
7. `_bind_section_dropdown_outside_close`
8. `_unbind_section_dropdown_outside_close`
9. `_on_section_dropdown_outside_click`
10. `_toggle_section_list`
11. `_on_section_row_click`
12. `_top_level_row_id_for_element`
13. `_top_level_row_id_for_selection`
14. `_set_section_row_highlight`
15. `_highlight_section_row`
16. `_highlight_section_rows`
17. `_section_row_index_at_root_y`
18. `_start_section_drag`
19. `_finish_section_drag`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_section_list_interaction.py`

Target owner:

```python
class GicleeFrameSectionListInteractionMixin:
```

After integration, every moved method must resolve by identity through the mixin:

```python
assert method_name not in GicleeFrameView.__dict__
assert getattr(GicleeFrameView, method_name) is getattr(
    GicleeFrameSectionListInteractionMixin,
    method_name,
)
```

Do not leave wrappers or duplicate implementations in the host.

## 3. Boundary helper and constant

Move the interaction-owned environment constant from the host:

```python
_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV = "GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK"
```

Move the helper:

```python
_collapse_section_list_on_click_enabled
```

The helper must preserve exact behavior:

- environment variable absent → `False`;
- accepted true values after trim/lower: `1`, `true`, `yes`, `on`, `debug`;
- every other value → `False`.

The interaction module must not import `gicleeframe_view.py`. Therefore the helper may implement the same bounded environment read directly with `os.environ.get` rather than calling the host-global `_env_enabled`.

Export the mixin, helper and constant through explicit `__all__`.

Do not move unrelated environment constants or helpers.

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
    ctk.CTkScrollableFrame,
):
```

The final class contains exactly **ten mixins** before `ctk.CTkScrollableFrame`.

The interaction mixin follows the renderer because:

- the renderer wires row callbacks to interaction methods through `self`;
- interaction may call `_render_section_list` through the renderer after a reorder;
- there are no duplicate method names between the two boundaries.

## 5. Mixin constraints

`GicleeFrameSectionListInteractionMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no filesystem writes, network access, subprocess calls, Shopify sync or deploy;
- may mutate only the existing in-memory `GicleeFramePageDraft` through `reorder_page_blocks`;
- may use `after()` only for the existing delayed outside-click binding;
- does not own selection generation or editor population internals;
- does not own inventory loading;
- does not own section-list rendering implementation;
- does not own section-list shell construction or scroll upgrade;
- does not own persistence or writer behavior.

## 6. Required direct imports

The new module may import direct dependencies from neutral modules:

- `os`, `time`;
- `customtkinter as ctk` for widget typing;
- `log_event`;
- `merge_inventory_with_draft`, `reorder_page_blocks`;
- `theme` only if directly required;
- `_GF_CARD_SOFT`, `_GF_BORDER_WARM` from view primitives;
- `_SECTION_LIST_WIDTH`, `_SECTION_PLACEHOLDER` from the section-list shell module.

Do not import the renderer host class. All cross-boundary calls go through `self`.

## 7. Host-owned adapters and state

The following remain in `GicleeFrameView.__dict__` and may be called through `self`:

```text
__init__
_render_section_list
_select_element
_set_merged
_update_top_bar
_populate_editor
_since_visual_enter_ms
_finalize_full_list_render
_rebuild_page_model_cache
_refresh_inventory
_refresh_inventory_light
```

The following state remains initialized in host `__init__`:

```text
_section_dropdown_popup
_section_list_trigger
_section_list_column
_section_list_expanded
_section_outside_close_active
_section_row_frames
_section_row_ids
_highlighted_section_id
_drag_from_index
_selected_id
_merged
_merged_by_id
_section_tree_rows_cache
_section_dropdown_options_cache
_page_draft
_inventory
_on_status
_selection_generation
_selection_click_mono
_section_list_static_lane
_section_list_scroll_upgrade_done
_perceived_ready_logged
_shell_control_built
```

GF-M12 must not introduce a mixin `__init__` or move state initialization.

## 8. Behavioral contract

### Selected label and trigger

Preserve exactly:

- placeholder when there are no merged elements;
- top-level row mapping for child selections;
- selected-option lookup order;
- fallback to first option or placeholder;
- chevron `▴` when expanded and `▾` when collapsed;
- no-op when the trigger does not exist;
- exact trigger text spacing.

### Collapse and open

Preserve exactly:

- expanded BooleanVar updates;
- popup `place_forget()` behavior;
- outside-close unbind before trigger refresh;
- popup/trigger/column guards;
- rows reuse/rebuild decision and exact telemetry;
- width calculation: `max(trigger.winfo_width(), _SECTION_LIST_WIDTH)`;
- scroll width calculation and minimum `180`;
- `update_idletasks`, root-coordinate positioning and `+2` vertical offset;
- popup `place`, `lift`, delayed `after(80, ...)` outside-close binding;
- trigger refresh order.

### Outside-click lifecycle

Preserve exactly:

- widget ancestry traversal through `.master`;
- popup and trigger count as inside;
- bind/unbind idempotence via `_section_outside_close_active`;
- top-level `<Button-1>` binding with `add="+"`;
- exact callback identity for bind and unbind;
- collapsed dropdown ignores outside clicks;
- inside clicks do not collapse;
- outside clicks collapse.

### Row click gateway

Preserve exactly:

- `_selection_click_mono` timestamp assignment before telemetry;
- exact `studio.gicleeframe.selection.click` event name and all payload fields;
- next-generation values;
- static-lane/scroll-ready flags;
- call to host `_select_element` with the same element ID;
- collapse policy controlled only by the moved environment helper.

Do not move `_select_element`.

### Top-level mapping and highlight

Preserve exactly:

- unknown/missing IDs return `None`;
- `jumbo`, `body` and `image` children map to the matching cached `media_section` row by `section_key`;
- non-child elements map to themselves;
- targeted highlight clears the previous visible top-level row only when different;
- active style uses `_GF_CARD_SOFT`, border width `1`, `_GF_BORDER_WARM`, radius `12`;
- inactive style uses transparent background, border width `0`, radius `12`;
- missing frames are no-ops;
- widget configuration exceptions remain swallowed as before;
- full re-highlight scans `_section_row_ids` in order;
- `_highlighted_section_id` is updated exactly as before.

### Drag/reorder

Preserve exactly:

- root-y hit testing in visible row order;
- start stores `_drag_from_index` and highlights only valid row frames;
- finish always clears `_drag_from_index` first;
- finish clears temporary backgrounds before validation;
- missing origin or y coordinate → full highlight restore and return;
- missing/same drop index → full highlight restore and return;
- failed `reorder_page_blocks` → full highlight restore and return;
- successful reorder mutates RAM only;
- if inventory exists, remerge through host `_set_merged(merge_inventory_with_draft(...))`;
- update top bar, rerender list, restore selected ID when still present and repopulate editor;
- exact status text: `Kolejność zaktualizowana w RAM · nic nie zapisano`;
- no persistence, file write or Shopify operation.

## 9. Explicit exclusions

GF-M12 must not move or modify:

- `_select_element` and its generation/cancellation/cache/atomic-swap pipeline;
- `_finalize_full_list_render` and initial-selection policy;
- renderer methods from GF-M11;
- shell/static-lane/scroll-upgrade methods from GF-M10;
- inventory loading or source reads;
- page-model cache building;
- editor construction or details-on-demand;
- page-context, preview, layer navigation or children population;
- RAM variant management;
- writer, persistence, filesystem mutation, Shopify, sync or deploy;
- `.github`, workflows, versioning, starter files or ZIP archives;
- wording, dimensions, colors, timings, event names or payload fields.

## 10. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_section_list_interaction.py`

Minimum coverage:

1. exact 19-method ownership;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no filesystem/network/subprocess/Shopify/deploy operations;
5. complete ten-mixin MRO;
6. method identity for all 19 methods;
7. host ownership of excluded adapters;
8. exact environment constant and helper semantics;
9. selected-label empty, selected, child-mapped and fallback paths;
10. trigger no-op and expanded/collapsed copy;
11. collapse order and unbind behavior;
12. dropdown row reuse with highlight and telemetry;
13. dropdown row rebuild with renderer delegation and telemetry;
14. open guards;
15. open geometry, sizing, placement, lift and delayed bind;
16. widget ancestry inside/outside behavior;
17. bind/unbind idempotence and callback identity;
18. outside-click collapsed, inside and outside paths;
19. toggle open/collapse paths;
20. row-click timestamp, exact telemetry payload and selection delegation;
21. collapse environment true/false behavior;
22. top-level media-child mapping and missing paths;
23. targeted previous/current highlight behavior;
24. full re-highlight behavior;
25. highlight widget exception guard;
26. root-y hit testing;
27. drag-start valid/invalid paths;
28. drag-finish missing-origin and missing-y paths;
29. drag-finish same/missing destination paths;
30. drag-finish reorder-failure path;
31. drag-finish successful RAM reorder without inventory;
32. drag-finish successful RAM reorder with inventory remerge;
33. selected-element restoration and editor repopulation after reorder;
34. exact RAM-only status copy.

Use fake widgets and monkeypatching where practical. Do not require a live display outside canonical Tk smoke.

## 11. Existing tests requiring ownership migration

Inspect and update only when directly affected, especially:

```text
cursor-api/tests/test_studio_gicleeframe_fast_selection.py
cursor-api/tests/test_studio_gicleeframe_selection_stability_6g5s2b.py
cursor-api/tests/test_studio_gicleeframe_perceived_responsiveness_6g4.py
cursor-api/tests/test_studio_gicleeframe_section_list_fast_lane_6g5j.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_shell.py
```

Search all tests for the 19 moved method names, collapse environment constant, dropdown event markers and reorder/highlight markers. Any directly affected source-ownership test may be migrated.

Complete-MRO tests may receive only membership/order assertions for `GicleeFrameSectionListInteractionMixin`:

```text
cursor-api/tests/test_studio_gicleeframe_view_brand.py
cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py
cursor-api/tests/test_studio_gicleeframe_view_readiness_row.py
cursor-api/tests/test_studio_gicleeframe_view_safety.py
cursor-api/tests/test_studio_gicleeframe_view_top_bar.py
cursor-api/tests/test_studio_gicleeframe_view_ram_variants.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py
cursor-api/tests/test_studio_gicleeframe_view_section_list_rendering.py
```

Rules:

- moved source assertions must point to the interaction module;
- cross-boundary ordering tests may use combined host/shell/renderer/interaction text;
- do not replace precise assertions with broad `hasattr` checks;
- do not weaken event, timing, layout or callback assertions;
- live Tk tests continue to invoke behavior through `GicleeFrameView` MRO;
- centralize identity assertions in the new boundary test.

## 12. Durable allowlist

Expected base scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m12-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_section_list_interaction.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_section_list_interaction.py`
6. directly affected tests identified in section 11;
7. complete-MRO tests listed in section 11, with membership/order-only changes.

Every additional changed test requires a concrete source-ownership or behavior dependency and explicit justification in the report.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

Do not use `git add -A`; stage exact approved files.

Expected implementation commit:

`refactor(gicleeframe): extract section list interaction`

The PR remains draft after implementation push.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M12 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M11 as historical checkpoints;
- change real future pointers from `GF-M12+` to `GF-M13+`;
- document exactly ten mixins after GF-M12;
- document that selection/editor orchestration remains the primary GF-M13+ candidate.

## 14. Required local validation

At minimum:

- `py_compile` for host, interaction module and every existing GICLÉE FRAME mixin;
- new interaction boundary/behavior tests;
- all directly changed dropdown/highlight/drag/reorder/selection tests;
- all `test_studio_gicleeframe_selection_stability_6g5s*.py` tests;
- section-list shell and renderer boundary tests;
- perceived/visual gate tests affected by row-click ownership;
- `pytest -q -k gicleeframe`;
- `pytest -q tests/test_runtime_write_inventory.py`;
- `git diff --check`;
- exact changed-file and numstat review.

Do not skip or weaken live Tk tests. A local Tcl/Tk failure must be reported separately and resolved by canonical ready CI.

## 15. CI and merge pipeline

1. Contract-head Hermetic on draft PR.
2. Cursor implementation in a dedicated worktree from exact contract head.
3. Push to the existing branch; PR stays draft.
4. Exact-head diff and ownership review.
5. Draft Hermetic artifact review.
6. Mark ready only after review.
7. Canonical Tk GUI + full pytest baseline.
8. Inspect Hermetic, Tk and full artifacts, including JUnit and runtime-write inventory.
9. Squash merge only with unchanged `expected_head_sha`.

No parallel GF-M13 implementation before GF-M12 merge.