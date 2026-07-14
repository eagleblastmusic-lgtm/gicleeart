# Current App State

**Paczka instrukcji:** v4.0 · ostatnia aktualizacja ręczna: 2026-07-14

---

## Current repository state

Weryfikacja: `git ls-remote` z `C:\Strona\pusty` (2026-07-13). GitHub connector (`gh`) niedostępny lokalnie — przed merge zweryfikuj przez connector w Custom GPT.

### gicleeart (`eagleblastmusic-lgtm/gicleeart`)

Default branch: `master`  
Current SHA: `f3d830910b2e9a5f108ec0896cc19c88d3d1eb5f`  
Open PRs: brak otwartego implementation PR na początku etapu v40  
Current primary stage: **Start Files v40 — autonomous engineering system** (w trakcie / po ukończeniu tego brancha)  
Poprzedni tor: **GICLÉE FRAME GF-M1–GF-M18 modularization — COMPLETED**  
Ostatnie merge: **PR #63 GF-M17** · **PR #64 GF-M18** @ `f3d830910b2e9a5f108ec0896cc19c88d3d1eb5f`  
Verified at: 2026-07-14 (`git fetch origin` + `rev-parse origin/master`)

#### GICLÉE FRAME GF-M1–GF-M18 — COMPLETED + final audit PASS (2026-07-14)

- **GF-M1–GF-M18 modularization complete**
- **16 mixinów** w MRO `GicleeFrameView`
- Host retains **4 behavioral methods**: `__init__`, `_editor_micro_defer_ms()`, `_progressive_boot_enabled_for_selection()`, `_apply_edit_to_draft`
- **Final audit:** PASS — dokumentacja w `cursor-api/giclee_app/docs/gicleeframe-planning.md` §30
- **Brak GF-M19** — modularizacja GICLÉE FRAME zamknięta
- Ready CI **#302**: Hermetic 48 passed; canonical Tk 6 passed (Tcl/Tk 8.6.15); full baseline 2342 passed, 1 optional skip; JUnit 2343 tests, 0 failures, 0 errors, 1 skipped; runtime-write inventory 714 files, 0 parse errors, 0 findings

**NEXT PRIMARY (po ukończeniu Start Files v40):** Bartosz OS / AgentRuntime / Antigravity SDK — discovery i pierwszy vertical slice (osobny program, nie GF-M19).

Guardrails (tor gicleeart): no Shopify mutation; no deploy; no live-theme writer; no automatic data migration; no ZIP generation without explicit instruction; no force-push.

#### HISTORICAL / SUPERSEDED — Runtime Foundation checkpoint 2026-07-13 (pre-PR #44–#46)

**Superseded by:** § Runtime-write Inventory Closure — COMPLETED (2026-07-13) poniżej.

#### Runtime Foundation / Repository Safety — checkpoint 2026-07-13

Merged stages (zamknięte):

- **PR #39** — CI Tcl/Tk runtime integrity (`windows-2022`, direct Tcl/Tk, no Tk retry, blocking GUI smoke + warm-up)
- **PR #38** — Description mark store (inventory 24→17)
- **PR #41** — Tytuły AI draft store (17→15)
- **PR #42** — Social Media cycle directories (15→13)
- **PR #43** — Kolaż Export Safety (13→12)

Latest verified Stage 2 baseline (HISTORICAL run reference): `29236997354` — Hermetic 48 passed; Tk GUI 6; warm-up 1; Full 1739 passed, 1 skipped; inventory 12; parse errors 0; scanned 696.

Remaining runtime-write inventory (12):

| Moduł | Findings | Klasyfikacja |
|-------|----------|--------------|
| KPiR | 8 | verified false positives — do not re-migrate |
| Karuzela | 2 | intentional Shopify theme writers — osobny Writer Safety |
| Print Optimize | 2 | user workspace — **NEXT PRIMARY** |

**NEXT PRIMARY (tor gicleeart / Runtime Foundation):** Print Optimize Workspace Safety  
- default `test_photos` i `ww_pairs` poza checkout  
- zachować user-selected paths  
- brak auto migracji/kasowania/nadpisywania  
- zachować GUI i CLI  
- focused tests; expected inventory delta: **12 → 10**  
Verified at: 2026-07-13 (master SHA potwierdzony `git ls-remote origin master`)

#### Runtime-write Inventory Closure — COMPLETED (2026-07-13)

**Status podtoru:** COMPLETED  
**runtime-write inventory:** `0` (parse errors: 0, scanned Python files: 696)  
**Delta inventory:** 12 → 10 → 8 → 0

**Zamknięte podzadania:**

- **Print Optimize Workspace Safety** — PR #44, merge `468fd381b708ee2c01832ac9b7b6695438c3e7fc`, head `2c1f38725de078aeac1666163a3f57f230465c22`, CI `29264514706` / run #221, Hermetic 48, Tk GUI 6, warm-up 1, Full 1747 passed / 1 skipped, inventory 12→10
- **Karuzela Writer Safety** — PR #45, merge `9933b83b901eee5026fbaab87adb9e67ef8cfe8a`, head `1e854ce0135ef39fd6052a4a6fe2a75352b4e964`, CI `29265629361` / run #223, Hermetic 48, Tk GUI 6, warm-up 1, Full 1759 passed / 1 skipped, inventory 10→8
- **KPiR Store Resolver Clarity** — PR #46, merge/master `c3cfe2efdee0de772415d905c5ca878e6d682b1d`, head `bbb0d17d4537de08a52b60e3936ef2ccc44f8ada`, CI `29266589571` / run #225, Hermetic 48, Tk GUI 6, warm-up 1, Full 1765 passed / 1 skipped, JUnit 1766 tests / 0 failures / 0 errors / 1 skipped, inventory 8→0

**Final validation for Runtime-write Inventory Closure — run #225:** dowód zamknięcia podtoru PR #46; **nie** koniec całego programu Stage 2 CI.

**GF-M1 — Pure View Contracts Extraction — COMPLETED (2026-07-13):**

- **PR #47** — merge SHA / aktualny master: `36d66b451596f233dc11b03e0c1ecdb9868940c6`
- base przed etapem: `c3cfe2efdee0de772415d905c5ca878e6d682b1d`
- historyczny finalny head przed merge: branch `gpt-work/gicleeframe-modularization-m1` @ `0f0b7bfc4f58cadb4862f632960c070363a2d588`
- CI run `29269940375` / run #227 — Hermetic 48, Tk GUI 6, warm-up 1, Full 1784 passed / 1 skipped, JUnit 1785 tests / 0 failures / 0 errors / 1 skipped, inventory 0, parse errors 0, scanned 697 Python files
- zakres: `PageContextRowSpec`, `SectionVisualCacheEntry`, `_ellipsize`, `_section_kind_copy` przeniesione do `cursor-api/giclee_app/ui/gicleeframe_view_models.py`; re-eksporty z `gicleeframe_view.py` zachowane; bez zmian UI, layoutu, timingów, performance, RAM-only workflow

**NEXT PRIMARY:** GF-M2 — GICLÉE FRAME Stateless UI Primitives Extraction (planowany discovery przed implementacją; nie rozpoczęty branch/PR).

**Po GF-M2 (plan):** dalsza modularizacja GICLÉE FRAME → Launcher composition → Shopify theme modularization → repo/documentation consolidation.

**Nadal otwarte (nie zamknięte tym podtorem):** szerszy ETAP 1 Repository Safety (m.in. finalny lokalny dry-run, zatwierdzona kopia danych, SHA źródło–cel, usunięcie zaakceptowanych runtime paths z trackingu, `.gitignore`, zero prohibited paths w `git ls-files`); szerszy ETAP 3A (AppPaths, ThemeRootResolver, TaskRunner, OperationResult, SafeFileTransaction, wspólny audit log); Theme Page Editor / WS-1.3 (osobny tor partial); szerszy ETAP 3C (launcher state, studio state, logi, cache, backupy, konfiguracja użytkownika).

Guardrails (tor gicleeart): no Shopify mutation; no deploy; no live-theme writer; no automatic data migration; no ZIP generation without explicit instruction; no force-push.

