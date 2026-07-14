# GF-M10 — Section List Column & Static First-Visible Lane Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `55d067254407df70e161c17b83a157750c5cd0d8`
Work branch: `gpt-work/gicleeframe-modularization-m10-section-list-shell`

## 1. Objective

Extract the cohesive **Section List Column & Static First-Visible Lane** boundary from `GicleeFrameView` into a dedicated mixin.

The package owns:

- scheduling the early sections-column lane;
- construction of the section-list column shell;
- the extras/title/dropdown slot presentation;
- construction of the static first-visible lane;
- rendering the static first batch through host adapters;
- fallback and after-perceived scheduling for the scroll upgrade.

This is a medium-size boundary. It deliberately does **not** absorb the global progressive bootstrap, the actual scroll-upgrade implementation, full/incremental row rendering, selection, drag/reorder, inventory or editor population.

## 2. Exact method boundary

Move exactly these 12 methods from `GicleeFrameView`:

1. `_schedule_sections_column_early_lane`
2. `_log_section_list_column_ready`
3. `_build_sections_column_shell`
4. `_create_section_list_scroll_frame`
5. `_populate_section_list_static_lane`
6. `_try_refresh_static_lane_before_scroll_upgrade`
7. `_cancel_section_list_scroll_upgrade_fallback`
8. `_ensure_section_list_scroll_upgrade_fallback`
9. `_schedule_section_list_scroll_upgrade_after_perceived`
10. `_schedule_section_list_scroll_upgrade`
11. `_build_sections_column_extras`
12. `_build_sections_column`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_section_list_shell.py`

Target owner:

`GicleeFrameSectionListShellMixin`

After integration, all 12 methods must be absent from `GicleeFrameView.__dict__` and resolve by identity from the mixin.

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
    ctk.CTkScrollableFrame,
):
```

The final class contains eight mixins total before `ctk.CTkScrollableFrame`.

## 4. Mixin constraints

`GicleeFrameSectionListShellMixin`:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- performs no file writes, network access, subprocess calls, Shopify operations or deploy operations;
- may use `after()` and `after_cancel()` because first-visible/scroll-upgrade scheduling belongs to this boundary;
- owns no global lifecycle method;
- owns no inventory loading;
- owns no selection population;
- owns no drag/reorder mutation;
- owns no editor or page-context implementation.

Export the mixin and the boundary-owned constants through an explicit `__all__`.

## 5. Boundary-owned constants

Move these constants to the new module after confirming their consumers:

- `_SECTION_PLACEHOLDER`
- `_SECTION_LIST_WIDTH`
- `_SECTION_LIST_HEIGHT`
- `_SECTION_LIST_LOADING_TEXT`
- `_GF_SECTION_FIRST_BATCH_SIZE`
- `_GF_SECTIONS_COLUMN_EARLY_DEFER_MS`
- `_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS`
- `_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS`

Preserve their exact current values.

`gicleeframe_view.py` may import these constants from the new module because remaining host-owned render/dropdown/workspace methods still consume them. Do not retain duplicate definitions in the host.

Do not move:

- `_SECTION_ROW_HEIGHT`
- `_SECTION_ROW_GRIP`
- `_GF_SECTION_BATCH_SIZE`
- `_GF_SECTION_BATCH_DELAY_MS`
- `_GF_SECTION_FIRST_VISIBLE_DEFER_MS`
- `_GF_MICRO_DEFER_MS`
- selection/page-context/editor timings.

## 6. Host-owned adapters and state

The host remains the composition root and retains at least:

- `__init__` and initialization of all section-list fields;
- `_build_page_editor_section_critical`;
- `_build_workspace_critical`;
- `_build_sections_column_deferred`;
- `_build_sections_column_extras_deferred`;
- `_flush_pending_section_list_if_needed`;
- `_schedule_section_list_incremental`;
- `_upgrade_section_list_scroll`;
- `_show_section_list_loading_state`;
- `_run_deferred_bootstrap`;
- `_try_mark_progressive_full_ready`;
- `_render_section_list`;
- `_render_full_list_chunk`;
- `_finalize_full_list_render`;
- `_render_section_list_incremental`;
- `_render_section_list_batch`;
- `_schedule_section_list_batch_continuation`;
- `_create_section_list_row`;
- `_build_section_row` when present;
- `_on_section_row_click`;
- `_select_element` and selection generation/populate;
- `_start_section_drag` and `_finish_section_drag`;
- `_render_section_menu`;
- `_highlight_section_row`;
- `_rebuild_page_model_cache`;
- `_log_visual_gate_ready`;
- `_try_mark_perceived_ready`;
- `_schedule_atomic_reveal_check`;
- inventory, editor, lifecycle and atomic-reveal orchestration.

The mixin may call these methods through `self` as explicit host adapters.

Keep all current section-list state initialization in host `__init__`, including static-lane, scroll-upgrade, extras, dropdown, row-cache and timing fields.

## 7. Behavioral contract

Preserve exactly:

### Early lane

- one-shot guard using `_sections_column_early_lane_scheduled` and `_shell_sections_built`;
- `_sections_column_early_lane_scheduled_mono` timestamp;
- event `studio.gicleeframe.sections_column.early_lane_scheduled`;
- exact delay and telemetry fields;
- callback `_build_sections_column_deferred`.

### Column shell

- card variant `panel_deep`, radius `16`;
- `_section_list_column` assignment;
- extras slot created and packed before static/scroll lane;
- static lane width `_SECTION_LIST_WIDTH - 12` and current height;
- static lane pack geometry;
- non-static path creates the `CTkScrollableFrame` with unchanged dimensions and geometry;
- current shell spans and ready telemetry.

