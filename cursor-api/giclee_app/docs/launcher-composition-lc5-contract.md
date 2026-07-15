# ETAP 4B / LC-5 — Background Services Scheduler

Status: implementation complete, awaiting exact review
Repository: eagleblastmusic-lgtm/gicleeart
Base: master @ c41bada4fac9e4a90dd43597893c682fd2dc6e93
Data weryfikacji: 2026-07-15

---

## 1. Cel LC-5
Celem LC-5 jest uporządkowanie i wyodrębnienie usług tła klasycznego launchera (`GicleeApp`). W obecnym stanie, harmonogramowanie (zarówno startowe, jak i cykliczne) za pomocą `root.after` oraz obsługa wątków są bezpośrednio wymieszane z logiką interfejsu Tkinter w pliku [launcher.py](../launcher.py). LC-5 zmierza do wydzielenia logiki zarządzania czasem i wyzwalaniem usług (Scheduler) do dedykowanego, neutralnego architektonicznie modułu, odciążając konstruktor `GicleeApp`.

## 2. Stan po zamknięciu LC-4
* LC-4A wydzielił klasyczny subprocess launch adapter (`launcher_classic_subprocess.py`).
* LC-4B zunifikował wywoływanie builderów inline w obu launcherach (`launcher_inline_builder.py`).
* Wątek główny master wskazuje na commit `c41bada4fac9e4a90dd43597893c682fd2dc6e93`.

## 3. Pełny fresh reconnaissance
Dokonano pełnego audytu kodu w [launcher.py](../launcher.py). Zidentyfikowano dokładnie dziewięć usług startowych. `auto_rescan` jest początkowo uruchamiany synchronicznie jako direct call, natomiast pozostałe osiem usług otrzymuje początkowe harmonogramy za pomocą `self.root.after()`. Część usług cyklicznych wykorzystuje następnie `after()` do rejestracji kolejnych ticków.

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
| Auto-rescan komponentów | 0 (direct call) | `_auto_rescan` |
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
| Shopify → Produkcja | 300 000 (5 min) | Po powrocie callbacku triggera |
| Shopify → Księgowość | 300 000 (5 min) | Po powrocie callbacku triggera |
| Daily backup | Brak | One-shot (idempotentna weryfikacja przy starcie) |
| Cure completion | 60 000 (1 min) | Po powrocie callbacku triggera |
| Social-media cycle publisher | 60 000 (1 min) | Po powrocie callbacku triggera |
| Weekly content reminder | Brak | One-shot (guard w pamięci `_cykl_reminder_shown`) |

## 7. Thread ownership
Wątki robocze (daemon threads) są tworzone wewnątrz metod klasycznych launchera (`GicleeApp`). Scheduler wywołuje jedynie główny callback na wątku UI (Tkinter). Scheduler nie zarządza bezpośrednio cyklem życia wątków roboczych ani nie tworzy nowych wątków systemowych — odpowiedzialność ta pozostaje wewnątrz callbacków aplikacji.

## 8. UI dispatch ownership
Wszystkie operacje dotykające widżetów Tkinter lub modyfikujące `self.status_var` wewnątrz wątków roboczych wykorzystują mechanizm `self.root.after(0, lambda: ...)` w celu bezpiecznego wykonania kodu na wątku głównym UI. Ten podział odpowiedzialności zostanie zachowany: callbacki robocze same wywołują `after(0, ...)` na obiekcie root.

## 9. Lazy import ownership
Pomiary wydajności i czasu startu wymagają, aby importy komponentów (`Komponenty._shared`, `Komponenty.zadania`, `Komponenty.produkcja`, `Komponenty.dokumentysprzedazy`, `Komponenty.socialmedia`) pozostały leniwe (wewnątrz metod/callbacków). Scheduler nie importuje żadnych modułów z katalogu `Komponenty`.

## 10. Dane i side effects
* Usługi odczytują/zapisują pliki JSON w przestrzeni `Komponenty` (np. `reminders.json`, `zamowienia.json`, `notified.json`).
* Wyzwalają one toasty systemowe (Windows `notify`) oraz toasty graficzne Tkinter (`show_toast`).
* Logika ta pozostaje nienaruszona i zamknięta w callbackach aplikacji.