**Merge authorization (stała autoryzacja użytkownika):** działa wyłącznie po finalnym review, odczycie artifactów, potwierdzeniu dokładnego head SHA, `behind_by: 0`, sprawdzeniu changed files, braku nierozwiązanych review threads i zielonych wymaganych jobów. **Nie oznacza zgody na:** deploy, Shopify mutation, automatyczną migrację, force-push, history rewrite, generowanie ZIP-a.

### gicleeapp (`eagleblastmusic-lgtm/gicleeapp`)

Default branch: `main`  
Current SHA: `294071efe832f2563dc64502412a75ada44246aa`  
Open PRs: nie zweryfikowano przez connector w tej sesji  
Role: kanoniczne repo aplikacji GicleeApp / cursor-api; push przez UI „Push GicleeApp do GitHub”  
Verified at: 2026-07-13

### gicleeart-gpt (`eagleblastmusic-lgtm/gicleeart-gpt`)

Default branch: `main`  
Current SHA: `13dd18beef4e1e0a5085769369430ef89e0ec6ad`  
Snapshot date: nieznana z tej sesji — traktuj jako working-tree mirror, nie live Shopify  
**Warning:** snapshot is not live Shopify production.  
Verified at: 2026-07-13 (`git ls-remote gpt main`)

### giclee-viewer (`eagleblastmusic-lgtm/giclee-viewer`)

Default branch: `main` (zakładane)  
Current SHA: **nie zweryfikowano w tej sesji** — ostatni znany lokalnie: `26446ce487d6fe1a511c7c137215834c78b6849f`  
Current completed stage: GV-7 (historycznie)  
Next verified stage: GV-8 Similarity / Variants / Pairing — **wymaga weryfikacji GitHub**  
Verified at: pending connector

### GicleeAppStudio_2 (`eagleblastmusic-lgtm/GicleeAppStudio_2`)

Default branch: `main` (zakładane)  
Current SHA: **nie zweryfikowano w tej sesji**  
Current implementation stage: sprawdź repo — może wyprzedzać opis „future only” w starszych sekcjach poniżej  
Verified at: pending connector

---

## Knowledge pack integration (integracjagpt)

**Status (2026-07-14):** `integracjagpt` — migracja do paczki **v40** (47 plików).

- ZIP: `giclee_cursor_architect_knowledge_v40.zip` (**47 plików**)
- Manifest: `CLEAN_PACK_V40_ACTIVE_FILES` w `zip_knowledge.py`
- Przycisk **„Skopiuj .zip”** w Oknie rozmowy generuje paczkę v40.

v39 pozostaje archiwum na dysku — nie aktywny manifest.

---

## HISTORICAL — Known integration mismatch

**Status: HISTORICAL / RESOLVED — 2026-07-13**

Wcześniej lokalne pliki były v39, a `integracjagpt` pakiował v38. Po aktualizacji kodu integracji (2026-07-13) oba są v39; manifest i ZIP zawierają 46 plików Knowledge.

---

## HISTORICAL / SUPERSEDED — auto-sync GicleeApp 2026-07-11

Poniższy blok zastąpiony przez § Current repository state (2026-07-13). Zachowany dla historii auto-sync Push GicleeApp.

<!-- gpt-starter:gicleeapp-push:start -->
GicleeApp Studio v1.54.3 (Writer Safety clean worktree) · GitHub gicleeapp v1.54.2

GitHub / aktualna wersja aplikacji (`eagleblastmusic-lgtm/gicleeapp`):
v1.54.2 — zgodnie z `cursor-api/giclee_app/__init__.py` i `cursor-api/package.json` w ostatnim pushu
Ostatni push GicleeApp: `294071e` na `main` (2026-07-11 17:25 UTC) — Refresh GicleeApp repository snapshot

Monorepo origin/master (projekt / docs):
3ccbd19 feat(home-flow): add direct navigation and bounded structure writer

Writer Safety — czysty worktree (osobny od mieszanego `C:\Strona\pusty`):
- worktree: `C:\Strona\pusty-ws12-clean`
- branch: `local/writer-safety-ws12-clean`
- accepted master checkpoint / baza prac: `3ccbd19ebe77b4aadf9403e271d821c3dd28bf2e`
- WS-1.2: `d7790d0086d785cf8c1eef08094563701d0f4fda`
- WS-1.3: `1364aea` — feat(writer-safety): lock window saves and apply sources (lokalny, **nie wypchnięty**)
- working tree po commicie WS-1.3: **CLEAN**
- wersja walidacji WS-1.3: **v1.54.3**

Previous checkpoint:
46fc718 feat(studio): add GICLÉE FRAME page inventory RAM editor (v1.40.0)

Branch status:
- **GitHub gicleeapp:** v1.54.2 / `main` @ `294071e` (auto-sync po Push GicleeApp, 2026-07-11 17:25 UTC)
- **monorepo origin/master:** `3ccbd19` — feat(home-flow): add direct navigation and bounded structure writer
- **Writer Safety clean worktree:** `local/writer-safety-ws12-clean` @ `1364aea` — lokalny commit **nie na GitHub**; working tree **CLEAN**
- **oryginalny worktree** `C:\Strona\pusty`: oddzielny, zawiera inne niezwiązane zmiany; **nie** traktować `audit/submenu-homeflow-20260711-1622` jako źródła Writer Safety

GPT starter files:
checkpoint refresh Writer Safety WS-1.3 (2026-07-11); GitHub gicleeapp nadal `294071e` v1.54.2; paczka v38; źródło = ten folder, nie ZIP

Recent context:
- **GitHub gicleeapp:** v1.54.2 / `main` @ `294071e` — auto-sync po Push GicleeApp (bez pushu WS-1.3)
- **Writer Safety WS-1…WS-1.3:** DONE / TESTED LOCALLY w czystym worktree; szczegóły § Writer Safety
- **Draft PR #1** (`gpt-work/writer-safety-ws1-clean` @ `492e516`) — OPEN / DRAFT / UNMERGED; blob SHA 6 plików WS-1.3 = lokalny `1364aea`
- GICLÉE FRAME™ F2.1: closed + pushed (historycznie v1.40.1 / `4647c1b`; aktualna wersja aplikacji na GitHub jest nowsza)
- Local runtime/untracked still outside commit and remote (working tree hygiene pending)
<!-- gpt-starter:gicleeapp-push:end -->


## Manual checkpoint — 2026-07-11

### Launcher GicleeApp — zaakceptowany lokalnie i wypchnięty w monorepo

Commit `2dde9e4` (`master` = `origin/master`) obejmuje zaakceptowany zakres launchera:
- nawigacja kategoriami → kafelki komponentów,
- menu **Opcje** (Token Setup, stan sesji, układ kafelków, skróty),
- konfigurowalne skróty: litery, cyfry, F1–F12,
- drag & drop kolejności kategorii i kafelków,
- ręcznie potwierdzone działanie skrótów na Windows.

Decyzja architektoniczna: skróty launchera na Windows celowo korzystają z pollingu WinAPI `user32.GetAsyncKeyState`, ponieważ `TkinterDnD.Tk` nie dostarczał niezawodnie zdarzeń przez `bind`, `bind_all` ani własne bindtagi. Skróty są aktywne tylko, gdy GicleeApp jest oknem foreground. **Nie zastępuj tego zwykłym bindingiem Tk bez realnego testu regresji Windows + TkinterDnD.**

Lokalny stan użytkownika — nie importować ani nie commitować przypadkowo:
- `cursor-api/giclee_app/data/launcher_shortcuts.json`
- `cursor-api/giclee_app/data/launcher_layout.json`

### FAQ — integracja efektów grafiki zastosowana lokalnie, walidacja pending

W working tree są już lokalnie zastosowane zmiany cross-repo dla Hero FAQ:
- `TemplateZone.image_effect_selector`,
- eksport zaufanego `targetSelector` do `assets/faq-section-effects.js`,
- runtime wybierający konkretny kontener grafiki Hero,
- selektywne ładowanie assetów efektów na szablonie FAQ,
- rozdzielenie transformacji: hover skaluje kontener, parallax przesuwa wewnętrzny obraz,
- test `cursor-api/tests/test_faq_hero_image_effect_linking.py`.

Status: **nie oznaczać jako closed/pushed**, dopóki nie przejdą testy Python, `compileall`, `git diff --check` i ręczny podgląd `/pages/faq`. Aktualny working tree zawiera również `assets/faq-section-effects.js` oraz lokalne dane wariantu FAQ.

