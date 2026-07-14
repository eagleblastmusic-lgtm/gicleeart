# TRYB RUNTIME DATA OWNERSHIP

Klasyfikuj każdy zapis **przed** refaktorem lub migracją danych.

Stosuj razem z: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v39.md`, `GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md`, `CURRENT_APP_STATE.md`.

---

## Kategorie

### 1. Mutable runtime state

Ustawienia, queue, drafty, znaczniki, logi, lokalne bazy.

→ **Local** lub **Roaming AppData**.

### 2. Dane użytkownika i workspace

Zdjęcia użytkownika, materiały kalibracyjne, katalogi robocze, pobrane pary obrazów, raporty i własne pliki robocze.

**Nie** są cache'em. **Nie** wolno ich automatycznie kasować, scalać ani migrować bez osobnej procedury i jawnej zgody.

Przykłady workspace (nie cache): domyślne lub wybrane katalogi `test_photos`, `ww_pairs`, raporty optymalizacji — pozostają pod kontrolą użytkownika; aplikacja może ustawić default poza checkout, ale nie nadpisuje ani nie kasuje legacy automatycznie.

### 3. Eksport użytkownika

Jawny target wybrany w Save dialogu pozostaje autorytatywny. Nie przekierowuj jawnie wybranego pliku do AppData.

### 4. Aplikacyjny staging / default export

Domyślny lub tymczasowy katalog aplikacji → poza checkout, zwykle Local AppData.

### 5. Świadomy writer projektu lub Shopify theme

Zapis do projektu **nie** jest sam błędem — wymaga kontraktu Writer Safety: jawny target, allowlista, preview/dry-run, backup, atomic write, undo, brak automatycznego deployu.

### 6. Project resource lub fixture

Może pozostać w repo, ale runtime **nie** powinien go niejawnie mutować.

### 7. False positive analizatora

Nie przepisuj poprawnego store'u wyłącznie po to, aby licznik spadł.

False positive musi być: udowodniony testami, sklasyfikowany, opisany, rozwiązany przez **semantyczną granicę** (np. nazwany store `settings/db/changelog`, jawny kontrakt helper interface) lub poprawę analizatora.

**Zakazane przy false positive:**
- allowlista pliku,
- global suppression,
- osłabienie reguły analizatora,
- ukrywanie wywołań przed analizatorem,
- globalne whitelistowanie `_write_path` / `_write_json` wyłącznie po nazwie helpera.

**Nie dąż mechanicznie do inventory = 0.**

---

## Reguły implementacyjne

Przy przenoszeniu runtime state zachowaj:

- external-first reads,
- Local/Roaming AppData writes,
- atomic writes,
- legacy read-only fallback,
- dynamiczne override'y,
- monkeypatchowane ścieżki,
- obecne formaty JSON,
- sortowanie i semantykę danych.

Domyślnie **nie** wykonuj:

- automatycznej migracji,
- przenoszenia,
- kasowania,
- nadpisywania legacy,
- cichego scalania danych.

---

## Expected inventory delta

Przed zmianą ustal oczekiwaną deltę runtime-write inventory i udowodnij ją po CI (artifact review).

Nie whitelistuj globalnie helpera wyłącznie na podstawie jego nazwy (np. `_write_path`, `_write_json`).

---

## Odniesienie do checkpointu

Bieżąca klasyfikacja findings, wynik scannera runtime-write inventory, SHA i PR-y → [CURRENT_APP_STATE.md](CURRENT_APP_STATE.md) § `gicleeart`.
