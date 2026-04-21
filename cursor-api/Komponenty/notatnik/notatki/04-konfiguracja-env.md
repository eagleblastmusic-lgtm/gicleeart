# Konfiguracja .env

Plik `cursor-api/.env` (NIE commituj go!) zawiera klucze API uzywane przez
aplikacje.

## Wymagane klucze
```
# Shopify (dla 'Dodaj obraz')
SHOPIFY_STORE=twoj-sklep.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# SerpAPI (dla 'Nazwij obraz' - Google Lens)
SERPAPI_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Skad wziac
- **SHOPIFY_ACCESS_TOKEN**: Shopify Admin -> Apps -> Develop apps ->
  Create app -> Configure Admin API scopes (potrzebne: `read_products`,
  `write_products`, `write_files`) -> Install -> kopiuj token.
- **SERPAPI_KEY**: https://serpapi.com/ -> Free plan (100 zapytan/mc) lub
  platny.

## Sprawdzenie
```
python -c "from cursor_api.env_loader import env_get; print(env_get('SERPAPI_KEY')[:8] + '...')"
```

Jezeli nie ma klucza:
- `Dodaj obraz` -> upload nie zadziala.
- `Nazwij obraz` -> Lens pominiety, ale 7 innych zrodel dziala.
- `Pobierz obraz` -> nie potrzebuje zadnych kluczy.
- `Notatnik` -> nie potrzebuje zadnych kluczy.
