# GF-M8 — Top Bar Subsystem Extraction Contract

Status: **DISCOVERY LOCKED — IMPLEMENTATION PENDING**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `fad62b512743b516beb724fe42e39663065a41ac`
Work branch: `gpt-work/gicleeframe-modularization-m8-top-bar-subsystem`

## 1. Objective

GF-M8 is the first medium-size modularization package after the small-boundary series GF-M3–GF-M7.

Extract the complete **Top Bar Subsystem** from `GicleeFrameView` into one cohesive mixin. The subsystem includes:

- the context bar shell;
- the working-variant/back-action placeholders and their real widgets;
- the command bar shell;
- primary RAM-action button presentation;
- secondary inventory/control button presentation;
- staggered late-build scheduling and telemetry for context, primary and secondary actions.

The extraction must preserve pixel/layout behavior, labels, commands, timings, telemetry event names and atomic-reveal integration.

## 2. Exact method boundary

Move exactly these 11 methods from `GicleeFrameView`:

1. `_build_context_bar`
2. `_build_context_bar_actions_placeholder`
3. `_build_context_bar_actions`
4. `_schedule_top_bar_actions_late_build`
5. `_start_top_bar_actions_late_build`
6. `_build_context_bar_actions_late`
7. `_build_command_bar_primary_actions_late`
8. `_build_command_bar_secondary_actions_late`
9. `_build_command_bar`
10. `_build_command_bar_primary_actions`
11. `_build_command_bar_secondary_actions`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_top_bar.py`

Target owner:

`GicleeFrameTopBarMixin`

The mixin:

- has no `__init__`;
- has no Tk/widget base class;
- does not import `gicleeframe_view.py`;
- owns no persistence, file writes, network, subprocess or Shopify operations;
- may use `after()` because late-build scheduling is part of this subsystem;
- must not own global lifecycle methods (`on_show`, `on_hide`, `set_navigation`) or atomic-reveal orchestration.

## 3. Target MRO

After integration:

```python
class GicleeFrameView(
    GicleeFrameBrandPanelMixin,
    GicleeFramePageReadinessMixin,
    GicleeFrameStructureDryRunMixin,
    GicleeFrameSafetyCardMixin,
    GicleeFrameReadinessRowMixin,
    GicleeFrameTopBarMixin,
    ctk.CTkScrollableFrame,
):
```

All 11 methods must be absent from `GicleeFrameView.__dict__` and resolve by identity from `GicleeFrameTopBarMixin`.

## 4. Constants owned by the subsystem

Move these subsystem-specific constants to `gicleeframe_view_top_bar.py` after confirming there are no consumers outside the moved methods:

- `_BACK_LABEL`
- `_SHELL_STATUS_CHIP`
- `_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS`
- `_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS`
- `_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS`
- `_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS`

Preserve exact values and ordering constraint:

```text
0 <= context < primary < secondary <= overall
```

Do not move unrelated editor, section-list, control-column or atomic-reveal constants.

## 5. Host-owned adapters and state

The host remains the composition root and retains:

- `__init__` and initialization of all top-bar widget/state attributes;
- `_build_shell` and its call to `_schedule_top_bar_actions_late_build()`;
- `_ensure_top_bar_actions_for_atomic_reveal`;
- `_schedule_atomic_reveal_check` and `_try_atomic_reveal`;
- `_should_suppress_visible_prewarm` and `_log_visible_prewarm_suppressed`;
- `_since_visual_enter_ms` and other generic timing helpers;
- `set_navigation` and `_handle_back`;
- `_sync_working_variant_menu` and `_on_working_variant_selected`;
- `_add_ram_variant`, `_duplicate_ram_variant`, `_rename_ram_variant`, `_clear_page_draft`;
- `_refresh_inventory`;
- `_run_structure_dry_run`;
- all lifecycle, selection, editor, section-list, control-column, preview, page-context, cache and details-on-demand behavior.

The top-bar mixin may call these host adapters through `self`, but must not absorb their implementations.

## 6. Widget/state attributes

Keep initialization in `GicleeFrameView.__init__` for:

- `_top_bar_actions_late_started`
- `_top_bar_actions_late_done`
- `_context_bar_row`
- `_context_bar_actions_slot`
- `_context_bar_actions_placeholder`
- `_context_bar_back_slot`
- `_context_bar_back_placeholder`
- `_command_bar_inner`
- `_command_bar_primary_slot`
- `_command_bar_primary_placeholder`
- `_command_bar_secondary_slot`
- `_command_bar_secondary_placeholder`
- `_top_meta_label`
- `_panel_status_label`
- `_working_variant_menu`
- `_working_variant_map`
- `_change_count_label`
- `_back_button`

GF-M8 does not introduce a second state container or duplicate these attributes.

## 7. Behavioral contracts

Preserve exactly:

### Context bar

- card variant `panel_deep`, radius `16`;
- outer pack `fill="x", padx=24, pady=(12, 8)`;
- status chip copy `RAM-only · bez zapisu`;
- initial metadata copy `Ładowanie…`;
- change counter copy `Zmiany: 0`;
- panel status copy from `PANEL_STATUS_UNSAVED`;
- working-variant menu width `168`, height `_BTN_HEIGHT`;
- back action width `112` and subtle styling;
- conditional back placeholder/button behavior based on `_on_back`.

### Command bar

- card variant `panel_deep`, radius `16`;
- two horizontal action slots and `56`-pixel placeholders;
- primary caption `Warianty RAM`;
- exact primary command order: add → duplicate → rename → clear;
- secondary caption `Inventory i kontrola`;
- exact secondary command order: refresh inventory → structure dry-run;
- no change to command callbacks or labels.

### Late build

- overall scheduling event and exact delay constant;
- staggered context/primary/secondary `after()` calls;
- suppression checks before visible prewarm;
- `winfo_exists()`/`tk.TclError` guards;
- all existing span and log-event names;
- `_top_bar_actions_late_done = True` only in secondary completion;
- menu synchronization after secondary completion;
- atomic-reveal check with trigger `top_bar_actions` after secondary completion.

## 8. Import cleanup

The new module imports only dependencies needed by the moved methods.

After extraction, remove host imports/constants only when source review proves they are dead. Likely candidates include command-label imports used only by command-bar presentation, but do not remove:

- `DEFAULT_VARIANT_NAME` if host workflow/menu methods still consume it;
- `RENAME_VARIANT_LABEL` if `_rename_ram_variant` still consumes it;
- any primitive or theme token with another host consumer.

No compatibility alias or wrapper should remain in the host for the 11 moved methods.

## 9. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_top_bar.py`

