# Production Giclée Studio profile

Status: **STUDIO-ISOLATION-3**

## Cel

Wprowadzić właściwy profil produkcyjny `studio` bez kopiowania kodu aplikacji i bez automatycznego uruchamiania przebudowy UI Studio.

Dostępne entrypointy:

```text
python -m giclee_app                  # klasyczny GicleeApp
python -m giclee_app.studio_preview   # Giclée Studio Preview
python -m giclee_app.studio           # produkcyjne Giclée Studio
```

## Profile

| Profil | Namespace stanu/logów | Kanały komponentów |
|---|---|---|
| `classic` | `GicleeApp` | wszystkie kanały, zgodność historyczna |
| `studio_preview` | `GicleeStudioPreview` | stable, preview, experimental, legacy |
| `studio` | `GicleeStudio` | wyłącznie stable |

Każdy profil ma osobny stan shella, geometrię, pinned/recent i shell/perf logi. Dane biznesowe, sesja Shopify, komponenty i logi biznesowe pozostają wspólne zgodnie z kontraktem STUDIO-ISOLATION-1.

## Reguła promocji

Komponent pojawia się w produkcyjnym Studio tylko wtedy, gdy oba warunki są spełnione:

1. `availability` zawiera `studio`;
2. `stability` ma wartość `stable`.

Przykład:

```json
{
  "availability": ["studio_preview", "studio"],
  "stability": "stable"
}
```

Kanały `preview`, `experimental` i `legacy` pozostają dostępne w Preview, ale są wykluczone z produkcyjnego indeksu Studio.

## Scoped profile context

Entrypoint wybiera profil jawnie i otacza import/życie shella kontekstem `app_profile_context(profile)`.

Kontekst jest oparty o `ContextVar`, ma zasięg bieżącego wykonania i zawsze zostaje przywrócony. Nie jest trwałym globalnym przełącznikiem. Umożliwia bezpieczne przekazanie profilu przez starsze granice kompozycji, które nie przyjmują jeszcze argumentu profilu, m.in. domyślny build indeksu i resolver perf logu.

## Zakres

Ten etap:

- dodaje profil i entrypoint produkcyjnego Studio;
- rozdziela stan i shell/perf logi;
- egzekwuje regułę promocji komponentów;
- nie klasyfikuje hurtowo istniejących komponentów;
- nie zmienia interfejsu Studio;
- nie uruchamia Shopify, sync, deploy ani usług tła;
- nie zastępuje klasycznego GicleeApp.

Przebudowa i rozwój interfejsu Studio pozostają wstrzymane do osobnego polecenia użytkownika.