### Notatnik — wiedza z ręcznie zaakceptowanego workflow

Ręcznie potwierdzono działanie: trwałej kolejności notatek per rozdział, sterowania kolejnością, dwukliku dla folderu/nazwy notatki oraz wklejania i wyświetlania obrazów ze schowka. Commit `a61c0f4` pozostaje historycznym revertem branch-only, ale aktualny snapshot `gicleeapp/main` @ `9342f5b` ponownie zawiera bieżący kod aplikacji. Przed kolejną zmianą nadal sprawdź rzeczywisty lokalny kod i testy — nie używaj starego revertu jako opisu obecnego `main`.

### Bieżący working tree — ochrona

Pliki runtime/config i lokalny stan użytkownika mogą pozostawać poza commitem. **Nie używać `reset`, `clean`, szerokiego `restore -- cursor-api`, `git add .` ani importu całego brancha.** Każdy import/rollback musi podawać dokładną listę plików. GICLÉE HOME FLOW / Pre-Hero nie jest już „nierozliczonym dirty work”: fundament v1.51.0 został wdrożony, wypchnięty i ręcznie zaakceptowany; dalsze zmiany mają rozwijać ten checkpoint, a nie odtwarzać jego podstawy.

### GICLÉE HOME FLOW — zaakceptowana architektura v1.51.0

Kanoniczna oś strony głównej:
- `GH-00` Pre-Hero — Od ekranu do materii
  - `GH-T01` Portal i tekst (`phase:portal`)
  - `GH-T02` Wjazd Hero (`phase:hero-rise`)
- `GH-01` Hero — Kolaż pracowni
  - `GH-T03` Postój Hero (`phase:hero-hold`)
  - `GH-T04` Decyzja o dźwięku (`phase:sound-consent`)
  - `GH-T05` Pozioma kurtyna Hero → Giclée Art (`phase:horizontal-curtain`)
- `GH-02` Giclée Art — Intro marki
  - `GH-T06` Postój sekcji (`phase:intro-hold`)
- `GH-03` Odtwarzanie dzieł
- `GH-04` Autorska korekcja kolorystyczna
- `GH-05` Potencjał ukryty w zdjęciu
- `GH-06` Zobacz różnicę
- `GH-07` Powiadomienie strony głównej

Trwałe zasady:
- kody `GH-xx` i `GH-Txx` są wyliczane z kolejności; logika i konfiguracja używają stabilnych ID `section:*` / `phase:*`,
- nazwy sekcji i faz można edytować per wariant bez zmiany technicznych ID,
- sekcje i fazy są pełnoprawnymi elementami jednego `Treeview`; oba typy otwierają edytor w tym samym prawym panelu,
- powrót faza → sekcja wywołuje bezpośredni renderer `_show_zone`; nie steruj panelem przez `event_generate` na ukrytym `Listboxie`,
- przejście Hero → Intro odsłania prawdziwą sekcję Shopify live; nie twórz klona z usuniętymi skryptami/ID,
- efekty sekcji Giclée Art startują od pierwszej klatki otwierania kurtyny i nie restartują się przy hand-offie,
- generator Pre-Hero zna pełny zestaw assetów i blokuje zapis przy brakach,
- zgoda na dźwięk używa opcjonalnego ambientu z Shopify CDN; lokalny fallback filmu Pre-Hero to `assets/giclee-home-prehero-scrub.mp4`,
- obecna baza jest zaakceptowana; następny produktowy etap może rozszerzać wstawianie/przesuwanie sekcji i faz, ale nie powinien przepisywać działającej nawigacji od zera.

Completed:
- Background Builder local v1: frozen
- Administracja strony rebuild strategy: done
- Katalog rebuild plan: done
- Katalog F1 read-only shell: done
- Katalog F2 bounded data map: done
- Katalog local planning layer F3+F4: done (draft state, dry-run, readiness, UI planu zmian)
- Push GicleeApp hygiene: done
- **GICLÉE HOME FLOW v1.51.0:** sekcje + fazy w Treeview, edycja faz inline, automatyczna numeracja, pełny generator Pre-Hero, live Intro, ambient i bezpośrednia nawigacja do renderera sekcji — implemented + pushed + ręcznie zaakceptowane.
- **GicleeApp push workflow:** użytkownik zwykle pushuje lokalną aplikację przyciskiem **„Push GicleeApp do GitHub”** w UI GicleeApp (nie ręcznie przez terminal): `cursor-api` → staging → `eagleblastmusic-lgtm/gicleeapp`; dry-run → audyt → potwierdzenie → commit + push na `main`. Nie dotyczy motywu Shopify, `gicleeart-gpt`, ZIP-a wiedzy ani plików startowych GPT.
- GICLÉE FRAME™ F2 page inventory + RAM editor foundation (v1.40.0): done
- GICLÉE FRAME™ F2.1 page editor workflow (v1.40.1): done
  - multi-variant RAM, type-aware editor, settings/reorder as RAM patches
  - trigger sekcji w nagłówku edytora, popup + drag reorder
  - dry-run, readiness accordion, F1 brand collapsed
- Studio Page Component Editor Pattern: documented (`gicleeframe-planning.md` §7, `admin-components-strategy.md`)
- **Performance Agent** (PA-1A–PA-3B): done lokalnie — guided audit + read-only analysis CLI w `cursor-api/tools/performance_agent/` (testy 162 passed; szczegóły § Performance Agent + GF-P0.1)
- **GF-P0.1** (Details CTA Timing Anchor / Baseline Hygiene): done w kodzie lokalnym; runtime validation pending (wymaga świeżego `--run`)

## GicleeApp Implemented Solutions Index

- Istnieje: `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`
- Przed nowym komponentem, helperem lub mechanizmem GicleeApp Cursor **musi** go sprawdzić (wzorce `_shared`, rejestracja, storage, logi, dialogi, DnD, operacje na plikach, guardrails)
- Po dodaniu reużywalnego komponentu/helpera/mechanizmu Cursor **musi** zaktualizować indeks — **nie** przy kosmetyce, tylko przy nowym wzorcu do ponownego użycia
- Writer Safety: `cursor-api/docs/theme-page-editor-writer-safety.md` + moduł `cursor-api/Komponenty/_shared/theme_page_editor/writer_safety_concurrency_fix.py` (WS-1.3)

Not started:
- GICLÉE FRAME™ F3 — lokalny zapis draftów RAM do pliku
- GICLÉE FRAME™ F4 — bounded writer + backup/undo
- F5 / F5.5 preview quality / Shopify sync-deploy
- Katalog writer
- Katalog Shopify integration
- Katalog migration

## HISTORICAL / SUPERSEDED — Next recommended 2026-07-11

**Superseded by:** § `gicleeart` → Runtime-write Inventory Closure COMPLETED + GF-M1 COMPLETED + GF-M2 NEXT PRIMARY (2026-07-13). Poniższe tory produktowe mogą nadal obowiązywać **osobno** — nie jako „current primary” dla toru GICLÉE FRAME modularization.

Next recommended (historyczne):

**Kontynuuj z aktualnego checkpointu — bez szerokiego cleanupu:**
1. FAQ Hero image effects: jeżeli nie ma nowszego potwierdzenia, wykonaj test celowany + `compileall` + `git diff --check` + ręczny podgląd live.
2. GICLÉE HOME FLOW: traktuj v1.51.0 jako zaakceptowaną bazę; kolejny etap planuj wyłącznie jako rozszerzenie (np. bezpieczne wstawianie/przesuwanie elementów), nie ponowną implementację fundamentu.
3. Każdy kolejny commit/rollback ma być jawny i ograniczony do dokładnej listy plików.

**Studio Performance — GICLÉE FRAME 6G.5:** **PASS / checkpoint**. Nie startować kolejnej szerokiej optymalizacji bez konkretnego objawu UX i nowych metryk.

**GICLÉE FRAME™ F3 / writer / Shopify sync-deploy:** nadal nie startować bez osobnej decyzji.

**Writer Safety — publikacja czystego ciągu:** `d7790d0` → `1364aea` na osobnym zdalnym branchu + podpięcie do draft PR **nie wykonane** — wymaga osobnej, wyraźnej zgody użytkownika.

---

