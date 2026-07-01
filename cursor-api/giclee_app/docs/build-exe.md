# Build .exe (PyInstaller)

Hub GicleeApp: [`README.md`](README.md)

---

## Budowa

Z katalogu `cursor-api`:

```powershell
pip install pyinstaller
python -m PyInstaller giclee_app.spec --noconfirm
```

Wynik: **`dist/GicleeApp.exe`** (jeden plik, okno bez konsoli).

---

## Ograniczenia

| Element | Zachowanie |
|---------|------------|
| **Launcher exe** | Samodzielny proces GUI |
| **Komponenty** | Nadal uruchamiane przez **systemowy Python** z PATH |
| **Python docelowy** | 3.11+ z „Add to PATH” na PC produkcyjnym |

Zmienna **`GICLEE_PYTHON`** — pełna ścieżka do `python.exe` jeśli nie ma w PATH:

```
GICLEE_PYTHON=C:\Python314\python.exe
```

Implementacja: `giclee_app/runtime.py` → `resolve_python_interpreter()`

---

## Skrót na pulpicie

Wskazuj na **pythonw**, nie python — brak czarnej konsoli przy starcie z kodu źródłowego.

Exe z PyInstaller nie wymaga pythonw — exe sam jest bez konsoli.

---

## Typowe problemy

| Objaw | Sprawdź |
|-------|---------|
| Exe startuje, komponent nie | Python w PATH lub `GICLEE_PYTHON` |
| Antywirus blokuje exe | Wyjątek dla `dist/GicleeApp.exe` |
| Stary exe | Przebuduj po zmianach w `launcher.py` |

→ [`troubleshooting.md`](troubleshooting.md)
