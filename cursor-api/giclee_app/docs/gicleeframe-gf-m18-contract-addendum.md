# GF-M18 Contract Addendum — Exact-Head Corrections

Status: **BINDING FOR IMPLEMENTATION**

Contract head reviewed: `2052b2be16fc3f6b206d99c4d50f4cecc1235770`  
Exact base: `e3b91f564d15b2e3d0749c7461af8207e65c7238`

This addendum corrects and clarifies
`gicleeframe-gf-m18-contract.md`. In any conflict, this addendum takes precedence.

## 1. Dead-constant evidence is a preflight artifact

The six declaration-only constants are still removed exactly as specified:

```text
_SECTION_LABEL_MAX_CHARS
_GF_BOOT_DEFER_MS
_GF_SHELL_SECTIONS_DEFER_MS
_GF_WORKSPACE_LOADING_TEXT
_GF_EDITOR_STALE_REFRESH_STATUS_TEXT
_GF_PERCEIVED_READY_DEFER_MS
```

However, the proof that they have zero `Load` uses on the frozen base must be
produced **before implementation** from the exact base source. It must not be deferred
to a normal post-extraction pytest that depends on Git history.

Required preflight from the repository root:

```powershell
$baseSha = "e3b91f564d15b2e3d0749c7461af8207e65c7238"
$source = git show "$baseSha`:cursor-api/giclee_app/ui/gicleeframe_view.py"
if ($LASTEXITCODE -ne 0) {
    throw "Nie można odczytać hosta z exact base."
}

$source | python -c @'
import ast
import sys

names = {
    "_SECTION_LABEL_MAX_CHARS",
    "_GF_BOOT_DEFER_MS",
    "_GF_SHELL_SECTIONS_DEFER_MS",
    "_GF_WORKSPACE_LOADING_TEXT",
    "_GF_EDITOR_STALE_REFRESH_STATUS_TEXT",
    "_GF_PERCEIVED_READY_DEFER_MS",
}

tree = ast.parse(sys.stdin.read())
loads = {name: 0 for name in names}
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        if node.id in loads:
            loads[node.id] += 1

print(loads)
if any(loads.values()):
    raise SystemExit(1)
'@

if ($LASTEXITCODE -ne 0) {
    throw "Co najmniej jedna stała ma aktywne użycie — zatrzymaj implementację."
}
```

Attach the exact printed mapping to the implementation report and PR comment.

The new boundary suite must instead assert:

- all six names are absent from the final host module;
- all six names are absent from the new lifecycle/inventory module;
- none is exported in `__all__`.

This replaces item 3 in contract section 9.

## 2. Exact module exports

The new module exports exactly:

```python
__all__ = (
    "GicleeFrameLifecycleInventoryMixin",
    "_GF_LOADING_OVERLAY_TEXT",
    "_CONTROL_COL_MINSIZE",
    "_PROGRESSIVE_BOOT_ENV",
    "_EAGER_BOOT_ENV",
    "_GF_SECTION_FIRST_VISIBLE_DEFER_MS",
    "_GF_INIT_REFRESH_LIGHT_DEFER_MS",
    "_GF_MICRO_DEFER_MS",
    "_GF_F1_DEFER_MS",
    "_GF_LAZY_SHELL_ENV",
    "_GF_SHELL_EDITOR_DEFER_MS",
    "_GF_SHELL_CONTROL_DEFER_MS",
    "_GF_CONTROL_LATE_BUILD_DEFER_MS",
    "_GF_SKELETON_SECTION_TEXT",
    "_GF_SKELETON_EDITOR_TEXT",
    "_GF_SKELETON_CONTROL_TEXT",
    "_env_enabled",
    "_progressive_boot_enabled",
    "_lazy_shell_enabled",
)
```

No other symbol is exported.

## 3. Worktree and clean-state gate

Implementation worktree:

`C:\Strona\gicleeart-gf-m18-worktree`

Required starting state:

- active branch:
  `gpt-work/gicleeframe-modularization-m18-lifecycle-inventory`;
- HEAD equals the final contract/addendum head published on PR #64;
- `git status --short` is empty;
- branch is not detached;
- `behind_by=0` against current `master`;
- no other open implementation PR in `eagleblastmusic-lgtm/gicleeart`.

## 4. Boundary-suite wording correction

The new suite must centralize all **58/58** ownership-and-identity assertions in one
test or one parametrized table. Existing suites may retain behavior tests but must not
become a second incomplete ownership source.

No test may use Git history, network, retry, skip or a live `ctk.CTk()` merely to prove
the structural boundary.
