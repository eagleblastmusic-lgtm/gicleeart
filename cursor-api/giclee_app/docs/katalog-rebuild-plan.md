# Katalog — Rebuild Plan

**docs-only / plan-only** · checkpoint `56b4c9c` · Studio **v1.36.0** (F1) · after [`admin-components-strategy.md`](admin-components-strategy.md) · **F5.5 not started** · **F1 read-only shell implemented @ 1.36.0**

Hub: [`admin-components-strategy.md`](admin-components-strategy.md) · [`studio-v2-workflows.md`](studio-v2-workflows.md) · [`studio-save-pattern.md`](studio-save-pattern.md) · [`background-builder.md`](background-builder.md) §19 · [`../../docs/komponenty/katalog.md`](../../docs/komponenty/katalog.md) · [`../../docs/komponenty/tldobio.md`](../../docs/komponenty/tldobio.md)

---

## 1. Executive summary

**Katalog** będzie nowym **parent workflow** w Studio v2 — centralnym miejscem administracji obszaru katalogowego (strony kolekcji, struktura, bio/context, tła).

| Punkt | Decyzja |
|-------|---------|
| Legacy | Nie portujemy starego UI 1:1; nie robimy płaskiej listy kafelków |
| Tło do Bio | `tldobio` → podfunkcja Katalogu, nie standalone tile Studio v2 |
| Ten dokument | Ustala zakres, mapę danych, ryzyka writera i kolejność faz — **bez implementacji** |
| Następny krok kodu | **Katalog F1 — read-only shell** (osobna akceptacja) |

Referencja Save Pattern Level 2: Background Builder local v1 (`stronaglowna`).

---

## 2. Strategic role

Katalog w Studio v2 pełni rolę **centralnego workflow** dla:

- struktury katalogowej (layout stron kolekcji / `collection.json`)
- podsekcji treści (biografia, showcase, dzieła — strefy z legacy `registry.py`)
- bio/context i tła per kolekcja (wchłonięte z `tldobio`)
- późniejszych rozszerzeń (podsekcje, warianty, readiness)

Katalog **nie jest**:

- pojedynczym małym komponentem inline w launcherze
- legacy portem `theme_page_editor` 1:1
- miejscem na Shopify sync w fazie Level 2

Launcher legacy (`python -m Komponenty.katalog`, `python -m Komponenty.tldobio`) pozostaje do czasu migracji UX.

---

## 3. Legacy inventory — read-only

Inwentaryzacja wykonana read-only @ checkpoint `56b4c9c`. **Żaden plik w `Komponenty/*` nie został zmieniony.**

### 3.1 `Komponenty/katalog/`

| Element | Opis |
|---------|------|
| `component.json` | Inline · „Katalog” · edycja `templates/collection.json` |
| `registry.py` | `PAGE_ZONES`: **biography** (tło sekcji BIO w szablonie), **showcase**, **works** — mapowanie pól → ścieżki JSON |
| `gui.py` | Cienka warstwa → `Komponenty/_shared/theme_page_editor/` (warianty, backup, deploy w legacy) |
| `view.py`, `__main__.py` | Entry subprocess |
| `data/variants/manifest.json` | Aktywny wariant `ka1` |
| `data/variants/ka1/collection.json` | Pełny szablon motywu Shopify (auto-generated header) — sekcje, bloki, ustawienia |

**Potencjalne źródła danych (do data map):**

- warianty lokalne: `data/variants/<id>/collection.json`
- manifest wariantów: `data/variants/manifest.json`
- strefy edycji: `registry.py` → ścieżki w JSON szablonu
- motyw storefront: `templates/collection.json` (deploy target — poza Studio layer w F1)

**Wymaga późniejszego data map:** które pola są read-only inventory vs. które mogą wejść do bounded local writer (jeśli w ogóle).

### 3.2 `Komponenty/tldobio/`

| Element | Opis |
|---------|------|
| `component.json` | Inline · „Tło do Bio” · tło sekcji biografii per kolekcja |
| `service.py` | Shopify Files upload + metafieldy kolekcji (`custom.bio_background_*`) |
| `data/collections.json` | Cache lokalny v2: `backgrounds` (handle → url, pos, overlay, mask, gradient…) + snapshot `catalog` |
| `data/*.jpg` | Assety testowe lokalne |
| `preview_render.py` | Compositing podglądu jak CSS motywu |
| `gui.py`, `view.py` | UI upload/kadr/gradient/maska |

**Potencjalne źródła danych (do data map):**

- cache read-only: `data/collections.json` (inventory listy kolekcji i ustawień tła)
- **Shopify metafields** (source of truth produkcyjny) — **Level 3 / F5.5+**, nie Level 2
- powiązanie z motywem: `giclee-artist-biography` (SSR + JS karuzela)

**Wymaga późniejszego data map:** rozdzielenie „local cache read” vs „Shopify write path” vs „motyw fallback (`background_image` w collection.json)”.

