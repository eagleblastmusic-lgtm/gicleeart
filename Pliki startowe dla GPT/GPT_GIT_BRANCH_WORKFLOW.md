# GPT Git Branch Workflow

Praktyczny przewodnik po bezpiecznej współpracy GPT ↔ GitHub ↔ lokalne monorepo `C:\Strona\pusty`.

**Źródło prawdy po akceptacji:** lokalne pliki w monorepo — nie branch GPT, nie snapshot theme, nie osobne repo `gicleeapp` bez importu.

Szczegóły trybów A/B: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md` § GPT GIT BRANCH IMPLEMENTATION MODE.

---

## 1. Architektura trzech remote’ów

Lokalne repozytorium: **`C:\Strona\pusty`** — jedno monorepo. Folder `cursor-api/` **nie** jest osobnym lokalnym repo Git (`git rev-parse --show-toplevel` z `cursor-api/` wskazuje `C:/Strona/pusty`).

| Remote | URL | Rola |
|--------|-----|------|
| `origin` | `https://github.com/eagleblastmusic-lgtm/gicleeart.git` | Właściwa historia lokalnego monorepo Giclée Art |
| `gpt` | `https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git` | Kanoniczny alias dokumentacji dla snapshota motywu Shopify |
| `gicleeapp` | `https://github.com/eagleblastmusic-lgtm/gicleeapp.git` | Zawartość aplikacji lokalnie pod prefiksem `cursor-api/` |

Zanim użyjesz nazwy remote, wykonaj `git remote -v`. Aktualna maszyna może mieć dodatkowy alias `gicleeart-gpt` wskazujący ten sam URL co `gpt`. Preferuj `gpt` w dokumentacji, ale nie dodawaj duplikatu, jeśli równoważny remote już istnieje. Nowy remote dodaj tylko wtedy, gdy żaden istniejący alias nie wskazuje właściwego repo.

```text
C:\Strona\pusty (monorepo, origin)
├── motyw Shopify (assets, sections, templates, …)
├── cursor-api/          ← odpowiada root gicleeapp na GitHub
│   ├── Komponenty/
│   ├── giclee_app/
│   └── package.json
└── Pliki startowe dla GPT/
```

---

## 2. Różnica: snapshot theme vs GicleeApp vs monorepo

| Warstwa | Repo GitHub | Lokalnie | Uwaga |
|---------|-------------|----------|--------|
| **Snapshot theme** | `gicleeart-gpt` (`gpt`) | working tree motywu w monorepo | Nie jest produkcją/live; branch GPT = wymiana kodu motywu |
| **GicleeApp** | `gicleeapp` | `cursor-api/` | Ścieżki w repo bez prefiksu `cursor-api/` |
| **Monorepo** | `gicleeart` (`origin`) | `C:\Strona\pusty` | Finalny commit po lokalnej akceptacji |

---

## 3. Workflow branch — motyw Shopify

**Repo:** `eagleblastmusic-lgtm/gicleeart-gpt` (kanoniczny alias w dokumentacji: `gpt`)

1. GPT tworzy branch roboczy, np. `gpt-work/home-stack-fix`.
2. GPT implementuje wyłącznie pliki związane z zadaniem i podaje Base SHA, Commit SHA oraz dokładną listę plików.
3. Użytkownik sprawdza aliasy i pobiera branch:

```powershell
cd C:\Strona\pusty
git remote -v
git -c maintenance.auto=false -c gc.auto=0 fetch gpt --prune
```

Jeżeli alias `gpt` nie istnieje, ale `gicleeart-gpt` wskazuje ten sam URL, użyj istniejącego aliasu w komendach. Nie twórz kolejnego duplikatu.

4. Wybierz sposób importu:

### A. Dokładne pliki przez `git restore`

Stosuj tylko wtedy, gdy wskazane lokalne pliki są czyste i snapshot jest zgodny z bieżącym lokalnym stanem:

```powershell
git restore `
  --source gpt/gpt-work/home-stack-fix `
  -- assets/giclee-home-stack.css `
     assets/giclee-home-stack.js `
     templates/index.json
```

### B. Patch-first — preferowany przy nowszym lub dirty working tree

```powershell
$patch = Join-Path $env:TEMP "gicleeart-theme-change.patch"
Remove-Item $patch -Force -ErrorAction SilentlyContinue

git diff `
  --binary `
  --output="$patch" `
  <BASE_SHA>..<COMMIT_SHA> `
  -- `
  assets/giclee-home-stack.css `
  assets/giclee-home-stack.js `
  templates/index.json

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $patch) -or (Get-Item $patch).Length -eq 0) {
  throw "Nie udało się utworzyć patcha motywu."
}

