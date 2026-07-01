"""Tłumaczenia dokumentów sprzedaży — 7 języków rynków Shopify."""

from __future__ import annotations

from typing import Literal

InvoiceLanguage = Literal["pl", "en", "de", "fr", "es", "nl", "it"]

INVOICE_LANGUAGES: tuple[InvoiceLanguage, ...] = ("pl", "en", "de", "fr", "es", "nl", "it")

# Kraj dostawy → język dokumentu (pozostałe kraje → angielski)
COUNTRY_TO_LANGUAGE: dict[str, InvoiceLanguage] = {
    "PL": "pl",
    "FR": "fr",
    "DE": "de",
    "ES": "es",
    "NL": "nl",
    "IT": "it",
}

LANGUAGE_LABELS: dict[InvoiceLanguage, str] = {
    "pl": "PL",
    "en": "EN",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "nl": "NL",
    "it": "IT",
}

MARKET_DEFAULT_COUNTRY: dict[InvoiceLanguage, str] = {
    "pl": "PL",
    "en": "GB",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "nl": "NL",
    "it": "IT",
}

# Tytuły dokumentów JDG (faktura bez VAT)
DOC_TYPE_JDG: dict[InvoiceLanguage, str] = {
    "pl": "Faktura bez VAT",
    "en": "Invoice without VAT",
    "de": "Rechnung ohne USt.",
    "fr": "Facture sans TVA",
    "es": "Factura sin IVA",
    "nl": "Factuur zonder BTW",
    "it": "Fattura senza IVA",
}

DOC_TYPE_JDG_CORRECTION: dict[InvoiceLanguage, str] = {
    "pl": "Korekta faktury bez VAT",
    "en": "Correction invoice without VAT",
    "de": "Korrekturrechnung ohne USt.",
    "fr": "Facture rectificative sans TVA",
    "es": "Factura rectificativa sin IVA",
    "nl": "Correctiefactuur zonder BTW",
    "it": "Fattura di rettifica senza IVA",
}

# Rachunki DNR (tylko język polski w numeracji DN; tłumaczenia na PDF dla spójności)
DOC_TYPE_DNR: dict[InvoiceLanguage, str] = {
    "pl": "Rachunek",
    "en": "Sales receipt",
    "de": "Verkaufsbeleg",
    "fr": "Reçu de vente",
    "es": "Recibo de venta",
    "nl": "Verkoopbewijs",
    "it": "Ricevuta di vendita",
}

DOC_TYPE_DNR_CORRECTION: dict[InvoiceLanguage, str] = {
    "pl": "Korekta rachunku",
    "en": "Correction receipt",
    "de": "Korrekturbeleg",
    "fr": "Reçu rectificatif",
    "es": "Recibo rectificativo",
    "nl": "Correctiebewijs",
    "it": "Ricevuta rettificativa",
}

DEFAULT_FOOTNOTES_DNR: dict[InvoiceLanguage, str] = {
    "pl": (
        "Sprzedaż prowadzona w ramach działalności nierejestrowanej. "
        "Sprzedawca nie jest czynnym podatnikiem VAT."
    ),
    "en": (
        "Sale conducted as non-registered business activity. "
        "The seller is not an active VAT taxpayer."
    ),
    "de": (
        "Verkauf im Rahmen einer nicht angemeldeten Tätigkeit. "
        "Der Verkäufer ist kein aktiver Umsatzsteuerzahler."
    ),
    "fr": (
        "Vente réalisée dans le cadre d'une activité non déclarée. "
        "Le vendeur n'est pas assujetti à la TVA."
    ),
    "es": (
        "Venta realizada en el marco de una actividad no registrada. "
        "El vendedor no es sujeto pasivo de IVA."
    ),
    "nl": (
        "Verkoop in het kader van niet-geregistreerde activiteit. "
        "De verkoper is geen actieve btw-belastingplichtige."
    ),
    "it": (
        "Vendita effettuata nell'ambito di attività non registrata. "
        "Il venditore non è soggetto passivo IVA."
    ),
}

