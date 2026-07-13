# Production order data outside the checkout

The `Produkcja` component has four entry points that share the same mutable order
state:

- the classic/inline Tk view,
- Shopify order synchronization,
- the workshop web server,
- retention and yearly archives.

These files are private user data and must not be written next to the Python
implementation.

## Runtime destinations

Normal runtime writes target Local AppData:

- `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/produkcja/dane/zamowienia.json`,
- `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/produkcja/dane/sync_state.json`,
- `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/produkcja/dane/archive_YYYY.json`.

The historical `Komponenty/produkcja/dane` directory remains read-only.

## Read and write contract

`Komponenty/produkcja/production_store.py` is the neutral shared path boundary.

- reads prefer Local AppData,
- when an external file does not exist, reads may use the legacy source-tree file,
- complete JSON writes always target Local AppData and use atomic replacement,
- writing state loaded from legacy creates the external copy without modifying,
  moving or deleting the legacy file,
- archives are listed from both locations with an external file taking precedence
  for the same year,
- reset of Shopify sync state writes an empty external object so a legacy fallback
  cannot silently become active again,
- explicit `_ORDERS_FILE`, `_SYNC_STATE_FILE` and `_DATA_DIR` overrides remain
  supported for tests and controlled tools.

## Consumers

The following modules resolve their persistence through the shared store:

- `orders_sync.py`,
- `view.py`,
- `web_server.py`,
- `retention.py`.

The UI command that opens the data directory now opens the application-owned
external directory rather than the repository checkout.

## Validation

`tests/test_production_store_appdata.py` verifies:

1. all four entry points observe the same external-first order state,
2. legacy order data remains byte-for-byte unchanged,
3. initialization without legacy creates only the external store,
4. sync-state save and reset semantics,
5. archive discovery and external precedence,
6. compatibility of explicit file/directory overrides,
7. atomic replacement without leftover temporary files,
8. removal of all production-store source-write findings from the inventory.
