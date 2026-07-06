# Current App State

GicleeApp Studio v1.40.1

Monorepo HEAD / origin/master:
4647c1b feat(studio): GICLÉE FRAME F2.1 editor workflow polish (v1.40.1)

Previous checkpoint:
46fc718 feat(studio): add GICLÉE FRAME page inventory RAM editor (v1.40.0)

Branch status:
master synced with origin/master (F2.1 pushed)

GPT starter files:
refreshed after F2.1 close (paczka v37; źródło = ten folder, nie ZIP)

Recent context:
- GICLÉE FRAME™ F2.1: closed + pushed on origin/master
- Local runtime/untracked still outside commit and remote (working tree hygiene pending)

Completed:
- Background Builder local v1: frozen
- Administracja strony rebuild strategy: done
- Katalog rebuild plan: done
- Katalog F1 read-only shell: done
- Katalog F2 bounded data map: done
- Katalog local planning layer F3+F4: done (draft state, dry-run, readiness, UI planu zmian)
- Push GicleeApp hygiene: done
- GICLÉE FRAME™ F2 page inventory + RAM editor foundation (v1.40.0): done
- GICLÉE FRAME™ F2.1 page editor workflow (v1.40.1): done
  - multi-variant RAM, type-aware editor, settings/reorder as RAM patches
  - trigger sekcji w nagłówku edytora, popup + drag reorder
  - dry-run, readiness accordion, F1 brand collapsed
- Studio Page Component Editor Pattern: documented (`gicleeframe-planning.md` §7, `admin-components-strategy.md`)

Not started:
- GICLÉE FRAME™ F3 — lokalny zapis draftów RAM do pliku
- GICLÉE FRAME™ F4 — bounded writer + backup/undo
- F5 / F5.5 preview quality / Shopify sync-deploy
- Katalog writer
- Katalog Shopify integration
- Katalog migration

Next recommended (choose one path — neither started):
- **A.** cleanup / runtime hygiene working tree (local M + untracked outside commits)
- **B.** GICLÉE FRAME™ F3 — lokalny zapis draftów RAM (no writer, no Save, no Shopify)

Technical backlog (only after separate acceptance):
- Katalog bounded writer / save layer
- zero Shopify / sync / deploy
- zero Save / Zapisz / Zastosuj without explicit approval
- do not mutate Komponenty/* runtime data from Studio panels

Important guardrails:
- Knowledge pack source folder: `C:\Strona\pusty\Pliki startowe dla GPT` — **Cursor edytuje tylko pliki źródłowe `.md` / `.txt` w tym folderze**
- **Cursor NIE generuje ZIP-a wiedzy** — bez osobnego, wyraźnego polecenia użytkownika
- ZIP wiedzy (`giclee_cursor_architect_knowledge_v37.zip`) generuje **automatycznie program użytkownika** przy wysyłce paczki przez **Okno rozmowy** (Integracja z GPT) — nie traktuj ZIP jako źródła prawdy
- Cursor nie uruchamia: `build_starter_knowledge_zip()`, GUI **Skopiuj .zip**, żadnego ręcznego generatora ZIP
- GICLÉE FRAME F2.1: RAM-only — no write_text, no writer, no sync/deploy, no Komponenty/* mutation from panel
- Do not start F3/F4/writer without separate approval
- Do not add Save/Zapisz/Zastosuj without separate approval
- Do not touch Shopify/sync/deploy
- Katalog F2 remains read-only
- tldobio absorbed into Katalog
- Background Builder local v1 = Level 2 reference (frozen)

Reference docs (repo):
- `cursor-api/giclee_app/docs/gicleeframe-planning.md`
- `cursor-api/giclee_app/docs/admin-components-strategy.md` (Giclee Frame = pattern reference)
