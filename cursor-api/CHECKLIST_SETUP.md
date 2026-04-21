# Token setup — checklista (Shopify + Meta)

Jedna lista kroków przy **pierwszej konfiguracji**, **po zmianie scope’ów** albo **po rotacji sekretów**.

---

## A. Shopify (aplikacja + token do Admin API)

1. **Spójność scope’ów** (ta sama lista w trzech miejscach):
   - `cursor-api/.env` → `SCOPES=...`
   - `cursor-api/shopify.app.toml` → `[access_scopes]` → `scopes = "..."`
   - **Shopify Partners** → Twoja aplikacja → Configuration → Admin API scopes

2. **Dodałeś lub zmieniłeś scope?** Wykonaj **w tej kolejności** (bez pomijania):
   - `cd cursor-api`
   - `npm run deploy -- --allow-updates`
   - `npm run oauth` → w przeglądarce zaakceptuj **nowe** uprawnienia dla sklepu

3. **Po OAuth**
   - Sprawdź `cursor-api/.shopify_session.json`: pole `scope` musi zawierać **pełną** listę.
   - Serwer OAuth możesz zamknąć (Ctrl+C).

4. **GicleeApp**
   - Uruchamiaj z katalogu `cursor-api` (Python musi widzieć folder `Komponenty/`).
   - Komponenty korzystają z tej samej sesji Shopify co `shopify_client` / `.shopify_session.json`.

---

## B. Meta — Facebook + Instagram (Cykl, „Dodaj post”)

1. **Aplikacja w [Meta for Developers](https://developers.facebook.com/)**
   - Tryb Live, jeśli publikujesz na prawdziwe strony; ewentualnie App Review dla wymaganych uprawnień.

2. **Typowe scope’y**
   - Strony: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`
   - Instagram: `instagram_basic`, `instagram_content_publish`

3. **Gdzie wklejasz tokeny**
   - **GicleeApp** → **Social Media** → ustawienia Meta (Cykl), **albo**
   - plik `Komponenty/socialmedia/data/cykl/meta_credentials.json` (nie commituj do gita).

4. **Co wpisać**
   - **Facebook:** `page_id` (ID strony) + `access_token` — najpewniej **Page Access Token** (albo long-lived user z `pages_manage_posts`; aplikacja stara się zamienić na token strony).
   - **Instagram:** `ig_user_id` + **ten sam** token co powiązana strona FB w danej parze językowej.

5. **Sprawdzenie**
   - W oknie konfiguracji Meta: **Test połączenia** na każdym kanale.
   - Potem krótki test publikacji (Cykl lub „Dodaj post”).

---

## C. Po wycieku sekretów (czat, zrzut ekranu, repo)

1. **Obróć:** token Shopify (nowy OAuth), tokeny Meta, w razie potrzeby **App Secret** w Meta.
2. **Upewnij się**, że `meta_credentials.json`, `.env`, `.shopify_session.json` są w **`.gitignore`** i nie trafiły do historii gita.
3. **Nie wklejaj pełnych sekretów** do czatu — wystarczy opis problemu lub końcówka tokenu.

---

## D. Tylko odświeżenie tokenów (bez zmiany scope’ów)

1. **Shopify:** `cd cursor-api` → `npm run oauth` → zaloguj sklep (jeśli lista scope’ów w Partners się nie zmieniła).
2. **Meta:** według **„Instrukcja odnowy”** w oknie ustawień Meta w aplikacji → wklej nowe tokeny → Test → Zapisz.
