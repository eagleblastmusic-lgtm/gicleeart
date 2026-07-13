# GF-M9 — RAM Variant Workflow Subsystem Extraction Contract

Status: **COMPLETED — MRO INTEGRATED**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `3dd985fb3861247a078e5596c51926b5dab222e5`
Work branch: `gpt-work/gicleeframe-modularization-m9-ram-variant-workflow`

## 1. Objective

Extract the complete **RAM Variant Workflow** from `GicleeFrameView` into one cohesive, RAM-only mixin.

The subsystem owns:

- synchronization of the working-variant menu;
- switching the active RAM variant;
- synchronization of variant/inventory metadata and draft edit count in the top bar;
- adding, duplicating, renaming and clearing RAM variants;
- status copy emitted by these variant operations.

The extraction must preserve all current behavior and must not introduce persistence, file writes, network access, Shopify mutation, lifecycle ownership or background scheduling.

## 2. Exact method boundary

Move exactly these seven methods from `GicleeFrameView`:

1. `_sync_working_variant_menu`
2. `_on_working_variant_selected`
3. `_update_top_bar`
4. `_add_ram_variant`
5. `_duplicate_ram_variant`
6. `_rename_ram_variant`
7. `_clear_page_draft`

Target module:

`cursor-api/giclee_app/ui/gicleeframe_view_ram_variants.py`

Target owner:

`GicleeFrameRamVariantMixin`

The mixin:

- has no `__init__`;
- has no Tk/CTk base class;
- does not import `gicleeframe_view.py`;
- owns no writer, persistence, filesystem, network, subprocess, Shopify or deployment behavior;
- owns no `after()` scheduling;
- owns no global lifecycle methods;
- may create the existing `ctk.CTkInputDialog` used by rename;
- may call host-owned adapters through `self`.

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
    GicleeFrameRamVariantMixin,
    ctk.CTkScrollableFrame,
):
```

All seven methods must be absent from `GicleeFrameView.__dict__` and resolve by identity from `GicleeFrameRamVariantMixin`.

No compatibility wrapper, alias or duplicate definition may remain in the host.

## 4. Host-owned state

Initialization remains in `GicleeFrameView.__init__` for all shared state, including:

- `_page_draft`;
- `_inventory`;
- `_merged` and `_merged_by_id`;
- `_selected_id`;
- `_working_variant_menu`;
- `_working_variant_map`;
- `_top_meta_label`;
- `_change_count_label`;
- `_structure_dry_label`;
- `_on_status`.

GF-M9 must not introduce a parallel state object or duplicate any of these attributes.

## 5. Host-owned adapters and excluded methods

The host remains the composition root and retains:

- `__init__`;
- `_apply_edit_to_draft` — editor-to-draft bridge, reserved for the editor subsystem;
- `_refresh_inventory` and `_refresh_inventory_light` — inventory implementations;
- `_set_merged` and `_rebuild_page_model_cache`;
- `_render_section_menu` and section-list implementations;
- `_populate_editor` and all selection/editor implementations;
- `_reset_structure_dry_run_display` — structure dry-run owner;
- `_build_shell` and all lifecycle methods;
- top-bar widget construction in `GicleeFrameTopBarMixin`;
- all atomic-reveal, scheduler, telemetry, control-column, preview, page-context, layer-nav and details-on-demand behavior.

The RAM-variant mixin may call these adapters through `self` but must not absorb their implementations.

## 6. Behavioral contract — menu synchronization

`_sync_working_variant_menu` must preserve exactly:

- no-op when `_working_variant_menu is None`;
- source pairs from `self._page_draft.variant_names()`;
- rebuilding `_working_variant_map` from display label to variant id;
- display labels produced by `working_variant_menu_label(variant)`;
- no-op when no labels exist;
- `configure(values=labels)` on the menu;
- active variant label selected when present;
- first label selected as fallback.

The method must not mutate variant data except the host-side display map.

## 7. Behavioral contract — selecting a variant

`_on_working_variant_selected(label)` must preserve exactly:

- no-op for an unknown/empty map result;
- `self._page_draft.switch_variant(variant_id)`;
- merge with current inventory only when inventory exists;
- `_update_top_bar()`;
- `_render_section_menu()`;
- repopulation of the currently selected element when it still exists;
- clearing `_selected_id` when the selected element no longer exists;
- status copy:

```text
Wariant roboczy: <draft_name> · <RAM_ONLY_STATUS>
```

No inventory reload is performed by variant switching.

## 8. Behavioral contract — top-bar state sync

`_update_top_bar` must preserve exactly:

- source variant fallback `—` when no inventory exists;
- draft count from `self._page_draft.draft_edit_count()`;
- source metadata based on `variant_environment_tag(...)` when inventory has a variant id;
- `PAGE_SOURCE_FILE` in the displayed source line;
- `_sync_working_variant_menu()` on every update;
- change count copy `Zmiany: <count>` when `_change_count_label` exists;
- no widget creation and no inventory mutation.

The method remains callable by host-owned inventory refresh and editor-apply paths.

## 9. Behavioral contract — add, duplicate, rename and clear

### Add

Preserve:

- `self._page_draft.add_variant()`;
- `_selected_id = None`;
- structure dry-run display reset when its label exists;
- host `_refresh_inventory(warn_if_draft=False)`;
- status copy `Dodano wariant RAM: ... · nic nie zapisano`.

### Duplicate

Preserve:

- `duplicate_active_variant()`;
- `_selected_id = None`;
- merge with current inventory when available;
- `_update_top_bar()`;
- `_render_section_menu()`;
- status copy `Zduplikowano wariant: ... · nic nie zapisano`;
- no inventory reload.

### Rename

Preserve:

- `ctk.CTkInputDialog`;
- prompt `Nowa nazwa wariantu roboczego (tylko pamięć):`;
- title from `RENAME_VARIANT_LABEL`;
- no-op for cancelled, empty or whitespace-only input;
- stripped name passed to `rename_active_variant`;
- `_update_top_bar()`;
- status copy `Zmieniono nazwę wariantu: ...`;
- no inventory reload and no section-list rebuild.

### Clear

Preserve:

- `self._page_draft.clear()`;
- `_selected_id = None`;
- structure dry-run display reset when its label exists;
- host `_refresh_inventory(warn_if_draft=False)`;
- status copy `Wyczyszczono wariant RAM: ... · nic nie zapisano`.

## 10. Imports and source ownership

The new module may import only what the seven methods require, including:

- `customtkinter as ctk`;
- `PAGE_SOURCE_FILE`, `RAM_ONLY_STATUS`, `RENAME_VARIANT_LABEL`, `merge_inventory_with_draft`, `working_variant_menu_label`;
- `variant_environment_tag`.

After extraction, remove these imports from the host only when no remaining host consumer exists.

Do not remove imports still needed by `_apply_edit_to_draft`, inventory, editor, section list or other host methods.

## 11. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_ram_variants.py`