## 11. Monthly reminders analysis
W `GicleeApp` historycznie istnieją dwa niezależne przypomnienia współdzielące klucz `monthly_plan`; LC-5 zachowuje obserwowane zachowanie bez interpretowania pierwotnej intencji:
1. **`_check_monthly_plan_reminder`** (opóźnienie 800 ms):
   * Aktywne **tylko** pierwszego dnia miesiąca (`today.day == 1`).
   * Zapisuje stan w `reminders.json` pod kluczem `monthly_plan` **PO** uzyskaniu odpowiedzi od użytkownika.
   * Używa okna modalnego z parametrem `parent=self.root`.
2. **`_check_monthly_reminder`** (opóźnienie 1500 ms):
   * Aktywne w dniach **1-5** miesiąca.
   * Zapisuje stan pod tym samym kluczem `monthly_plan` **PRZED** wyświetleniem dialogu (zapobiega to ponownemu otwarciu dialogu przy przeładowaniu).
   * Nie przekazuje parametru `parent`.
* **Wniosek:** LC-5 zachowuje oba callbacki, ich opóźnienia, dni miesiąca, teksty, parent/no-parent, kolejność zapisu, wspólny storage key oraz sposób otwierania generatorów bez żadnych zmian.

## 12. Timery wykluczone z LC-5
Wyklucza się z zakresu LC-5 następujące wywołania `after` i `after_idle`:
* UI `after_idle(self._focus_tiles_canvas)` — obsługa fokusu UI.
* UI `after_idle(self._flush_tiles_canvas_wheel)` — buforowanie przewijania kołem myszy (flush wheel).
* UI-thread dispatch `root.after(0, lambda: self.status_var.set(...))` — powroty z wątków roboczych na wątek UI.
* Watcher subprocessu (`_watch_proc` w `launcher_classic_subprocess.py` / `launcher.py`).
* Auto-refresh log preview (`win.after(2000, _auto)`).
* 500 ms generator delay (`self.root.after(500, lambda: open_tasks_generator(...))` / `_open_zadania_generator`).
* DnD timers.
* Shortcut polling timers.
* Component-owned timers.
* Studio timers i asynchroniczne wywołania.
* Wszystkie timery poza dziewięcioma usługami startowymi wymienionymi w LC-5.

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
* Start schedulera odbywa się jednorazowo przy starcie launchera. Nie wprowadzamy idempotentności wywołania `start()` ani stopping/cancel metod jako wymagania projektowego, aby uniknąć rozszerzania zakresu i wprowadzania niepotrzebnych timer IDs.

## 15. Publiczne API

Nowy moduł: `giclee_app/launcher_background_services.py`

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
        monthly_reminder: Callable[[], None],
        monthly_plan_reminder: Callable[[], None],
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

* Sygnatura konstruktora `LauncherBackgroundServices` odwzorowuje dokładnie **Exact registration order**, a nie delay order.
* Metoda `start()` jest wywoływana dokładnie raz przez konstruktor launchera.

## 16. Exact registration order
Kolejność rejestracji w konstruktorze `GicleeApp` (bez sortowania według opóźnień):
1. `_auto_rescan` — bezpośrednio (synchronicznie);
2. `_check_monthly_reminder` — 1500 ms;
3. `_check_monthly_plan_reminder` — 800 ms;
4. `_poll_orders_from_shopify` — 30 000 ms;
5. `_poll_accounting_orders` — 35 000 ms;
6. `_run_daily_backup` — 2000 ms;
7. `_check_cure_done_notifications` — 15 000 ms;
8. `_poll_cykl_publisher` — 45 000 ms;
9. `_check_cykl_weekly_reminder` — 3000 ms.

## 17. Expected firing order
Kolejność wyzwalania początkowych zdarzeń wynikająca z opóźnień startowych:
1. `auto_rescan` — synchronicznie (direct call);
2. `monthly_plan_reminder` — 800 ms;
3. `monthly_reminder` — 1500 ms;
4. `daily_backup` — 2000 ms;
5. `weekly_content_reminder` — 3000 ms;
6. `cure_notifications` — 15 000 ms;
7. `shopify_orders` — 30 000 ms;
8. `accounting_orders` — 35 000 ms;
9. `social_publisher` — 45 000 ms.

