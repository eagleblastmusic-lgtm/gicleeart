"""Wysyłka e-mail z dokumentów sprzedaży — SMTP Gmail lub szkic z załącznikiem."""

from __future__ import annotations

import os
import smtplib
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser
from dataclasses import dataclass
from email import policy
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from Komponenty.poczta.env_config import (
    DEFAULT_USER as GMAIL_SHOP_ACCOUNT,
    credentials_configured,
    gmail_imap_password,
    gmail_imap_user,
)

from .i18n import (
    DOC_TYPE_DNR,
    DOC_TYPE_DNR_CORRECTION,
    DOC_TYPE_JDG,
    DOC_TYPE_JDG_CORRECTION,
    InvoiceLanguage,
    normalize_language,
)
from .models import InvoiceRecord, SellerSettings
from .storage import load_settings

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


@dataclass(frozen=True)
class EmailSendResult:
    sender: str
    mode: str  # smtp | eml | compose
    attached: bool = False


class EmailDeliveryError(RuntimeError):
    """Nie udało się wysłać ani przygotować wiadomości z załącznikiem."""


def shop_sender_email(settings: SellerSettings | None = None) -> str:
    """Adres nadawcy — ustawienia faktury lub domyślny Gmail sklepu."""
    if settings and (settings.email or "").strip():
        return settings.email.strip()
    return GMAIL_SHOP_ACCOUNT


def _use_gmail_web(sender: str) -> bool:
    return sender.lower().endswith("@gmail.com")


