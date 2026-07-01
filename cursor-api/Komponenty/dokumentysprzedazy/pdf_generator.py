"""Generowanie PDF — Faktura bez VAT / Invoice without VAT (A4, reportlab)."""

from __future__ import annotations

import xml.sax.saxutils as saxutils
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .constants import BUSINESS_MODE_DNR
from .invoice_builder import is_dnr_business_mode
from .invoice_helpers import is_test_invoice
from .models import InvoiceRecord, SellerSettings
from .numbering import parse_invoice_number
from .pdf_fonts import register_invoice_fonts

# Kolorystyka
_CLR_INK = colors.HexColor("#1a1a1a")
_CLR_MUTED = colors.HexColor("#5c5c5c")
_CLR_LINE = colors.HexColor("#d8dce3")
_CLR_HEAD = colors.HexColor("#eef1f6")
_CLR_ACCENT = colors.HexColor("#2f3d4f")

_CLR_DNR_ACCENT = colors.HexColor("#3d4f3a")
_CLR_DNR_HEAD = colors.HexColor("#eef3ea")

_LOGO_MAX_W = 42 * mm
_LOGO_MAX_H = 22 * mm


def _fit_logo_image(path: str) -> Image:
    """Skaluje logo z zachowaniem proporcji (maks. _LOGO_MAX_W × _LOGO_MAX_H)."""
    logo = Image(path)
    iw = float(logo.imageWidth or 0)
    ih = float(logo.imageHeight or 0)
    if iw <= 0 or ih <= 0:
        logo.drawWidth = _LOGO_MAX_W
        logo.drawHeight = _LOGO_MAX_H
        return logo
    scale = min(_LOGO_MAX_W / iw, _LOGO_MAX_H / ih)
    logo.drawWidth = iw * scale
    logo.drawHeight = ih * scale
    return logo


def _esc(text: str) -> str:
    return saxutils.escape(str(text or ""))


def _fmt_money(amount: float, currency: str) -> str:
    sym = {"PLN": "zł", "EUR": "€", "USD": "$", "GBP": "£"}.get(currency.upper(), currency)
    if currency.upper() in ("PLN",):
        return f"{amount:,.2f} {sym}".replace(",", "\u00a0").replace(".", ",")
    return f"{sym}{amount:,.2f}"


def _styles(reg: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "inv_title",
            parent=base["Normal"],
            fontName=bold,
            fontSize=20,
            leading=24,
            textColor=_CLR_ACCENT,
            spaceAfter=0,
        ),
        "subtitle": ParagraphStyle(
            "inv_subtitle",
            parent=base["Normal"],
            fontName=reg,
            fontSize=9,
            leading=12,
            textColor=_CLR_MUTED,
        ),
        "normal": ParagraphStyle(
            "inv_normal",
            parent=base["Normal"],
            fontName=reg,
            fontSize=9.5,
            leading=13,
            textColor=_CLR_INK,
        ),
        "small": ParagraphStyle(
            "inv_small",
            parent=base["Normal"],
            fontName=reg,
            fontSize=8,
            leading=11,
            textColor=_CLR_MUTED,
        ),
        "label": ParagraphStyle(
            "inv_label",
            parent=base["Normal"],
            fontName=bold,
            fontSize=9,
            leading=12,
            textColor=_CLR_ACCENT,
            spaceAfter=2,
        ),
        "table_head": ParagraphStyle(
            "inv_table_head",
            parent=base["Normal"],
            fontName=bold,
            fontSize=8,
            leading=10,
            textColor=_CLR_ACCENT,
            spaceAfter=0,
        ),
        "meta_val": ParagraphStyle(
            "inv_meta_val",
            parent=base["Normal"],
            fontName=reg,
            fontSize=9,
            leading=12,
            textColor=_CLR_INK,
        ),
    }


