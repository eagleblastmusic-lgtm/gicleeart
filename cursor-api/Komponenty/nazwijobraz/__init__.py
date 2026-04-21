"""nazwijobraz - GUI do automatycznej zmiany nazw plikow obrazow.

Krok po kroku:
1. Wgraj/przeciagnij obrazy.
2. Aplikacja czyta autora z dowolnego segmentu sciezki (np. .../Sisley, Alfred/...).
3. Wykonuje reverse image search (SerpAPI Google Lens) i wyciaga tytul obrazu.
4. Pokazuje propozycje "Autor - Tytul.<ext>" do akceptacji.
5. Po kliknieciu "Zmien nazwy" nadpisuje nazwy plikow na dysku.
"""
