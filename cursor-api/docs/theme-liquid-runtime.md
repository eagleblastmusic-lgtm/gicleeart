# Theme post-layout runtime composition

`layout/theme.liquid` renders a thin runtime composition root:

```text
snippets/giclee-theme-runtime.liquid
```

The parent owns ordering only and renders four mechanically extracted domains:

- `giclee-theme-runtime-general.liquid` — divider, accordion, product-card and catalog-panel behavior;
- `giclee-theme-runtime-navigation.liquid` — homepage/mobile and page-transition runtime;
- `giclee-theme-runtime-photo-mockup.liquid` — conditional photo-mockup product data and UI runtime;
- `giclee-theme-runtime-footer.liquid` — link normalization, site notice and FAQ accessibility.

## Contract

- child order is fixed;
- each child has a recorded line count and SHA-256;
- recomposing all children must reproduce the original 1,526-line runtime region;
- reinserting that region into the layout must reproduce the pre-runtime-extraction theme byte-for-byte;
- critical head and header-height scripts remain in `layout/theme.liquid`;
- no deploy or live-theme mutation is implied.