### Static first-visible lane

- clear old children and row caches;
- use cached dropdown options, rebuilding the page-model cache only when required;
- create at most `_GF_SECTION_FIRST_BATCH_SIZE` rows;
- call `_create_section_list_row(..., parent=lane, static_lane=True)`;
- preserve exact `static_lane_ready` and `first_visible_ready` events and payloads;
- set `_section_list_first_visible_built` only for real rows;
- preserve visual-gate, perceived-ready and atomic-reveal adapter calls;
- placeholder path must not claim first-visible readiness.

### Scroll-upgrade scheduling

- keep fallback `after` id ownership in host state;
- preserve cancellation exception handling;
- preserve fallback reason `fallback_timeout`;
- preserve after-perceived reason `after_perceived_ready`;
- preserve delay calculation and telemetry fields;
- scheduling callback remains host-owned `_upgrade_section_list_scroll`.

### Extras

- preserve destroyed/missing-slot guards and events;
- preserve title/subtitle and pack geometry;
- preserve hidden section trigger and dropdown popup construction;
- preserve trigger callback `_toggle_section_list`;
- `_build_sections_column` still composes shell then extras.

## 8. Explicit exclusions

GF-M10 must not change:

- full or incremental row rendering behavior;
- selection click behavior;
- initial selection behavior;
- drag/reorder behavior;
- dropdown open/close behavior beyond constructing its widgets;
- inventory loading or merge behavior;
- RAM variant behavior;
- editor/page-context/preview/layer/children behavior;
- perceived-ready or atomic-reveal gate definitions;
- lifecycle;
- wording, dimensions, colors, timings or telemetry names;
- writer, persistence, filesystem mutation, Shopify, sync or deploy;
- workflows, starter files or ZIP archives.

## 9. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py`

Minimum coverage:

1. exact 12-method ownership;
2. object-only mixin with no `__init__`;
3. no reverse host import;
4. no write/network/subprocess/Shopify/deploy operations;
5. `after()` and `after_cancel()` explicitly allowed only for boundary scheduling;
6. complete eight-mixin MRO;
7. identity for all 12 methods;
8. host ownership of excluded adapters;
9. exact constants and delay ordering;
10. early-lane one-shot scheduling and telemetry;
11. shell card/extras/static/scroll layout;
12. real and placeholder static-lane paths;
13. first-visible state/event ordering;
14. fallback scheduling and cancellation;
15. after-perceived scheduling;
16. missing/destroyed extras-slot guards;
17. shell→extras composition order.

Use fake widgets and monkeypatching where practical. Do not require a live display except existing canonical Tk smoke tests.

## 10. Existing tests requiring migration

Migrate source ownership without weakening behavioral assertions. Directly affected tests include at least:

- `test_studio_gicleeframe_sections_column_split_6g5l.py`
- `test_studio_gicleeframe_sections_column_early_lane_6g5k.py`
- `test_studio_gicleeframe_sections_column_early_lane_queue_6g5m.py`
- `test_studio_gicleeframe_sections_column_shell_diag_6g5p.py`
- `test_studio_gicleeframe_sections_column_static_lane_6g5q.py`
- `test_studio_gicleeframe_section_list_fast_lane_6g5j.py`
- `test_studio_gicleeframe_section_list_diagnostics_6g5i.py`
- `test_studio_gicleeframe_first_visible_sections_6g5f.py`
- `test_studio_gicleeframe_shell.py`
- complete-MRO boundary tests.

Rules:

- assertions for moved methods/constants/events read the new module;
- assertions for host-owned adapters continue to read the host;
- cross-boundary ordering tests may use combined source text, but retain exact markers and ordering checks;
- live Tk tests continue to call methods through `GicleeFrameView` MRO;
- do not replace precise source assertions with broad `hasattr` checks;
- add complete-MRO membership only where an existing test truly asserts the complete MRO;
- centralize all 12 identity assertions in the new boundary test.

Add `_SECTION_LIST_SHELL_VIEW_PATH` and no-write/no-network guardrails to `test_studio_gicleeframe_shell.py`. Do not add the UI module to `_NEW_PLANNING_MODULES`.

## 11. Documentation

After green validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M10 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M9 as historical checkpoints;
- change future-stage references from `GF-M10+` to `GF-M11+` only where they are actual future pointers;
- correct the GF-M9 wording so it states that the final GF-M9 MRO contained **seven mixins total**, not “seven plus RamVariant”;
- document that full/incremental rendering, dropdown interaction, selection and reorder remain host-owned candidates for GF-M11.

## 12. Durable allowlist

Expected maximum scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m10-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_section_list_shell.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_section_list_shell.py`
6. directly affected section-column/section-list source tests listed above;
7. `cursor-api/tests/test_studio_gicleeframe_shell.py`;
8. directly affected complete-MRO tests with explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

## 13. Required validation

Local validation:

- `py_compile` for host, the new module and all existing mixins;
- new boundary tests;
- all directly affected sections-column/static-lane/fast-lane/diagnostic tests;
- shell, lazy-shell, progressive-boot, perceived-ready, atomic-reveal, lifecycle and selection-stability tests;
- `pytest -q -k gicleeframe`;
- runtime-write inventory;
- `git diff --check`;
- exact changed-file allowlist review.

CI contract:

1. draft Hermetic on exact final head;
2. artifact review;
3. ready only after exact-head Hermetic success;
4. canonical Tk GUI smoke;
5. full baseline and runtime-write inventory review;
6. exact-head final review;
7. squash merge with `expected_head_sha`.
