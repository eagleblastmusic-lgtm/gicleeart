# Troubleshooting — GicleeApp

Hub: [`README.md`](README.md)  
API / OAuth: [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md)

---

## Launcher

| Objaw | Sprawdź |
|-------|---------|
| Puste okno / brak kafelków | `Komponenty/` — czy folder istnieje względem exe/kodu |
| Kafelek brakuje | [`component-loader.md`](component-loader.md) — `__main__.py` |
| Crash po kliknięciu | `cursor-api/logs/`, uruchom komponent ręcznie |
| Stara lista kafelków | Odśwież / poczekaj 3 s |

---

## Python / exe

| Objaw | Sprawdź |
|-------|---------|
| „Python not found” z exe | PATH lub `GICLEE_PYTHON` |
| Dwa okna konsoli | Użyj `pythonw` zamiast `python` |
| Import Komponenty fail | Uruchamiaj z `cursor-api` jako cwd |

→ [`build-exe.md`](build-exe.md)

---

## Sesja Shopify

Toolbar **Stan sesji** → [`session-status.md`](session-status.md)

---

## Inline view nie ładuje się

Komponenty inline (`blog`, `produkcja`, `limity`, `poczta`, …) wymagają `view.py`. Błąd importu — sprawdź zależności w `requirements.txt` komponentu.

---

## Limity / Poczta

| Objaw | Sprawdź |
|-------|---------|
| Limity: pusta sekcja Resend | `.env` → `RESEND_API_KEY` **Full access** (send-only = 401) |
| Limity: Resend 403 | Zrestartuj app po aktualizacji (User-Agent w collectors) |
| Limity: scroll kółkiem | `limity/view.py` — wheel bind po renderze |
| Poczta: login failed | Hasło **aplikacji** Google, nie zwykłe hasło — [`../../docs/komponenty/poczta.md`](../../docs/komponenty/poczta.md) |
| Meta: odnowa tokenów | Limity → **Odnów tokeny** → [`../../docs/komponenty/meta-tokeny.md`](../../docs/komponenty/meta-tokeny.md) |

→ [`../../docs/komponenty/limity.md`](../../docs/komponenty/limity.md)
