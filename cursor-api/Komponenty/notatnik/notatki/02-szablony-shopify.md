# Szablony Shopify - workflow

## Sciaganie szablonu
```
mkdir nazwa-szablonu
cd nazwa-szablonu
shopify theme pull --live --store=twoj-sklep.myshopify.com
```
Mozesz tez sciagnac inny niz live theme:
```
shopify theme list
shopify theme pull --theme=1234567890
```

## Lokalna edycja
1. `shopify theme dev` - uruchamia lokalny serwer (zwykle `http://127.0.0.1:9292`).
2. Edytujesz pliki w Cursorze (folder `sections/`, `templates/`, `snippets/`,
   `assets/`, `config/`).
3. Browser auto-przeladowuje sie po kazdym zapisie.

## Wysylka zmian
- Test: stworz **kopie** szablonu przez Shopify Admin -> Themes -> Customize -> Duplicate.
- Wyslij zmiany do **kopii** (nie live!):
  ```
  shopify theme push --theme=<ID-kopii>
  ```
- Sprawdz na froncie -> dopiero potem promote do live:
  ```
  shopify theme publish --theme=<ID-kopii>
  ```

## Co NIE wchodzi w git
W `.gitignore` szablonu:
```
config/settings_data.json
node_modules/
.shopify/
```
`settings_data.json` zawiera ustawienia konkretnego sklepu - inne dla dev/live.
