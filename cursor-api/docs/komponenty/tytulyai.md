# Komponent: tytulyai

**Cel:** Batch generowania tytułów obrazów oraz **roboczych opisów** przez **Gemini API** (domyślnie `gemini-3.5-flash`). Tytuły → prompty do Cursora; opisy → podgląd w oknie (bez zapisu do Shopify).

| Plik | Rola |
|------|------|
| `gui.py` | Notebook: zakładka **Tytuły** + **Opisy**; lista produktów, batch API |
| `batch.py` | Tytuły: obraz → Gemini → prompt Cursora |
| `descriptions.py` | Opisy: obraz + prompt «Opis z obrazu» → JSON `akapity` (roboczo) |
| `storage.py` | Trwały zapis roboczych tytułów i opisów (`data/*.json`) |
| `prompts.py` | Instrukcja dla modelu (format pól PL/EN/DE…); presety Gemini czat |
| `_shared/gemini_client.py` | REST `generateContent`, klucz z `.env`, retry przy HTTP 429/503 i timeoutach sieci; **bez retry** przy wyczerpanych kredytach/billingu (429) |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu** (po «Zmień tytuły»).

## Konfiguracja

W `cursor-api/.env` (lub przycisk **Zmien klucz API…** w oknie komponentu — zapis do `.env`):

```env
GEMINI_API_KEY=...
```

Klucz: [Google AI Studio → API keys](https://aistudio.google.com/apikey)

## Workflow

Okno ma dwie zakładki: **Tytuły** (dotychczasowa funkcja) i **Opisy** (robocze opisy premium). Model i przerwa między obrazami — wspólne u góry okna.

### Tytuły

0. **Gemini czat (ręcznie):** «Kopiuj prompt startowy (Gemini czat)» → nowa rozmowa w gemini.google.com → wklej → potwierdzenie → zdjęcia po kolei → kopiuj bloki kodu → «Zmień tytuły» lub Cursor.
1. Zaznacz produkty (Ctrl/Shift). Wiersze **na zielono** = tytuł oznaczony jako zmieniony. Filtr **Status tytułu:** `wszystkie` / `zmienione` / `niezmienione`.
2. **Generuj tytuły (Gemini API)** — miniatura z Shopify → Gemini → prompt Cursora. Kolumna **Tytuł** (✓) = zapisany roboczy prompt.
3. Zaznacz produkt z ✓ — podgląd promptu na dole (wielokrotny wybór = wiele promptów).
4. **Kopiuj wyniki** / **Zapisz do pliku**.
5. **Przerwa** domyślnie **8 s**; przy HTTP 429/503 **ponawia do skutku** (503: min. 30 s, max 120 s; tylko **gemini-3.5-flash**).

**Robocze tytuły** — zapis lokalny w `Komponenty/tytulyai/data/title_drafts.json` (po ID produktu). Nie znikają po zamknięciu okna.

**Unikalność:** lista innych tytułów PL artysty; ostrzeżenia «KOLIZJA TYTULOW».

### Opisy

1. Zakładka **Opisy** — lista produktów, kolumna **v1/v2** (✓/✓ = oba warianty gotowe).
2. Zaznacz produkt(y) → **Generuj opisy v1 + v2 (Gemini API)** — dwa wywołania Gemini na obraz (pomija warianty, które już mają poprawne akapity; ponawia tylko te z błędem, np. timeout sieci):
   - **Opis z obrazu** (v1)
   - **Opis z obrazu v2** (naturalniejszy styl)
3. W sekcji **Roboczy opis** — przełącznik radiowy **Opis z obrazu** / **Opis z obrazu v2**.
4. **Dwuklik** — okno z pełnym tekstem (też z przełącznikiem wariantu).
5. **Kopiuj opis** — schowek (aktywny wariant, tekst); **Kopiuj JSON (porównywarka)** — `{"akapity":[...]}` do wklejenia w **Aktualizuj opis → Porównywarka** («Wklej całość» lub Ctrl+V poza polem tekstu); **bez zapisu do Shopify**.

**Robocze opisy** — zapis lokalny w `Komponenty/tytulyai/data/description_drafts.json` (pola `v1` i `v2`). Nie znikają po zamknięciu okna. Stary format pliku (tylko v1) jest wczytywany jako v1.

Powiązane: [`zmietytuly.md`](zmietytuly.md) — schowek promptów, ręczna korekta tytułów; [`aktualizujopis.md`](aktualizujopis.md) — ten sam prompt «Opis z obrazu».

→ [`README.md`](README.md)
