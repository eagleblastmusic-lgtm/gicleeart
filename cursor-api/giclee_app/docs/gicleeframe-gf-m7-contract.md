# GF-M7 — Shared Readiness Row Renderer Extraction Contract

Status: **BOUNDARY SEEDED — MRO INTEGRATION PENDING**

Repository: `eagleblastmusic-lgtm/gicleeart`
Base branch: `master`
Exact base SHA: `a008e881426a94219d53e9f8ef7cc0cc29836eed`
Work branch: `gpt-work/gicleeframe-modularization-m7-readiness-row-renderer`

## 1. Discovery decision

GF-M7 extracts the smallest coherent boundary remaining after GF-M6: the shared **readiness row renderer** used by both the F1 Brand Panel and the F2 Page Readiness Panel.

Move exactly one method:

1. `_pack_readiness_row`

The method is presentation-only. It creates one readiness row, resolves the status-dot color and packs the label/value widgets. It owns no state, lifecycle, scheduling, telemetry, persistence, inventory or editor behavior.

Rejected for this stage:

- command bar, because construction is split across lazy late-build lanes and is coupled to telemetry, menu sync and atomic reveal;
- RAM-variant actions, because they cross inventory refresh, selected element state, section rendering and editor population;
- control-column composition, because `_build_control_column` remains the host composition root for structure → readiness → safety;
- section list, editor, preview and details-on-demand, because they are larger and performance-sensitive.

## 2. Target architecture

Create:

`cursor-api/giclee_app/ui/gicleeframe_view_readiness_row.py`

Preferred shape:

- a narrow mixin named `GicleeFrameReadinessRowMixin`;
- no `__init__`;
- no Tk/widget base class;
- no import from `gicleeframe_view.py`;
- no file writes, network, subprocess, dialogs or Shopify operations;
- no `after()`, `after_idle()` or `after_cancel()`;
- `GicleeFrameView` inherits it after the four existing panel mixins and before `ctk.CTkScrollableFrame`.

The mixin form preserves the existing private call contract:

- `GicleeFrameBrandPanelMixin` continues calling `self._pack_readiness_row(...)`;
- `GicleeFramePageReadinessMixin` continues calling `self._pack_readiness_row(...)`;
- neither consumer needs behavioral or layout changes.

## 3. Exact ownership boundary

The new module owns exactly one method:

- `_pack_readiness_row(parent, label, value, ok)`.

Preserve exactly:

- transparent row frame;
- `fill="x"`, `pady=2`;
- status dot text `●`;
- dot width `20`;
- dot color from `status_color(ok)`;
- label width `180`, anchor `w`;
- label font `theme.get_font(11)` and `theme.TextMuted`;
- value anchor `w` and bold font `theme.get_font(11, "bold")`;
- widget order: dot → label → value.

The renderer must remain synchronous and stateless.

## 4. Host-owned behavior

The following remain in `gicleeframe_view.py`:

- `_build_control_column` and `_CONTROL_COL_MINSIZE`;
- `_toggle_f1_section`;
- all lifecycle and scheduler methods;
- command-bar lazy construction;
- telemetry and atomic-reveal gates;
- inventory and RAM-variant actions;
- section list, selection, editor, page context, preview, layer navigation, cache and details-on-demand.

The four existing panel mixins retain their current ownership:

- `GicleeFrameBrandPanelMixin`;
- `GicleeFramePageReadinessMixin`;
- `GicleeFrameStructureDryRunMixin`;
- `GicleeFrameSafetyCardMixin`.

GF-M7 does not combine or otherwise refactor those modules.

## 5. Import ownership after extraction

After removing `_pack_readiness_row` from the host, remove the host import:

- `status_color`

only when source review proves there is no remaining host consumer.

Retain `ctk`, `theme` and every primitive import still consumed elsewhere in the host.

The new module imports:

- `customtkinter as ctk`;
- `.theme`;
- `.widgets.status_color`.

No duplicate status-color helper is allowed.

## 6. Compatibility contracts

Preserve:

- `GicleeFrameView` public import path and class identity;
- private method name and call signature;
- identity resolution through MRO;
- all readiness copy and row ordering supplied by the F1/F2 consumer modules;
- `None`, `True` and `False` status-color behavior;
- no UI/copy/layout changes;
- no timing, telemetry or performance changes;
- no writer, persistence, sync, deploy or Shopify mutation.