### 3.3 Studio layer (istniejące, read-only awareness)

| Plik | Rola |
|------|------|
| `giclee_app/studio/background_capabilities.py` | `tldobio` → tier `bio_workflow` |
| `giclee_app/studio/background_state.py` | `_summarize_tldobio()` — podsumowanie stanu z package path |
| `giclee_app/launcher_layout.py` | Oba foldery w sekcji „Administracja strony” (legacy launcher) |

### 3.4 Nakładanie się domen (uwaga planistyczna)

Legacy **Katalog** (`registry.py` → zone `biography`) edytuje `background_image` w szablonie kolekcji. Legacy **tldobio** edytuje metafieldy per kolekcja Shopify. To **dwa różne mechanizmy persystencji** dla podobnej strefy UI. Nowy Katalog musi to ujednolicić w data map — bez mieszania zapisów w F1.

---

## 4. Absorbed workflow: Tło do Bio

| Aspekt | Decyzja |
|--------|---------|
| Standalone tile Studio v2 | **Nie** — `tldobio` wchłonięte do Katalogu |
| Legacy launcher | Pozostaje do migracji UX |
| Docelowa podsekcja w Katalogu (robocze nazwy) | **Bio / Context** · **Catalog background** · **Artist/collection contextual background** |

Funkcjonalność legacy (upload, kadr, overlay, gradient, maska radialna) **nie jest implementowana** w tym planie — tylko zakres i miejsce w shellu.

**Zasada mutacji danych:**

> Legacy `tldobio` data may be read for inventory, but must not be mutated until a bounded data map and write policy exist.

Dotyczy: `collections.json`, metafieldów Shopify, plików w `data/`.

---

## 5. Data ownership map — draft

Robocza tabela — **nie jest jeszcze write policy**.

| Obszar | Potencjalny owner | Status | Ryzyko |
|--------|-------------------|--------|--------|
| Catalog structure (layout) | `Komponenty/katalog/data/variants/*/collection.json` | inventory done · data map needed | medium |
| Catalog zones (biography/showcase/works) | `katalog/registry.py` paths | mapped in legacy · Studio map TBD | medium |
| Bio/background context (per collection) | `Komponenty/tldobio/data/collections.json` + Shopify metafields | absorbed · read inventory | medium |
| Theme template deploy target | motyw `templates/collection.json` | external to Studio F1 | medium |
| Shopify collections/products | external / **F5.5+** | out of scope | **high** |
| Studio draft state | future `giclee_app/studio/katalog_*` | planned | low |
| Local bounded writer | future Level 2 module | **not started** | Level 2 |
| Sync/deploy (Shopify Files, metafields) | future **F5.5 / Level 3** | out of scope | **high** |

**Zasady:**

- **Nie ma jeszcze write policy** — żaden writer w F0/F1
- **Nie wolno implementować writera bez data map** (patrz §8)
- **Nie wolno mieszać local write z Shopify** w jednym przycisku „Zapisz”

---

## 6. Proposed Studio v2 UX structure

Wysokopoziomowy shell (koncepcja, nie kod):

```
Katalog (parent workflow)
├── Overview / status          — checkpoint, capability summary, link do legacy launch (opcjonalnie)
├── Structure                  — warianty, sekcje collection.json (read-only inventory F1)
├── Bio / Context / Tło do Bio — absorbed tldobio subflow (read-only list F1)
├── Visual / background        — podgląd ustawień tła (bez upload F1)
├── Draft changes              — F3+
├── Dry-run / readiness        — F4+
├── Local save                 — F5+ (bounded writer, jeśli potrzebny)
└── Sync / deploy              — osobno · Level 3 · F5.5+ · nie teraz
```

Nawigacja **workflow-first** (sidebar / tabs w shellu Studio), nie płaska lista kafelków launcher.

---

## 7. Save Pattern phases for Katalog

Wzorzec: [`studio-save-pattern.md`](studio-save-pattern.md) · referencja Level 2: Background Builder local v1.

| Faza | Cel | Implementacja |
|------|-----|---------------|
| **Katalog F0** | Plan / data map (ten dokument + doprecyzowanie mapy pól) | **done (docs)** |
| **Katalog F1** | Read-only shell — wejście w workflow, inventory, zero write | **done @ 1.36.0** |
| **Katalog F2** | Bounded catalog inventory parser (warianty, strefy, tldobio cache read) | **next** |
| **Katalog F3** | Local draft state (Studio-only, nie dotyka plików) | planned |
| **Katalog F4** | Dry-run / readiness contract | planned |
| **Katalog F5** | Bounded local writer — **tylko jeśli potrzebny** | planned |
| **Katalog F6** | Backup / session undo (mirror Background Builder) | planned |
| **Katalog F7** | Optional Shopify/sync/deploy — **Level 3, F5.5+** | deferred |