git apply --check "$patch"
if ($LASTEXITCODE -ne 0) {
  throw "Patch motywu koliduje z lokalnymi plikami. Niczego nie zastosowano."
}

git apply "$patch"
```

5. Kontrola:

```powershell
git status --short
git diff -- `
  assets/giclee-home-stack.css `
  assets/giclee-home-stack.js `
  templates/index.json
```

6. Test lokalny → akceptacja → dopiero wtedy finalny commit w monorepo.

**W PowerShell nie generuj patcha przekierowaniem `>`**. Używaj `git diff --output="$patch"`, aby uniknąć pliku z kodowaniem, którego `git apply` nie rozpozna.

---

## 4. Workflow branch — GicleeApp

**Repo:** `eagleblastmusic-lgtm/gicleeapp` (remote `gicleeapp`)

Ścieżki w repo `gicleeapp` (root):
- `Komponenty/...`
- `giclee_app/...`
- `package.json`

Lokalnie odpowiadają im ścieżki pod `cursor-api/`.

**Nie wolno:** merge brancha `gicleeapp` do monorepo, `git checkout gicleeapp/... -- .`, kopiowanie całego repo do root monorepo ani szeroki rollback `cursor-api/`, gdy istnieją niezwiązane lokalne zmiany.

1. GPT tworzy branch `gpt-work/<task-slug>` i podaje Base SHA, Commit SHA oraz dokładną listę plików.
2. Użytkownik pobiera branch:

```powershell
cd C:\Strona\pusty
git -c maintenance.auto=false -c gc.auto=0 fetch gicleeapp --prune
```

3. Utwórz patch przez `--output`, nie przez `>`:

```powershell
$patch = Join-Path $env:TEMP "gicleeapp-change.patch"
Remove-Item $patch -Force -ErrorAction SilentlyContinue

git diff `
  --binary `
  --output="$patch" `
  <BASE_SHA>..<COMMIT_SHA> `
  -- `
  Komponenty/example.py `
  tests/test_example.py

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $patch) -or (Get-Item $patch).Length -eq 0) {
  throw "Nie udało się utworzyć patcha GicleeApp."
}
```

4. Test apply z prefiksem lokalnym:

```powershell
git apply --check --directory=cursor-api "$patch"
if ($LASTEXITCODE -ne 0) {
  throw "Patch GicleeApp koliduje z lokalnymi plikami. Niczego nie zastosowano."
}
```

5. Po PASS:

```powershell
git apply --directory=cursor-api "$patch"
```

6. Kontrola dokładnego zakresu:

```powershell
git status --short
git diff -- `
  cursor-api/Komponenty/example.py `
  cursor-api/tests/test_example.py
```

7. Sprzątanie:

```powershell
Remove-Item "$patch" -ErrorAction SilentlyContinue
```

Skrót `gicleeapp/main...gicleeapp/gpt-work/<branch>` jest dozwolony tylko, gdy branch faktycznie bazuje na bieżącym `gicleeapp/main`. Przy rozjechanym snapshocie zawsze używaj jawnego Base SHA z raportu GPT.

---

## 5. Import zmian — zasady ogólne

- Importuj **tylko** pliki lub patch wskazany w raporcie GPT.
- Nie importuj całego snapshota ani całego brancha bez listy plików.
- Przy zadaniu cross-repo utwórz osobny patch dla GicleeApp i osobny dla motywu. **Oba `git apply --check` muszą przejść przed zastosowaniem któregokolwiek patcha.**
- Po imporcie zawsze `git status` + `git diff` na zaimportowanym zakresie.
- Kod z brancha GPT **nie jest finalny** bez lokalnego testu i świadomej akceptacji.
- Dirty working tree nie jest powodem do `reset`/`clean`; jest sygnałem do jeszcze węższego zakresu patcha i rollbacku.

---

## 6. Kontrola diff

- Theme: `git diff -- <lista-plików-motywu>`
- GicleeApp: `git diff -- cursor-api` (lub węższa lista ścieżek)
- Porównuj z opisem zmian w raporcie GPT.
- Jeśli diff obejmuje pliki spoza zadania — **nie commituj**; cofnij import (§9).

---

