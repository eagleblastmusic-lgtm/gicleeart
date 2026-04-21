"""Instrukcja + preferowane specyfikacje zdjec dla komponentu Cykl."""

HELP_TEXT = """# Cykl - "Obraz na rano, popoludnie i wieczor"

## Co robi ta aplikacja

Automatyczny cykl postow na Facebooku i Instagramie:
- 3 posty dziennie (rano 08:00, popoludnie 14:00, wieczor 20:00),
- publikacja rownolegle na 4 kanalach (FB PL, FB EN, IG PL, IG EN),
- tresc generowana przez Opusa na tydzien z gory,
- kolejka budowana z kolekcji artystow w Shopify w kolejnosci alfabetycznej
  (Achenbach -> Aivazovsky -> ... -> Whistler),
- nowi artysci i nowe obrazy "wciskaja sie" w kolejke po zakonczeniu biezacego artysty.

## Jak uruchomic - pierwszy raz

1. **Zbuduj kolejke**: przycisk "Odswiez z Shopify". Aplikacja pobierze wszystkie
   kolekcje artystow (tytul "Nazwisko, Imie"), posortuje alfabetycznie i dla kazdego
   artysty pobierze jego obrazy wraz z opisem PL i EN. To moze potrwac kilka minut
   przy duzej kolekcji.

2. **Skonfiguruj Meta API**: przycisk "Ustawienia Meta API" - wprowadz Page ID i
   Access Token dla 4 kanalow. Zobacz instrukcje w tamtym dialogu (przycisk
   "Pokaz instrukcje").

3. **Wgraj zdjecia**: przycisk "Otworz folder obrazow". Struktura:
   - `Obrazy/<artysta-slug>/<tytul-slug>/main.jpg` (lub png/webp)
   - `Obrazy/<artysta-slug>/<tytul-slug>/zoom_<cokolwiek>.jpg` (zblizenia do IG)
   - `Obrazy/<artysta-slug>/<tytul-slug>/MOCKUP_<cokolwiek>.jpg` (mockup w ramce - ostatnie IG)

   Lub uzyj dialogu "Edytuj..." na konkretnej pozycji - mozesz przeciagnac pliki
   bezposrednio z pulpitu.

4. **Wygeneruj tresc tygodnia**: przycisk "Generuj tresc tygodnia (Opus)". Okno
   pokaze prompt - skopiuj, wklej w chat Cursor (z wybranym modelem Claude Opus),
   a potem wklej odpowiedz w dolne pole i kliknij "Zastosuj".

5. **Sprawdz braki**: przycisk "Lista kontrolna" pokaze, w ktorych pozycjach brakuje
   main/zoom/mockup. Pozycje bez zdjec nie zostana opublikowane.

6. **Gotowe**: publisher w tle (sprawdza co 60 sekund) bedzie publikowac posty
   ktorych nadeszla godzina. Wlacz tryb auto-publish w Ustawieniach Meta API.

## Sterowanie kolejka

- **+1 dzien WSZYSTKIE** / **-1 dzien WSZYSTKIE**: przesuwa wszystkie zaplanowane
  posty o dzien. Np. jedziesz na weekend i chcesz zatrzymac cykl - klikasz "+1 dzien"
  trzy razy (przesunie o 3 dni).
- **PPM na pozycji**:
  - Edytuj... - otwiera pelny edytor pozycji (4 zakladki, po jednej na kanal).
  - Publikuj teraz - pomija scheduled_at i publikuje natychmiast.
  - Przesun ten +1 dzien / -1 dzien - tylko ta jedna pozycja sie rusza.
  - Gora / Dol - zmiana kolejnosci w liscie (sloty przeliczane automatycznie).
  - Pomin - oznacza jako skipped (nie bedzie publikowany).
  - Usun z kolejki - usuniecie permanentne (mozesz odzyskac tylko przez rebuild).
  - Wyslij w trybie manualnym - kopiuje caption do schowka i otwiera FB/IG Business Suite.

## Logika kontekstu postow

Dla kazdego obrazu prompt zawiera flagi, ktore Opus interpretuje:

- **Pierwszy obraz artysty**: post zaczyna sie intro "Rozpoczynamy nasz cykl z
  obrazami X. Malarz / malarka [krotki kontekst]..."
- **Ostatni obraz artysty**: na koncu post dodaje "To ostatni obraz X w naszej
  biezacej prezentacji. W kolejnym poscie pokazemy Y."
- **Nowy artysta** (pojawil sie po rozpoczeciu cyklu): intro "Na stronie pojawil
  sie nowy artysta: X. Witamy jego/jej prac w naszej galerii!"
- **Nowy obraz** (u istniejacego artysty): "Dolozylismy nowy obraz do naszej
  kolekcji X: Y."

## Preferowane specyfikacje plikow zdjeciowych

### Instagram (Feed + karuzela)

- **Format**: JPG albo PNG (PNG przy ostrym kontrascie + jasnych kolorach).
- **Rozdzielczosc**: 1080x1350 (4:5, zalecane dla IG) lub 1080x1080 (1:1).
- **Kolor**: sRGB.
- **Rozmiar pliku**: do 8 MB (idealnie 1-4 MB).
- **Karuzela**: 2-10 obrazow, wszystkie ten sam aspect ratio (IG wymaga).

Kolejnosc w karuzeli:
1. main.jpg (glowne zdjecie produktu - 1. slide)
2. zoom_*.jpg (zblizenia - 2.-9. slide, alfabetycznie)
3. MOCKUP_*.jpg (mockup w ramce - ostatni slide, uzytkownik "konczy podrze"
   widokiem jak obraz wyglada u niego w pokoju)

### Facebook

- **Format**: JPG albo PNG.
- **Rozdzielczosc**: 1200x1200 (1:1) lub 1200x628 (1.91:1 - bardziej horizontalne).
- **Rozmiar**: do 4 MB.
- FB publikuje tylko 1 zdjecie (to sam main.jpg z folderu).

### Mockup (ostatnie IG)

- Obraz w ramce na tle sciany / pokoju. Ten sam aspect ratio co karuzela (4:5).
- Sufiks `MOCKUP` w nazwie (case-insensitive), np. `my_obraz_MOCKUP.jpg`.

## Co sugerujemy zooomowac

Opus wraz z tresciami zwraca `zoom_hints` - 3-5 sugestii co warto pokazac w
zblizeniach. Przyklady:
- "faktura plotna przy dluzszym oceanie"
- "detal twarzy postaci z lewej"
- "refleksy swiatla na falach"
- "bogata paleta zolci i ugrow w tle"

Znajdziesz je w dialogu "Edytuj..." -> zakladka "Podsumowanie".

## Reminder tygodniowy

Status bar na dole okna pokazuje "Tresc wygenerowana do: DD.MM.YYYY". Gdy
zostanie mniej niz 2 dni wygenerowanej tresci - pojawi sie zolta etykieta
"Czas wygenerowac kolejny tydzien". Tez dialog wyskoczy przy starcie launchera.

## Gdy brakuje tlumaczenia na EN

Jesli produkt w Shopify nie ma jeszcze tlumaczen EN (body_html), Opus dostanie
puste pole i zostanie poproszony o przetlumaczenie z PL. Zalecamy jednak zrobic
porzadny push tlumaczen przez `dodajobraz` PRZED pierwszym uruchomieniem cyklu -
dostaniesz lepszy tekst.
"""


IMAGE_SPECS_QUICK = """
Szybki brief specyfikacji zdjec:

  Instagram:  1080x1350 (4:5) lub 1080x1080 (1:1), JPG/PNG, sRGB, <8 MB.
  Facebook:   1200x1200 (1:1) lub 1200x628 (1.91:1), JPG/PNG, <4 MB.
  Karuzela:   2-10 obrazow, TEN SAM aspect ratio.

Sufiks MOCKUP w nazwie = ostatnie w karuzeli IG (ramka w pokoju).
Kolejnosc IG: main.jpg -> zoomy (alfabetycznie) -> MOCKUP.
"""