## 18. Exact recurrence semantics

### A. Auto-rescan
* Wywoływany bezpośrednio synchronicznie podczas wywołania `start()`.
* Po wykonaniu callbacku, następny tick (3000 ms) jest planowany w bloku `finally`.
* Jeśli callback rzuci wyjątek, cykliczne harmonogramowanie (3000 ms) nadal zostaje zarejestrowane, a oryginalny wyjątek propaguje się i nie jest tłumiony przez scheduler.
* Istnieje wyraźne rozróżnienie pomiędzy: osiem początkowych wywołań `after`, bezpośredni synchroniczny start `auto_rescan` oraz pierwsze recurrence 3000 ms rejestrowane po direct call.

### B. Cykliczne usługi (Shopify Produkcja, Shopify Księgowość, Cure, Social Publisher)
* Semantyka harmonogramu:
  1. Wywołaj callback triggera.
  2. Callback uruchamia daemon thread i wraca natychmiast bez oczekiwania na wątek roboczy.
  3. Dopiero po pomyślnym powrocie triggera (z wątku głównego) zarejestruj następny tick.
  4. Nie czekaj na zakończenie workera.
* Jeśli trigger rzuci wyjątek na wątku głównym przed powrotem, scheduler **nie może** zarejestrować następnego ticka (zgodnie z zachowaniem oryginalnego kodu).
* Zabraniamy planowania kolejnego ticka przed wywołaniem callbacku triggera.

### C. Usługi jednorazowe (Monthly remindery, Daily backup, Weekly content reminder)
* Zdarzenia one-shot są uruchamiane tylko raz przy starcie aplikacji (z odpowiednimi opóźnieniami) i nie są rejestrowane ponownie.

## 19. Error semantics
Scheduler zachowuje obecne zachowanie i nie wprowadza globalnego tłumienia wyjątków (`except Exception: pass`). Wyjątki rzucane na wątku głównym przez callbacki są propagowane zgodnie z logiką Pythona.

## 20. RuntimeError semantics
Wyjątki `RuntimeError` rzucane z Tkinter (np. podczas wywołania `after` po zniszczeniu głównego okna `root` aplikacji) muszą być bezpiecznie przechwytywane i ignorowane przez Scheduler wyłącznie w tych miejscach harmonogramowania, w których obecny launcher już je przechwytuje. Nie zmieniamy zachowania początkowych wywołań `after` ani nie wprowadzamy logiki retry czy backoff.

## 21. Dependencies allowed
* Moduł `giclee_app/launcher_background_services.py` może importować standardowe biblioteki Pythona (`typing`, `collections.abc`).

