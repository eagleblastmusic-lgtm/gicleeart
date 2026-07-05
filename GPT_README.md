# GicleeArt — snapshot motywu dla Custom GPT

To repo jest **lustrem read-only** motywu Shopify (bez `cursor-api/`, backupów, `.env`).

> Snapshot jest kopią lokalnego working tree motywu Shopify. Nie musi odpowiadać ostatniemu commitowi głównego repo ani stanowi live. GPT powinien traktować snapshot jako materiał review, a nie jako źródło prawdy o produkcji.

## Dla Custom GPT

- **Rola:** architekt + code reviewer + ocena UX (nagrania / PNG w `docs/review-demos/`).
- **Indeks sesji:** `REVIEW_MANIFEST.json` + `SYNC_NOTES.md`.
- **Review wizualny:** `latest-desktop.webm`, `latest-mobile.webm`, `latest-*.png`, `console-errors.txt`.

Workflow: GPT planuje → user wkleja prompt do Cursor → push z GicleeApp → GPT ocenia.

## Jak interpretować snapshot

Ten snapshot jest kopią lokalnego working tree motywu Shopify. Nie musi odpowiadać ostatniemu commitowi głównego repo ani stanowi live/production.

GPT powinien traktować snapshot jako paczkę review, a nie jako źródło prawdy o produkcji.

## changed_files

Pole `changed_files` w `REVIEW_MANIFEST.json` oznacza pliki zaktualizowane podczas synchronizacji lustra na podstawie porównania hashy przed/po kopiowaniu.

To **nie** jest pełny git diff względem głównego repo, master/main ani produkcji.

## snapshot_commit

Pole `snapshot_commit` jest dostępne tylko po pushu do repo snapshot.

W trybie **Review package only** może mieć wartość `null`, ponieważ paczka została wygenerowana lokalnie i nie została jeszcze wypchnięta do GitHuba.

## recordings / screenshots / console_errors

Manifest może zawierać standardowe ścieżki do plików webm, PNG i console log.

Te pliki istnieją tylko wtedy, gdy w danej sesji wykonano nagranie / review package z nagrywaniem.

Jeśli wykonano tylko sync bez nagrania, GPT **nie** powinien zakładać, że webm/PNG/console log faktycznie istnieją.

## routes_recorded

W Fazie A `routes_recorded` zwykle zawiera tylko ostatnią nagraną trasę, najczęściej `/`.

Wiele tras będzie dopiero elementem późniejszej fazy.

## console-errors.txt

`console-errors.txt` zawiera błędy i warningi zebrane przez Playwright podczas nagrania.

Nie obejmuje ręcznego testowania strony w przeglądarce ani błędów zauważonych poza Playwrightem.

## commit timezone

Commit message może używać czasu UTC. Przy sesjach wieczornych data/godzina może różnić się od lokalnej strefy czasu w Polsce.

## snapshot_commit a HEAD

Pole `snapshot_commit` jest zapisywane tuż przed `git commit --amend`. Jeśli różni się od SHA ostatniego commita na branchu, **użyj SHA z pusha / `git log -1`** jako punktu review — to commit zawierający aktualny manifest i snapshot.
