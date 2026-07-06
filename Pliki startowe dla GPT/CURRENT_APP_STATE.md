# Current App State

GicleeApp Studio v1.38.0

Monorepo local HEAD / origin/master:
65e862be05183cac9e6ca94786802035cf77b943

gicleeapp main:
a056bb5

Recent context:
- Push GicleeApp denylist hotfix e844789: done + pushed

Completed:
- Background Builder local v1: frozen
- Administracja strony rebuild strategy: done
- Katalog rebuild plan: done
- Katalog F1 read-only shell: done
- Katalog F2 bounded data map: done
- Katalog local planning layer F3+F4: done (draft state, dry-run, readiness, UI planu zmian)

Not started:
- F5.5 Shopify / sync / deploy
- Katalog writer
- Katalog Shopify integration
- Katalog migration

Next recommended:
Katalog bounded writer / save layer — only after separate acceptance:
- zero Shopify / sync / deploy
- zero Save / Zapisz / Zastosuj without explicit approval
- do not mutate Komponenty/* runtime data

Important guardrails:
- Knowledge pack source folder: `C:\Strona\pusty\Pliki startowe dla GPT` (edit sources here; regenerate ZIP — do not treat ZIP as source of truth)
- Do not start writer without separate approval.
- Do not add Save/Zapisz/Zastosuj without separate approval.
- Do not touch Shopify/sync/deploy.
- Do not mutate Komponenty/* runtime data.
- Katalog F2 is read-only and must remain read-only.
- tldobio is absorbed into Katalog, not a standalone Studio v2 main tile.
- Background Builder local v1 is the Level 2 reference implementation.
