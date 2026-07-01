"""Klucze API wyszukiwarki — odczyt/zapis cursor-api/.env."""

from __future__ import annotations

import os
from pathlib import Path

from Komponenty.limity.env_config import env_str, set_env_value

ENV_KEY = "SMITHSONIAN_API_KEY"
LEGACY_ENV_KEY = "SI_API_KEY"
FNG_ENV_KEY = "FNG_API_KEY"
PARIS_MUSEES_ENV_KEY = "PARIS_MUSEES_API_TOKEN"
EUROPEANA_ENV_KEY = "EUROPEANA_API_KEY"
COOPER_HEWITT_ENV_KEY = "COOPER_HEWITT_ACCESS_TOKEN"
NYPL_ENV_KEY = "NYPL_API_TOKEN"
SIGNUP_URL = "https://api.data.gov/signup/"
FNG_SIGNUP_URL = "https://www.kansallisgalleria.fi/en/open-data"
FNG_SWAGGER_URL = "https://kokoelma.kansallisgalleria.fi/api/swagger"
PARIS_MUSEES_SIGNUP_URL = "https://apicollections.parismusees.paris.fr/en/explorer"
EUROPEANA_SIGNUP_URL = "https://pro.europeana.eu/page/get-api"
COOPER_HEWITT_SIGNUP_URL = "https://collection.cooperhewitt.org/api/"
NYPL_SIGNUP_URL = "https://api.repo.nypl.org/"


def smithsonian_api_key() -> str:
    return env_str(ENV_KEY) or env_str(LEGACY_ENV_KEY)


def fng_api_key() -> str:
    return env_str(FNG_ENV_KEY)


def paris_musees_api_token() -> str:
    return env_str(PARIS_MUSEES_ENV_KEY)


def europeana_api_key() -> str:
    return env_str(EUROPEANA_ENV_KEY)


def cooper_hewitt_access_token() -> str:
    return env_str(COOPER_HEWITT_ENV_KEY)


def nypl_api_token() -> str:
    return env_str(NYPL_ENV_KEY)


def fng_api_key_hint() -> str:
    key = fng_api_key()
    if not key:
        return ""
    if len(key) <= 8:
        return "..." + key[-4:]
    return "..." + key[-6:]


def paris_musees_api_token_hint() -> str:
    key = paris_musees_api_token()
    if not key:
        return ""
    if len(key) <= 8:
        return "..." + key[-4:]
    return "..." + key[-6:]


def smithsonian_api_key_hint() -> str:
    key = smithsonian_api_key()
    if not key:
        return ""
    if len(key) <= 8:
        return "..." + key[-4:]
    return "..." + key[-6:]


def set_smithsonian_api_key(value: str) -> Path:
    key = (value or "").strip()
    if not key:
        raise ValueError("Klucz API nie moze byc pusty.")
    path = set_env_value(ENV_KEY, key)
    os.environ[ENV_KEY] = key
    return path


def set_fng_api_key(value: str) -> Path:
    key = (value or "").strip()
    if not key:
        raise ValueError("Klucz API nie moze byc pusty.")
    path = set_env_value(FNG_ENV_KEY, key)
    os.environ[FNG_ENV_KEY] = key
    return path


def set_paris_musees_api_token(value: str) -> Path:
    key = (value or "").strip()
    if not key:
        raise ValueError("Token API nie moze byc pusty.")
    path = set_env_value(PARIS_MUSEES_ENV_KEY, key)
    os.environ[PARIS_MUSEES_ENV_KEY] = key
    return path
