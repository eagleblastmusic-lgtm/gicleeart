# ETAP 4B / LC-5 — Background Services Scheduler

Status: fresh reconnaissance · contract frozen, awaiting implementation
Repository: eagleblastmusic-lgtm/gicleeart
Base: master @ c41bada4fac9e4a90dd43597893c682fd2dc6e93
Data weryfikacji: 2026-07-15

---

## 1. Cel LC-5
Celem LC-5 jest uporządkowanie i wyodrębnienie usług tła klasycznego launchera (`GicleeApp`). W obecnym stanie, harmonogramowanie (zarówno startowe, jak i cykliczne) za pomocą `root.after` oraz obsługa wątków są bezpośrednio wymieszane z logiką interfejsu Tkinter w pliku [launcher.py](file:///C:/Strona/pusty/cursor-api/giclee_app/launcher.py). LC-5 zmierza do wydzielenia logiki zarządzania czasem i wyzwalaniem usług (Scheduler) do dedykowanego, neutralnego architektonicznie modułu, odciążając konstruktor `GicleeApp`.

## 2. Stan po zamknięciu LC-4
* LC-4A wydzielił klasyczny subprocess launch adapter (`launcher_classic_subprocess.py`).
* LC-4B zunifikował wywoływanie builderów inline w obu launcherach (`launcher_inline_builder.py`).
* Wątek główny master wskazuje na commit `c41bada4fac9e4a90dd43597893c682fd2dc6e93`.

## 3. Pełny fresh reconnaissance
Dokonano pełnego audytu kodu w [launcher.py](file:///C:/Strona/pusty/cursor-api/giclee_app/launcher.py). Zidentyfikowano dokładnie 9 usług uruchamianych podczas startu aplikacji. Wszystkie te usługi używają `self.root.after()` do planowania początkowych opóźnień oraz (częściowo) do cyklicznego wznawiania.

## 4. Tabela wszystkich usług

| Lp. | Nazwa usługi | Metoda w GicleeApp | Typ zadania | Wątek roboczy (Thread) |
|---|---|---|---|---|
| 1 | Auto-rescan komponentów | `_auto_rescan` | Cykliczne (recurring) | Brak (Wątek UI) |
| 2 | Monthly reminder | `_check_monthly_reminder` | One-shot | Brak (Wątek UI) |
| 3 | Monthly plan reminder | `_check_monthly_plan_reminder` | One-shot | Brak (Wątek UI) |
| 4 | Shopify → Produkcja | `_poll_orders_from_shopify` | Cykliczne (recurring) | Daemon Thread |
| 5 | Shopify → Księgowość | `_poll_accounting_orders` | Cykliczne (recurring) | Daemon Thread |
| 6 | Daily backup | `_run_daily_backup` | One-shot | Daemon Thread |
| 7 | Cure completion | `_check_cure_done_notifications` | Cykliczne (recurring) | Daemon Thread |
| 8 | Social-media cycle publisher | `_poll_cykl_publisher` | Cykliczne (recurring) | Daemon Thread |
| 9 | Weekly content reminder | `_check_cykl_weekly_reminder` | One-shot | Brak (Wątek UI) |

## 5. Tabela initial delays

| Usługa | Initial Delay (ms) | Callback |
|---|---|---|
| Auto-rescan komponentów | 0 (wywołane bezpośrednio w `__init__`) | `_auto_rescan` |
| Monthly plan reminder | 800 | `_check_monthly_plan_reminder` |
| Monthly reminder | 1500 | `_check_monthly_reminder` |
| Daily backup | 2000 | `_run_daily_backup` |
| Weekly content reminder | 3000 | `_check_cykl_weekly_reminder` |
| Cure completion | 15 000 | `_check_cure_done_notifications` |
| Shopify → Produkcja | 30 000 | `_poll_orders_from_shopify` |
| Shopify → Księgowość | 35 000 | `_poll_accounting_orders` |
| Social-media cycle publisher | 45 000 | `_poll_cykl_publisher` |

## 6. Tabela recurrence

| Usługa | Recurrence Interval (ms) | Sposób planowania następnego ticka |
|---|---|---|
| Auto-rescan komponentów | 3000 | W bloku `finally` metody `_auto_rescan` |
| Monthly reminder | Brak | One-shot (weryfikacja stanu przy starcie) |
| Monthly plan reminder | Brak | One-shot (weryfikacja stanu przy starcie) |
| Shopify → Produkcja | 300 000 (5 min) | Po uruchomieniu wątku roboczego (w `_poll_orders_from_shopify`) |
| Shopify → Księgowość | 300 000 (5 min) | Po uruchomieniu wątku roboczego (w `_poll_accounting_orders`) |
| Daily backup | Brak | One-shot (idempotentna weryfikacja przy starcie) |
| Cure completion | 60 000 (1 min) | Po uruchomieniu wątku roboczego (w `_check_cure_done_notifications`) |
| Social-media cycle publisher | 60 000 (1 min) | Po uruchomieniu wątku roboczego (w `_poll_cykl_publisher`) |
| Weekly content reminder | Brak | One-shot (guard w pamięci `_cykl_reminder_shown`) |

## 7. Thread ownership
Wątki robocze (daemon threads) są tworzone wewnątrz metod klasycznych launchera (`GicleeApp`). Scheduler wywołuje jedynie główny callback na wątku UI (Tkinter). Scheduler nie zarządza bezpośrednio cyklem życia wątków roboczych ani nie tworzy nowych wątków systemowych — odpowiedzialność ta pozostaje wewnątrz callbacków aplikacji.

## 8. UI dispatch ownership
Wszystkie operacje dotykające widżetów Tkinter lub modyfikujące `self.status_var` wewnątrz wątków roboczych wykorzystują mechanizm `self.root.after(0, lambda: ...)` w celu bezpiecznego wykonania kodu na wątku głównym UI. Ten podział odpowiedzialności zostanie zachowany: callbacki robocze same wywołują `after(0, ...)` na obiekcie root, który przekazują do scheduler-a.

## 9. Lazy import ownership
Pomiary wydajności i czasu startu wymagają, aby importy komponentów (`Komponenty._shared`, `Komponenty.zadania`, `Komponenty.produkcja`, `Komponenty.dokumentysprzedazy`, `Komponenty.socialmedia`) pozostały leniwe (wewnątrz metod/callbacków). Scheduler nie importuje żadnych modułów z katalogu `Komponenty`.

## 10. Dane i side effects
* Usługi odczytują/zapisują pliki JSON w przestrzeni `Komponenty` (np. `reminders.json`, `zamowienia.json`, `notified.json`).
* Wyzwalają one toasty systemowe (Windows `notify`) oraz toasty graficzne Tkinter (`show_toast`).
* Logika ta pozostaje nienaruszona i zamknięta w callbackach aplikacji.

## 11. Monthly reminders analysis
W `GicleeApp` zaimplementowano dwa przypomnienia miesięczne, które celowo nakładają się pierwszego dnia miesiąca:
1. **`_check_monthly_plan_reminder`** (opóźnienie 800 ms):
   * Aktywne **tylko** pierwszego dnia miesiąca (`today.day == 1`).
   * Zapisuje stan w `reminders.json` pod kluczem `monthly_plan` **PO** uzyskaniu odpowiedzi od użytkownika.
   * Używa okna modalnego z parametrem `parent=self.root`.
2. **`_check_monthly_reminder`** (opóźnienie 1500 ms):
   * Aktywne w dniach **1-5** miesiąca.
   * Zapisuje stan pod tym samym kluczem `monthly_plan` **PRZED** wyświetleniem dialogu (zapobiega to ponownemu otwarciu dialogu przy przeładowaniu).
   * Nie przekazuje parametru `parent`.
* **Wniosek:** Jest to celowy mechanizm fallback/historyczny. W ramach LC-5 zachowujemy oba callbacki, ich opóźnienia, teksty oraz logikę zapisu stanu bez żadnych zmian.

## 12. Timery wykluczone z LC-5
Wyklucza się z zakresu LC-5 następujące wywołania `after` i `after_idle`:
* `root.after_idle(self._focus_tiles_canvas)` — obsługa fokusu UI.
* `root.after_idle(self._flush_tiles_canvas_wheel)` — buforowanie przewijania kołem myszy.
* `root.after(0, lambda: self.status_var.set(...))` — powroty z wątków roboczych na wątek UI.
* `self.root.after(500, lambda: open_tasks_generator(...))` — opóźnienie przed otwarciem generatora zadań po zamontowaniu widoku inline.
* `win.after(2000, _auto)` — odświeżanie okna podglądu logów komponentu.
* Watcher procesu subprocessu (`_watch_proc` w `launcher_classic_subprocess.py` / `launcher.py`).
* Timery i asynchroniczne wywołania skrótów klawiszowych w powiązanych plikach.

## 13. Ocenione warianty architektury
* **A. Startup Schedule Registry:** Rejestruje tylko początkowe opóźnienia. Słaby, ponieważ cała logika recurrence (np. 5 minut dla Shopify) pozostaje rozproszona w metodach `GicleeApp`.
* **B. BackgroundServices Scheduler (Wybrany):** Nowa klasa `LauncherBackgroundServices` przejmuje odpowiedzialność za całe harmonogramowanie (początkowe i cykliczne). Metody `GicleeApp` nie wywołują już `root.after` do ponownego planowania. Callbacki zwracają status lub po prostu wykonują swoje zadanie, a Scheduler decyduje o kolejnym ticku.
* **C. Full BackgroundServices Coordinator:** Przejmuje całe ciała workerów i importy. Odrzucony z uwagi na ogromne ryzyko naruszenia logiki biznesowej, cykli importów oraz wysoki koszt i złożoność testowania.
* **D. Osobne adaptery per service:** Odrzucony z powodu nadmiernego boilerplate (9 małych modułów dla prostych zadań czasowych).

## 14. Wybrana granica
Wdrażamy wariant **B — Launcher Background Services Scheduler**.
Odpowiedzialności:
* Klasa `LauncherBackgroundServices` zarządza harmonogramowaniem początkowym (initial delays) oraz cyklicznym (recurrence intervals).
* Ciała metod wykonawczych pozostają w `GicleeApp` jako callbacki.
* Usługi cykliczne są rejestrowane w schedulerze. Scheduler wykonuje rejestrację kolejnego zdarzenia Tkinter (`root.after`).
* Aby zachować nienaruszoną semantykę (reschedule następuje natychmiast po uruchomieniu worker threadu), callbacki rejestrowane w schedulerze reprezentują rozpoczęcie pracy (trigger), a scheduler planuje następne wywołanie przed lub po wykonaniu callbacku (w zależności od specyfiki usługi).

## 15. Publiczne API

Nowy moduł: `cursor-api/giclee_app/launcher_background_services.py`

```python
from collections.abc import Callable
from typing import Any, Protocol

class AfterScheduler(Protocol):
    def __call__(self, delay_ms: int, callback: Callable[[], None]) -> Any:
        ...

class LauncherBackgroundServices:
    def __init__(
        self,
        after_fn: AfterScheduler,
        *,
        auto_rescan: Callable[[], None],
        monthly_plan_reminder: Callable[[], None],
        monthly_reminder: Callable[[], None],
        shopify_orders: Callable[[], None],
        accounting_orders: Callable[[], None],
        daily_backup: Callable[[], None],
        cure_notifications: Callable[[], None],
        social_publisher: Callable[[], None],
        weekly_content_reminder: Callable[[], None],
    ) -> None:
        ...

    def start(self) -> None:
        """Uruchamia planowanie wszystkich usług tła."""
        ...
```

* Metoda `start()` jest idempotentna (ponowne wywołanie nie dubluje timerów).
* Klasa nie przechowuje referencji do widżetów Tkinter (poza funkcją `after_fn` przekazaną z `root.after`).

## 16. Exact startup order
Dokładna kolejność rejestracji i startu w konstruktorze `GicleeApp`:
1. `_build_ui()`
2. `_refresh_components()`
3. Inicjalizacja `LauncherBackgroundServices`
4. Wywołanie `services.start()`

Kolejność wyzwalania początkowych zdarzeń (zgodnie z wartościami delay):
1. `auto_rescan` (natychmiast przy inicjalizacji / start)
2. `monthly_plan_reminder` (800 ms)
3. `monthly_reminder` (1500 ms)
4. `daily_backup` (2000 ms)
5. `weekly_content_reminder` (3000 ms)
6. `cure_notifications` (15 000 ms)
7. `shopify_orders` (30 000 ms)
8. `accounting_orders` (35 000 ms)
9. `social_publisher` (45 000 ms)

## 17. Exact recurrence semantics
Cykliczne planowanie:
* **Auto-rescan:** Co 3000 ms. Zawsze planowane ponownie w bloku `finally` wykonania callbacku.
* **Shopify produkcja:** Co 300 000 ms (5 min). Następny tick planowany natychmiast przy wywołaniu triggera (przed zakończeniem wątku roboczego).
* **Shopify księgowość:** Co 300 000 ms (5 min). Następny tick planowany natychmiast przy wywołaniu triggera.
* **Cure completion:** Co 60 000 ms (1 min). Następny tick planowany natychmiast przy wywołaniu triggera.
* **Social publisher:** Co 60 000 ms (1 min). Następny tick planowany natychmiast przy wywołaniu triggera.

## 18. Error semantics
Błędy rzucane przez callbacki wewnątrz wątków roboczych (np. błędy sieciowe Shopify) są przechwytywane wewnątrz samych wątków (worker bodies) i nie wpływają na scheduler. Jeśli sam callback triggera rzuci wyjątek na wątku głównym, scheduler nie powinien ulec awarii (błąd zostanie zalogowany / zignorowany), a cykl harmonogramu nie może zostać przerwany.

## 19. RuntimeError semantics
Wyjątki `RuntimeError` rzucane z Tkinter (np. przy próbie wywołania `after` po zniszczeniu oku głównego `root`) muszą być bezpiecznie przechwytywane i ignorowane przez Scheduler.

## 20. Zachowania pozostające bez zmian
* Wszelkie interwały czasowe i opóźnienia początkowe.
* Wątki robocze `daemon=True` uruchamiane w callbackach.
* Sposób zapisu plików stanu JSON oraz klucz `monthly_plan`.
* Zachowanie zmiennej stanu `_cykl_reminder_shown`.
* Brak uruchamiania usług tła w `launcher_studio.py` oraz `launcher_delegate.py`.

## 21. Dependencies allowed
* Moduł `giclee_app/launcher_background_services.py` może importować standardowe biblioteki Pythona (`typing`, `collections.abc`).
* Może importować typy/protokoły pomocnicze.

## 22. Dependencies forbidden
* Zakaz importowania `customtkinter`, `tkinter` (poza typowaniem ad-hoc) w nowym module.
* Zakaz importu jakichkolwiek modułów z przestrzeni `Komponenty`.
* Zakaz bezpośredniego dostępu do zmiennych stanowych interfejsu graficznego.

## 23. Out-of-scope
* Modyfikacje logiki biznesowej synchronizacji Shopify, generowania zadań, backupów oraz publikowania postów.
* Zmiana tekstów powiadomień, okien dialogowych i statusów.
* Integracja usług tła ze Studio.
* Zmiany w MRO, drag-and-drop, persistence, url/subprocess launch.

## 24. Implementation allowlist
W procesie implementacji wolno modyfikować/tworzyć wyłącznie następujące pliki:
* `cursor-api/giclee_app/docs/launcher-composition-lc5-contract.md` (ten plik)
* `cursor-api/giclee_app/docs/launcher.md`
* `cursor-api/giclee_app/launcher.py`
* `cursor-api/giclee_app/launcher_background_services.py` [NEW]
* `cursor-api/tests/test_launcher_background_services.py` [NEW]
* `cursor-api/tests/test_launcher_composition.py`

## 25. Focused test matrix
Testy jednostkowe w `test_launcher_background_services.py` must zweryfikować:
1. Pomyślne utworzenie obiektu `LauncherBackgroundServices` z prawidłowymi callbackami.
2. Wywołanie `start()` rejestruje początkowe opóźnienia (dokładnie 9 zarejestrowanych wywołań w fałszywym schedulerze).
3. Prawidłowość wartości opóźnień początkowych (800, 1500, 2000, 3000, 15000, 30000, 35000, 45000).
4. Wywołanie `auto_rescan` natychmiast po starcie (opóźnienie 0 lub bezpośrednie wywołanie).
5. Zachowanie cykliczności (recurrence) dla auto-rescan (3000 ms), Shopify (300 000 ms), cure notifications (60 000 ms), social publisher (60 000 ms) przy użyciu mock-ów czasu bez rzeczywistego czekania.
6. Ignorowanie `RuntimeError` przy wywołaniu callbacku po zniszczeniu środowiska Tk.
7. Idempotentność metody `start()` (ponowne wywołanie nie rejestruje nowych timerów).
8. Izolację: testy nie mogą uruchamiać rzeczywistych wątków roboczych ani importować modułów z `Komponenty`.

## 26. Source guards
* `launcher_background_services.py` nie zawiera importów z `Komponenty`.
* `launcher.py` nie posiada bezpośrednich odwołań do `root.after` dla harmonogramowania tych 9 usług (całość delegowana do `LauncherBackgroundServices`).
* Moduł testowy nie używa `time.sleep()`.

## 27. Validation commands
```powershell
python -m pytest cursor-api/tests/test_launcher_background_services.py
python -m pytest cursor-api/tests/test_launcher_composition.py
```

## 28. Rollback boundary
W razie wykrycia krytycznych regresji stabilności timera lub problemów z wątkami UI, rollback następuje do rewizji bazowej `c41bada4fac9e4a90dd43597893c682fd2dc6e93`.

## 29. Completion criteria
1. Kod modyfikuje/tworzy wyłącznie pliki z allowlisty.
2. Zintegrowany test suite przechodzi pomyślnie.
3. Konstruktor `GicleeApp` został odchudzony z logiki `root.after`.
4. Czystość `git status` (brak niezatwierdzonych zmian).

## 30. Ocena, czy LC-5 kończy BackgroundServices
Tak. LC-5 w pełni wyodrębnia i zamyka architekturę usług tła klasycznego launchera.

## 31. Warunek wejścia do LC-6
Pomyślne scalenie PR dla LC-5 oraz akceptacja zmian przez CI/manual review.
