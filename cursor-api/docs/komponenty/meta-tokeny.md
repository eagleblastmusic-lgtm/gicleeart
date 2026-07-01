# Meta — tokeny Graph API (Cykl)

**Powiązane komponenty:** `socialmedia/cykl`, kafelek **Limity** w GicleeApp  
**Plik credentials:** `Komponenty/socialmedia/data/cykl/meta_credentials.json` (nie commitować)

---

## Po co

Cykl publikuje na **4 kanały** (Facebook PL/EN, Instagram PL/EN). Każdy kanał ma Page token w `meta_credentials.json`. Tokeny wygasają (~60 dni dla user tokenów); Limity pokazuje status i uruchamia kreator odnowy.

---

## Gdzie w kodzie

| Plik | Rola |
|------|------|
| `socialmedia/cykl/meta_token_status.py` | `analyze_meta_tokens()`, `debug_access_token` |
| `socialmedia/cykl/meta_renew_wizard.py` | Kreator 5 kroków — **Odnów tokeny** w Limity |
| `socialmedia/cykl/meta_config.py` | Zapis credentials + odświeżenie metadanych |
| `limity/collectors.py` | Sekcja Meta w dashboardzie |
| `limity/view.py` | Przycisk **Odnów tokeny** |

---

## Kreator odnowy (Limity → Odnów tokeny)

1. Krótki opis — **jeden** user access token wystarczy na wszystkie 4 kanały.
2. Wklejenie tokena z [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
3. Wymiana na long-lived (jeśli w `.env` są `META_APP_ID` + `META_APP_SECRET`).
4. Pobranie Page tokenów dla stron FB PL/EN.
5. Zapis do `meta_credentials.json` — wszystkie 4 kanały naraz.

Po zapisie Limity odświeża sekcję Meta automatycznie.

---

## Opcjonalna konfiguracja `.env`

```env
META_APP_ID=...
META_APP_SECRET=...
```

Bez tych zmiennych kreator nadal działa — long-lived wymaga ręcznej wymiany w Explorerze.

---

## Interpretacja statusu

| Wyświetlane | Znaczenie |
|-------------|-----------|
| X dni do wygaśnięcia | User token z datą z `debug_token` |
| bez daty wygaśnięcia (OK) | Typowe dla Page tokenów — nie oznacza błędu |
| wygasł / błąd | Odśwież przez kreator |

---

## Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Cykl nie publikuje | Limity → Meta — sprawdź daty; **Odnów tokeny** |
| debug_token fail | Dodaj `META_APP_ID` / `META_APP_SECRET` do `.env` |
| Brak Page w kreatorze | Token musi mieć uprawnienia `pages_show_list`, `pages_read_engagement` |
| Stary sposób (Ustawienia Meta) | Nadal w socialmedia/cykl; preferuj kreator z Limity |

→ [`socialmedia.md`](socialmedia.md) · [`limity.md`](limity.md) · [`../../../USLUGI.md`](../../../USLUGI.md)
