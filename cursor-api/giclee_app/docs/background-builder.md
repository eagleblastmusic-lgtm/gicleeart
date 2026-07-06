# Premium Background Builder — UX contract (F5.0)

Hub: [`background-parity.md`](background-parity.md) · Studio: [`studio-preview.md`](studio-preview.md) · roadmap: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

**F5.0** = dokumentacja i kontrakt UX dla przyszłego *Premium Background Builder / Asset Manager* w Studio Preview. **Bez kodu UI, bez zapisu, bez Shopify.**

Stan po F4 (zrealizowane): panel tła read-only, sekcja „Aktualny stan”, handoff do inline, brak edycji w panelu.

---

## 1. Cel F5

F5 ma doprowadzić panel tła w Studio Preview od **read-only awareness (F4)** do **premium UX kreatora tła / asset managera**, który:

- oferuje spójny, muzealny interfejs do wyboru i podglądu assetów (obraz, wideo, kolaż wideo),
- **nie zastępuje** od razu klasycznego launchera ani ciężkich inline edytorów,
- rozszerza istniejący panel F4.2 (`background_panel.py`) — bez równoległego routera,
- docelowo może delegować zapis do istniejących pipeline’ów komponentów (F5.4+), a nie budować nowej warstwy Shopify w Studio.

F5 to **ścieżka produktowa** rozbita na małe fazy — nie jeden commit ani jedna wersja.

---

## 2. Dlaczego start od `stronaglowna` / `section_background`

| Aspekt | `stronaglowna` (Tier 2) |
|--------|-------------------------|
| Model danych | Lokalne `manifest.json` + `{active}/index.json`; 5 stref `section_background` już zmapowane w [`background_state.py`](../studio/background_state.py) |
| Typy assetów F5 | Obraz i wideo w `section_background`; kolaż wideo jako osobne pole hero (`video_collage`) — informacyjnie w shellu |
| Lokalny podgląd | Refs `shopify://shop_images/…` mogą mieć lokalny odpowiednik w theme `assets/` (wzorzec `resolve_local_shopify_image_path` w `service.py` — **tylko referencja, bez importu w Studio**) |
| Precedens F4 | F4.3b czyta manifest/index defensywnie, pure read-only, zero `Komponenty.*` |
| Ryzyko F5.0–F5.1 | Niskie — shell UX + ewentualnie bounded read w F5.1b |

**Pierwszy komponent F5:** wyłącznie `stronaglowna`.

Strefy `section_background` (z rejestru):

| field_id | section_key | Etykieta |
|----------|-------------|----------|
| `ga_background` | `section_ThWw4Q` | Giclée Art — intro |
| `rest_background` | `section_XwRNDp` | Odrestaurowywanie dzieł |
| `cc_background` | `section_bj9cY3` | Autorska korekcja kolorystyczna |
| `pot_background` | `section_p9Kcm6` | Potencjał ukryty w zdjęciu |
| `sd_background` | `section_P9LgB3` | Zobacz różnicę |

---

## 3. Dlaczego `tldobio` jest później

| Aspekt | `tldobio` (Tier 1) |
|--------|---------------------|
| Persystencja | Shopify Files + metafieldy kolekcji (`custom.bio_background_*`) |
| Upload | `upload_bio_background`, GraphQL, `metafieldDefinitionCreate` |
| Cache | `collections.json` — sync z Shopify może nadpisywać lokalnie |
| Side-effecty | Import `tldobio/service.py` → Shopify client, `write_text` |
| Ryzyko | Wysokie — upload/metafield od wczesnych faz F5 |

**`tldobio`** wchodzi do F5 dopiero po stabilizacji ścieżki `stronaglowna` (osobna akceptacja, prawdopodobnie F5.x+ lub osobna gałąź Tier 1).

---

## 4. Podział faz F5

| Faza | Nazwa | Zakres | Zapis | Akceptacja |
|------|-------|--------|-------|------------|
| **F5.0** | Docs / UX contract | Ten dokument + linki w docs | brak | **bieżąca** |
| **F5.1** | Read-only asset shell | Sekcja „Biblioteka / Assety” w panelu; typy obraz/wideo/kolaż; placeholdery | brak | osobna, po F5.0 |
| **F5.1b** | Bounded asset list (opcja) | Lista assetów tylko z aktywnego `index.json` + bounded local resolve | brak | osobna |
| **F5.2** | Local draft selection | Wybór strefy + typu w UI; stan tylko w pamięci panelu | brak persist | osobna |
| **F5.3** | Preview-only apply | Podgląd wybranego assetu bez mutacji JSON | brak | osobna |
| **F5.4** | Controlled save | Zapis przez istniejący API komponentu / handoff z payload | tak | **osobna decyzja** |
| **F5.5** | Shopify / sync / deploy | Upload, CDN, deploy motywu, polling | tak, sieć | **osobna decyzja produktowa** |
| **F5.6** | Domyślny launcher Studio | Przełącznik `GICLEE_STUDIO_UI` (wcześniej myląco „F5.1” w roadmapie) | konfig | osobna, przed F6 |

