# TRYB WRITER / EXPORT SAFETY

Kontrakt dla zapisów użytkownika, eksportów automatycznych i writerów motywu Shopify.

Stosuj razem z: `GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md`, `GICLEE_ANALYST_MODE_SHOPIFY_SNAPSHOT_v1.md`.

---

## Eksport wybrany przez użytkownika

Gdy użytkownik wybiera ścieżkę przez systemowy dialog:

- dokładny `Path` pozostaje bez zmian,
- systemowy dialog odpowiada za potwierdzenie nadpisania,
- model **nie** może po cichu zmienić lokalizacji.

---

## Eksport automatyczny

Automatyczne nazwy powinny być:

- slugowane,
- jednoznaczne,
- chronione przed kolizją,
- bez cichego nadpisania.

Przy kolizji stosuj deterministycznie:

```text
nazwa.jpg
nazwa-2.jpg
nazwa-3.jpg
```

Aplikacyjny default/staging export → Local AppData (poza checkout).

---

## Zapis ustawień vs writer motywu

**Invariant:** zwykłe `Zapisz` (zapis ustawień / wariantu w panelu) **nie może** cicho zmieniać śledzonego pliku motywu Shopify ani innego pliku źródłowego projektu.

Bezpieczny writer do pliku motywu wymaga **osobnej, jawnej akcji** i pełnego kontraktu:

```text
osobna akcja (nie Zapisz)
plan bez zapisu
exact target
preview diff
SHA przed zapisem i po zapisie
stale-state check (źródło nie zmieniło się między preview a apply)
jawna fraza potwierdzenia użytkownika
backup poza repo
atomic write
weryfikacja końcowego SHA
```

Nie łącz zapisu ustawień GUI z zapisem motywu bez preview, diffu i autoryzacji.

---

## Shopify writer (osobny etap)

Dla Karuzeli i innych writerów motywu wymagany kontrakt:

```text
explicit target
preview diff
allowlist plików
backup
atomic write
undo
test snapshotu
zero live deploy without explicit approval
```

Nie traktuj writerów motywu jako zwykłych danych runtime.

Intentional theme writers wymagają osobnego toru **Writer Safety** z kontraktem powyżej; szczegóły checkpointowe (merge, branch, inventory) → [CURRENT_APP_STATE.md](CURRENT_APP_STATE.md) § `gicleeart`.

---

## Theme Page Editor (GicleeApp)

Writer Safety dla edytora stron: `cursor-api/docs/theme-page-editor-writer-safety.md`.

Zasady: delta-only save, source-locked Apply, brak automatycznego deployu Shopify bez jawnej zgody.
