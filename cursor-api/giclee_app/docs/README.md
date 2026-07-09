# GicleeApp — dokumentacja launchera

Warstwa **giclee_app**. Hub: [`../../../docs/README.md`](../../../docs/README.md) · polityka docs tam samo.

Główna aplikacja-launcher uruchamiająca komponenty z `cursor-api/Komponenty/`. **Zmiany launcher →** pliki w tym folderze (`launcher.md` itd.), nie `SHOP_KNOWLEDGE.md`.

---

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
python -m giclee_app
```

Bez konsoli (tylko GUI):

```powershell
pythonw -m giclee_app
```

Szczegóły exe: [`build-exe.md`](build-exe.md)

**Studio Preview (F1):** [`studio-preview.md`](studio-preview.md) — `python -m giclee_app.studio_preview` (CustomTkinter, obok klasycznego launchera).

---

## Dokumenty w tym folderze

| Plik | Temat |
|------|--------|
| [`launcher.md`](launcher.md) | GUI, sekcje kafelków, toolbar |
| [`studio-preview.md`](studio-preview.md) | **Studio Preview (F1)** — ciemny shell CTk |
| [`component-loader.md`](component-loader.md) | Discovery, `component.json`, tryby |
| [`build-exe.md`](build-exe.md) | PyInstaller, `GICLEE_PYTHON` |
| [`session-status.md`](session-status.md) | Raport OAuth, NBP, git |
| [`troubleshooting.md`](troubleshooting.md) | Problemy launchera |

**Mapa wzorców (nie duplikuj helperów):** [`../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md)

Logika komponentów (biznes): [`../docs/komponenty/README.md`](../docs/komponenty/README.md)

---

## Wszystkie komponenty (55)

Pełna tabela z trybami GUI, plikami, config i wzorcami reuse: [`../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md)

Skrócony indeks docs biznesowych: [`../docs/komponenty/README.md`](../docs/komponenty/README.md)

Sekcje w launcherze (kolejność UI, nie `order` JSON): patrz [`launcher.md`](launcher.md)

---

## Architektura (skrót)

```
cursor-api/
├── giclee_app/          ← launcher (ten folder)
│   ├── launcher.py
│   ├── component_loader.py
│   └── runtime.py
└── Komponenty/          ← izolowane procesy / inline views
```

Komponenty **izolowane** — crash jednego nie ubija launchera.

---

## Dodawanie nowego komponentu

1. **Najpierw:** [`../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](../docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md) — sprawdź, czy helper lub podobny komponent już istnieje.
2. Patrz [`component-loader.md`](component-loader.md) — folder + `__main__.py` + opcjonalnie `component.json`.

GicleeApp wykrywa nowe co **3 sekundy** (przycisk Odśwież).