DEFAULT_FOOTNOTES_JDG: dict[InvoiceLanguage, str] = {
    "pl": "Sprzedawca korzysta ze zwolnienia z VAT. Faktura bez VAT.",
    "en": "The seller is VAT exempt. Invoice without VAT.",
    "de": "Der Verkäufer ist von der Umsatzsteuer befreit. Rechnung ohne USt.",
    "fr": "Le vendeur est exonéré de TVA. Facture sans TVA.",
    "es": "El vendedor está exento de IVA. Factura sin IVA.",
    "nl": "De verkoper is vrijgesteld van btw. Factuur zonder BTW.",
    "it": "Il venditore è esente da IVA. Fattura senza IVA.",
}

DEFAULT_THANK_YOU: dict[InvoiceLanguage, str] = {
    "pl": "Dziękujemy za zakup.",
    "en": "Thank you for your purchase.",
    "de": "Vielen Dank für Ihren Einkauf.",
    "fr": "Merci pour votre achat.",
    "es": "Gracias por su compra.",
    "nl": "Bedankt voor uw aankoop.",
    "it": "Grazie per il suo acquisto.",
}

PDF_LABELS: dict[InvoiceLanguage, dict[str, str]] = {
    "pl": {
        "issue": "Data wystawienia",
        "sale": "Data sprzedaży",
        "payment_date": "Data wpływu płatności",
        "order": "Zamówienie Shopify",
        "seller": "Sprzedawca",
        "buyer": "Nabywca",
        "ship": "Adres dostawy",
        "lp": "Lp.",
        "name": "Nazwa towaru / usługi",
        "qty": "Ilość",
        "unit": "Cena jednostkowa",
        "disc": "Rabat",
        "amount": "Wartość",
        "total": "Suma do zapłaty",
        "payment": "Metoda płatności",
        "currency": "Waluta",
        "number": "Nr dokumentu",
        "number_dnr": "Nr rachunku",
        "legal_dnr": "Działalność nierejestrowana — sprzedawca nie jest podatnikiem VAT.",
        "correction": "Korekta",
        "before": "przed",
        "after": "po",
        "test_watermark": "DOKUMENT TESTOWY",
        "nbp_rate": "Kurs NBP",
        "nbp_record": "Ewidencja",
    },
    "en": {
        "issue": "Issue date",
        "sale": "Sale date",
        "payment_date": "Payment received",
        "order": "Shopify order",
        "seller": "Seller",
        "buyer": "Buyer",
        "ship": "Shipping address",
        "lp": "No.",
        "name": "Product name",
        "qty": "Qty",
        "unit": "Unit price",
        "disc": "Discount",
        "amount": "Amount",
        "total": "Total amount",
        "payment": "Payment method",
        "currency": "Currency",
        "number": "Document no.",
        "number_dnr": "Receipt no.",
        "legal_dnr": "",
        "correction": "Correction",
        "before": "before",
        "after": "after",
        "test_watermark": "TEST DOCUMENT",
        "nbp_rate": "NBP rate",
        "nbp_record": "Record",
    },
    "de": {
        "issue": "Ausstellungsdatum",
        "sale": "Verkaufsdatum",
        "payment_date": "Zahlungseingang",
        "order": "Shopify-Bestellung",
        "seller": "Verkäufer",
        "buyer": "Käufer",
        "ship": "Lieferadresse",
        "lp": "Pos.",
        "name": "Bezeichnung",
        "qty": "Menge",
        "unit": "Einzelpreis",
        "disc": "Rabatt",
        "amount": "Betrag",
        "total": "Gesamtbetrag",
        "payment": "Zahlungsart",
        "currency": "Währung",
        "number": "Dokumentnr.",
        "number_dnr": "Belegnr.",
        "legal_dnr": "",
        "correction": "Korrektur",
        "before": "vorher",
        "after": "nachher",
        "test_watermark": "TESTDOKUMENT",
        "nbp_rate": "NBP-Kurs",
        "nbp_record": "Erfassung",
    },
    "fr": {
        "issue": "Date d'émission",
        "sale": "Date de vente",
        "payment_date": "Date de paiement",
        "order": "Commande Shopify",
        "seller": "Vendeur",
        "buyer": "Acheteur",
        "ship": "Adresse de livraison",
        "lp": "N°",
        "name": "Désignation",
        "qty": "Qté",
        "unit": "Prix unitaire",
        "disc": "Remise",
        "amount": "Montant",
        "total": "Montant total",
        "payment": "Mode de paiement",
        "currency": "Devise",
        "number": "N° document",
        "number_dnr": "N° reçu",
        "legal_dnr": "",
        "correction": "Rectification",
        "before": "avant",
        "after": "après",
        "test_watermark": "DOCUMENT TEST",
        "nbp_rate": "Taux NBP",
        "nbp_record": "Enregistrement",
    },
    "es": {
        "issue": "Fecha de emisión",
        "sale": "Fecha de venta",
        "payment_date": "Fecha de pago",
        "order": "Pedido Shopify",
        "seller": "Vendedor",
        "buyer": "Comprador",
        "ship": "Dirección de envío",
        "lp": "N.º",
        "name": "Descripción",
        "qty": "Cant.",
        "unit": "Precio unitario",
        "disc": "Descuento",
        "amount": "Importe",
        "total": "Importe total",
        "payment": "Forma de pago",
        "currency": "Moneda",
        "number": "N.º documento",
        "number_dnr": "N.º recibo",
        "legal_dnr": "",
        "correction": "Rectificación",
        "before": "antes",
        "after": "después",
        "test_watermark": "DOCUMENTO DE PRUEBA",
        "nbp_rate": "Tipo NBP",
        "nbp_record": "Registro",
    },
    "nl": {
        "issue": "Uitgiftedatum",
        "sale": "Verkoopdatum",
        "payment_date": "Datum betaling",
        "order": "Shopify-bestelling",
        "seller": "Verkoper",
        "buyer": "Koper",
        "ship": "Verzendadres",
        "lp": "Nr.",
        "name": "Omschrijving",
        "qty": "Aantal",
        "unit": "Stukprijs",
        "disc": "Korting",
        "amount": "Bedrag",
        "total": "Totaalbedrag",
        "payment": "Betaalmethode",
        "currency": "Valuta",
        "number": "Documentnr.",
        "number_dnr": "Bewijsnr.",
        "legal_dnr": "",
        "correction": "Correctie",
        "before": "voor",
        "after": "na",
        "test_watermark": "TESTDOCUMENT",
        "nbp_rate": "NBP-koers",
        "nbp_record": "Registratie",
    },
    "it": {
        "issue": "Data di emissione",
        "sale": "Data di vendita",
        "payment_date": "Data pagamento",
        "order": "Ordine Shopify",
        "seller": "Venditore",
        "buyer": "Acquirente",
        "ship": "Indirizzo di spedizione",
        "lp": "N.",
        "name": "Descrizione",
        "qty": "Qtà",
        "unit": "Prezzo unitario",
        "disc": "Sconto",
        "amount": "Importo",
        "total": "Importo totale",
        "payment": "Metodo di pagamento",
        "currency": "Valuta",
        "number": "N. documento",
        "number_dnr": "N. ricevuta",
        "legal_dnr": "",
        "correction": "Rettifica",
        "before": "prima",
        "after": "dopo",
        "test_watermark": "DOCUMENTO DI PROVA",
        "nbp_rate": "Tasso NBP",
        "nbp_record": "Registrazione",
    },
}