## Writer Safety — Theme Page Editor (checkpoint WS-1.3 — 2026-07-11)

**Tor:** `gicleeart` / Theme Page Editor — **osobny od Runtime Foundation**. Nie jest „next primary” dla toru Print Optimize.

**Status:** WS-1, WS-1.1, WS-1.2, WS-1.3 — **DONE / TESTED LOCALLY** w czystym worktree.

**Czysty worktree:** `C:\Strona\pusty-ws12-clean` · branch `local/writer-safety-ws12-clean` · working tree **CLEAN** po `1364aea`.

**Baza prac:** `3ccbd19` (accepted master checkpoint).

| Etap | Commit | Opis |
|------|--------|------|
| WS-1 | (w ciągu clean) | Rozdzielenie zapisu wariantu od zapisu motywu |
| WS-1.1 | (w ciągu clean) | Naprawa kontekstu deferred closure dla przycisków wielu okien |
| WS-1.2 | `d7790d0` | Delta-only variant save i Apply |
| WS-1.3 | `1364aea` | Izolacja zapisów między oknami i blokada źródeł Apply |

**WS-1.3 — główne zabezpieczenia:**
- każde okno: własny SHA-256 wariantu z chwili wczytania; nieaktualne okno blokowane przy zapisie,
- podgląd Apply zamraża bajty i hashe bazy oraz wariantu,
- przed i po Apply ponowna weryfikacja źródeł; przy zmianie źródła — rollback celów i bazy,
- baza otrzymuje dokładne bajty wariantu z podglądu, nie nowszą zawartość pliku.

**Nowe pliki WS-1.3:**
- `cursor-api/Komponenty/_shared/theme_page_editor/writer_safety_concurrency_fix.py`
- `cursor-api/tests/test_theme_page_editor_writer_safety_concurrency_fix.py`

**Walidacja WS-1.3:** 20 passed · compileall PASS · `git diff --check` PASS · porównanie 6 plików z draft PR head `492e516` — blob SHA identyczne.

**Manualne testy:** dwa okna (stale save zablokowany, gf3=0.6); stale Apply preview (blokada po zewnętrznej zmianie wariantu); cleanup gf3 — motyw/gf1/gf2 bez zmian.

**Writer Safety gwarantuje obecnie:**
- Save zapisuje wyłącznie aktywny wariant; nie zapisuje motywu ani innych wariantów,
- nieaktualne okno nie nadpisuje nowszego zapisu,
- Apply stosuje wyłącznie zarządzaną deltę; nie używa zmienionych źródeł po preview,
- Apply wycofuje zapisane cele przy wykryciu zmiany źródła; brak automatycznego deployu.

**Zdalny draft PR** (`eagleblastmusic-lgtm/gicleeart`):
- **#1** — feat(writer-safety): per-window save and source-locked apply (v1.54.3)
- branch: `gpt-work/writer-safety-ws1-clean` · head: `492e516427910c9760f9cd5b2ca00df0e9e397fa`
- stan: OPEN · DRAFT · UNMERGED

**Nie wykonano:** push lokalnego `1364aea`, merge PR, deploy, zapis do Shopify.

**Oryginalny worktree** `C:\Strona\pusty` pozostaje oddzielny z niezwiązanymi zmianami. Nie traktować `audit/submenu-homeflow-20260711-1622` jako źródła merge/push Writer Safety.

**Next (wymaga osobnej zgody):** publikacja czystego ciągu `d7790d0` → `1364aea` na osobnym zdalnym branchu; podpięcie do draft PR lub nowy draft PR.

---

## GicleeApp Studio Performance (checkpoint 2026-07-07)

**Kontekst:** optymalizacja wydajności GicleeApp Studio. Fazy **5F–6G.2** i główna nitka **6G.5** (GICLÉE FRAME) przeprowadzone lokalnie w Cursorze (working tree może wyprzedzać GitHub connector).

**Źródło prawdy dla diagnozy:** bundle z **Performance Agent** (`report.md`, `summary.json`) — preferuj nad surowym logiem. Gdy brak bundle: `cursor-api/giclee_app/logs/studio_perf.log`. **Zawsze od metryk, nie od hipotez po UI.**

### Zasada diagnostyki (obowiązkowa)

Jeśli użytkownik pisze „dalej muli”, „wolno się otwiera”, „sekcje przycinają” — GPT **najpierw prosi o**:
1. najnowszy bundle Performance Agent (`report.md` / `summary.json` z `cursor-api/reports/performance/**`), **albo**
2. najnowszy `giclee_app/logs/studio_perf.log`, **albo**
3. raport Cursora z agregacją ostatniej sesji.

**Nie zgadywać po objawie. Najpierw metryki, potem kod.**

Jeśli GitHub connector widzi starszy stan niż lokalny Cursor — **lokalny working tree / log użytkownika wygrywa** dla bieżącej diagnozy wydajności.

### Status faz (done lokalnie) — skrót 5F–6G.2

**5F / 5G — Hub:** batching, hover/auto hydration OFF; hub nie jest głównym bottleneckiem.

**6A–6F:** cold views, GF progressive boot (~2.8 s → ~0.6–0.7 s), progressive `page_context`, lazy divider groups, lightweight setting rows, responsive section selection.

**6G.1–6G.2:** route shell, freeze reduction; po 6G.2 GF `open` ~31 ms, `visible_ready` ~179 ms; Asset Lab shell batches ~13–18 ms.

---

## GicleeApp / GICLÉE FRAME performance checkpoint

Główna nitka performance **6G.5** jest zamknięta jako **PASS / checkpoint**.

### Zrealizowane fazy

- **6G.5-K** — Sections Column Early Lane.
- **6G.5-L** — Split sections column.
- **6G.5-L.1** — Extras layout fix.
- **6G.5-M** — Defer init refresh behind early lane.
- **6G.5-N.DIAG** — Hub mount lane diagnostics.
- **6G.5-N.1** — `GicleeFrameView.uses_async_first_paint=True`, launcher `update_idletasks` skipped.
- **6G.5-O** — repeatable smoke baseline.
- **6G.5-P.DIAG** — `CTkScrollableFrame` constructor identified as sections shell bottleneck.
- **6G.5-Q.SPIKE** — static lane before scroll upgrade.
- **6G.5-Q.1** — scroll upgrade delayed until after perceived ready.
- **6G.5-R.DIAG** — perceived ready gate attribution; control gate identified as last gate.
- **6G.5-S.DIAG** — section click interaction latency diagnostics.
- **6G.5-S.1** — selection stability during `init_refresh.light` + editor identity prewarm.
- **6G.5-S.2A** — editor rows/form shell warmup.
- **6G.5-S.2A.VERIFY** — click UX cause matrix.
- **6G.5-S.2B** — selection priority lane / populate enter queue reduction.

### Najważniejsze wyniki

- Hub → GICLÉE FRAME mount queue improved; launcher `update_idletasks` is skipped for `GicleeFrameView`.
- `early_lane_enter.queue_latency_ms` stable around ~35 ms.
- Static lane shows real first rows early; `first_visible_ready` moved into roughly ~175–250 ms range depending on run.
- `CTkScrollableFrame` cost is shifted to scroll upgrade after first/perceived readiness.
- `ensure_identity` cold cost was removed from first click via identity prewarm.
- `ensure_rows` cold cost was reduced via rows prewarm.
- Section click latency improved significantly in **S.2B**:
  - `click → populate_enter` median around ~17.5 ms,
  - max around ~27.3 ms in verify run,
  - divider `populate_done` around ~55 ms,
  - section_legacy `populate_done` around ~59 ms,
  - media_section `populate_done` around ~56 ms,
  - highlight remains around ~8–18 ms.
- Rapid clicking works; latest generation wins and stale jobs are cancelled/ignored.
- Page context remains a secondary **P2** topic: it can still take roughly ~200–430 ms cumulative, but it is not the main blocker for the immediate click response.
- Perceived ready can still be influenced by control gate / control deferred chain, but this is no longer the primary UX blocker for clicking sections.

### Current recommendation

- **STOP / checkpoint** the main 6G.5 performance thread.
- Do not start another broad optimization unless manual UX still shows a clear problem.
- Optional later topic: page context polish / perceived-ready semantics / control late work, only if user still feels lag after real manual use.
- Optional small hygiene: update analyzer scenario C criteria so immediate basic populate is not incorrectly reported as FAIL.

