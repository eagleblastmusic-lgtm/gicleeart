# GICLÉE HOME FLOW

## Cel

`GICLÉE HOME FLOW` jest wspólną osią identyfikacji sekcji oraz faz przejść strony głównej.

Metadane wariantu są zapisane w:

```text
Komponenty/stronaglowna/data/variants/<variant_id>/home_flow.json
```

Zmiana nazw i szkic HF-3A nie modyfikują `templates/index.json`,
`config/settings_data.json`, assetów motywu ani Shopify.

## Stabilne identyfikatory

Sekcje i fazy używają trwałych ID, np.:

```text
section:prehero
phase:portal
phase:hero-rise
section:hero
phase:hero-hold
phase:sound-consent
phase:horizontal-curtain
section:intro
phase:intro-hold
```

Kody prezentacyjne `GH-00`, `GH-01`, `GH-T01` itd. nie są zapisywane.
Są wyliczane przy każdym odczycie z bieżącej kolejności.

## Status etapów

### Etap 1 — identyfikacja i nazwy: done

- wspólna oś sekcji i faz,
- stabilne identyfikatory,
- nazwy użytkowe per wariant,
- automatyczna numeracja,
- osobne okno pełnej osi.

### Etap 2 — edycja faz i bezpośrednia nawigacja: done

- sekcje i fazy jako pełnoprawne elementy `Treeview`,
- edycja faz w tym samym prawym panelu,
- bezpośredni renderer sekcji bez sterowania ukrytym `Listbox` przez `event_generate`,
- ustawienia Pre-Hero, Hero, zgody na dźwięk, kurtyny i postoju Intro,
- pełny generator assetów Pre-Hero.

### HF-3A — Structure Planner: done

HF-3A dodaje bezpieczny planner struktury.

Funkcje:

- schema `home_flow.json` v2 z kompatybilnym odczytem schema v1,
- trwałe pole `structure_draft`,
- zmiana kolejności sekcji w RAM,
- przyciski `Wyżej` / `Niżej`,
- drag-and-drop w bezpiecznym obszarze osi,
- katalog blueprintów nowych sekcji,
- usuwanie wyłącznie nowych sekcji szkicu,
- dry-run i readiness,
- jawne blokery i ostrzeżenia,
- zapis / reset szkicu per wariant.

Kotwice, których HF-3A nie pozwala przesuwać:

1. `section:prehero`,
2. `section:hero`,
3. `section:intro`,
4. `section:notice` jako ostatni element.

Fazy pozostają przypisane do sekcji i przesuwają się razem z właścicielem.

### HF-3B — Bounded Writer: implemented on branch

HF-3B dodaje osobny przycisk `Zastosuj szkic…` i bezpieczny writer kolejności
istniejących sekcji.

Writer:

- ponownie waliduje szkic oraz `index.json` wariantu,
- mapuje stabilne ID Home Flow na istniejące klucze sekcji Shopify,
- podmienia wyłącznie istniejące sloty zarządzanych sekcji w tablicy `order`,
- zachowuje pozycje i kolejność wszystkich niezarządzanych elementów,
- zapisuje wyłącznie:
  `Komponenty/stronaglowna/data/variants/<variant_id>/index.json`,
- przed zapisem tworzy dokładny backup bajtowy,
- używa pliku tymczasowego i `os.replace`,
- zapisuje hash pliku sprzed i po operacji,
- oferuje jednooperacyjne Undo,
- blokuje Undo, gdy `index.json` zmienił się po operacji,
- wymaga wpisania frazy `ZASTOSUJ <variant_id>` albo `COFNIJ <variant_id>`.

Pliki runtime HF-3B:

```text
Komponenty/stronaglowna/data/variants/<variant_id>/
  home_flow_structure_writer.json
  home_flow_structure_backups/
    index-before-hf3b-<timestamp>-<hash>.json
```

Są tworzone dopiero podczas użycia writer-a i nie należą do implementacji źródłowej.

## Granice bezpieczeństwa

### HF-3A

Przycisk `Zapisz szkic` aktualizuje wyłącznie `structure_draft` w
`home_flow.json` aktywnego wariantu. Sam planner nie zapisuje `index.json`.

### HF-3B

HF-3B **nie wykonuje**:

- zapisu do głównego `templates/index.json`,
- zapisu do `config/settings_data.json`,
- generowania lub modyfikowania assetów,
- przełączenia aktywnego wariantu,
- uruchomienia Shopify CLI,
- deployu development, unpublished ani live,
- materializacji blueprintów nowych sekcji.

Writer zmienia jedynie lokalny magazyn wskazanego wariantu. Istniejący mechanizm
przełączania wariantu może później skopiować wariant do motywu, ale nie jest to
częścią operacji HF-3B.

## Katalog blueprintów HF-3A

- Editorial — tekst i grafika,
- Editorial — tekst i film,
- Porównanie przed / po,
- Galeria dzieł.

Blueprint jest opisem przyszłej sekcji. Nie jest fragmentem Liquid ani gotową
sekcją Shopify. Dlatego obecność choć jednego blueprintu blokuje writer HF-3B.

## Algorytm reorder HF-3B

Writer nie usuwa i nie przesuwa nieznanych sekcji, dividerów ani elementów
technicznych.

Przykład:

```text
przed:
utility → Hero → divider → Intro → Restoration → divider → Color → Potential

szkic:
Hero → Intro → Restoration → Potential → Color

po:
utility → Hero → divider → Intro → Restoration → divider → Potential → Color
```

Zmieniane są tylko sloty należące do sekcji zarządzanych przez Home Flow.

## Backup i Undo

Backup jest dokładną kopią bajtową pliku sprzed operacji.

Undo jest dostępne wyłącznie wtedy, gdy:

1. istnieje stan ostatniej operacji,
2. bieżący `index.json` ma hash zapisany jako `after_sha256`,
3. backup istnieje,
4. backup ma hash zapisany jako `before_sha256`,
5. operacja nie została już cofnięta.

Jeżeli użytkownik lub inny mechanizm zmieni `index.json` po HF-3B, Undo zostaje
zablokowane, aby nie nadpisać nowszych zmian.

## Następny etap

### HF-3C — Runtime Integration & Acceptance

Planowany osobno:

- bezpieczne materializowanie zatwierdzonych blueprintów,
- dynamiczne hooki nowych sekcji,
- integracja nowych sekcji z edytorem GicleeApp,
- stack / section-scroll,
- separatory,
- asset generation,
- testy desktop, mobile i reduced-motion,
- ręczna akceptacja wariantu.

## Testy

HF-3A obejmuje migrację schema, nazwy, kotwice, drag-and-drop, blueprinty i
potwierdzenie braku zapisu do `index.json`.

HF-3B obejmuje:

- podmianę wyłącznie zarządzanych slotów,
- zachowanie niezarządzanych pozycji,
- dokładny backup,
- atomic write,
- brak zmian poza wariantem,
- dokładne Undo,
- blokadę Undo po zewnętrznej zmianie,
- blokadę brakujących sekcji,
- blokadę blueprintów do HF-3C,
- ochronę przed zapisem na podstawie nieaktualnego podglądu.