def _build_mime_message(
    *,
    to: str,
    subject: str,
    body: str,
    sender: str,
    pdf_path: str = "",
) -> MIMEMultipart:
    msg = MIMEMultipart(policy=policy.SMTP)
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText((body or "").strip(), "plain", "utf-8"))
    if pdf_path:
        path = Path(pdf_path)
        if path.is_file():
            part = MIMEApplication(path.read_bytes(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            msg.attach(part)
    return msg


def _smtp_send(*, to: str, subject: str, body: str, sender: str, pdf_path: str = "") -> None:
    password = gmail_imap_password()
    login = gmail_imap_user()
    msg = _build_mime_message(to=to, subject=subject, body=body, sender=sender, pdf_path=pdf_path)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=45) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(login, password)
        smtp.send_message(msg)


def _open_eml_draft(*, to: str, subject: str, body: str, sender: str, pdf_path: str) -> None:
    msg = _build_mime_message(to=to, subject=subject, body=body, sender=sender, pdf_path=pdf_path)
    fd, raw_path = tempfile.mkstemp(suffix=".eml", prefix="giclee-doc-")
    os.close(fd)
    path = Path(raw_path)
    path.write_bytes(msg.as_bytes())
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


def _open_web_compose(
    *,
    to: str,
    subject: str,
    body: str,
    sender: str,
    pdf_path: str = "",
) -> None:
    full_body = (body or "").strip()
    if pdf_path:
        full_body = f"{full_body}\n\n---\nZałącz PDF ręcznie:\n{pdf_path}".strip()

    if _use_gmail_web(sender):
        params = urllib.parse.urlencode(
            {
                "authuser": sender,
                "view": "cm",
                "fs": "1",
                "to": to,
                "su": subject,
                "body": full_body,
            },
            quote_via=urllib.parse.quote,
        )
        webbrowser.open(f"https://mail.google.com/mail/?{params}")
        return

    params = urllib.parse.urlencode(
        {"subject": subject, "body": full_body},
        quote_via=urllib.parse.quote,
    )
    webbrowser.open(f"mailto:{urllib.parse.quote(to)}?{params}")


def deliver_email_with_attachment(
    *,
    to: str,
    subject: str,
    body: str,
    sender: str | None = None,
    pdf_path: str = "",
) -> EmailSendResult:
    """Wysyła lub przygotowuje wiadomość z PDF (SMTP → .eml → Gmail Web)."""
    to = (to or "").strip()
    if not to:
        raise ValueError("Brak adresu odbiorcy.")
    settings = load_settings().seller
    from_addr = (sender or shop_sender_email(settings)).strip()
    attachment = (pdf_path or "").strip()
    has_file = bool(attachment and Path(attachment).is_file())

    if has_file and credentials_configured():
        try:
            _smtp_send(to=to, subject=subject, body=body, sender=from_addr, pdf_path=attachment)
            return EmailSendResult(sender=from_addr, mode="smtp", attached=True)
        except (OSError, smtplib.SMTPException) as exc:
            last_err: Exception = exc
        else:
            last_err = None
    else:
        last_err = None

    if has_file:
        try:
            _open_eml_draft(
                to=to, subject=subject, body=body, sender=from_addr, pdf_path=attachment,
            )
            return EmailSendResult(sender=from_addr, mode="eml", attached=True)
        except OSError as exc:
            if last_err is None:
                last_err = exc

    try:
        _open_web_compose(
            to=to,
            subject=subject,
            body=body,
            sender=from_addr,
            pdf_path=attachment if has_file else "",
        )
    except OSError as exc:
        raise EmailDeliveryError(str(last_err or exc)) from exc

    return EmailSendResult(sender=from_addr, mode="compose", attached=False)


def open_compose_email(
    *,
    to: str,
    subject: str,
    body: str,
    sender: str | None = None,
    pdf_path: str = "",
) -> EmailSendResult:
    """Otwiera compose bez załącznika lub deleguje do deliver_email_with_attachment."""
    if pdf_path:
        return deliver_email_with_attachment(
            to=to, subject=subject, body=body, sender=sender, pdf_path=pdf_path,
        )
    to = (to or "").strip()
    if not to:
        raise ValueError("Brak adresu odbiorcy.")
    settings = load_settings().seller
    from_addr = (sender or shop_sender_email(settings)).strip()
    _open_web_compose(to=to, subject=subject, body=body, sender=from_addr)
    return EmailSendResult(sender=from_addr, mode="compose", attached=False)


_PL_EMAIL_DOC: dict[str, str] = {
    DOC_TYPE_JDG["pl"]: "fakturę bez VAT",
    DOC_TYPE_JDG_CORRECTION["pl"]: "korektę faktury bez VAT",
    DOC_TYPE_DNR["pl"]: "rachunek",
    DOC_TYPE_DNR_CORRECTION["pl"]: "korektę rachunku",
}


def _email_doc_phrase(invoice: InvoiceRecord) -> str:
    """Sformułowanie dokumentu w treści maila (PL: biernik — „przesyłamy fakturę”)."""
    label = (invoice.doc_type_label or "").strip()
    if invoice.language == "pl":
        return _PL_EMAIL_DOC.get(label, label.lower() or "dokument")
    return label or "Dokument sprzedaży"


def invoice_email_body(invoice: InvoiceRecord, settings: SellerSettings | None = None) -> str:
    """Treść wiadomości z fakturą/rachunkiem w języku dokumentu."""
    seller = settings or load_settings().seller
    sender = shop_sender_email(seller)
    name = (seller.name or "GicleeArt").strip()
    doc = _email_doc_phrase(invoice)
    num = invoice.invoice_number or ""
    lang = invoice.language

    if lang == "pl":
        return (
            f"Dzień dobry,\n\n"
            f"W załączniku przesyłamy {doc} {num} "
            f"do zamówienia {invoice.shopify_order_name or ''}.\n\n"
            f"Pozdrawiamy,\n{name}\n{sender}"
        ).strip()
    if lang == "de":
        return (
            f"Guten Tag,\n\n"
            f"Anbei erhalten Sie {doc} {num} "
            f"für Bestellung {invoice.shopify_order_name or ''}.\n\n"
            f"Mit freundlichen Grüßen\n{name}\n{sender}"
        ).strip()
    if lang == "fr":
        return (
            f"Bonjour,\n\n"
            f"Veuillez trouver ci-joint {doc} {num} "
            f"pour la commande {invoice.shopify_order_name or ''}.\n\n"
            f"Cordialement,\n{name}\n{sender}"
        ).strip()
    if lang == "es":
        return (
            f"Buenos días,\n\n"
            f"Adjuntamos {doc} {num} "
            f"para el pedido {invoice.shopify_order_name or ''}.\n\n"
            f"Saludos,\n{name}\n{sender}"
        ).strip()
    if lang == "nl":
        return (
            f"Goedendag,\n\n"
            f"Bijgevoegd vindt u {doc} {num} "
            f"voor bestelling {invoice.shopify_order_name or ''}.\n\n"
            f"Met vriendelijke groet,\n{name}\n{sender}"
        ).strip()
    if lang == "it":
        return (
            f"Buongiorno,\n\n"
            f"In allegato {doc} {num} "
            f"per l'ordine {invoice.shopify_order_name or ''}.\n\n"
            f"Cordiali saluti,\n{name}\n{sender}"
        ).strip()
    return (
        f"Hello,\n\n"
        f"Please find attached {doc} {num} "
        f"for order {invoice.shopify_order_name or ''}.\n\n"
        f"Best regards,\n{name}\n{sender}"
    ).strip()


def production_eta_line(language: str, days: int) -> str:
    """Jedna linia o szacowanym czasie produkcji obrazu (1–7 dni)."""
    lang: InvoiceLanguage = normalize_language(language)
    n = max(1, min(7, int(days)))

    if lang == "pl":
        unit = "dzień" if n == 1 else "dni"
        return f"Szacowany czas produkcji obrazu: {n} {unit}."
    if lang == "de":
        unit = "Tag" if n == 1 else "Tage"
        return f"Geschätzte Produktionszeit des Bildes: {n} {unit}."
    if lang == "fr":
        unit = "jour" if n == 1 else "jours"
        return f"Délai de production estimé de l'œuvre : {n} {unit}."
    if lang == "es":
        unit = "día" if n == 1 else "días"
        return f"Tiempo estimado de producción de la obra: {n} {unit}."
    if lang == "nl":
        unit = "dag" if n == 1 else "dagen"
        return f"Geschatte productietijd van het werk: {n} {unit}."
    if lang == "it":
        unit = "giorno" if n == 1 else "giorni"
        return f"Tempo stimato di produzione dell'opera: {n} {unit}."
    unit = "day" if n == 1 else "days"
    return f"Estimated artwork production time: {n} {unit}."


def order_confirmation_body(
    order_name: str,
    settings: SellerSettings | None = None,
    *,
    language: str = "pl",
    production_days: int | None = None,
) -> str:
    seller = settings or load_settings().seller
    sender = shop_sender_email(seller)
    name = (seller.name or "GicleeArt").strip()
    lang: InvoiceLanguage = normalize_language(language)
    eta = (
        production_days
        if production_days is not None and 1 <= int(production_days) <= 7
        else None
    )

    if lang == "pl":
        opening = (
            f"Potwierdzamy przyjęcie zamówienia {order_name} do realizacji."
            if eta
            else f"Potwierdzamy przyjęcie zamówienia {order_name}."
        )
        lines = ["Dzień dobry,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Pozdrawiamy,\n{name}\n{sender}"])
        return "\n".join(lines).strip()
    if lang == "de":
        opening = (
            f"Wir bestätigen den Eingang Ihrer Bestellung {order_name} zur Bearbeitung."
            if eta
            else f"Wir bestätigen den Eingang Ihrer Bestellung {order_name}."
        )
        lines = ["Guten Tag,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Mit freundlichen Grüßen\n{name}\n{sender}"])
        return "\n".join(lines).strip()
    if lang == "fr":
        opening = (
            f"Nous confirmons la prise en charge de votre commande {order_name}."
            if eta
            else f"Nous confirmons la réception de votre commande {order_name}."
        )
        lines = ["Bonjour,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Cordialement,\n{name}\n{sender}"])
        return "\n".join(lines).strip()
    if lang == "es":
        opening = (
            f"Confirmamos la aceptación de su pedido {order_name} para su preparación."
            if eta
            else f"Confirmamos la recepción de su pedido {order_name}."
        )
        lines = ["Buenos días,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Saludos,\n{name}\n{sender}"])
        return "\n".join(lines).strip()
    if lang == "nl":
        opening = (
            f"Wij bevestigen de aanname van uw bestelling {order_name} voor verwerking."
            if eta
            else f"Wij bevestigen de ontvangst van uw bestelling {order_name}."
        )
        lines = ["Goedendag,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Met vriendelijke groet,\n{name}\n{sender}"])
        return "\n".join(lines).strip()
    if lang == "it":
        opening = (
            f"Confermiamo l'accettazione del suo ordine {order_name} per la lavorazione."
            if eta
            else f"Confermiamo la ricezione del suo ordine {order_name}."
        )
        lines = ["Buongiorno,", "", opening]
        if eta:
            lines.extend(["", production_eta_line(lang, eta)])
        lines.extend(["", f"Cordiali saluti,\n{name}\n{sender}"])
        return "\n".join(lines).strip()

    opening = (
        f"We confirm acceptance of your order {order_name} for processing."
        if eta
        else f"We confirm receipt of your order {order_name}."
    )
    lines = ["Hello,", "", opening]
    if eta:
        lines.extend(["", production_eta_line(lang, eta)])
    lines.extend(["", f"Best regards,\n{name}\n{sender}"])
    return "\n".join(lines).strip()


