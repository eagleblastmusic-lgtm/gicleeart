"""GicleeApp - glowny launcher uruchamiajacy komponenty z folderu `Komponenty/`.

Po starcie wyswietla siatke kafelkow - po jednym dla kazdego komponentu wykrytego
w `cursor-api/Komponenty/`. Klikniecie kafelka odpala komponent jako osobny proces
(`python -m Komponenty.<nazwa>`).
"""

# Trzymaj zgodne z `cursor-api/package.json` (wersja aplikacji desktop).
__version__ = "1.26.2"
