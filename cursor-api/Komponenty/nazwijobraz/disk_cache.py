"""Trwaly cache wynikow API na dysku.

Magazyn: katalog `<workspace>/.cache/nazwijobraz/<source>.json`.
Klucz: `(artist_lower, query_lower, key_extra_lower)`.

Wartosc: dowolna struktura JSON-serializowalna (lista/dict/str/None).
Zapisujemy tez `ts` (epoch seconds) i czyscimy wpisy starsze niz `ttl_seconds`.

Uzycie:
    cache = DiskCache(Path('.cache/nazwijobraz'))
    val = cache.get('wikipedia', 'Van Gogh', 'sunflowers')  # None jesli brak/expired
    cache.set('wikipedia', 'Van Gogh', 'sunflowers', payload)
    cache.flush()  # zapisz na dysk

Zapis jest BUFOROWANY - flush() wywolujemy okresowo (np. co 30s) lub na koniec sesji,
zeby nie przesilac dyskiem przy 30 plikach.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


_DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 dni


class DiskCache:
    def __init__(
        self,
        base_dir: Path,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        schema_version: str = "v1",
    ) -> None:
        """schema_version - bump przy zmianie logiki wyszukiwania, zeby
        automatycznie zinwalidowac stare wyniki z dysku (te zostaly zapisane
        przez wczesniejsza wersje kodu i moga byc niepoprawne)."""
        self.base_dir = Path(base_dir)
        self.ttl_seconds = ttl_seconds
        self.schema_version = schema_version
        self._lock = threading.RLock()
        # in-memory mirror per source: {source: {key_str: {"ts": float, "v": Any}}}
        self._data: dict[str, dict[str, dict[str, Any]]] = {}
        # ktore source-y maja niezapisane zmiany
        self._dirty: set[str] = set()
        self._loaded: set[str] = set()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(artist: str, query: str, key_extra: str = "") -> str:
        return "\x1f".join([
            (artist or "").strip().lower(),
            (query or "").strip().lower(),
            (key_extra or "").strip().lower(),
        ])

    def _path(self, source: str) -> Path:
        safe = "".join(c for c in source if c.isalnum() or c in ("-", "_")) or "misc"
        return self.base_dir / f"{safe}.json"

    def _ensure_loaded(self, source: str) -> None:
        if source in self._loaded:
            return
        path = self._path(source)
        store: dict[str, dict[str, Any]] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                # Format v2: {"_schema": "vN", "entries": {...}}.
                # Format v1 (legacy): {key: {ts, v}, ...} - traktujemy jak
                # zinwalidowane bo nie da sie sprawdzic wersji.
                if isinstance(raw, dict) and isinstance(raw.get("_schema"), str):
                    if raw["_schema"] == self.schema_version:
                        entries = raw.get("entries", {})
                        if isinstance(entries, dict):
                            now = time.time()
                            for k, v in entries.items():
                                if not isinstance(v, dict):
                                    continue
                                ts = v.get("ts")
                                if not isinstance(ts, (int, float)):
                                    continue
                                if (now - float(ts)) > self.ttl_seconds:
                                    continue
                                store[str(k)] = v
                # else: stary format / inna wersja schemy -> ignoruj cache
                # (kasujemy stary plik przy pierwszym flush-u).
            except (OSError, json.JSONDecodeError, ValueError):
                store = {}
        self._data[source] = store
        self._loaded.add(source)

    def get(self, source: str, artist: str, query: str, *, key_extra: str = "") -> Any:
        with self._lock:
            self._ensure_loaded(source)
            entry = self._data.get(source, {}).get(self._key(artist, query, key_extra))
            if not entry:
                return None
            ts = entry.get("ts")
            if not isinstance(ts, (int, float)):
                return None
            if (time.time() - float(ts)) > self.ttl_seconds:
                return None
            return entry.get("v")

    def set(
        self,
        source: str,
        artist: str,
        query: str,
        value: Any,
        *,
        key_extra: str = "",
    ) -> None:
        # Zapisuj tylko JSON-serializowalne wyniki.
        try:
            json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return
        with self._lock:
            self._ensure_loaded(source)
            store = self._data.setdefault(source, {})
            store[self._key(artist, query, key_extra)] = {
                "ts": time.time(),
                "v": value,
            }
            self._dirty.add(source)

    def flush(self) -> None:
        """Zapisz wszystkie niezapisane source-y na dysk (atomic write).

        Format pliku: {"_schema": "<wersja>", "entries": {...}} - dzieki
        temu po bumpie `schema_version` w kodzie stare pliki sa traktowane
        jak puste (i nadpisywane przy pierwszym zapisie).
        """
        with self._lock:
            sources = list(self._dirty)
            for source in sources:
                store = self._data.get(source, {})
                payload = {"_schema": self.schema_version, "entries": store}
                path = self._path(source)
                tmp = path.with_suffix(path.suffix + ".tmp")
                try:
                    tmp.write_text(
                        json.dumps(payload, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    tmp.replace(path)
                    self._dirty.discard(source)
                except OSError:
                    try:
                        if tmp.exists():
                            tmp.unlink()
                    except OSError:
                        pass

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {s: len(d) for s, d in self._data.items()}