## 22. Dependencies forbidden
* Zakaz importowania `customtkinter` i `tkinter` (poza typowaniem ad-hoc w adnotacjach) w module schedulera.
* Zakaz importu jakichkolwiek modułów z przestrzeni `Komponenty`.
* Zakaz bezpośredniego dostępu do zmiennych stanowych interfejsu graficznego (np. `status_var`, okien dialogowych).
* Zakaz wykonywania operacji I/O, zapisu plików i wyzwalania powiadomień przez scheduler.
* Zakaz używania `time.sleep` w kodzie schedulera.
* Studio nie importuje ani nie uruchamia schedulera.

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
Testy w `cursor-api/tests/test_launcher_background_services.py` i `cursor-api/tests/test_launcher_composition.py` muszą zweryfikować:
1. **Exact registration order:** Sprawdzenie, czy konstruktor schedulera przyjmuje argumenty w exact registration order, bez sortowania według opóźnień.
2. **Expected firing order:** Weryfikacja opóźnień początkowych (800, 1500, 2000, 3000, 15000, 30000, 35000, 45000) jako osobnego zestawu faktów.
3. **Synchronous auto-rescan:** Sprawdzenie, czy `auto_rescan` jest wywoływany synchronicznie podczas startu schedulera.
4. **Initial after schedules:** Weryfikacja, że pozostałe 8 usług rejestruje początkowe opóźnienia przez `after`.
5. **Recurrence in finally:** Weryfikacja, że po wykonaniu `auto_rescan` planowany jest kolejny tick 3000 ms w bloku `finally`.
6. **Exception propagation for rescan:** Test sprawdzający, czy wyjątek z `auto_rescan` propaguje się na zewnątrz, ale kolejne wywołanie 3000 ms zostaje poprawnie zaplanowane.
7. **Callback-before-reschedule:** Dla usług cyklicznych (Shopify, cure, social publisher) kolejny tick jest planowany dopiero po pomyślnym zakończeniu callbacku triggera.
8. **No reschedule on exception:** Test sprawdzający, czy rzucenie wyjątku przez callback triggera w cyklicznej usłudze blokuje planowanie kolejnego ticka (brak reschedule).
9. **Monthly reminders:** Sprawdzenie, że oba remindery miesięczne są wywoływane jako osobne callbacki i współdzielą klucz `monthly_plan` bez deduplikacji.
10. **Brak prawdziwych wątków i I/O:** Testy schedulera nie mogą tworzyć prawdziwych wątków ani wykonywać operacji I/O.
11. **Brak time.sleep:** Testy nie mogą korzystać z `time.sleep` i nie mogą czekać rzeczywistych milisekund.
12. **Brak timer IDs i cancellation:** Testy weryfikują brak mechanizmów cancellation, jitter, retry i backoff.
13. **Source guards:** Weryfikacja braku niedozwolonych importów z `Komponenty`, `tkinter` oraz `customtkinter`.
14. **Studio integration check:** Potwierdzenie, że moduł Studio nie importuje schedulera.
15. **Liczba daemon threads:** Utrzymanie stabilnej liczby wątków roboczych daemon=True w integracji launchera.
16. **Ochrona timerów wyłączonych z zakresu:** Upewnienie się, że timery wyłączone z LC-5 (fokus, watcher, log preview, generator delay) nie zostały naruszone.

## 26. Source guards
* `launcher_background_services.py` nie importuje `Komponenty`, `tkinter` ani `customtkinter`.
* `launcher.py` nie posiada bezpośrednich odwołań do `root.after` dla harmonogramowania tych 9 usług (całość delegowana do `LauncherBackgroundServices`).
* Moduł testowy nie używa `time.sleep()`.

## 27. Validation commands
```powershell
python -m pytest cursor-api/tests/test_launcher_background_services.py
python -m pytest cursor-api/tests/test_launcher_composition.py
```

## 28. Rollback boundary
* **Docs-only kontrakt:** W razie problemów rollback do commitu `c41bada4fac9e4a90dd43597893c682fd2dc6e93`.
* **Przyszła implementacja:** W razie regresji rollback do nowego `master` zawierającego już scalony kontrakt. Rollback kodu produkcyjnego nie powinien usuwać zatwierdzonego kontraktu.

## 29. Completion criteria
Formalne zamknięcie LC-5 wymaga spełnienia poniższych warunków:
1. Kontrakt LC-5 został scalony do gałęzi `master`.
2. Implementacja jest w pełni zgodna z exact API i allowlistą.
3. Focused test suite przechodzi na zielono (`green`).
4. `git diff --check` nie zgłasza żadnych błędów.
5. Budowanie Hermetic na CI kończy się powodzeniem (`green`).
6. Exact-head re-review zakończone zatwierdzeniem.
7. Hermetic smoke testy na zielono.
8. Tk GUI manual smoke testy na zielono.
9. Pełna baza pytestów na zielono (`full pytest baseline green`).
10. Raport JUnit nie zawiera żadnych błędów ani awarii.
11. Runtime inventory nie wykazuje nowych problemów architektonicznych.
12. Status brancha: `behind_by=0`, brak otwartych wątków review, status `mergeable`.
13. Squash merge wykonany przy użyciu `expected_head_sha`.
14. Potwierdzony i zwalidowany nowy commit `master`.

Dopiero po spełnieniu wszystkich powyższych warunków można rozpocząć fresh reconnaissance kolejnego etapu (LC-6).
