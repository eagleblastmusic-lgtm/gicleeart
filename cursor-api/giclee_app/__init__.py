"""GicleeApp - glowny launcher uruchamiajacy komponenty z folderu `Komponenty/`.

Po starcie wyswietla siatke kafelkow - po jednym dla kazdego komponentu wykrytego
(`python -m Komponenty.<nazwa>`).
"""

from .version import __version__

__all__ = ["__version__"]
