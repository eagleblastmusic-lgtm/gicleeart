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
| **F5.0** | Docs / UX contract | Ten dokument + linki w docs | brak | done |
| **F5.1** | Read-only asset shell | Sekcja „Biblioteka / Assety”; typy obraz/wideo/kolaż | brak | done |
| **F5.1b** | Bounded asset list | Przypisania z aktywnego `index.json` — obraz/wideo/brak per strefa | brak | done |
| **F5.2** | Local draft selection | Wybór strefy + typu w UI; stan tylko w pamięci panelu | brak persist | done |
| **F5.3** | Conceptual draft preview | Podgląd koncepcyjny draftu w panelu — **nie** apply | brak | **implementacja — raport** |
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

## 8. F5.1 — Read-only asset browser shell (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduły | `studio/background_asset_types.py`, `studio/background_asset_shell.py` |
| UI | sekcja **Biblioteka / Assety** w `background_panel.py` — tylko `stronaglowna` |
| Typy | obraz, wideo, kolaż wideo — deklaratywnie, bez listowania plików |
| Strefy | 5× `section_background` — etykiety z `STRONAGLOWNA_SECTION_BGS` |
| `tldobio` | brak sekcji biblioteki |
| Zakazy | zero I/O, zero `Komponenty.*`, zero upload/zapis/Shopify |
| Wersja | **1.29.0** |

Manual smoke F5.1: patrz [`studio-preview.md`](studio-preview.md).

## 9. Kryteria akceptacji F5.1 (checklist)

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

Pliki F5.1:

- `giclee_app/studio/background_asset_types.py`
- `giclee_app/studio/background_asset_shell.py`
- rozszerzenie `giclee_app/ui/background_panel.py`
- `tests/test_studio_background_asset_shell.py`

---

## 10. F5.1b — Bounded read-only asset list (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Shared read | `background_state.py` — `stronaglowna_zone_statuses`, `section_bg_status` |
| Shell | `background_asset_shell.py` — lista przypisań z manifest + index |
| UI | **Biblioteka / Assety** — aktywny wariant + 5 stref: obraz/wideo/brak |
| Preview hint | **pominięty** — bez resolve ścieżek motywu (F5.1c/F5.3+) |
| Zakazy | bez URL-i, bez glob, bez preview file scan |
| Wersja | **1.29.1** |

Manual smoke F5.1b: patrz [`studio-preview.md`](studio-preview.md).

---

## 11. F5.2 — Local draft selection (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `background_draft_state.py` — pure in-memory draft |
| UI | sekcja **Draft wyboru** — tylko `stronaglowna`, po „Biblioteka / Assety” |
| Interakcja | wybór strefy + typ (obraz/wideo/kolaż) · **Wyczyść draft** |
| Persist | **brak** — `on_hide()` czyści draft lokalnie w panelu |
| Zakazy | brak Zapisz, upload, file picker, preview apply |
| Wersja | **1.29.2** |

Manual smoke F5.2: patrz [`studio-preview.md`](studio-preview.md).

---

## 12. F5.3 — Conceptual draft preview (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `background_draft_preview.py` — pure formatowanie podglądu |
| UI | sekcja **Podgląd draftu** — po „Draft wyboru”, tylko `stronaglowna` |
| Copy | `podgląd koncepcyjny · niezastosowany` — **nie** „apply” |
| Placeholder | tekstowy per typ (obraz/wideo/kolaż) — bez plików, bez miniatur |
| Persist / apply | **brak** — F5.3 nie stosuje zmian; F5.4 = controlled save |
| Wersja | **1.29.3** |

Manual smoke F5.3: patrz [`studio-preview.md`](studio-preview.md).

---

## 13. F5.4a — Save contract + dry-run (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `background_save_contract.py` — pure validate + dry-run |
| UI | sekcja **Plan zapisu** — po „Podgląd draftu”, tylko `stronaglowna` |
| Akcja | **Sprawdź zapis** — semantic diff obecny stan → draft intent |
| Copy | `dry-run · nic nie zapisano` — **nie** „Zapisz” / „Zastosuj” |
| Persist | **brak** — zero `write_text`, zero mutacji index.json |
| Walidacja | image/video OK · video_collage odrzucone (poza section_background) |
| Wersja | **1.31.0** |

Roadmap zapisu:

- **F5.4b0** — save readiness / ref policy (zero zapisu)
- **F5.4b1** — bounded writer + minimal backup (tylko clear)
- **F5.4c** — rollback / post-save validation
- **F5.4d** — asset ref selection
- **F5.5** — Shopify / upload / deploy / sync osobno

Manual smoke F5.4a: patrz [`studio-preview.md`](studio-preview.md).

---

## 14. F5.4b0 — Save readiness / ref policy (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `background_save_readiness.py` — `evaluate_save_readiness()`, `SaveOperation` |
| UI | **Gotowość zapisu** w sekcji Plan zapisu — po dry-run |
| Operacje | `noop` · `clear` (plan) · `set_with_ref` (zablokowane bez ref) |
| Reguły | kind change bez ref → zablokowane · brak→typ bez ref → zablokowane |
| Clear plan | checkbox „Plan: wyczyść tło…” — readiness only, **bez** writera |
| Copy | `F5.4b0 nadal nic nie zapisuje` · realny zapis = F5.4b1 |
| Persist | **brak** — zero `write_text`, zero backupu |
| Wersja | **1.31.1** |

Manual smoke F5.4b0: patrz [`studio-preview.md`](studio-preview.md).

---

## 15. F5.4b1 — Bounded local clear writer (zrealizowane w kodzie)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `background_save_writer.py` — jedyny moduł z `write_text` + `copy2` |
| API | `clear_section_background_with_backup()` → `SaveWriteResult` |
| Zakres | tylko operacja **clear** z gotowością zapisu |
| Patch | 4 pola: `background_media`, `background_image`, `video`, `background_overlay_pct` |
| Backup | `data/backups/index-{YYYYMMDD-HHMMSS}.json` przed zapisem |
| Plik | aktywny `data/variants/{active}/index.json` — bez manifest/settings |
| UI | przycisk **Zapisz lokalnie** — widoczny tylko clear-ready po „Sprawdź zapis” |
| Confirm | `messagebox.askyesno` — bez Shopify · bez deploy |
| Po zapisie | odświeżenie read-only „Aktualny stan” / „Biblioteka / Assety” |
| Wersja | **1.32.0** |

Manual smoke F5.4b1: patrz [`studio-preview.md`](studio-preview.md).

---

## Powiązane dokumenty

- F4 audit: [`background-parity.md`](background-parity.md)
- Studio hub: [`studio-preview.md`](studio-preview.md)
- Roadmap: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)
