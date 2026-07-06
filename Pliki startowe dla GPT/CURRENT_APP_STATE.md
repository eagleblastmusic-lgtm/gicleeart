# Current App State

GicleeApp Studio v1.37.0

Canonical HEAD / origin/master:
16febff71dd2aad397f6c35ff8b8eef896abbb49

Completed:
- Background Builder local v1: frozen
- Administracja strony rebuild strategy: done
- Katalog rebuild plan: done
- Katalog F1 read-only shell: done
- Katalog F2 bounded data map: done

Not started:
- F5.5 Shopify / sync / deploy
- Katalog writer
- Katalog Shopify integration
- Katalog migration

Next recommended:
Katalog local planning layer:
- local draft state
- dry-run
- readiness
- UI planu zmian
- zero write
- zero Save

Important guardrails:
- Knowledge pack source folder: `C:\Strona\pusty\Pliki startowe dla GPT` (edit sources here; regenerate ZIP — do not treat ZIP as source of truth)
- Do not start writer in the next step.
- Do not add Save/Zapisz/Zastosuj in the next step.
- Do not touch Shopify/sync/deploy.
- Do not mutate Komponenty/* runtime data.
- Katalog F2 is read-only and must remain read-only.
- tldobio is absorbed into Katalog, not a standalone Studio v2 main tile.
- Background Builder local v1 is the Level 2 reference implementation.