def _items_col_widths(content_w: float) -> list[float]:
    """Szerokości kolumn pozycji — dopasowane do długich nagłówków (DE, PL, NL)."""
    w_lp = 13 * mm
    w_qty = 18 * mm
    w_unit = 32 * mm
    w_disc = 20 * mm
    w_amt = 28 * mm
    w_name = content_w - (w_lp + w_qty + w_unit + w_disc + w_amt)
    return [w_lp, max(w_name, 40 * mm), w_qty, w_unit, w_disc, w_amt]


def _is_dnr_layout(invoice: InvoiceRecord, settings: SellerSettings) -> bool:
    """Szablon rachunku (DNR) — tryb PL, nie test."""
    if is_test_invoice(invoice) or invoice.language != "pl":
        return False
    mode = getattr(invoice, "business_mode", "") or settings.business_mode or BUSINESS_MODE_DNR
    if is_dnr_business_mode(mode):
        return True
    parsed = parse_invoice_number(invoice.invoice_number or "")
    return bool(parsed and parsed[0] in ("DN", "KDN"))


from .i18n import pdf_header_labels


def _seller_paragraphs(
    labels: dict[str, str],
    invoice: InvoiceRecord,
    settings: SellerSettings,
    st: dict[str, ParagraphStyle],
) -> list:
    lines: list = [Paragraph(f"<b>{_esc(labels['seller'])}</b>", st["label"])]
    if invoice.seller.name:
        for part in invoice.seller.name.split("\n"):
            if part.strip():
                lines.append(Paragraph(_esc(part.strip()), st["normal"]))
    for line in (invoice.seller.address_lines or "").split("\n"):
        if line.strip():
            lines.append(Paragraph(_esc(line.strip()), st["normal"]))
    if settings.phone:
        lines.append(Paragraph(_esc(f"tel. {settings.phone}"), st["small"]))
    if settings.email or invoice.seller.email:
        lines.append(Paragraph(_esc(settings.email or invoice.seller.email), st["small"]))
    if settings.website:
        lines.append(Paragraph(_esc(settings.website), st["small"]))
    return lines


def _table_cell(text: str, style: ParagraphStyle, *, align: str = "left") -> Paragraph:
    para = Paragraph(_esc(text), style)
    para.hAlign = align
    return para


def _party_paragraphs(title: str, party, st: dict[str, ParagraphStyle]) -> list:
    lines: list = [Paragraph(f"<b>{_esc(title)}</b>", st["label"])]
    if party.name:
        for part in party.name.split("\n"):
            if part.strip():
                lines.append(Paragraph(_esc(part.strip()), st["normal"]))
    for line in (party.address_lines or "").split("\n"):
        if line.strip():
            lines.append(Paragraph(_esc(line.strip()), st["normal"]))
    if party.email:
        lines.append(Paragraph(_esc(party.email), st["small"]))
    return lines


