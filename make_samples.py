"""Generates synthetic invoice PDFs (fictional companies) with deliberately different layouts.

Only needed to recreate the sample input; the extractor itself does not need PyMuPDF.
Requires: pymupdf.
"""
from __future__ import annotations

from pathlib import Path

import fitz

OUT = Path(__file__).resolve().parent / "input"
FONT = "C:/Windows/Fonts/arial.ttf"  # has the euro sign; the built-in Helvetica does not

# (file, layout, fields) — layout changes labels, order and number formats on purpose.
INVOICES = [
    ("inv_001.pdf", "A", {"no": "INV-2026-0141", "date": "2026-09-03", "vendor": "Contoso Supplies Ltd",
                          "lines": [("Paper A4, 10 boxes", 1, 85.00), ("Toner XL", 2, 64.50)], "vat": 20}),
    ("inv_002.pdf", "B", {"no": "F-77812", "date": "14/09/2026", "vendor": "Atelier Fabrikam Création SARL",
                          "lines": [("Design work, 6 h", 6, 55.00)], "vat": 20}),
    ("inv_003.pdf", "A", {"no": "INV-2026-0157", "date": "2026-09-18", "vendor": "Contoso Supplies Ltd",
                          "lines": [("USB-C hub", 3, 29.90), ("Cable set", 3, 12.00), ("Delivery", 1, 9.50)], "vat": 20}),
    ("inv_004.pdf", "C", {"no": "2026/0932", "date": "22.09.2026", "vendor": "Tailspin Logistics GmbH",
                          "lines": [("Freight Nice-Munich", 1, 1240.00)], "vat": 19}),
    # Planted defect: printed total does not match the lines (should be flagged, not "fixed").
    ("inv_005.pdf", "B", {"no": "F-77840", "date": "29/09/2026", "vendor": "Atelier Fabrikam Création SARL",
                          "lines": [("Logo revisions", 1, 180.00)], "vat": 20, "total_override": 225.00}),
    # Planted defect: no invoice number on the document.
    ("inv_006.pdf", "C", {"no": "", "date": "30.09.2026", "vendor": "Tailspin Logistics GmbH",
                          "lines": [("Storage, September", 1, 310.00)], "vat": 19}),
]


def money(v: float, layout: str) -> str:
    if layout == "A":
        return f"{v:,.2f}"                                       # 1,240.00
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")         # 1 240,00
    return s + (" EUR" if layout == "C" else " €")


def render(path: Path, layout: str, f: dict) -> None:
    net = round(sum(q * p for _, q, p in f["lines"]), 2)
    vat = round(net * f["vat"] / 100, 2)
    total = f.get("total_override", round(net + vat, 2))
    labels = {
        "A": ("INVOICE", "Invoice No:", "Date:", "Subtotal", "VAT", "TOTAL DUE"),
        "B": ("FACTURE", "Facture n°", "Date :", "Total HT", "TVA", "Total TTC"),
        "C": ("RECHNUNG / INVOICE", "Invoice number", "Invoice date", "Net amount", "VAT", "Amount due"),
    }[layout]
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="arial", fontfile=FONT)
    y = 60
    page.insert_text((50, y), f["vendor"], fontsize=15, fontname="arial")
    page.insert_text((400, y), labels[0], fontsize=15, fontname="arial")
    y += 40
    if f["no"]:
        page.insert_text((50, y), f"{labels[1]} {f['no']}", fontsize=10, fontname="arial")
    page.insert_text((300, y), f"{labels[2]} {f['date']}", fontsize=10, fontname="arial")
    y += 40
    page.insert_text((50, y), "Description", fontsize=10, fontname="arial")
    page.insert_text((330, y), "Qty", fontsize=10, fontname="arial")
    page.insert_text((400, y), "Unit", fontsize=10, fontname="arial")
    page.insert_text((480, y), "Amount", fontsize=10, fontname="arial")
    for desc, q, p in f["lines"]:
        y += 18
        page.insert_text((50, y), desc, fontsize=10, fontname="arial")
        page.insert_text((330, y), str(q), fontsize=10, fontname="arial")
        page.insert_text((400, y), money(p, layout), fontsize=10, fontname="arial")
        page.insert_text((480, y), money(q * p, layout), fontsize=10, fontname="arial")
    y += 36
    for label, value in ((labels[3], net), (f"{labels[4]} {f['vat']}%", vat), (labels[5], total)):
        page.insert_text((330, y), label, fontsize=10, fontname="arial")
        page.insert_text((480, y), money(value, layout), fontsize=10, fontname="arial")
        y += 18
    page.insert_text((50, 800), "Synthetic sample for a demo. Fictional company.", fontsize=8, fontname="arial")
    doc.save(path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, layout, fields in INVOICES:
        render(OUT / name, layout, fields)
    print("written", len(INVOICES), "PDFs to", OUT)