### Post-checkpoint UX follow-up

6G.5-S.2B remains a technical PASS / checkpoint for the main GICLÉE FRAME performance thread.

However, the user reported after the checkpoint that real manual interaction still does not feel fully ideal when clicking sections. This does not reopen the whole 6G.5 performance track. Future work should be symptom-driven and scoped narrowly.

Next optional follow-up:
- 6G.5-T.UX — Manual Friction Capture
  - run GICLÉE FRAME with `GICLEE_STUDIO_PERF=1`,
  - manually test early click, normal section clicks, rapid section clicks, and visual stability,
  - identify the exact UX symptom before proposing code changes.

Do not start broad optimization without a concrete manual UX symptom and perf log.
Likely future micro-topics, only if confirmed by manual UX:
- page context polish,
- static lane / scroll upgrade flicker polish,
- selection visual stability,
- preview repaint polish,
- early-click race validation.

### GF-P0.1 — instrumentation follow-up (nie reopen 6G.5)

Lokalnie wdrożono **GF-P0.1**: details CTA loguje latencję od request/CTA (`since_request_ms`, `since_details_cta_ms`), nie od wieku widoku (`since_enter_ms`). To wąski follow-up instrumentation — **nie** ponowne otwarcie nitki 6G.5. Pełna walidacja wymaga **świeżego `--run`** (świadomie odłożone). Stare bundle mogą nadal pokazywać legacy wiersze w `slow_events.csv` — to oczekiwane, nie błąd narzędzia.

### Performance guardrails

- GicleeApp Studio performance = lokalny projekt aplikacji (`gicleeapp`), **nie** Shopify theme.
- Nie ruszać `Komponenty/*`, Shopify sync/deploy, writerów, Save/Zapisz/Zastosuj bez osobnej zgody.
- Nie zmieniać launcher lifecycle bez osobnego scope.
- Nie zmieniać static lane / scroll upgrade bez nowej scoped phase.
- Nie zmieniać DnD behavior bez explicit scope.
- Background Builder local v1 pozostaje frozen.
- Cursor aktualizuje tylko źródła w `Pliki startowe dla GPT` — **nie generuje ZIP-a** (ZIP = Okno rozmowy u użytkownika).

