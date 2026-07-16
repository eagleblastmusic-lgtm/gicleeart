# Component availability and stability channels

Status: **STUDIO-ISOLATION-2**

## Cel

Jeden wspólny katalog `Komponenty/*` obsługuje trzy profile aplikacji bez kopiowania kodu i bez globalnego przełącznika runtime:

- `classic` — klasyczny GicleeApp;
- `studio_preview` — Giclée Studio Preview;
- `studio` — przyszłe produkcyjne Giclée Studio.

Każdy komponent może opcjonalnie zadeklarować w `component.json`:

```json
{
  "availability": ["classic", "studio_preview", "studio"],
  "stability": "stable"
}
```

## Availability

Dozwolone identyfikatory:

- `classic`
- `studio_preview`
- `studio`

Brak pola oznacza pełną kompatybilność wsteczną: komponent jest dostępny we wszystkich trzech profilach.

Jawne pole z niepoprawną wartością działa fail-closed. Jeżeli po normalizacji nie zostanie żaden znany profil, komponent nie trafia do profilowanego indeksu Studio.

Kolejność jest kanoniczna i niezależna od kolejności w JSON:

```text
classic → studio_preview → studio
```

## Stability

Dozwolone kanały:

- `stable` — gotowy do profilu produkcyjnego;
- `preview` — dopuszczony do Preview, jeszcze bez promocji do Stable;
- `experimental` — eksperyment, może być niestabilny;
- `legacy` — zachowany dla kompatybilności lub migracji.

Brak pola zachowuje dotychczasowe zachowanie i przyjmuje `stable`.

Niepoprawna jawna wartość zostaje zdegradowana do `experimental`. Dzięki temu przyszły profil produkcyjny nie promuje błędnie opisanego komponentu.

## Discovery i indeks

`discover_components()` nadal wykonuje jedno wykrycie wszystkich komponentów i zwraca pełny katalog wraz z metadanymi kanałów.

`StudioComponentIndex.build(profile=...)` tworzy następnie widok profilowy:

- `all_components` — pełny wynik discovery, przydatny diagnostycznie;
- `available_components` — komponenty dopuszczone dla danego `profile_id`;
- `visible_components` — dostępne i nieukryte;
- `by_folder` oraz `by_category` — wyłącznie komponenty dostępne w aktywnym profilu.

Domyślnym profilem indeksu pozostaje `studio_preview`, więc istniejący entrypoint Preview zachowuje dotychczasowe zachowanie.

## Zakres tego etapu

STUDIO-ISOLATION-2 wprowadza kontrakt, parser i profilowane filtrowanie. Nie zmienia żadnego istniejącego `component.json`, nie klasyfikuje hurtowo komponentów i nie uruchamia migracji danych.

Promocja kanałów do właściwego profilu produkcyjnego `studio` należy do **STUDIO-ISOLATION-3**.