Kolejność obowiązkowa po F5.0:

```text
F5.0 → raport → akceptacja → F5.1 → raport → akceptacja → …
```

**Nie łączyć F5.0 i F5.1 w jednym kroku** — F5.1 dotyka UI panelu i bump wersji.

---

## 5. Guardrails (Studio F5.0–F5.3)

Warstwa `giclee_app/studio/*` i `giclee_app/ui/background_panel.py` (od F5.1):

| Reguła | Szczegół |
|--------|----------|
| Importy | **Zero** `Komponenty.*` |
| Zapis | **Zero** `write_text`, `open(..., 'w')`, mutacji JSON |
| Shopify | **Zero** client/session/upload/sync |
| Manifest | **Nie** używać `load_manifest()` z `homepage_variants.py` (migracja → zapis) |
| Backupy | **Nie** skanować `data/backups/*` |
| Runtime | **Nie** czytać logów, sekretów, tokenów, sesji |
| UI | **Nie** pokazywać URL-i, `shopify://` refs, metafieldów, collection_id |
| Parser | Defensywny — fallback zamiast crasha (wzorzec F4.3b) |
| Launcher | **Nie** ruszać `launcher.py`, `__main__.py` |
| Handoff F4.3a | Bez regresji — panel nie staje się drugim edytorem zapisującym |

Testy (od F5.1): pure functions + AST guardrails; unikać Tk GUI na CI.

---

## 6. Pierwszy komponent — tylko `stronaglowna`

- F5.1 pokazuje sekcję „Biblioteka / Assety” **tylko** dla `folder_name == "stronaglowna"`.
- `tldobio`: brak sekcji biblioteki w F5.1 (panel F4 bez regresji).
- Tier 3 (`katalog`, `kontakt`, `faq`, `stronablogu`) — poza F5.

Typy assetów w kontrakcie UX (informacyjnie w shellu F5.1):

| Typ | Opis | Powiązanie |
|-----|------|------------|
| **obraz** | Tło sekcji jako `shopify://shop_images/…` | `section_background`, media=image |
| **wideo** | Plik wideo sekcji | `section_background`, media=video |
| **kolaż wideo** | JSON kolażu hero | pole `video_collage` (hero) — osobny pipeline od 5 stref |

---

## 7. Poza zakresem F5.0 / wczesnego F5

- Implementacja UI (F5.1+) — **poza F5.0**
- `tldobio` — integracja asset managera
- Tier 3 — hero `background_image`
- Upload plików
- Zapis do `index.json`, `settings.json`, theme assets
- Asset manager z prawdziwym skanowaniem katalogów / backupów
- F5.4 controlled save
- F5.5 Shopify / sync / deploy / polling
- Zmiany w `Komponenty/*`, `component.json`
- PyInstaller (F6)

---

## 8. Kryteria akceptacji F5.1 (plan — bez implementacji w F5.0)

F5.1 uznaje się za gotowe, gdy:

1. Panel **Strona główna** → **Tło** pokazuje sekcję **„Biblioteka / Assety”** (po „Aktualny stan”).
2. Sekcja zawiera copy dla typów: obraz, wideo, kolaż wideo + placeholdery („Wkrótce” / read-only shell).
3. Mapowanie 5 stref jako etykiety informacyjne (bez edycji).
4. Badge / status: shell · read-only — brak przycisków upload/zapisz.
5. **`tldobio`** — brak nowej sekcji biblioteki; F4 panel bez regresji.
6. **Edytuj w komponencie** (F4.3a) działa bez zmian.
7. Testy: `test_studio_background_asset_shell.py` + rozszerzenie panel/imports; AST bez `Komponenty.*` i `write_text`.
8. Scoped pytest green; manual smoke: brak nowych/zmienionych plików w `Komponenty/stronaglowna/data/*`.
9. Bump wersji **1.29.0** (nowa widoczna sekcja UI).

Pliki spodziewane w F5.1 (referencja — **nie tworzyć w F5.0**):

- `giclee_app/studio/background_asset_types.py`
- `giclee_app/studio/background_asset_shell.py`
- rozszerzenie `giclee_app/ui/background_panel.py`

---

## Powiązane dokumenty

- F4 audit: [`background-parity.md`](background-parity.md)
- Studio hub: [`studio-preview.md`](studio-preview.md)
- Roadmap: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)
