# Theme inline overrides extraction

The large conditional CSS layer previously embedded in `layout/theme.liquid` lives in:

```text
snippets/giclee-theme-inline-overrides.liquid
```

The layout renders it at the original location, immediately after splash markup and before `skip-to-content-link`. It remains Liquid because it contains request/template-dependent conditions.

## Contract

- mechanical move only;
- the snippet line count and SHA-256 are fixed by regression tests;
- reinserting the CSS snippet restores the intermediate layout layer;
- the separate runtime-composition contract verifies reconstruction of the complete historical layout;
- no deploy or live-theme mutation is implied.
