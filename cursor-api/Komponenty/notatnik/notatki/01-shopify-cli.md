# Shopify CLI w Cursorze

## Logowanie
1. Otworz terminal w Cursorze (`Ctrl+\``).
2. Sprawdz czy CLI jest zainstalowane:
   ```
   shopify version
   ```
3. Zaloguj sie do swojego sklepu:
   ```
   shopify auth login
   ```
   Otworzy sie okno przegladarki - zatwierdz dostep.
4. Sprawdz aktualnie zalogowanego usera:
   ```
   shopify auth status
   ```

## Polaczenie ze sklepem
Po zalogowaniu wybierz sklep:
```
shopify theme dev --store=twoj-sklep.myshopify.com
```
LUB ustaw na stale w `shopify.theme.toml`:
```toml
[environments.development]
store = "twoj-sklep.myshopify.com"
theme = "1234567890"
```

## Czeste komendy
- `shopify theme list` - lista wszystkich szablonow w sklepie.
- `shopify theme pull --live` - sciagnij aktywny szablon.
- `shopify theme dev` - lokalny dev server z hot reload.
- `shopify theme push` - wysylka zmian na serwer.
- `shopify theme publish` - publikacja jako live theme.

## Trobleshoot
- **Bledy autoryzacji**: `shopify auth logout && shopify auth login`.
- **Wolne pull/push**: dodaj `--ignore` dla folderow ktorych nie ruszasz.
- **Konflikty**: zawsze `pull` przed `push` jesli ktos jeszcze pracuje na szablonie.
