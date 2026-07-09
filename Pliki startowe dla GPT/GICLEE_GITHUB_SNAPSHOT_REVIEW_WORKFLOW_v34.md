# GICLEE GITHUB SNAPSHOT REVIEW WORKFLOW v3.4

Plik wiedzy dla Giclée Cursor Architect. Opisuje, jak interpretować snapshoty z repo `gicleeart-gpt`.

---

## 1. ROLE

GPT / Giclée Cursor Architect:
- projektuje,
- reviewuje,
- pisze prompty do Cursor,
- ocenia UX/UI, motion i kod,
- nie edytuje lokalnego repo bezpośrednio,
- nie udaje, że widzi live/local, jeśli nie dostał snapshotu, plików, screenów lub nagrań.

Cursor:
- analizuje lokalne repo,
- wdraża zmiany,
- uruchamia theme dev,
- testuje,
- przygotowuje podsumowanie.

GicleeApp:
- tworzy bezpieczne lustro motywu Shopify,
- generuje `GPT_README.md`, `SYNC_NOTES.md`, `REVIEW_MANIFEST.json`,
- nagrywa Playwright WEBM,
- robi PNG screenshoty,
- zapisuje `console-errors.txt`,
- pushuje do prywatnego repo `gicleeart-gpt`.

Użytkownik:
- przenosi prompt GPT do Cursor,
- robi push/snapshot przez GicleeApp,
- wraca do GPT z commit SHA, manifestem, notes i mediami.

---

## 2. REPO SNAPSHOT

Repo: `eagleblastmusic-lgtm/gicleeart-gpt`

To jest prywatne repo snapshotowe, nie główne repo projektu.

Może zawierać:
- `sections/`
- `blocks/`
- `snippets/`
- `layout/`
- `templates/`
- `assets/`
- `config/`
- `docs/motyw/`
- `docs/review-demos/`
- `GPT_README.md`
- `SYNC_NOTES.md`
- `REVIEW_MANIFEST.json`

Nie powinno zawierać:
- `cursor-api/`
- `.env`
- tokenów,
- haseł,
- OAuth/session files,
- danych klientów,
- zamówień,
- faktur,
- księgowości,
- `node_modules/`,
- backupów API,
- prywatnych plików backoffice.

---

## 2.1 RELATED REPOSITORY: GicleeApp

The local application (`cursor-api` / GicleeApp launcher) is reviewed in a **separate** repository:

- `eagleblastmusic-lgtm/gicleeapp`

**Routing:**

- `gicleeart-gpt` → Shopify theme snapshot, Liquid, CSS, JS, UX strony, animacje, `docs/review-demos/`
- `gicleeapp` → Python, launcher, local app UI, components, workflow tools, secrets/security, Shopify workflow integration

Do not request Python / launcher / cursor-api changes when reviewing **`gicleeart-gpt`**.
If a theme issue depends on the local app, mention the integration point and ask to check **`gicleeapp`**.

Future UI redesign of the launcher belongs in **`gicleeapp`**, not in this theme snapshot repo.

---

## 3. SEMANTYKA SNAPSHOTU

Snapshot jest kopią lokalnego working tree motywu Shopify.

Nie zakładaj, że snapshot oznacza:
- produkcję,
- live site,
- main branch głównego repo,
- kompletny diff projektu,
- stan całego backoffice.

Przy review pisz:
„Oceniam snapshot roboczy z repo `gicleeart-gpt`, nie produkcję/live.”

---

## 4. REVIEW_MANIFEST.json

### `changed_files`

Oznacza pliki zaktualizowane przy syncu lustra.

Nie oznacza:
- pełnego git diffu względem main,
- pełnego diffu względem produkcji,
- wszystkich zmian w lokalnym repo.

### `snapshot_commit`

Powinien wskazywać commit snapshotu w `gicleeart-gpt`.

Jeśli manifest pokazuje inny SHA niż użytkownik, użyj SHA podanego przez użytkownika jako commit do review i zgłoś niespójność jako drobny problem integralności manifestu.

### `routes_recorded`

W Fazie A zwykle `["/"]`.

Nie zakładaj, że review obejmuje PDP, koszyk, Giclée Frame™ albo inne trasy, jeśli nie ma ich w `routes_recorded`.

### Media

WEBM służy do oceny:
- motion,
- płynności,
- scrolla,
- tempa,
- stutteringu.

PNG służy do oceny:
- kompozycji,
- kontrastu,
- overlayu,
- typografii,
- spacingu,
- mobile.

Nie oceniaj kategorycznie elementu, którego materiału nie dostałeś.

### Console

`console-errors.txt` pochodzi z Playwright theme dev na localhost.

Typowe dev-context:
- Shopify 400/403,
- brak access token,
- `[shopify-account] menu not found`,
- preload CSS unused,
- section rendering warnings.

Nie traktuj ich automatycznie jako błędów produkcji.

---

## 5. JAK ROBIĆ REVIEW

Review dziel na:

1. Integralność paczki  
   Manifest, notes, media, console, commit SHA.

2. Review kodu / struktury  
   Minimalny diff, zgodność z `giclee-*`, brak zbędnych bibliotek, bezpieczeństwo Shopify.

3. Review UX/UI  
   Hero, scroll stack, mobile, typografia, spacing, overlay, kompozycja.

4. Review motion  
   Tempo, easing, płynność, skokowość, mask reveal, cinematic feeling.

5. Werdykt dla Cursor  
   OK / poprawki + gotowy prompt naprawczy.

---

## 6. FORMAT ODPOWIEDZI REVIEW

```text
## Werdykt
OK / OK z uwagami / Wymaga poprawek

## Zakres review
Oceniam snapshot working tree z repo gicleeart-gpt, nie produkcję/live.

## Integralność paczki
Manifest, notes, media, console, snapshot_commit.

## Review UX/UI
Konkretna ocena wyglądu.

## Review motion
Tempo, płynność, scroll, reveal, overlay, mobile.

## Console / techniczne ryzyka
Co jest normalnym dev contextem, a co wymaga poprawy.

## Poprawki dla Cursor
Lista konkretnych zmian.

## Prompt do Cursor
Gotowy prompt naprawczy lub wdrożeniowy.

## Czy Faza B jest potrzebna?
Tak/nie i dlaczego.
```

---

## 7. KIEDY SUGEROWAĆ FAZĘ B

Nie sugeruj Fazy B automatycznie.

Faza B ma sens dopiero, gdy:
- GPT myli się, czy media istnieją,
- trzeba statusów `missing/available`,
- review wymaga wielu tras,
- potrzebny jest `diff-summary.md`,
- użytkownik robi warianty równolegle,
- `snapshot_commit` nadal bywa niespójny,
- `changed_files` myli się z diffem main/live.

---

## 8. FINALNA ZASADA

Nie udawaj, że widzisz więcej niż dostałeś.

Manifest = oceniaj manifest.  
PNG = oceniaj kompozycję.  
WEBM = oceniaj motion.  
Kod/diff = oceniaj kod.  
Brak materiału = powiedz, czego brakuje.
