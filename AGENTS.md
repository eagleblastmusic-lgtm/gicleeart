# Instrukcje repozytorium dla AI

## Film-scroll

Jeżeli polecenie zawiera `Film-scroll`, `wstaw moduł Film-scroll` albo
oczywistą literówkę `Fillm-scroll`, przed zmianami przeczytaj w całości
`docs/Film-scroll.md`.

To polecenie zawsze oznacza pełny moduł: frontend oraz nową widoczną sekcję
GicleeApp dla danej instancji, z przyciskiem `Charakter odtwarzania`, obsługę
biblioteki i aktywacji zasobów, deploy oraz test przewijania w dół i w górę.
Nie implementuj tylko jednej z tych warstw. `docs/Film-scroll.md` jest jedynym
źródłem prawdy.

## Dodaj tekst

Jeżeli polecenie zawiera `Dodaj tekst` albo `wstaw moduł Dodaj tekst`, przed
zmianami przeczytaj w całości `docs/Dodaj-tekst.md`.

To polecenie oznacza użycie jednego wspólnego modułu warstw tekstowych, a nie
tworzenie osobnej sekcji lub jednorazowego pola w JSON. Moduł musi zostać
podłączony do stabilnego klucza istniejącej sekcji, zapisu bieżącego wariantu,
podglądu, kontrolowanego zastosowania do motywu, listy wdrożeniowej i runtime.
Wiersze ustawień globalnych bez elementu Shopify nie przyjmują warstw tekstu.
`docs/Dodaj-tekst.md` jest jedynym źródłem prawdy.

## Wstaw ekran

Jeżeli polecenie zawiera `Wstaw ekran`, użyj wspólnego modułu opisanego w
`docs/Wstaw-ekran.md`. Oznacza to prawdziwą, pustą sekcję Shopify wstawioną
bezpośrednio po wskazanej sekcji, z wysokością edytowaną w `vh`, a nie
jednorazowy margines, padding ani odstęp istniejącej sekcji. Utworzony ekran
ma też własną, potwierdzaną akcję PPM `Usuń ekran…`.
