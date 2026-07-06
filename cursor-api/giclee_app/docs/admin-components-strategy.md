# Administracja strony — Component Rebuild Strategy

**docs-only** · checkpoint `caabb27` · Studio **v1.35.0** · after Background Builder local v1 freeze · **F5.5 not started**

Hub: [`studio-v2-workflows.md`](studio-v2-workflows.md) · [`studio-save-pattern.md`](studio-save-pattern.md) · [`background-builder.md`](background-builder.md) §19 · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

---

## 1. Executive summary

Po freeze **Background Builder local v1** (`stronaglowna` → section_background) porządkujemy sekcję launcher **„Administracja strony”** jako **Studio v2 workflows** — nie jako płaską listę kafelków.

| Decyzja | Zakres |
|---------|--------|
| **Rebuild od zera** | 9 komponentów (patrz §2) |
| **Adapt-first** | Pozostałe komponenty launcher — zachować dobrą logikę, nowy shell Studio v2 |
| **Absorbed** | `tldobio` (Tło do Bio) → część workflow **Katalog** |
| **Frozen reference** | `stronaglowna` — Background Builder local v1 complete |

Strategia nie rozpoczyna implementacji komponentów. Plan Katalogu: [`katalog-rebuild-plan.md`](katalog-rebuild-plan.md). Następny krok implementacyjny: **Katalog read-only shell (F1)** — osobna akceptacja.

---

## 2. Components to rebuild from scratch

| Komponent | Folder | Decyzja | Uwagi |
|-----------|--------|---------|-------|
| Katalog | `katalog` | rebuild | Parent workflow; zawiera Tło do Bio |
| Własna fotografia | `wlasnafotografia` | rebuild | Nowy workflow od zera |
| Giclee Frame | `gicleeframe` | rebuild | **F2.1 ready** — referencja [`Studio Page Component Editor Pattern`](gicleeframe-planning.md#7-f21-jako-wzorzec-dla-przyszłych-edytorów-strony) |
| Współpraca | `wspolpraca` | rebuild | Nowy workflow od zera |
| Filozofia marki | `filozofiamarki` | rebuild | Nowy workflow od zera |
| Kontakt | `kontakt` | rebuild | Nowy workflow od zera |
| Blog / Strona blogu | `stronablogu` | rebuild | Nowy workflow od zera |
| FAQ | `faq` | rebuild | Nowy workflow od zera |
| Losuj Obraz | `losujobraz` | rebuild | Nowy workflow od zera |

---

## 3. Components to adapt

If a component is not listed in the rebuild table, treat it as **adapt-first** unless the user explicitly reclassifies it.

**Known adapt-first** (sekcja launcher „Administracja strony”, [`launcher_layout.py`](../launcher_layout.py)):

| Folder | Uwaga |
|--------|-------|
| `wzorzecszablonu` | adapt-first · szablony produktu |
| `stronaproduktu` | adapt-first · strona produktu |
| `karuzela` | adapt-first · karuzela sekcji |

**Adapt-first oznacza:**

- zachować dobrą istniejącą logikę w `Komponenty/*`
- nowy shell Studio v2 (read-only first, launch delegate tam gdzie sensowne)
- draft / dry-run / readiness / bounded writer **tylko jeśli potrzebne**
- guardrails ze [`studio-save-pattern.md`](studio-save-pattern.md)

**Frozen reference (nie adapt, nie rebuild target):**

- `stronaglowna` — Background Builder local v1 complete; nie rozszerzać poza **F5.5** albo osobny, jasno zaakceptowany follow-up

---

## 4. Components absorbed into larger workflows

| Komponent | Folder | Docelowe miejsce |
|-----------|--------|------------------|
| Tło do Bio | `tldobio` | Część workflow **Katalog** |

- **Nie** jako osobny główny tile Studio v2
- Katalog odpowiada za: strukturę katalogową, bio/context, tła i późniejsze podsekcje
- Legacy inline `tldobio` pozostaje dostępny przez klasyczny launcher do czasu migracji UX

---

## 5. Katalog as parent workflow

**Katalog** (`katalog`) jest rebuildowany od zera jako **parent workflow** obszaru katalogowego w Site Builder / Collections.

Docelowe fazy (bez implementacji w tym etapie):

1. read-only shell
2. bounded data map
3. draft state
4. dry-run contract
5. save readiness
6. bounded writer (jeśli potrzebny)
7. backup + session undo przy zapisach lokalnych

Katalog wchłania **Tło do Bio** i porządkuje największy obszar administracji strony.

**Katalog rebuild plan:** [`katalog-rebuild-plan.md`](katalog-rebuild-plan.md) · status: **planned / docs-only** · next implementation: **Katalog read-only shell (F1)**

---

## 6. Save Pattern requirements

Odwołanie: [`studio-save-pattern.md`](studio-save-pattern.md)

| Poziom | Wymaganie |
|--------|-----------|
| **Level 2 reference** | Background Builder local v1 (`stronaglowna`) — bounded writer + backup + session undo |
| **Pipeline** | read-only → draft → dry-run → readiness → bounded writer → backup → session undo |
| **Level 3** | external sync / deploy — **tylko F5.5**, osobna akceptacja |

Rebuild komponentów **nie** portuje legacy UI 1:1 bez decyzji. Każdy nowy writer wymaga bounded data map przed kodem.

---

## 7. Suggested implementation order

1. **F6.3** — Site Builder / Administracja shell strategy — **Katalog rebuild plan done (docs)**
2. Katalog rebuild plan (docs + data map) — **done** · [`katalog-rebuild-plan.md`](katalog-rebuild-plan.md)
3. Katalog read-only shell (F1)
4. Katalog draft / dry-run / readiness
5. Katalog bounded writer, jeśli potrzebny
6. Własna fotografia
7. Giclee Frame
8. Współpraca
9. Filozofia marki
10. Kontakt
11. FAQ
12. Blog / Strona blogu
13. Losuj Obraz

Katalog powinien iść **pierwszy**, bo wchłania Tło do Bio i porządkuje największy obszar. Kolejność pozycji 6–13 może się zmienić po F6.3.

---

## 8. Out of scope

- implementacja komponentów
- zmiany `Komponenty/*`
- migracja danych
- runtime data / backupy lokalne
- **F5.5** · Shopify / sync / deploy
- version bump
- `studio_categories.json` · `component.json` · `studio_workflows.json`

---

## Powiązane dokumenty

- [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)
- [`studio-preview.md`](studio-preview.md)
- [`studio-v2-workflows.md`](studio-v2-workflows.md)
- [`studio-save-pattern.md`](studio-save-pattern.md)
- [`katalog-rebuild-plan.md`](katalog-rebuild-plan.md)
