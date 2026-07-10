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
| `gpt` | `https://github.com/eagleblastmusic-lgtm/gicleeart-gpt.git` | Snapshot motywu Shopify — analiza, review, branchy robocze GPT |
| `gicleeapp` | `https://github.com/eagleblastmusic-lgtm/gicleeapp.git` | Zawartość aplikacji lokalnie pod prefiksem `cursor-api/` |

Nie dodawaj nowego remote — wszystkie trzy już istnieją.

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

**Repo:** `eagleblastmusic-lgtm/gicleeart-gpt` (remote `gpt`)

1. GPT tworzy branch roboczy, np. `gpt-work/home-stack-fix`.
2. GPT implementuje wyłącznie pliki związane z zadaniem.
3. GPT podaje raport (patrz §14).
4. Użytkownik pobiera zmiany lokalnie:

```powershell
cd C:\Strona\pusty
git fetch gpt --prune
```

5. Import **wyłącznie wskazanych plików**:

```powershell
git restore `
  --source gpt/gpt-work/home-stack-fix `
  -- assets/giclee-home-stack.css `
     assets/giclee-home-stack.js `
     templates/index.json
```

6. Kontrola:

```powershell
git status --short
git diff -- `
  assets/giclee-home-stack.css `
  assets/giclee-home-stack.js `
  templates/index.json
```

7. Test lokalny → akceptacja → dopiero wtedy finalny commit w monorepo.

---

## 4. Workflow branch — GicleeApp

**Repo:** `eagleblastmusic-lgtm/gicleeapp` (remote `gicleeapp`)

Ścieżki w repo `gicleeapp` (root):

- `Komponenty/...`
- `giclee_app/...`
- `package.json`

Lokalnie odpowiadają im:

- `cursor-api/Komponenty/...`
- `cursor-api/giclee_app/...`
- `cursor-api/package.json`

**Nie wolno:** merge brancha `gicleeapp` do monorepo, `git checkout gicleeapp/... -- .` bez prefiksu, kopiować całego repo do root monorepo, tworzyć `Komponenty/` lub `giclee_app/` bezpośrednio w `C:\Strona\pusty`.

1. GPT tworzy branch, np. `gpt-work/studio-component-fix`.
2. GPT **musi podać Base SHA i Commit SHA** w raporcie.
3. Użytkownik:

```powershell
cd C:\Strona\pusty
git fetch gicleeapp --prune
```

4. **Kanon:** patch z dokładnych SHA (GPT zawsze podaje oba):

```powershell
git diff --binary `
  <BASE_SHA>..<COMMIT_SHA> `
  > "$env:TEMP\gicleeapp-change.patch"
```

**Skrót** (tylko gdy branch bazuje dokładnie na aktualnym `gicleeapp/main`):

```powershell
git diff --binary `
  gicleeapp/main...gicleeapp/gpt-work/studio-component-fix `
  > "$env:TEMP\gicleeapp-change.patch"
```

Jeżeli branch powstał na innym commicie niż bieżący `gicleeapp/main`, użyj Base SHA z raportu GPT — nie zakładaj `main`.

5. Test apply:

```powershell
git apply `
  --check `
  --directory=cursor-api `
  "$env:TEMP\gicleeapp-change.patch"
```

6. Po PASS:

```powershell
git apply `
  --directory=cursor-api `
  "$env:TEMP\gicleeapp-change.patch"
```

7. Kontrola:

```powershell
git status --short
git diff -- cursor-api
```

8. Sprzątanie:

```powershell
Remove-Item "$env:TEMP\gicleeapp-change.patch" -ErrorAction SilentlyContinue
```

---

## 5. Import zmian — zasady ogólne

- Importuj **tylko** pliki lub patch wskazany w raporcie GPT.
- Nie importuj całego snapshota ani całego brancha bez listy plików.
- Po imporcie zawsze `git status` + `git diff` na zaimportowanym zakresie.
- Kod z brancha GPT **nie jest finalny** bez lokalnego testu i świadomej akceptacji.

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

**Cały import GicleeApp (przed commitem):**

```powershell
git restore --source=HEAD --staged --worktree -- cursor-api
```

(lub węższa lista plików z raportu)

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
| Merge / force push / deploy bez zgody | Guardrails brancha GPT |

---

## 12. Checklist — przed importem

- [ ] Potwierdzone repo (`gpt` vs `gicleeapp`)
- [ ] Potwierdzony branch `gpt-work/<task-slug>`
- [ ] Dla GicleeApp: **Base SHA** i **Commit SHA** z raportu GPT
- [ ] Lista zmienionych plików zgodna z zadaniem
- [ ] Brak plików runtime/config poza zakresem (`gpt_config.json`, `orders_sync_state.json`, …)
- [ ] `git fetch <remote> --prune` wykonany
- [ ] Nie planujesz `merge` ani `pull` całego remote

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
Branch: gpt-work/<task-slug>
Base SHA: <pełny SHA bazy brancha — obowiązkowy dla gicleeapp>
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