## 7. Test lokalny

Przed finalnym commitem w monorepo:

- uruchom testy dopasowane do zakresu (patrz COMPACT v38 § ZASADY TESTOWANIA),
- ręcznie sprawdź UI/flow dotknięty zmianą,
- użytkownik decyduje o akceptacji — GPT nie traktuje swojego commita jako wdrożenia.

---

## 8. Akceptacja

Po pozytywnym teście:

1. Jawny `git add <lista-plików>` — unikaj `git add .`
2. Commit w monorepo `C:\Strona\pusty`
3. Push `origin` tylko po osobnej decyzji użytkownika
4. Kolejny snapshot theme (`gpt`) / push GicleeApp — dopiero ze zweryfikowanego lokalnego stanu

---

## 9. Cofnięcie zmian (rollback)

**Pojedyncze pliki (przed commitem):**

```powershell
git restore -- <ścieżka-do-pliku>
```

**Import wielu plików GicleeApp (przed commitem):**

```powershell
git restore --source=HEAD --staged --worktree -- `
  cursor-api/Komponenty/example.py `
  cursor-api/tests/test_example.py
```

Używaj wyłącznie dokładnej listy zaimportowanych plików. **Nie wykonuj `git restore ... -- cursor-api`**, gdy katalog zawiera inne lokalne zmiany. Nowe pliki utworzone przez patch usuń pojedynczo dopiero po sprawdzeniu listy. `git clean` pozostaje zakazane.

**Po commicie:** `git revert` lub reset tylko po świadomej decyzji użytkownika — nie automatycznie.

---

## 10. Sprzątanie plików tymczasowych

```powershell
Remove-Item "$env:TEMP\gicleeapp-change.patch" -ErrorAction SilentlyContinue
```

Nie zostawiaj patchy w repo ani w stage.

---

## 11. Typowe błędy i zakazane komendy

| Zakaz | Powód |
|-------|--------|
| `git pull gpt ...` | Może nadpisać lokalną historię / pobrać cały snapshot |
| `git merge gpt/...` | Branch GPT nie jest finalną historią monorepo |
| `git merge gicleeapp/...` | Złe ścieżki — brak prefiksu `cursor-api/` |
| `git pull gicleeapp main` | Nie synchronizuj całego repo do monorepo |
| `git checkout gicleeapp/... -- .` | Kopiuje do root bez prefiksu |
| Import całego snapshota | Nadpisuje niezwiązane lokalne zmiany |
| `git add .` przy imporcie | Ryzyko stage runtime/config |
| `git diff ... > patch` w Windows PowerShell | Możliwe kodowanie/plik nierozpoznany przez `git apply`; użyj `--output` |
| `git restore ... -- cursor-api` przy dirty tree | Usuwa również niezwiązane prace lokalne |
| `git clean` | Ryzyko bezpowrotnego usunięcia nowych plików użytkownika |
| Merge / force push / deploy bez zgody | Guardrails brancha GPT |

---

## 12. Checklist — przed importem

- [ ] `git remote -v` sprawdzone; wybrany istniejący alias wskazuje właściwy URL
- [ ] Potwierdzone repo (`gpt` / równoważny alias theme vs `gicleeapp`)
- [ ] Potwierdzony branch `gpt-work/<task-slug>`
- [ ] Dla GicleeApp: **Base SHA** i **Commit SHA** z raportu GPT
- [ ] Lista zmienionych plików zgodna z zadaniem
- [ ] Brak plików runtime/config poza zakresem (`gpt_config.json`, `orders_sync_state.json`, …)
- [ ] `git fetch <remote> --prune` wykonany
- [ ] Patch utworzony przez `git diff --output`, ma niezerowy rozmiar
- [ ] Dla cross-repo oba patche przechodzą `--check` przed pierwszym `git apply`
- [ ] Nie planujesz `merge`, `pull`, szerokiego `restore` ani `clean`

---

## 13. Checklist — po imporcie

- [ ] `git status --short` — tylko oczekiwane pliki
- [ ] `git diff` na zaimportowanym zakresie
- [ ] Test lokalny PASS
- [ ] Patch tymczasowy usunięty
- [ ] Jawny `git add <lista>` przed commitem
- [ ] Brak przypadkowego stage plików runtime

---

## 14. Format raportu GPT (obowiązkowy po implementacji na branchu)

GPT przekazuje użytkownikowi:

