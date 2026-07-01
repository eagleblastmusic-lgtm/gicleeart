"""Uruchomienie serwera analityki: python -m Komponenty.analytics.server"""

from Komponenty.analytics.server import start_server
from Komponenty.analytics.env_config import server_port
from Komponenty.analytics import storage

if __name__ == "__main__":
    storage.init_db()
    start_server(port=server_port(), background=False)
