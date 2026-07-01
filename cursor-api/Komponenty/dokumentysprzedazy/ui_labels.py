"""Etykiety przycisków UI — faktura vs rachunek (DNR/JDG)."""

from __future__ import annotations

from .constants import BUSINESS_MODE_DNR


def issue_button_label(mode: str, *, preview: bool = False) -> str:
    if mode == BUSINESS_MODE_DNR:
        return "Wystaw rachunek" if not preview else "Wystaw rachunek →"
    return "Wystaw fakturę bez VAT" if not preview else "Wystaw fakturę bez VAT →"


def send_document_label() -> str:
    return "Wyślij fakturę"


def send_receipt_label() -> str:
    return "Wyślij rachunek"


def send_label_for_mode(mode: str) -> str:
    if mode == BUSINESS_MODE_DNR:
        return send_receipt_label()
    return send_document_label()


def editor_title(mode: str, *, read_only: bool = False, is_test: bool = False) -> str:
    if is_test:
        return "Podgląd faktury testowej" if read_only else "Faktura testowa"
    if read_only:
        return "Podgląd dokumentu"
    if mode == BUSINESS_MODE_DNR:
        return "Wystaw rachunek"
    return "Wystaw fakturę bez VAT"