```text
Repo: eagleblastmusic-lgtm/gicleeart-gpt | eagleblastmusic-lgtm/gicleeapp
Remote alias used locally: gpt | gicleeart-gpt | gicleeapp
Branch: gpt-work/<task-slug>
Base SHA: <pełny SHA bazy brancha — obowiązkowy dla patch-first>
Commit SHA: <pełny SHA commita z implementacją>
Changed files:
  - <ścieżka/względem repo>
  - …
Opis zmian: <krótki opis>
Import command: <gotowe polecenia PowerShell>
Verification: git status --short; git diff -- <zakres>
Rollback: git restore -- <pliki> lub instrukcja cofnięcia patcha
Push status: branch pushed, main untouched
```

**Uwagi:**

- Nie wpisuj fikcyjnych SHA.
- Dla motywu Base SHA = commit, od którego odgałęziono branch (jeśli istotny); Commit SHA = HEAD brancha.
- Dla GicleeApp **Base SHA i Commit SHA są obowiązkowe** w kanonicznym `git diff --binary <BASE_SHA>..<COMMIT_SHA>`.
- `Push status` dla zwykłego brancha roboczego: `branch pushed, main untouched`.

**Przykład (szablon — uzupełnij prawdziwymi wartościami):**

```text
Repo: eagleblastmusic-lgtm/gicleeart-gpt
Branch: gpt-work/home-stack-fix
Base SHA: <BASE_SHA>
Commit SHA: <COMMIT_SHA>
Changed files:
  - assets/giclee-home-stack.css
  - assets/giclee-home-stack.js
  - templates/index.json
Import command:
  git fetch gpt --prune
  git restore --source gpt/gpt-work/home-stack-fix -- assets/giclee-home-stack.css assets/giclee-home-stack.js templates/index.json
Verification:
  git status --short
  git diff -- assets/giclee-home-stack.css assets/giclee-home-stack.js templates/index.json
Rollback:
  git restore -- assets/giclee-home-stack.css assets/giclee-home-stack.js templates/index.json
Push status: branch pushed, main untouched
```

<!-- gpt-window-2:powershell-import-hardening:start -->
## Addendum — PowerShell import i reconcile hardening

Poniższe zasady wynikają z realnych problemów wykrytych podczas importu brancha do lokalnego monorepo.

### 1. Używaj absolutnego katalogu repo

Nie zakładaj, że:

- bieżący katalog PowerShell,
- katalog procesu .NET,
- katalog wyświetlany w promptcie

są zawsze identyczne.

Bezpieczny wzorzec:

```powershell
$root = (
  Resolve-Path -LiteralPath "C:\Strona\pusty"
).Path

git -C $root status

$filePath = Join-Path `
  $root `
  "assets\example.js"

$text = [System.IO.File]::ReadAllText($filePath)
```

Do `[System.IO.File]::ReadAllText()`, `ReadAllBytes()`, `WriteAllText()` i podobnych metod przekazuj ścieżki absolutne.

### 2. Nie używaj `git show --output` jako pewnego zapisu bloba

Dla pojedynczego pliku z commita bezpieczniej przechwycić stdout:

```powershell
$lines = @(
  git -C $root show `
    "${sha}:assets/example.js"
)

if ($LASTEXITCODE -ne 0 -or $lines.Count -eq 0) {
  throw "Nie udało się odczytać pliku z commita."
}

