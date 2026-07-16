# GicleeApp — dokumentacja launchera i profili Studio

Warstwa **giclee_app**. Hub: [`../../../docs/README.md`](../../../docs/README.md) · polityka docs tam samo.

Główna aplikacja uruchamia komponenty z `cursor-api/Komponenty/`. Zmiany launchera i profili dokumentuj w tym folderze, nie w archiwalnym `SHOP_KNOWLEDGE.md`.

---

## Status architektury

ETAP 4B / LC-1 — LC-6, stabilizacja RC1 oraz STUDIO-ISOLATION-1 — 3 są architektonicznie zakończone.

Kanoniczne podsumowanie całego zamkniętego zakresu:

[`../../docs/GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md`](../../docs/GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md)

Status RC1, historyczne dowody CI i checklist manualnego smoke Windows:

[`launcher-stabilization-rc1.md`](launcher-stabilization-rc1.md)

Klasyczny GicleeApp, Studio Preview i produkcyjne Studio korzystają ze wspólnego kodu komponentów. Profile Studio mają osobne namespace stanu i shell/perf logów; dane biznesowe oraz sesja Shopify pozostają wspólne.

Przebudowa wizualna Studio jest poza zakończonym zakresem.

---

## Entrypointy

Z katalogu `cursor-api`:

```text
python -m giclee_app                  # klasyczny GicleeApp
python -m giclee_app.studio_preview   # Giclée Studio Preview
python -m giclee_app.studio           # produkcyjne Giclée Studio
```

Klasyczny produkcyjny entrypoint:

```text
python -m giclee_app
  -> giclee_app.__main__
  -> giclee_app.launcher_app.main
  -> launcher.main(app_factory=LauncherApp)
```

Bez konsoli, tylko klasyczne GUI na Windows:

```powershell
pythonw -m giclee_app
```

Szczegóły exe: [`build-exe.md`](build-exe.md)

---

## Profile i kanały komponentów

| Profil | Rola | Namespace stanu/logów | Dopuszczone kanały |
|---|---|---|---|
| `classic` | stabilny klasyczny launcher | `GicleeApp` | zgodność historyczna |
| `studio_preview` | eksperymentalny shell Preview | `GicleeStudioPreview` | stable, preview, experimental, legacy |
| `studio` | produkcyjne Giclée Studio | `GicleeStudio` | tylko stable |

Komponent może opcjonalnie deklarować w `component.json`:

```json
{
  "availability": ["classic", "studio_preview", "studio"],
  "stability": "stable"
}
```

Brak pól zachowuje kompatybilność istniejących manifestów. Szczegóły:

- [`component-channels.md`](component-channels.md)
- [`studio-production-profile.md`](studio-production-profile.md)
- [`studio-preview.md`](studio-preview.md)

---

## Dokumenty w tym folderze

| Plik | Temat |
|------|--------|
| [`launcher-stabilization-rc1.md`](launcher-stabilization-rc1.md) | Kanoniczny status ETAPU 4B, finalne CI i manualny smoke RC1 |
| [`launcher.md`](launcher.md) | GUI, sekcje kafelków, toolbar i wydzielone granice LC |
| [`studio-preview.md`](studio-preview.md) | Studio Preview — ciemny shell CTk |
| [`studio-production-profile.md`](studio-production-profile.md) | Produkcyjny profil `studio`, osobny state/log namespace i promotion policy |
| [`component-channels.md`](component-channels.md) | `availability` i `stability` komponentów |
| [`component-loader.md`](component-loader.md) | Discovery, `component.json`, tryby |
| [`studio-save-pattern.md`](studio-save-pattern.md) | Ograniczony wzorzec zapisu Studio |
| [`build-exe.md`](build-exe.md) | PyInstaller, `GICLEE_PYTHON` |
| [`session-status.md`](session-status.md) | Raport OAuth, NBP, git |
| [`troubleshooting.md`](troubleshooting.md) | Problemy launchera |

Mapa wzorców i reuse: [`../../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md)

Logika biznesowa komponentów: [`../../docs/komponenty/README.md`](../../docs/komponenty/README.md)

---

## Architektura — skrót

```text
cursor-api/
├── giclee_app/
│   ├── __main__.py             ← klasyczny package entrypoint
│   ├── studio_preview.py       ← entrypoint Preview
│   ├── studio.py               ← produkcyjny entrypoint Studio
│   ├── app_profile.py          ← niemutowalne profile i scoped context
│   ├── launcher_app.py         ← klasyczny composition root
│   ├── launcher.py             ← bazowy klasyczny shell
│   ├── launcher_studio.py      ← współdzielony shell Studio
│   ├── component_loader.py     ← discovery + metadata kanałów
│   ├── studio/                 ← indeks, state, perf i funkcje Studio
│   └── runtime.py
└── Komponenty/                 ← subprocessy i inline views
```

Finalna klasa klasycznego launchera jest aliasem, nie nową podklasą:

```python
LauncherApp is DragDropCategoryGicleeApp
```

Komponenty subprocess są izolowane — crash jednego nie ubija launchera. Inline views podlegają kontraktom lifecycle i teardown.

---

## Dodawanie nowego komponentu

1. Najpierw przeczytaj [`../../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md).
2. Sprawdź [`component-loader.md`](component-loader.md).
3. Dodaj folder i wymagany plik dla trybu: `__main__.py`, `view.py` albo manifest URL.
4. Deklaruj `availability`/`stability` tylko świadomie; brak pól zachowuje zgodność wsteczną.
5. Nie twórz kopii helperów istniejących w `Komponenty/_shared/`.

Klasyczny GicleeApp wykrywa nowe komponenty cyklicznie. Indeks Studio jest budowany dla aktywnego profilu i filtruje komponenty zgodnie z jego polityką.
