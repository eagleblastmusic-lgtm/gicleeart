# Theme inline overrides extraction

The large inline CSS block previously embedded in `layout/theme.liquid` now lives in:

```text
snippets/giclee-theme-inline-overrides.liquid
```

The layout renders the snippet at the exact previous location, immediately after the splash markup and before `skip-to-content-link`.

## Scope

- mechanical move only;
- no selector, declaration, animation, Liquid condition, or ordering change;
- no conversion to an asset because the block contains request/template-dependent Liquid conditions;
- no deploy or live-theme mutation.

The regression test records the extracted block SHA-256 and line count, verifies the render location, and confirms that reinserting the snippet restores the original layout line count. Intentional future edits to this snippet must update the recorded digest.