$text = $lines -join "`n"
```

Nie zakładaj, że:

```powershell
git show --output="$file" "$sha`:path"
```

zawsze zapisze blob bez wypisywania go do terminala.

### 3. Patch może być już częściowo obecny lokalnie

Gdy `git apply --check` zwraca:

* `already exists in working directory`,
* `patch does not apply`,

nie używaj automatycznie `--force`, nie usuwaj plików i nie resetuj repo.

Najpierw:

1. odczytaj wzorcowy blob z brancha,
2. porównaj z lokalnym plikiem po normalizacji LF/CRLF i BOM,
3. sprawdź, czy loader lub wpis konfiguracyjny już istnieje,
4. wykonaj idempotentny reconcile tylko dokładnych plików,
5. zachowaj backup.

### 4. `git diff --stat` nie pokazuje plików untracked

Nowy plik oznaczony jako:

```text
?? assets/example.js
```

nie pojawi się w zwykłym `git diff --stat`.

Końcowy raport powinien zawierać oba polecenia:

```powershell
git -C $root status --short -- <dokładne-pliki>
git -C $root diff --stat -- <dokładne-pliki>
```

### 5. Standard importu pozostaje bez zmian

* `git diff --binary --output="$patch"` zamiast `>`,
* `git apply --check` przed `git apply`,
* przy zadaniu cross-repo oba checki muszą przejść przed pierwszym apply,
* tylko dokładna lista plików,
* backup przed reconcile,
* bez `git add .`,
* bez `git clean`,
* bez szerokiego `restore`,
* bez merge, push i deployu bez jawnej zgody użytkownika.

<!-- gpt-window-2:powershell-import-hardening:end -->

<!-- gpt-window-3:transactional-reconcile-state:start -->
## Addendum — stan transakcji, ponowienia i porównywanie plików

### 1. Rozróżniaj etap, na którym wystąpił błąd

Nie każdy błąd oznacza, że „niczego nie zastosowano”.

- błąd preflight przed `git apply`, `git restore`, zapisem lub usunięciem — working tree nie został zmieniony,
- błąd po zastosowaniu plików, np. podczas `node --check` lub `git diff --check` — część albo całość zmian może już istnieć lokalnie.

Po błędzie post-apply:

1. sprawdź `git status --short`,
2. sprawdź istnienie plików docelowych,
3. nie uruchamiaj ponownie preflightu wymagającego, aby nowe pliki nie istniały,
4. kontynuuj od naprawy i końcowej walidacji albo wykonaj świadomy rollback z backupu.

### 2. `git diff <branch> -- <path>` nie jest testem zawartości pliku untracked

Dla plików `??` Git może potraktować plik jako nieobecny względem drzewa brancha.

Przy weryfikacji plików tracked i untracked osobno sprawdzaj:

- czy plik istnieje,
- wzorcowy blob z konkretnego brancha lub SHA,
- rzeczywistą zawartość pliku,
- końcowy status Git.

Nie opieraj całego preflightu na jednym `git diff --quiet <branch>`.

### 3. Nie porównuj UTF-8 przez niejawne dekodowanie PowerShell

`Get-Content`, przechwytywanie stdout programu natywnego i konsola mogą użyć różnych sposobów dekodowania. Może to wytworzyć różne formy mojibake mimo identycznej logiki.

Wzorzec z przechwytywaniem `git show` do tablicy linii jest odpowiedni do inspekcji tekstowej, ale nie do byte-exact verification.

Dla dokładnej kontroli:

- użyj absolutnych ścieżek,
- pobierz blob bez transformacji tekstowej,
- porównaj surowe bajty,
- jeśli dopuszczasz różnicę systemową, normalizuj wyłącznie CRLF do LF,
- nie zmieniaj kodowania, BOM ani znaków Unicode bez świadomej decyzji.

### 4. Targeted restore jako kontrolowany fallback

Jeśli patch nie może zostać bezpiecznie zastosowany, ponieważ working tree zawiera już wcześniejsze etapy tej samej funkcji, dopuszczalny jest precyzyjny:

```powershell
git restore --source="<przypięty-branch>" --worktree -- <dokładna-lista-plików>
```

Wyłącznie gdy:

* branch i HEAD zostały zweryfikowane,
* zakres obejmuje tylko uzgodnione pliki,
* aktualne źródła zostały zinwentaryzowane,
* utworzono backup,
* cudze zmiany nie są nadpisywane,
* stare pliki usuwa się dopiero po potwierdzeniu integracji ich zachowania,
* po operacji wykonywane są testy składni, whitespace i porównanie z targetem.

Nie jest to zgoda na szeroki restore całego repozytorium.

### 5. Retry musi być idempotentny

Skrypt ponawiany po częściowym zastosowaniu powinien:

* rozpoznać pliki już zgodne z targetem,
* nie zgłaszać ich automatycznie jako konflikt,
* nie usuwać ich przed porównaniem,
* przejść do brakującego kroku lub walidacji,
* raportować, czy jest w fazie preflight, apply czy post-apply.

### 6. Końcowa pusta linia też może przerwać walidację

Po zapisaniu krótkich plików loaderów i konfiguracji zawsze wykonaj:

```powershell
git diff --check -- <dokładne-pliki>
```

Komunikat `new blank line at EOF` oznacza dodatkową pustą linię na końcu pliku. Plik powinien kończyć się pojedynczym znakiem nowej linii, bez dodatkowego pustego wiersza.

<!-- gpt-window-3:transactional-reconcile-state:end -->