def send_invoice_email(invoice: InvoiceRecord) -> EmailSendResult:
    """Wysyła lub przygotowuje wiadomość z dokumentem PDF."""
    settings = load_settings().seller
    if not (invoice.buyer.email or "").strip():
        raise ValueError("Brak adresu e-mail nabywcy.")
    if not invoice.pdf_path or not Path(invoice.pdf_path).is_file():
        raise ValueError("Brak pliku PDF dokumentu.")
    subject = f"{invoice.doc_type_label} {invoice.invoice_number}"
    body = invoice_email_body(invoice, settings)
    return deliver_email_with_attachment(
        to=invoice.buyer.email,
        subject=subject,
        body=body,
        sender=shop_sender_email(settings),
        pdf_path=invoice.pdf_path,
    )


def invoice_send_prompt(to: str) -> str:
    """Tekst potwierdzenia przed wysyłką dokumentu."""
    if credentials_configured():
        return f"Wysłać dokument z załączonym PDF na {to}?"
    return (
        f"Przygotować wiadomość do {to}?\n\n"
        "PDF zostanie dołączony w kliencie poczty. "
        "Bez GMAIL_IMAP_APP_PASSWORD w .env — Gmail w przeglądarce (załącznik ręcznie)."
    )


def compose_hint(result: EmailSendResult) -> str:
    if result.mode == "smtp":
        return f"Wysłano z {result.sender} (PDF w załączniku)."
    if result.mode == "eml":
        return "Otwarto szkic z załączonym PDF — kliknij Wyślij w kliencie poczty."
    if _use_gmail_web(result.sender):
        return f"Otwarto Gmail ({result.sender}) — dołącz PDF ręcznie."
    return "Otwarto klienta poczty — dołącz PDF ręcznie."