SHIPPING_LABEL: dict[InvoiceLanguage, str] = {
    "pl": "Wysyłka",
    "en": "Shipping",
    "de": "Versand",
    "fr": "Livraison",
    "es": "Envío",
    "nl": "Verzending",
    "it": "Spedizione",
}

PRODUCT_PLACEHOLDER: dict[InvoiceLanguage, str] = {
    "pl": "Reprodukcja / obraz",
    "en": "Art print",
    "de": "Kunstdruck",
    "fr": "Reproduction / tirage",
    "es": "Reproducción / lámina",
    "nl": "Kunstprint",
    "it": "Riproduzione / stampa",
}

PAYMENT_MANUAL: dict[InvoiceLanguage, str] = {
    "pl": "Przelew / gotówka",
    "en": "Bank transfer / card",
    "de": "Überweisung / Karte",
    "fr": "Virement / carte",
    "es": "Transferencia / tarjeta",
    "nl": "Overschrijving / kaart",
    "it": "Bonifico / carta",
}

TEST_LINE_ITEM: dict[InvoiceLanguage, str] = {
    "pl": "Pozycja testowa",
    "en": "Test line item",
    "de": "Testposition",
    "fr": "Ligne de test",
    "es": "Línea de prueba",
    "nl": "Testregel",
    "it": "Voce di test",
}