Minimum coverage:

1. narrow object-only mixin, no `__init__` and exactly seven methods;
2. no reverse host import;
3. no writer/filesystem/network/subprocess/Shopify/deploy operations;
4. no `after()`, lifecycle or inventory implementation ownership;
5. seven-mixin MRO and identity for all moved methods;
6. host ownership retained for all adapters listed in section 5;
7. menu map rebuild, active selection and fallback behavior;
8. unknown variant selection no-op;
9. known variant selection ordering and selected-element preservation/clearing;
10. top-bar source metadata and draft-count synchronization;
11. add/duplicate/rename/clear operation ordering;
12. cancel/blank/trimmed rename cases;
13. exact status copy and `warn_if_draft=False` refresh calls;
14. proof that all operations remain RAM-only.

Use fakes and monkeypatching. The boundary test must not require a live display.

## 12. Existing tests requiring migration

Update source-location and ownership expectations without weakening behavior.

Directly affected tests include at least:

- `test_studio_gicleeframe_view_top_bar.py` — RAM methods cease to be host-owned adapters and must resolve from the new mixin;
- `test_studio_gicleeframe_shell.py` — variant workflow symbols move from host source to the RAM-variant module;
- current complete-MRO boundary tests;
- any test that explicitly slices host source around one of the seven moved methods.

`test_studio_gicleeframe_selection_stability_6g5s1.py` should normally remain unchanged: it patches `_update_top_bar` on the view instance and therefore should continue to work through MRO. Modify it only if a concrete source-location assertion requires migration.

Do not modify the model-level behavior tests in `test_studio_gicleeframe_page_draft.py` unless the extraction reveals a real import/ownership dependency.

## 13. Documentation

After green local validation:

- set this contract to `COMPLETED — MRO INTEGRATED`;
- add GF-M9 to `gicleeframe-planning.md`;
- preserve GF-M3–GF-M8 as historical checkpoints;
- change later-stage references from `GF-M9+` to `GF-M10+`;
- document that `_apply_edit_to_draft`, inventory, section-list and editor population remain host-owned;
- identify Section List as the next larger subsystem candidate.

## 14. Durable allowlist

Expected maximum scope:

1. `cursor-api/giclee_app/docs/gicleeframe-gf-m9-contract.md`
2. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
3. `cursor-api/giclee_app/ui/gicleeframe_view.py`
4. `cursor-api/giclee_app/ui/gicleeframe_view_ram_variants.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_ram_variants.py`
6. `cursor-api/tests/test_studio_gicleeframe_view_top_bar.py`
7. `cursor-api/tests/test_studio_gicleeframe_shell.py`
8. directly affected complete-MRO boundary tests, with explicit justification.

Additional directly affected tests are allowed only when the report names the exact source-ownership dependency.

No `.github`, workflow, version, Shopify/theme, writer, persistence, deploy, starter-file or ZIP changes.

## 15. Required validation

Local validation:

- `py_compile` for host, RAM-variant module and all existing mixins;
- new RAM-variant boundary tests;
- top-bar boundary tests;
- shell and complete-MRO tests;
- page-draft model tests;
- selection-stability tests;
- lazy-shell, progressive-boot, lifecycle and atomic-reveal tests;
- `pytest -q -k gicleeframe`;
- runtime-write inventory;
- `git diff --check`;
- exact changed-file allowlist review.

CI contract:

1. draft Hermetic on the exact final head;
2. artifact review;
3. ready only after exact-head Hermetic success;
4. canonical Tk GUI smoke;
5. full baseline and runtime-write inventory review;
6. exact-head final review;
7. squash merge with `expected_head_sha`.

## 16. Explicit exclusions

- no `_apply_edit_to_draft` extraction;
- no inventory implementation extraction;
- no section-list or editor extraction;
- no top-bar widget construction changes;
- no navigation or lifecycle extraction;
- no atomic-reveal or scheduler extraction;
- no wording, dialog, ordering or callback behavior changes;
- no writer, persistence, filesystem, network, deploy or Shopify mutation;
- no starter-file update;
- no ZIP generation.
