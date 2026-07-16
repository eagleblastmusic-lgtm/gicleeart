# Theme post-layout runtime extraction

The post-layout inline runtime previously embedded near the end of `layout/theme.liquid` now lives in:

```text
snippets/giclee-theme-runtime.liquid
```

The snippet contains the existing divider, accordion, product-card, homepage mobile, transition, photo-mockup, product-data, accessibility, catalog-panel, and site-notice runtime in its original order. It remains a Liquid snippet rather than a static JavaScript asset because it contains template/request objects, product data loops, asset URLs, conditional Liquid, and nested snippet renders.

## Scope

- mechanical move only;
- no JavaScript statement, Liquid condition, product-data structure, nested render, or execution order change;
- critical head and header-height scripts remain in `layout/theme.liquid`;
- no deploy or live-theme mutation.

The regression contract records both the extracted-region SHA-256 and the original complete-theme SHA-256. Reinserting the snippet at the render marker must restore the pre-extraction theme byte-for-byte.