TEST_BUYER_NAME: dict[InvoiceLanguage, str] = {
    "pl": "[TEST] Nabywca testowy",
    "en": "[TEST] Test buyer",
    "de": "[TEST] Testkäufer",
    "fr": "[TEST] Acheteur test",
    "es": "[TEST] Comprador de prueba",
    "nl": "[TEST] Testkoper",
    "it": "[TEST] Acquirente test",
}

TEST_NOTE: dict[InvoiceLanguage, str] = {
    "pl": "DOKUMENT TESTOWY — do testu przepływu DNR/KPiR; nie trafia do eksportu ani licznika VAT.",
    "en": "TEST DOCUMENT — for DNR/ledger flow testing; excluded from export and VAT turnover.",
    "de": "TESTDOKUMENT — zum Testen des DNR/KPiR-Ablaufs; nicht in Export oder Umsatzsteuer.",
    "fr": "DOCUMENT TEST — pour tester le flux DNR/KPiR ; exclu de l'export et du chiffre d'affaires TVA.",
    "es": "DOCUMENTO DE PRUEBA — para probar el flujo DNR/KPiR; excluido de exportación e IVA.",
    "nl": "TESTDOCUMENT — voor DNR/KPiR-test; niet in export of btw-omzet.",
    "it": "DOCUMENTO DI PROVA — per test flusso DNR/KPiR; escluso da export e fatturato IVA.",
}

TAX_ID_LABELS: dict[str, dict[InvoiceLanguage, str]] = {
    "PL": {
        "pl": "NIP",
        "en": "Tax ID (NIP)",
        "de": "Steuernummer (NIP)",
        "fr": "N° fiscal (NIP)",
        "es": "NIF (NIP)",
        "nl": "Fiscaal nummer (NIP)",
        "it": "Codice fiscale (NIP)",
    },
    "EU": {
        "pl": "Nr VAT",
        "en": "VAT ID",
        "de": "USt-IdNr.",
        "fr": "N° TVA",
        "es": "NIF-IVA",
        "nl": "Btw-nummer",
        "it": "Partita IVA",
    },
    "OTHER": {
        "pl": "Identyfikator podatkowy",
        "en": "Tax ID",
        "de": "Steuer-ID",
        "fr": "N° fiscal",
        "es": "ID fiscal",
        "nl": "Fiscaal nummer",
        "it": "Codice fiscale",
    },
}


def normalize_language(lang: str | None, *, default: InvoiceLanguage = "pl") -> InvoiceLanguage:
    code = (lang or "").strip().lower()
    if code in INVOICE_LANGUAGES:
        return code  # type: ignore[return-value]
    return default


def language_from_country(country_code: str | None) -> InvoiceLanguage:
    cc = (country_code or "").strip().upper()[:2]
    return COUNTRY_TO_LANGUAGE.get(cc, "en")


def is_polish_language(lang: str) -> bool:
    return normalize_language(lang) == "pl"


def pdf_header_labels(lang: str, *, dnr: bool = False) -> dict[str, str]:
    code = normalize_language(lang)
    labels = dict(PDF_LABELS[code])
    labels["number"] = labels["number_dnr"] if dnr else labels["number"]
    if dnr and code == "pl":
        labels["legal"] = labels["legal_dnr"]
    else:
        labels["legal"] = ""
    return labels


def doc_type_for_mode(
    mode: str,
    lang: str,
    *,
    is_correction: bool = False,
    is_dnr: bool | None = None,
) -> str:
    """Tytuł dokumentu wg trybu JDG/DNR i języka."""
    from .constants import BUSINESS_MODE_DNR

    code = normalize_language(lang)
    dnr = is_dnr if is_dnr is not None else mode == BUSINESS_MODE_DNR
    if is_correction:
        if dnr and code == "pl":
            return DOC_TYPE_DNR_CORRECTION[code]
        if dnr:
            return DOC_TYPE_DNR_CORRECTION[code]
        return DOC_TYPE_JDG_CORRECTION[code]
    if dnr and code == "pl":
        return DOC_TYPE_DNR[code]
    if dnr:
        return DOC_TYPE_DNR[code]
    return DOC_TYPE_JDG[code]