**Pierwsza implementacja po tym planie = read-only shell (F1), nie writer.**

---

## 8. Writer risk policy

Writer **nie może powstać** przed:

1. zatwierdzoną **data ownership map** (§5 — wersja finalna)
2. listą **jawnie dozwolonych plików/pól**
3. **dry-run + readiness** dla każdej operacji zapisu

Gdy writer powstanie (F5+), obowiązuje:

| Reguła | Wymaganie |
|--------|-----------|
| Bounded | Mutacja tylko jawnie wskazanych plików/pól |
| Backup | Backup before write (jak Background Builder) |
| Session undo | Przywrócenie z backupu w sesji |
| No Shopify | Brak GraphQL / metafield / Files w Level 2 |
| No upload | Brak uploadu assetów w Level 2 shell |
| No deploy | Brak push do motywu / theme deploy |
| No manual external refs | Brak zapisu surowych CDN URL bez polityki asset ref |

**Szczególne ryzyko:** legacy `tldobio/service.py` zapisuje do Shopify — ten path **nie wchodzi** do Katalog F5 Level 2. Wymaga osobnej fazy F7 / F5.5.

---

## 9. Tests strategy

Plan testów na przyszłość ( **nie dodawać teraz** ):

| Warstwa | Zakres |
|---------|--------|
| Imports | `test_studio_imports.py` + moduły `giclee_app/studio/katalog_*` |
| Shell render smoke | Panel Katalog montuje się bez subprocess write |
| Data map fixtures | Minimal JSON: variant manifest, collection snippet, tldobio cache sample |
| Read-only inventory parser | F2 — listy wariantów, stref, backgrounds count |
| Draft state | F3 — izolacja od filesystem |
| Dry-run contract | F4 — diff preview bez write |
| Readiness | F4 — policy gates przed save |
| Writer bounded diff | F5 — tylko allowlisted paths |
| Backup/undo | F6 — mirror Background Builder tests |
| AST guardrails | Brak forbidden imports (Shopify client w shell F1) |

---

## 10. Manual smoke strategy

Plan przyszłego smoke (po F1):

1. Uruchomić Studio Preview (`python -m giclee_app.studio_preview`)
2. Wejść w **Katalog** (nowy workflow entry — nie legacy tile)
3. Zobaczyć **Overview** ze statusem read-only
4. Zobaczyć **read-only inventory** (warianty ka1, strefy registry, liczba wpisów tldobio cache)
5. **Brak przycisku Save** w F1
6. **Brak zmian** w `Komponenty/katalog/data/*`, `Komponenty/tldobio/data/*`
7. **Brak** wywołań Shopify / upload / deploy

---

## 11. Out of scope

- implementacja Katalogu (kod UI / studio modules)
- writer · migracja danych
- zmiany `Komponenty/*` · zmiany `tldobio` data
- Shopify / sync / deploy · **F5.5**
- upload · overlay editor (osobne legacy)
- version bump · testy w tym etapie
- `studio_categories.json` · `studio_workflows.json` · `component.json`

---

## 12. Recommendation

| # | Rekomendacja |
|---|--------------|
| 1 | Przyjąć **Katalog rebuild** jako następny główny workflow po admin strategy |
| 2 | Zacząć od **F0/F1 read-only** — shell + inventory, zero writer |
| 3 | **`tldobio`** traktować jako **absorbed subflow** w shellu Katalogu |
| 4 | **Nie zaczynać od writera** — najpierw data map final + F2 inventory parser |
| 5 | **Nie ruszać Shopify** — metafield/upload path wyłącznie F7 / F5.5 |
| 6 | Background Builder local v1 jako wzorzec Level 2 **tylko dla lokalnych plików JSON** — nie dla tldobio Shopify path |

**Next implementation target:** Katalog **F2 — bounded data map / inventory parser**.

---

## 13. F1 read-only shell (implemented)

| Element | Lokalizacja |
|---------|-------------|
| Inventory module | `giclee_app/studio/katalog_inventory.py` — bounded read-only paths |
| UI shell | `giclee_app/ui/katalog_view.py` — overview + inventory + warnings |
| Routing | Sidebar **Katalog** (NAV, bez zmiany `studio_categories.json`); hub click on `katalog` → shell (not legacy inline) |
| tldobio | Shown as **absorbed subflow** in inventory — **no** new standalone Studio v2 tile |

**F1 guardrails:** no Save · no writer · no Shopify · no upload · no deploy/sync · no `Komponenty.*` import in Studio layer.

**Next:** F2 bounded data map.

---

## Powiązane dokumenty

- [`admin-components-strategy.md`](admin-components-strategy.md)
- [`studio-v2-workflows.md`](studio-v2-workflows.md)
- [`studio-save-pattern.md`](studio-save-pattern.md)
- [`background-builder.md`](background-builder.md)
- [`studio-preview.md`](studio-preview.md)
- [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)