def generate_invoice_pdf(
    invoice: InvoiceRecord,
    settings: SellerSettings,
    dest_path: Path,
) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    reg, bold = register_invoice_fonts()
    lang = invoice.language
    dnr_layout = _is_dnr_layout(invoice, settings)
    labels = pdf_header_labels(lang, dnr=dnr_layout)
    st = _styles(reg, bold)
    if dnr_layout:
        st["title"].textColor = _CLR_DNR_ACCENT
        st["label"].textColor = _CLR_DNR_ACCENT
    head_bg = _CLR_DNR_HEAD if dnr_layout else _CLR_HEAD
    accent_line = _CLR_DNR_ACCENT if dnr_layout else _CLR_ACCENT

    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story: list = []
    content_w = doc.width

    # Nagłówek: logo + tytuł
    title_block = [
        Paragraph(_esc(invoice.doc_type_label), st["title"]),
        Spacer(1, 2 * mm),
        Paragraph(_esc(invoice.invoice_number), st["subtitle"]),
    ]
    if dnr_layout and labels.get("legal"):
        title_block.append(Spacer(1, 1 * mm))
        title_block.append(Paragraph(_esc(labels["legal"]), st["small"]))
    if settings.logo_path and Path(settings.logo_path).is_file():
        try:
            logo = _fit_logo_image(settings.logo_path)
            logo.hAlign = "LEFT"
            header_tbl = Table([[logo, title_block]], colWidths=[content_w * 0.42, content_w * 0.58])
            header_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(header_tbl)
        except Exception:
            story.extend(title_block)
    else:
        story.extend(title_block)

    story.append(Spacer(1, 6 * mm))

    # Metadane w ramce
    meta_rows = [
        [
            _table_cell(labels["issue"], st["small"]),
            _table_cell(invoice.issue_date, st["meta_val"]),
            _table_cell(labels["sale"], st["small"]),
            _table_cell(invoice.sale_date, st["meta_val"]),
        ],
        [
            _table_cell(labels["order"], st["small"]),
            _table_cell(invoice.shopify_order_name or "—", st["meta_val"]),
            _table_cell(labels["number"], st["small"]),
            _table_cell(invoice.invoice_number, st["meta_val"]),
        ],
    ]
    pay_date = (invoice.payment_date or "")[:10]
    if dnr_layout and pay_date:
        meta_rows.append([
            _table_cell(labels["payment_date"], st["small"]),
            _table_cell(pay_date, st["meta_val"]),
            _table_cell("", st["small"]),
            _table_cell("", st["meta_val"]),
        ])
    meta_tbl = Table(meta_rows, colWidths=[32 * mm, 52 * mm, 32 * mm, content_w - 116 * mm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), head_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, _CLR_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, _CLR_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 7 * mm))

    # Sprzedawca / nabywca
    seller_block = (
        _seller_paragraphs(labels, invoice, settings, st)
        if dnr_layout
        else _party_paragraphs(labels["seller"], invoice.seller, st)
    )
    party_tbl = Table(
        [[seller_block, _party_paragraphs(labels["buyer"], invoice.buyer, st)]],
        colWidths=[content_w / 2 - 2 * mm, content_w / 2 - 2 * mm],
    )
    party_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.5, _CLR_LINE),
        ("BOX", (1, 0), (1, 0), 0.5, _CLR_LINE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(party_tbl)

    if invoice.shipping_address.address_lines and (
        invoice.shipping_address.address_lines != invoice.buyer.address_lines
    ):
        story.append(Spacer(1, 4 * mm))
        ship_lines = [Paragraph(f"<b>{_esc(labels['ship'])}</b>", st["label"])]
        for line in invoice.shipping_address.address_lines.split("\n"):
            if line.strip():
                ship_lines.append(Paragraph(_esc(line.strip()), st["normal"]))
        story.append(Table([[ship_lines]], colWidths=[content_w]))

    story.append(Spacer(1, 8 * mm))

    # Pozycje
    col_w = _items_col_widths(content_w)
    head_style = st["table_head"]
    table_data: list = [[
        _table_cell(labels["lp"], head_style, align="center"),
        _table_cell(labels["name"], head_style),
        _table_cell(labels["qty"], head_style, align="right"),
        _table_cell(labels["unit"], head_style, align="right"),
        _table_cell(labels["disc"], head_style, align="right"),
        _table_cell(labels["amount"], head_style, align="right"),
    ]]
    for item in invoice.items:
        table_data.append([
            _table_cell(str(item.position), st["normal"], align="center"),
            _table_cell(item.name[:80], st["normal"]),
            _table_cell(f"{item.quantity:g}", st["normal"], align="right"),
            _table_cell(_fmt_money(item.unit_price, invoice.currency), st["normal"], align="right"),
            _table_cell(
                _fmt_money(item.discount, invoice.currency) if item.discount else "—",
                st["normal"],
                align="right",
            ),
            _table_cell(_fmt_money(item.amount, invoice.currency), st["normal"], align="right"),
        ])

    items_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), head_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent_line),
        ("FONTNAME", (0, 0), (-1, -1), reg),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, _CLR_LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 1, _CLR_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, _CLR_LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (0, 0), 3),
        ("RIGHTPADDING", (0, 0), (0, 0), 3),
        ("LEFTPADDING", (2, 0), (2, 0), 3),
        ("RIGHTPADDING", (2, 0), (2, 0), 3),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 4 * mm))

    # Podsumowanie
    totals: list = [
        ["", "", "", "", labels["total"], _fmt_money(invoice.order_total, invoice.currency)],
        ["", "", "", "", labels["currency"], invoice.currency],
    ]
    if invoice.payment_method:
        totals.append(["", "", "", "", labels["payment"], invoice.payment_method])

    tot_rows = []
    for row in totals:
        tot_rows.append([
            "", "", "", "",
            _table_cell(row[4], st["normal"] if row[4] != labels["total"] else st["label"], align="right"),
            _table_cell(
                row[5],
                st["meta_val"] if row[4] == labels["total"] else st["normal"],
                align="right",
            ),
        ])

    tot_tbl = Table(tot_rows, colWidths=col_w)
    tot_tbl.setStyle(TableStyle([
        ("LINEABOVE", (4, 0), (-1, 0), 1, accent_line),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (5, 0), (5, 0), 11),
    ]))
    story.append(tot_tbl)

    if invoice.doc_kind == "correction":
        story.append(Spacer(1, 5 * mm))
        corr_lbl = labels["correction"]
        story.append(Paragraph(
            f"<b>{_esc(corr_lbl)}</b>: {_esc(invoice.correction_of_number)} · "
            f"{labels['before']}: "
            f"{_esc(_fmt_money(invoice.amount_before_correction, invoice.currency))} · "
            f"{labels['after']}: "
            f"{_esc(_fmt_money(invoice.amount_after_correction, invoice.currency))}",
            st["normal"],
        ))

    story.append(Spacer(1, 10 * mm))
    story.append(Table([[""]], colWidths=[content_w], style=TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.5, _CLR_LINE),
    ])))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_esc(invoice.footnote), st["small"]))
    if invoice.thank_you_footer:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(_esc(invoice.thank_you_footer), st["small"]))

    if invoice.currency.upper() != "PLN" and invoice.exchange.total_amount_pln > 0:
        story.append(Spacer(1, 4 * mm))
        if lang == "pl":
            acc = (
                f"Kurs NBP ({invoice.exchange.exchange_rate_date}): "
                f"1 {invoice.currency} = {invoice.exchange.exchange_rate_value:.4f} PLN · "
                f"Ewidencja: {_fmt_money(invoice.exchange.total_amount_pln, 'PLN')}"
            )
        else:
            acc = (
                f"{labels['nbp_rate']} ({invoice.exchange.exchange_rate_date}): "
                f"1 {invoice.currency} = {invoice.exchange.exchange_rate_value:.4f} PLN"
            )
        story.append(Paragraph(_esc(acc), st["small"]))

    if is_test_invoice(invoice):
        test_lbl = labels["test_watermark"]

        def _watermark(canvas, _doc) -> None:
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#f8d7da"))
            canvas.setFont("Helvetica-Bold", 42)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, test_lbl)
            canvas.restoreState()

        doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
    else:
        doc.build(story)
    return dest_path


def pdf_filename(invoice: InvoiceRecord) -> str:
    parsed = parse_invoice_number(invoice.invoice_number or "")
    if parsed:
        prefix, seq, year = parsed
        order_part = invoice.shopify_order_name.replace("#", "").strip() or str(invoice.shopify_order_id)
        return f"{prefix}-{year}-{seq:03d}-order-{order_part}.pdf"
    parts = (invoice.invoice_number or "DOC/0/0").split("/")
    prefix = parts[0] if parts else "DOC"
    num = parts[1] if len(parts) > 1 else "0"
    year = parts[2] if len(parts) > 2 else "2026"
    order_part = invoice.shopify_order_name.replace("#", "").strip() or str(invoice.shopify_order_id)
    return f"{prefix}-{num}-{year}-order-{order_part}.pdf"