def default_footnote_text(mode: str, lang: str) -> str:
    from .constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG

    code = normalize_language(lang)
    if mode == BUSINESS_MODE_DNR:
        return DEFAULT_FOOTNOTES_DNR[code]
    if mode == BUSINESS_MODE_JDG:
        return DEFAULT_FOOTNOTES_JDG[code]
    return DEFAULT_FOOTNOTES_DNR[code]


def all_default_footnotes_for_lang(lang: str) -> set[str]:
    from .constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG

    code = normalize_language(lang)
    return {
        DEFAULT_FOOTNOTES_DNR[code],
        DEFAULT_FOOTNOTES_JDG[code],
    }


def thank_you_footer(lang: str) -> str:
    return DEFAULT_THANK_YOU[normalize_language(lang)]


def manual_doc_label(lang: str, *, mode: str) -> str:
    """Etykieta języka w UI (sprzedaż poza Shopify)."""
    from .constants import BUSINESS_MODE_DNR

    code = normalize_language(lang)
    title = doc_type_for_mode(mode, code, is_dnr=mode == BUSINESS_MODE_DNR)
    return f"{LANGUAGE_LABELS[code]} — {title}"


# Próbki do podglądu PDF
SAMPLE_DATA: dict[InvoiceLanguage, dict[str, str | list[str]]] = {
    "pl": {
        "buyer_name": "Jan Kowalski",
        "buyer_email": "jan.kowalski@example.com",
        "buyer_addr": "ul. Przykładowa 1\n00-001 Warszawa\nPolska",
        "country": "PL",
        "currency": "PLN",
        "product": "Reprodukcja — Hahnemühle Photo Rag (A4)",
        "payment": "Przelew / karta",
    },
    "en": {
        "buyer_name": "John Smith",
        "buyer_email": "john@example.com",
        "buyer_addr": "Example Street 12\nSW1A 1AA London\nUnited Kingdom",
        "country": "GB",
        "currency": "EUR",
        "product": "Art print — Hahnemühle Photo Rag (A4)",
        "payment": "Card / bank transfer",
    },
    "de": {
        "buyer_name": "Hans Müller",
        "buyer_email": "hans@example.com",
        "buyer_addr": "Beispielstraße 12\n10115 Berlin\nDeutschland",
        "country": "DE",
        "currency": "EUR",
        "product": "Kunstdruck — Hahnemühle Photo Rag (A4)",
        "payment": "Karte / Überweisung",
    },
    "fr": {
        "buyer_name": "Marie Dupont",
        "buyer_email": "marie@example.com",
        "buyer_addr": "12 rue Exemple\n75001 Paris\nFrance",
        "country": "FR",
        "currency": "EUR",
        "product": "Tirage — Hahnemühle Photo Rag (A4)",
        "payment": "Carte / virement",
    },
    "es": {
        "buyer_name": "María García",
        "buyer_email": "maria@example.com",
        "buyer_addr": "Calle Ejemplo 12\n28001 Madrid\nEspaña",
        "country": "ES",
        "currency": "EUR",
        "product": "Lámina — Hahnemühle Photo Rag (A4)",
        "payment": "Tarjeta / transferencia",
    },
    "nl": {
        "buyer_name": "Jan de Vries",
        "buyer_email": "jan@example.com",
        "buyer_addr": "Voorbeeldstraat 12\n1012 AB Amsterdam\nNederland",
        "country": "NL",
        "currency": "EUR",
        "product": "Kunstprint — Hahnemühle Photo Rag (A4)",
        "payment": "Kaart / overschrijving",
    },
    "it": {
        "buyer_name": "Marco Rossi",
        "buyer_email": "marco@example.com",
        "buyer_addr": "Via Esempio 12\n20121 Milano\nItalia",
        "country": "IT",
        "currency": "EUR",
        "product": "Stampa — Hahnemühle Photo Rag (A4)",
        "payment": "Carta / bonifico",
    },
}