Technical backlog (only after separate acceptance):
- Katalog bounded writer / save layer
- zero Shopify / sync / deploy
- zero Save / Zapisz / Zastosuj without explicit approval
- do not mutate Komponenty/* runtime data from Studio panels

Important guardrails:
- Knowledge pack source folder: `C:\Strona\pusty\Pliki startowe dla GPT` — **Cursor edytuje tylko pliki źródłowe `.md` / `.txt` w tym folderze**
- **Cursor NIE generuje ZIP-a wiedzy** — bez osobnego, wyraźnego polecenia użytkownika
- ZIP traktuj jako **aktualny snapshot wiedzy** załączony do rozmowy; ZIP wiedzy (`giclee_cursor_architect_knowledge_v39.zip`) generuje **automatycznie program użytkownika** przy wysyłce paczki przez **Okno rozmowy** (Integracja z GPT); **źródłem edycji dla Cursora** są lokalne pliki w `Pliki startowe dla GPT`
- Cursor nie uruchamia: `build_starter_knowledge_zip()`, GUI **Skopiuj .zip**, żadnego ręcznego generatora ZIP
- GICLÉE FRAME F2.1: RAM-only — no write_text, no writer, no sync/deploy, no Komponenty/* mutation from panel
- Do not start F3/F4/writer without separate approval
- Do not add Save/Zapisz/Zastosuj without separate approval
- Do not touch Shopify/sync/deploy
- Katalog F2 remains read-only
- tldobio absorbed into Katalog
- Background Builder local v1 = Level 2 reference (frozen)

Reference docs (repo):
- `cursor-api/giclee_app/docs/gicleeframe-planning.md`
- `cursor-api/giclee_app/docs/admin-components-strategy.md` (Giclee Frame = pattern reference)

---

## Performance Agent + GF-P0.1 (checkpoint PA/GF — 2026-07-08)

**Status:** PA-1A…PA-3B **done lokalnie**. GF-P0.1 **done w kodzie**, **bez świeżej walidacji runtime**.  
**Testy:** 162 passed (pakiet PA + powiązane studio perf).  
**Commit / push / ZIP:** brak w tym checkpointcie — nie zakładać bez potwierdzenia użytkownika.

**Lokalizacja:** `cursor-api/tools/performance_agent/` (narzędzie diagnostyczne; nie mieszać z optymalizacją runtime Studio 6G.5).  
**Canonical docs:** `tools/performance_agent/README.md` (GitHub) = `cursor-api/tools/performance_agent/README.md` (local). Run from `cursor-api/`.

### Mapa faz (done)

| Faza | Zakres | Status |
|------|--------|--------|
| PA-1A–PA-1C.2 | parse-only, wizard, `--run`, coverage, human-readable scenarios | done |
| PA-1D | `--latest`, `--list-reports` (read-only index) | done |
| PA-1E–PA-1H | ChatGPT copy, health gate | done |
| PA-1I | `--doctor`, `--prepare-chatgpt-latest`, `--open-latest` | done |
| PA-2A | `--analyze-*`, `--compare-*` | done |
| PA-2B | `--hotspots-*`, `--timeline-*`, `--cursor-prompt-*` | done |
| PA-2C | `--history`, `--trend-latest`, `--baseline-candidate` | done |
| PA-3A | `--coverage-*`, `--run-playbook`, `--scenario-checklist` | done |
| PA-3B | semantics (`since_enter_ms` filter, evidence tiers) | done |
| GF-P0.1 | details CTA: `since_request_ms` / `since_details_cta_ms` | done locally; fresh run pending |

### Operator CLI — read-only analysis (preferowane w sesji)

```powershell
python -m tools.performance_agent --doctor
python -m tools.performance_agent --prepare-chatgpt-latest
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --compare-latest
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --timeline-latest
python -m tools.performance_agent --cursor-prompt-latest
python -m tools.performance_agent --history
python -m tools.performance_agent --trend-latest
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --run-playbook
python -m tools.performance_agent --scenario-checklist
```

**Generowanie nowego bundle** (gdy potrzebny świeży run): `--parse-only` · `--manual` · `--run`.

**Rekomendowany flow:** `--doctor` → `--coverage-latest` / `--analyze-latest` → `--hotspots-latest` / `--timeline-latest` → `--cursor-prompt-latest`.

### Zasady interpretacji (nie traktować jako bug)

| Sygnał | Znaczenie |
|--------|-----------|
| `1/9` coverage | **Weak evidence** — nie dowód poprawy/regresji wydajności |
| `9/9` + `early_event_seen` | **Reviewable / READY** z caveat (np. `dashboard_cold`) — nie alarm jak 1/9 |
| `since_enter_ms` | Wiek widoku — **nie** latencja kliknięcia |
| details CTA | Prawdziwe pola: **`since_request_ms`**, **`since_details_cta_ms`** (GF-P0.1) |
| Stary `slow_events.csv` | Legacy wiersze (`since_click_ms`, `cancelled`) w starych bundle — **oczekiwane** przy `--hotspots-latest` |
| `SCENARIO_LOG_NOT_CONFIRMED` | Jakość danych sesji — **nie** automatycznie regresja runtime |

### Baseline bundles (GF)

- **Dobry pierwszy GF baseline:** `20260707-214246_giclee_studio`
- **Nie używać jako GF baseline:** `20260707-160215_giclee_studio` — nie mierzył `studio.gicleeframe.*`
- Automatyczny wybór: `--baseline-candidate`; ręczne porównanie: `--compare-reports`

### Pending

1. **Świeży `--run`** — walidacja GF-P0.1 w nowym `slow_events.csv` / timeline (świadomie odłożone)
2. **Opcjonalny P1** — `render_section_list` / selection pipeline — **tylko** jeśli potwierdzi świeży baseline; nie startować bez dowodu

### Bundle wyjściowy

`reports/performance/<YYYYMMDD-HHMMSS>_giclee_studio/` — m.in. `report.md`, `summary.json`, `slow_events.csv`, `scenario_timeline.csv`, `raw/studio_perf.log`. Runtime output i log ignorowane przez git.

---

## HISTORICAL / SUPERSEDED — Giclee Viewer — current state (2026-07-08)

**Superseded by:** § Current repository state → `giclee-viewer` (weryfikacja pending). Poniższe szczegóły mogą być nieaktualne — sprawdź GitHub przed pracą.

Repo GitHub:

`eagleblastmusic-lgtm/giclee-viewer`

Repo lokalne:

`C:\Strona\giclee-viewer`

Aktualny HEAD:

`26446ce487d6fe1a511c7c137215834c78b6849f`

Commit:

`feat: add GV-7 creative metadata workspace`

Status:

- working tree clean
- build PASS
- test PASS: 143/143
- brak push
- znane ostrzeżenia: NU1903 dla transitive dependency `SQLitePCLRaw.lib.e_sqlite3`
- metadane kreatywne zapisywane tylko w SQLite
- zero zapisu do oryginalnych obrazów/wideo/EXIF

Zamknięte etapy Giclee Viewer:

- GV-0 — WPF skeleton
- GV-1 — SQLite index foundation
- GV-2 — thumbnail cache and grid
- GV-6.2 — rename execution
- GV-6.2.1 — collections test stability
- GV-6.3 — rename recovery and cleanup
- GV-6.4 — rename UX and audit polish
- GV-7 — Creative Metadata Workspace

GV-7 done:

- schema SQLite v7
- rozwinięta istniejąca tabela `prompts`
- bez nowej tabeli `creative_prompt_records`
- nowe modele:
  - `CreativePromptRecord`
  - `CreativePromptType`
  - `CreativeMetadataSummary`
  - `CreativeMetadataRules`
- nowe repozytorium:
  - `CreativeMetadataRepository`
- nowy ViewModel:
  - `CreativeMetadataViewModel`
  - `CreativePromptRecordViewModel`
- panel `Creative Metadata`
- pola:
  - Main prompt
  - Negative prompt
  - Video prompt
  - Tool
  - Model
  - Settings
  - Notes
  - Last updated
- Save metadata:
  - pierwszy zapis tworzy `version=1`
  - `record_type=creative`
  - `is_primary=1`
- Add version:
  - nowa wersja z `is_primary=0`
- Set as primary
- Copy Main / Negative / Video / All
- filtry:
  - Has prompt
  - Prompt contains
  - Tool
  - Model
- badge `PROMPT` na kafelkach
- badge ładowany batchowo, zero query per tile
- po save lokalny refresh jednego kafelka
- `_loadGeneration` i `_loadedFileId` chronią przed zapisem do złego pliku przy szybkim klikaniu
- rename module nietknięty
- metadane zachowane przez `file_id`, więc rename zachowuje prompty

Usunięte / zastąpione:

- `PromptRepository`
- `PromptEditorViewModel`
- stare testy promptów

Nowe / zmienione pliki GV-7:

Core:
- `CreativePromptRecord.cs`
- `CreativePromptType.cs`
- `CreativeMetadataSummary.cs`
- `CreativeMetadataRules.cs`
- `MediaFilter.cs`

Data:
- `DbInitializer.cs`
- `CreativeMetadataRepository.cs`
- `CreativeMetadataFilterSql.cs`
- `SqlLikePattern.cs`
- `MediaFileRepository.cs`
- `CollectionRepository.cs`

UI:
- `CreativeMetadataViewModel.cs`
- `CreativePromptRecordViewModel.cs`
- `MainViewModel.cs`
- `ThumbnailGridViewModel.cs`
- `ThumbnailItemViewModel.cs`

App:
- `MainWindow.xaml`
- `MainWindow.xaml.cs`
- `ThumbnailTile.xaml`

Tests:
- `CreativeMetadataRepositoryTests.cs`
- `CreativeMetadataViewModelTests.cs`
- `SqlLikePatternTests.cs`
- `ViewModelTestHelpers.cs`
- `DbInitializerTests.cs`

Docs:
- `ARCHITECTURE.md`
- `MVP_PLAN.md`
- `PERFORMANCE_RULES.md`
- `README.md`

Następny sugerowany etap Giclee Viewer:

GV-8 — Similarity / Variants / Pairing

Zakres przyszły:
- wykrywanie podobnych obrazów
- warianty tego samego obrazu
- różne rozdzielczości tego samego pliku
- wybór wersji głównej
- ręczne zatwierdzanie par
- powiązanie wariantów z promptami/metadanymi

---

## HISTORICAL / SUPERSEDED — GicleeApp Studio 2.0 — future direction (2026-07-08)

**Superseded by:** § Current repository state → `GicleeAppStudio_2` (weryfikacja pending). Repo `GicleeAppStudio_2` na GitHubie może wyprzedzać opis „future only” poniżej.

GicleeApp Studio 2.0 ma być przyszłym C# / WPF shell dla obecnego workflow Giclée Art.

Założenie architektoniczne:

- C# / WPF: UI, dashboard, moduły, routing, statusy, logi, panele, szybka responsywność
- Python / obecny gicleeapp / cursor-api: workers, generatory, Shopify helpers, GPT ZIP, raporty, Performance Agent, automatyzacje
- komunikacja: command JSON → Python worker → result JSON/report → UI

Nie przepisywać obecnego GicleeApp 1:1.
Nie usuwać obecnych narzędzi Python.
Budować nowy shell obok i podpinać istniejące workers etapami.

Sztywny szablon modułów: `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md` — nie zmieniać nazw, kolejności ani struktury bez wyraźnej decyzji użytkownika.

Pierwszy przyszły etap:

GAS-0 — GicleeApp Studio 2.0 Information Architecture & Shell Plan

Cel GAS-0:

- przeanalizować obecny GicleeApp / cursor-api,
- zaprojektować WPF shell,
- zachować sztywny szablon modułów użytkownika,
- zaproponować dashboard,
- zaproponować worker bridge,
- zaproponować routing,
- zaproponować roadmapę GAS-1/GAS-2/GAS-3,
- bez implementacji i bez przepisywania obecnego GicleeApp.

---

## Programming / Architecture Principles — current direction

Aktualna preferowana architektura dla nowych aplikacji Giclée Art:

```text
C# / WPF
= UI, dashboard, routing, szybka responsywność, MVVM, panele, statusy

Python
= workers, generatory, Shopify helpers, GPT ZIP, raporty, automatyzacje

SQLite / JSON
= lokalny stan, indeks, historia, komunikacja między modułami
```

Nie „Python kontra C#” — oba warstwy współpracują.

1. Dla nowych aplikacji desktopowych preferować **C# / WPF + MVVM**.
   Powód: lepsza responsywność UI, wirtualizacja list, stabilniejsze desktopowe layouty, async/await, dobre testowanie ViewModeli.

2. **Python zostaje ważnym silnikiem narzędziowym.**
   Nie przepisywać działających Pythonowych workerów bez powodu. Python jest dobry do:
   - generowania plików,
   - integracji GPT,
   - Shopify helpers,
   - raportów,
   - automatyzacji,
   - lokalnych narzędzi workflow.

3. **Długie operacje nigdy nie mogą blokować UI.**
   Każda ciężka operacja powinna działać jako:
   - background task,
   - worker process,
   - kolejka,
   - albo async service z CancellationToken.

4. **Local-first.**
   Dane aplikacji trzymać lokalnie:
   - SQLite dla stanu aplikacji,
   - JSON/report files dla wymiany wyników,
   - cache lokalny dla miniatur i artefaktów.
   Nie zapisywać metadanych do oryginalnych plików bez osobnej decyzji użytkownika.

5. **Data safety first.**
   Operacje na prawdziwych plikach muszą mieć:
   - dry-run,
   - walidację,
   - double confirmation,
   - audit,
   - recovery/rollback, jeśli operacja jest destrukcyjna lub częściowo odwracalna.

6. **No per-tile / per-row heavy queries.**
   Dla gridów, miniatur, badge'ów i filtrów preferować batch queries oraz cache. Unikać zapytań DB wykonywanych osobno dla każdego kafelka.

7. **Nie rozdrabniać pracy bez powodu.**
   Małe etapy są dobre tylko przy ryzyku danych, migracji lub operacjach na plikach.
   Dla funkcji produktowych preferować większe, spójne pakiety.

8. **Existing GicleeApp is not a mistake.**
   Obecne Pythonowe GicleeApp traktować jako działający worker/tooling foundation.
   GicleeApp Studio 2.0 ma być nowym WPF shell obok, a nie brutalnym przepisaniem 1:1.

9. **Connector / private repo rule.**
   Dla prywatnych repo używać GitHub connectora, nie publicznych raw URL.

10. **Cursor role.**
    Cursor implementuje lokalnie.
    GPT/assistant projektuje architekturę, reviewuje raporty, wykrywa ryzyka i przygotowuje precyzyjne prompty.

Szczegóły w COMPACT v38 § Programming / Architecture Principles.

---

## Current technical lessons from Giclee Viewer

Giclee Viewer potwierdził, że C# / WPF + SQLite jest dobrym kierunkiem dla nowych lokalnych aplikacji Giclée Art.

Sprawdzone wzorce:
- MVVM z testowalnymi ViewModelami,
- SQLite migracje addytywne i idempotentne,
- batch queries zamiast query per tile,
- background thumbnail generation,
- cache lokalny,
- generation counters dla async loadów,
- dry-run + execution + rollback + audit dla operacji na plikach,
- ViewModel tests bez kruchych Task.Delay,
- oddzielanie UI od worker/service layer.

Te wzorce powinny być traktowane jako baza dla przyszłego GicleeApp Studio 2.0.

Szczegóły w COMPACT v38 § Current technical lessons from Giclee Viewer.

---

## Strategic Direction — Giclée Art Studio OS

Długoterminowy kierunek projektu to budowa lokalnego ekosystemu:

Giclée Art Studio OS

Obecnie składa się / będzie składał z dwóch głównych filarów:

1. Giclee Viewer
   - szybka lokalna biblioteka obrazów/wideo,
   - miniatury,
   - kolekcje,
   - flagi/tagi,
   - creative metadata,
   - prompty,
   - warianty/podobieństwo,
   - preview,
   - selekcja materiałów.

2. GicleeApp Studio 2.0
   - przyszły C# / WPF shell dla workflow Giclée Art,
   - bazujący na obecnym Pythonowym GicleeApp / cursor-api,
   - nie jako przepisanie 1:1, tylko nowy premium desktop shell,
   - Python pozostaje worker/tooling layer.

Giclee Viewer traktować jako praktyczny wzorzec technologiczny dla przyszłego GicleeApp Studio 2.0:
- WPF / MVVM,
- SQLite,
- testowalne ViewModele,
- migracje addytywne,
- batch queries,
- background tasks,
- safety-first workflow,
- lokalny cache,
- brak blokowania UI.

GicleeApp Studio 2.0 ma używać sztywnego szablonu modułów użytkownika z pliku:

`GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`

Nie zmieniać nazw, kolejności ani struktury modułów bez wyraźnej decyzji użytkownika.

Szczegóły w COMPACT v38 § Strategic Direction — Giclée Art Studio OS.

---

## Work Planning Rule

Nie rozdrabniać dalszych prac na zbyt małe mikroetapy.

Małe etapy są uzasadnione tylko przy:
- migracjach bazy,
- operacjach na prawdziwych plikach,
- ryzyku utraty danych,
- rollback/recovery,
- dużych zmianach architektury.

Dla funkcji produktowych preferować większe, spójne pakiety:
- GV-8 Similarity / Variants / Pairing
- GV-9 Preview Workspace
- GV-10 Review Workflow
- GAS-0 GicleeApp Studio 2.0 Architecture Discovery

Szczegóły w COMPACT v38 § Work Planning Rule.

---

## UI / Product Taste Direction

Docelowy styl nowych aplikacji Giclée Art:
- premium,
- spokojny,
- ciemny,
- czytelny,
- studyjny,
- bez chaosu,
- bez przeładowania efektami,
- dużo oddechu,
- logiczne karty,
- jasne statusy,
- estetyka: fine art / museum / creative operations dashboard.

Nie kopiować chaotycznie obecnego UI 1:1.
Zachować użyteczne elementy obecnego GicleeApp Studio, ale GicleeApp Studio 2.0 projektować jako bardziej dojrzały, elegancki i responsywny shell.

Szczegóły w COMPACT v38 § UI / Product Taste Direction.

---

## HISTORICAL / SUPERSEDED — Source of Truth / Decision Memory (2026-07-08)

**Superseded by:** `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v39.md` § Hierarchia źródeł prawdy oraz § Current repository state powyżej.

W nowych sesjach GPT należy traktować poniższe zasady jako obowiązujące:

1. Giclee Viewer i GicleeApp Studio 2.0 to dwa różne projekty.

Giclee Viewer:
- GitHub: `eagleblastmusic-lgtm/giclee-viewer`
- lokalnie: `C:\Strona\giclee-viewer` (osobne od `gicleeapp` / `gicleeart-gpt`)
- C# / WPF / SQLite
- media library, thumbnails, tags, collections, rename, prompts, metadata, future variants/preview

GicleeApp / GicleeApp Studio 2.0:
- obecny workflow bazuje na `C:\Strona\pusty` / `cursor-api`
- obecne GicleeApp to działający Python tooling foundation
- GicleeApp Studio 2.0 ma być przyszłym C# / WPF shell + Python workers

Nie mieszać tych dwóch codebase'ów bez wyraźnego polecenia użytkownika.

2. ZIP = aktualny snapshot wiedzy załączony do rozmowy.

Źródłem edycji dla Cursora są lokalne pliki:

`C:\Strona\pusty\Pliki startowe dla GPT`

Cursor aktualizuje lokalne pliki źródłowe, a ZIP jest generowany z nich automatycznie przez Integrację z GPT.

Cursor nie generuje ZIP-a bez osobnej komendy użytkownika.

3. Sztywny szablon GicleeApp Studio 2.0 jest obecnie decyzją użytkownika.

Plik:

`GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`

zawiera aktualny, sztywny układ modułów.

Nie zmieniać nazw, kolejności ani struktury modułów bez wyraźnej decyzji użytkownika.

4. Nie wracać do dyskusji „Python czy C#” od zera.

Aktualna decyzja strategiczna:
- C# / WPF dla nowych desktopowych shelli i UI,
- Python dla istniejących workerów, automatyzacji, generatorów i narzędzi,
- SQLite / JSON / raporty jako lokalna warstwa stanu i wymiany danych.

5. Nie rozdrabniać roadmapy bez powodu.

Preferować większe pakiety produktowe.

Mikroetapy są dopuszczalne tylko przy:
- ryzyku utraty danych,
- operacjach na realnych plikach,
- migracjach bazy,
- rollback/recovery,
- dużych zmianach architektury.

6. Każda nowa sesja GPT powinna najpierw sprawdzić aktualny checkpoint.

Najważniejsze bieżące checkpointy:
- Giclee Viewer HEAD: `26446ce487d6fe1a511c7c137215834c78b6849f`
- GV-7 Creative Metadata Workspace done
- build PASS
- test PASS: 143/143
- working tree clean
- brak push
- next likely GV stage: GV-8 Similarity / Variants / Pairing
- future GAS stage: GAS-0 GicleeApp Studio 2.0 Information Architecture & Shell Plan

Szczegóły w COMPACT v38 § Source of Truth / Decision Memory.

---

## GPT starter procedural update (2026-07-10)

- Lokalny projekt `C:\Strona\pusty` jest **jednym monorepo**; `cursor-api/` nie jest osobnym lokalnym repozytorium Git.
- Remotes: `origin` → gicleeart · `gpt` → gicleeart-gpt · `gicleeapp` → gicleeapp.
- Uzgodniono **GPT Git Branch Implementation Mode** — implementacja na branchu `gpt-work/<task-slug>` w `gicleeart-gpt` lub `gicleeapp`, import do monorepo, finalny test i commit **lokalnie**.
- `main`/`master` na GitHubie **nie są modyfikowane** bez osobnej, jednoznacznej zgody użytkownika.
- Paczka wiedzy: **v3.8** (`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`, `GPT_GIT_BRANCH_WORKFLOW.md`). Procedura importu: Base SHA + Commit SHA obowiązkowe dla GicleeApp.
- Brak deklaracji konkretnej implementacji na branchu GPT bez dowodu w GitHub / raporcie użytkownika.

<!-- gpt-window-2:catalog-submenu-preview-queue:start -->
## Checkpoint — Shopify Katalog submenu / kolejka podglądów — 2026-07-11

### Aktualny wygląd i decyzje wizualne

- Utworzono szeroki snapshot audytowy motywu:
  - repo: `eagleblastmusic-lgtm/gicleeart-gpt`,
  - branch: `audit/submenu-current-20260711-165132`,
  - SHA: `2b352462cdffc64bef1e03356aa7d1439b136e58`.
- Branch audytowy jest tylko snapshotem do odczytu. Zawiera wiele niezwiązanych zmian motywu i nie powinien być używany jako branch wdrożeniowy ani bezpośredni PR.
- Obecny wygląd submenu z trzema kolumnami artystów i dużym podglądem obrazu po prawej został oceniony jako udany, przestronny i muzealny.
- Nie zmieniać automatycznie:
  - `const totalSlots = artistLinks.length`
  - na `visible.length`.
- Obecne liczenie wysokości zachowuje celowy rytm pionowy także po ukryciu 24 artystów. Zmiana na liczbę widocznych elementów mogłaby nadmiernie ścisnąć listę u góry.
- Dostępne efekty nazw artystów:
  - `classic`,
  - `curatorial_glow`,
  - `depth_of_field`,
  - `museum_marker`,
  - `preview_focus`.
- Aktualnie testowany efekt lokalny: `museum_marker`.
- Lista ukrytych artystów jest przechowywana jako zwykły wieloliniowy tekst, bez konwersji do HTML.
- Testy komponentu Submenu katalog obejmują obecnie 6 przypadków i przechodziły lokalnie.

### Priorytetowa kolejka podglądów artystów

Branch implementacyjny:

- branch: `gpt-work/catalog-preview-priority-queue`,
- baza: `2b352462cdffc64bef1e03356aa7d1439b136e58`,
- HEAD: `b46dea314c7466cf2dd81fe007ed65c0c8133811`.

Dokładny zakres brancha:

- `assets/giclee-catalog-preview-queue.js` — nowy plik,
- `snippets/stylesheets.liquid` — jedna linia loadera.

Zachowanie kolejki:

- maksymalnie 3 requesty łącznie,
- maksymalnie 2 requesty tła,
- jeden slot pozostaje dostępny dla aktualnego hover/focus,
- hover intent delay: 75 ms,
- najnowszy hover otrzymuje priorytet,
- starsze nierozpoczęte priorytety wracają do kolejki tła,
- wspólny cache zapobiega ponownym requestom,
- focus klawiatury może bezpośrednio zażądać podglądu.

Stan lokalny w `C:\Strona\pusty` po synchronizacji:

- `?? assets/giclee-catalog-preview-queue.js`,
- `M snippets/stylesheets.liquid`,
- loader istnieje dokładnie jeden raz,
- `node --check` — PASS,
- `git diff --check` — PASS,
- brak merge, deployu i pushu.

Test Network potwierdził, że 53 requesty `products.json` nie startują jednocześnie. Requesty tła były wykonywane partiami po maksymalnie dwa równolegle.

Ważne ograniczenie obecnej wersji:

- kolejka ogranicza równoległość,
- ale nadal stopniowo prefetchuje wszystkie 53 widoczne kolekcje,
- następne opcjonalne usprawnienie to ograniczenie automatycznego prefetchu do około 4–6 artystów albo małych paczek uruchamianych podczas bezczynności,
- to dalsze ograniczenie nie zostało jeszcze zaimplementowane.

Błędy `shop.app ... 403` oraz część błędów konta Shopify podczas Theme Dev na `127.0.0.1` nie były związane z kolejką podglądów.
<!-- gpt-window-2:catalog-submenu-preview-queue:end -->

<!-- gpt-window-3:catalog-panel-modularization:start -->
## Checkpoint — Shopify Katalog submenu / modularizacja panelu — 2026-07-11

**Status:** zastosowane lokalnie w `C:\Strona\pusty`; walidacja statyczna PASS; test wizualny po modularizacji pozostaje do wykonania.

### Branch i źródło

- repo: `eagleblastmusic-lgtm/gicleeart-gpt`
- snapshot bazowy: `audit/submenu-current-20260711-165132`
- Base SHA: `2b352462cdffc64bef1e03356aa7d1439b136e58`
- branch docelowy: `gpt-work/catalog-panel-modularize-current`
- finalny HEAD: `efd4464c46be700aa0c5e601f314d06a6c2816d6`
- branch nie został zmergowany ani wdrożony do Shopify
- nie używać wcześniejszego `gpt-work/catalog-panel-modularize` jako finalnego źródła wdrożenia

### Docelowa architektura

- `snippets/giclee-catalog-panel.liquid` — centralny punkt ładowania modułu
- `assets/giclee-catalog-panel.css` — układ, wygląd i animacje panelu
- `assets/giclee-catalog-panel.js` — logika panelu, konfiguracja, runtime efektów artystów oraz priorytetowa kolejka podglądów
- `assets/giclee-catalog-artist-effects.css` — warianty wizualnego wyróżnienia aktywnego artysty

`layout/theme.liquid` zawiera już tylko dwa wywołania modułu:

- render stylów,
- render skryptu.

Blok loadera efektów FAQ w `layout/theme.liquid` został zachowany.

### Runtime’y zintegrowane

Kod dwóch wcześniejszych, osobnych plików został włączony do `assets/giclee-catalog-panel.js`:

- `assets/giclee-catalog-artist-effects.js`
- `assets/giclee-catalog-preview-queue.js`

Oba stare pliki zostały usunięte z lokalnego working tree.

Nie przywracać ich ani ich globalnych loaderów.

Priorytetowa kolejka nadal zachowuje:

- maksymalnie 3 requesty łącznie,
- maksymalnie 2 requesty tła,
- jeden slot dla aktualnego hover/focus,
- hover intent delay 75 ms,
- priorytet najnowszego hover,
- współdzielony `imageCache`,
- obsługę focusu klawiatury.

Checkpoint `gpt-window-2:catalog-submenu-preview-queue` pozostaje historią implementacji kolejki, ale jego opis osobnego pliku i globalnego loadera został funkcjonalnie zastąpiony przez ten checkpoint modularizacji.

### Ładowanie globalne

`snippets/stylesheets.liquid` nie ładuje już:

- `giclee-catalog-artist-effects.css`,
- `giclee-catalog-artist-effects.js`,
- `giclee-catalog-preview-queue.js`.

Zasoby katalogu są obsługiwane przez `snippets/giclee-catalog-panel.liquid`.

### Lokalny status po zastosowaniu

Oczekiwany zakres:

- `M assets/giclee-catalog-artist-effects.css`
- `D assets/giclee-catalog-artist-effects.js`
- `M layout/theme.liquid`
- `M snippets/stylesheets.liquid`
- `?? assets/giclee-catalog-panel.css`
- `?? assets/giclee-catalog-panel.js`
- `?? snippets/giclee-catalog-panel.liquid`

`assets/giclee-catalog-preview-queue.js` był lokalnym plikiem nieśledzonym i został usunięty po integracji, dlatego nie musi pojawić się jako `D`.

### Walidacja

- `node --check assets/giclee-catalog-panel.js` — PASS
- `git diff --check` dla dokładnego zakresu — PASS
- porównanie końcowych plików z branchem docelowym po normalizacji CRLF/LF — PASS
- tagi `<style>` i `<script>` zrównoważone
- render modułu nie znajduje się wewnątrz `<style>` ani `<script>`
- stare globalne loadery usunięte
- runtime efektów artystów obecny dokładnie raz
- runtime kolejki podglądów obecny dokładnie raz

### Nie wykonano

- wizualnego smoke testu po modularizacji,
- lokalnego commita,
- merge,
- deployu Shopify,
- zapisu lub synchronizacji do Shopify.

### Następny krok

Przetestować wizualnie:

- otwieranie i zamykanie Katalogu,
- szybkie przechodzenie kursorem między artystami,
- ładowanie podglądów,
- `museum_marker`,
- focus klawiatury,
- kliknięcie artysty i kurtynę przejścia,
- FAQ/paralaksę,
- menu mobilne.

<!-- gpt-window-3:catalog-panel-modularization:end -->