The method must be absent from `GicleeFrameView.__dict__` after wiring and resolve identically from `GicleeFrameReadinessRowMixin`.

## 7. Existing tests affected by ownership

Update only obsolete ownership assertions.

`test_studio_gicleeframe_view_brand.py`:

- keep `_pack_readiness_row` outside `GicleeFrameBrandPanelMixin`;
- replace the assertion that the method is host-owned with an assertion that it resolves from `GicleeFrameReadinessRowMixin`;
- keep `_toggle_f1_section` host-owned.

`test_studio_gicleeframe_view_page_readiness.py`:

- keep `_pack_readiness_row` outside `GicleeFramePageReadinessMixin`;
- remove the obsolete host-ownership assertion;
- verify the new mixin is in the view MRO and method identity is preserved;
- keep `_build_control_column` host-owned.

Other panel tests may add the new mixin to complete-MRO assertions, but must not change their ownership boundaries.

## 8. New boundary tests

Create:

`cursor-api/tests/test_studio_gicleeframe_view_readiness_row.py`

Minimum coverage:

1. mixin has no `__init__` and no Tk base;
2. exact one-method ownership;
3. no `Komponenty.*`, writes, network, subprocess, dialogs, Shopify or scheduler ownership;
4. method produces dot, label and value widgets in the original order;
5. exact pack/configuration contract;
6. `status_color(ok)` receives `True`, `False` and `None` unchanged;
7. all five mixins occur in `GicleeFrameView.__mro__` after wiring;
8. method is absent from `GicleeFrameView.__dict__`;
9. `GicleeFrameView._pack_readiness_row is GicleeFrameReadinessRowMixin._pack_readiness_row`;
10. `_build_control_column` and `_toggle_f1_section` remain host-owned.

## 9. Source-text tests

Update `test_studio_gicleeframe_shell.py` with a separate UI-module path for `gicleeframe_view_readiness_row.py`.

Move ownership-sensitive assertions for:

- `_pack_readiness_row`;
- `status_color(ok)`;
- the readiness-dot/label/value layout

to the new module.

Keep host assertions for:

- `_build_control_column`;
- `_CONTROL_COL_MINSIZE`;
- `_toggle_f1_section`;
- lifecycle, scheduler and shell contracts.

Add no-write/no-network/no-scheduler source guardrails. Do not add the UI module to `_NEW_PLANNING_MODULES`, which resolves paths under `studio`.

## 10. Durable allowlist

Maximum scope:

1. `cursor-api/giclee_app/ui/gicleeframe_view.py`
2. `cursor-api/giclee_app/ui/gicleeframe_view_readiness_row.py`
3. `cursor-api/tests/test_studio_gicleeframe_view_readiness_row.py`
4. `cursor-api/tests/test_studio_gicleeframe_view_brand.py`
5. `cursor-api/tests/test_studio_gicleeframe_view_page_readiness.py`
6. only directly affected complete-MRO tests in existing Giclée Frame boundary files
7. `cursor-api/tests/test_studio_gicleeframe_shell.py`
8. `cursor-api/giclee_app/docs/gicleeframe-planning.md`
9. this contract document

No `.github`, workflow, version, Shopify/theme, starter-file or ZIP changes.

## 11. Required validation

Before integration push:

- `py_compile` for host and all five mixin modules;
- new readiness-row boundary tests;
- brand/page-readiness/structure/safety boundary and MRO tests;
- shell, lifecycle, lazy-shell and progressive-boot tests;
- `pytest -q -k gicleeframe`;
- runtime-write inventory;
- `git diff --check`;
- exact changed-file allowlist review.

CI contract:

1. draft Hermetic and artifact review;
2. ready only after exact-head Hermetic success;
3. canonical Tk GUI smoke;
4. full baseline and runtime-write inventory review;
5. exact-head final review;
6. squash merge with `expected_head_sha`.

## 12. Explicit exclusions

- no command-bar extraction;
- no RAM-variant action extraction;
- no control-column extraction;
- no panel redesign or copy change;
- no lifecycle, scheduler, telemetry or performance change;
- no editor, section-list, preview, page-context, layer-nav, cache or details-on-demand change;
- no writer, persistence or Shopify operation;
- no starter-file update;
- no ZIP generation.