Minimum coverage:

1. mixin is a narrow non-widget boundary with no `__init__`;
2. exact 11-method ownership;
3. no write/network/subprocess/Shopify imports or operations;
4. no reverse import from host;
5. all six mixins are present in `GicleeFrameView.__mro__`;
6. each moved method is absent from `GicleeFrameView.__dict__` and resolves by identity from the mixin;
7. host ownership remains for `_build_shell`, `_ensure_top_bar_actions_for_atomic_reveal`, `set_navigation`, `_handle_back`, RAM actions, inventory and atomic-reveal methods;
8. context-bar widget order, layout, placeholders and conditional back behavior;
9. command-bar slot layout and placeholder behavior;
10. primary and secondary labels, command order and callbacks;
11. staggered delays and scheduling order;
12. done flag, menu sync and atomic-reveal trigger occur only after secondary completion;
13. suppression and destroyed-widget guards are preserved.

Tests may use fakes/monkeypatching; they must not require a live display except existing canonical Tk smoke coverage.

## 10. Existing tests requiring migration

Update ownership/source-location expectations without weakening behavioral contracts.

Directly affected tests include at least:

- `test_studio_gicleeframe_top_bar_lazy_actions_6g5g.py`
- `test_studio_gicleeframe_top_bar_late_split_6g5h.py`
- `test_studio_gicleeframe_first_visible_sections_6g5f.py`
- `test_studio_gicleeframe_section_list_fast_lane_6g5j.py`
- `test_studio_gicleeframe_section_list_diagnostics_6g5i.py`
- `test_studio_gicleeframe_sections_column_early_lane_6g5k.py`
- `test_studio_gicleeframe_shell.py`
- complete-MRO assertions in current Giclée Frame boundary tests.

Rules:

- top-bar methods, constants and events must be asserted in `gicleeframe_view_top_bar.py`;
- `_build_shell` scheduling call and atomic-reveal adapter calls remain asserted in the host;
- cross-performance tests may read both host and top-bar source, but must keep their original ordering/marker assertions;
- rename tests whose names would falsely claim host ownership after extraction;
- do not replace precise assertions with broad `hasattr` checks.

## 11. Documentation

After green local validation:

- set this document to `COMPLETED — MRO INTEGRATED`;
- add GF-M8 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M7 as historical checkpoints;
- update later-stage label from `GF-M8+` to `GF-M9+`;
- document that RAM workflow remains host-owned for the next package.

## 12. Durable allowlist

Expected maximum scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m8-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_top_bar.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_top_bar.py`
6. `cursor-api/tests/test_studio_gicleeframe_top_bar_lazy_actions_6g5g.py`
7. `cursor-api/tests/test_studio_gicleeframe_top_bar_late_split_6g5h.py`
8. `cursor-api/tests/test_studio_gicleeframe_first_visible_sections_6g5f.py`
9. `cursor-api/tests/test_studio_gicleeframe_section_list_fast_lane_6g5j.py`
10. `cursor-api/tests/test_studio_gicleeframe_section_list_diagnostics_6g5i.py`
11. `cursor-api/tests/test_studio_gicleeframe_sections_column_early_lane_6g5k.py`
12. `cursor-api/tests/test_studio_gicleeframe_shell.py`
13. directly affected complete-MRO boundary tests, with explicit justification.

No `.github`, workflow, version, Shopify/theme, writer, persistence, starter-file or ZIP changes.

## 13. Required validation

Local integration validation:

- `py_compile` for host, top-bar module and all existing mixins;
- new top-bar boundary tests;
- all directly affected source/migration tests;
- shell, lifecycle, lazy-shell, progressive-boot and atomic-reveal tests;
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

## 14. Explicit exclusions

- no RAM workflow extraction;
- no inventory implementation extraction;
- no navigation/lifecycle extraction;
- no atomic-reveal orchestration extraction;
- no command labels or callback behavior changes;
- no timing or telemetry renames;
- no section-list, editor, control-column, preview, page-context, layer-nav, cache or details-on-demand extraction;
- no writer, persistence, deploy or Shopify mutation;
- no starter-file update;
- no ZIP generation.
