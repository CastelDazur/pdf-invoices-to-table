"""PDF invoices -> one checked table.

Reads every PDF in a folder (text PDFs, not scans), pulls invoice number, date, vendor,
net, VAT and total, checks that net + VAT = total, and writes:
  invoices.csv  one row per PDF, with a needs_review column
  report.md     counts and the files that need a human decision
Nothing is guessed: if a field is missing or the numbers don't add up, the row is flagged.

Requires: pypdf.  Usage: python pdf_to_table.py input --out out
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

# pypdf prints a line for every odd entry in a font's character map; the text still comes
# out right, so those notices are kept out of the user's console.
logging.getLogger("pypdf").setLevel(logging.ERROR)

LABELS = {
    "no": [r"Invoice No:", r"Facture n°", r"Invoice number"],
    "date": [r"Date:", r"Date :", r"Invoice date"],
    "net": [r"Subtotal", r"Total HT", r"Net amount"],
    "vat": [r"VAT \d+%", r"TVA \d+%"],
    "total": [r"TOTAL DUE", r"Total TTC", r"Amount due"],
}
AMOUNT = r"(-?[\d][\d  ,.]*\d)\s*(?:€|EUR)?"
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y")


@dataclass
class Row:
    file: str
    invoice_no: str = ""
    date: str = ""
    vendor: str = ""
    net: str = ""
    vat: str = ""
    total: str = ""
    review: list[str] = field(default_factory=list)


def normalize(text: str) -> str:
    """Many PDFs (Word/Excel exports, embedded fonts) give odd spaces and dashes:
    non-breaking and thin spaces, soft hyphens, en dashes. Turn them into plain ones."""
    for odd in ("\xa0", " ", " "):
        text = text.replace(odd, " ")
    for odd in ("\xad", "‐", "‑", "‒", "–"):
        text = text.replace(odd, "-")
    return text


def parse_amount(text: str) -> float | None:
    """'1,240.00' / '1 240,00' / '180,00' -> float. Returns None if it can't be read safely."""
    s = text.replace(" ", " ").replace("\xa0", " ").strip()
    if re.fullmatch(r"\d{1,3}(,\d{3})*\.\d{2}", s):
        return float(s.replace(",", ""))
    if re.fullmatch(r"\d{1,3}( \d{3})*,\d{2}", s) or re.fullmatch(r"\d+,\d{2}", s):
        return float(s.replace(" ", "").replace(",", "."))
    if re.fullmatch(r"\d+\.\d{2}", s):
        return float(s)
    return None


def find_after(text: str, labels: list[str], pattern: str) -> str:
    for label in labels:
        m = re.search(label + r"\s*" + pattern, text)
        if m:
            return m.group(1).strip()
    return ""


def iso_date(raw: str) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract(path: Path) -> Row:
    text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    text = normalize(text)
    row = Row(file=path.name)
    if not text.strip():
        row.review.append("no text layer (scanned PDF?): needs OCR")
        return row
    # The first line holds the vendor; a document title printed on the same line (INVOICE,
    # FACTURE, RECHNUNG / INVOICE) comes out glued to it, so only those known titles are cut off.
    first = text.strip().splitlines()[0].strip()
    row.vendor = re.sub(r"\s+(RECHNUNG / INVOICE|INVOICE|FACTURE|RECHNUNG)$", "", first)
    row.invoice_no = find_after(text, LABELS["no"], r"([A-Z0-9][A-Z0-9/\-]+)")
    raw_date = find_after(text, LABELS["date"], r"([\d./\-]{8,10})")
    numbers = {k: find_after(text, LABELS[k], AMOUNT) for k in ("net", "vat", "total")}

    if not row.invoice_no:
        row.review.append("invoice number not found")
    if raw_date:
        d = iso_date(raw_date)
        row.date = d or raw_date
        if not d:
            row.review.append(f"date not recognised: {raw_date}")
    else:
        row.review.append("date not found")

    values = {}
    for k, raw in numbers.items():
        v = parse_amount(raw) if raw else None
        values[k] = v
        setattr(row, k, f"{v:.2f}" if v is not None else raw)
        if v is None:
            row.review.append(f"{k} not found or unreadable")
    if None not in values.values() and abs(values["net"] + values["vat"] - values["total"]) > 0.01:
        row.review.append(f"net + VAT = {values['net'] + values['vat']:.2f} but total says {values['total']:.2f}")
    return row


def run(src: Path, out: Path) -> list[Row]:
    out.mkdir(parents=True, exist_ok=True)
    rows = [extract(p) for p in sorted(src.glob("*.pdf"))]
    with (out / "invoices.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "invoice_no", "date", "vendor", "net", "vat", "total", "needs_review"])
        for r in rows:
            w.writerow([r.file, r.invoice_no, r.date, r.vendor, r.net, r.vat, r.total, "; ".join(r.review)])
    flagged = [r for r in rows if r.review]
    lines = [f"# PDF to table report: {src.name}", "",
             f"- PDFs read: {len(rows)}", f"- Clean rows: {len(rows) - len(flagged)}",
             f"- Need your decision: {len(flagged)}", ""]
    if flagged:
        lines.append("## Need your decision (values were not guessed)")
        lines += [f"- {r.file}: {'; '.join(r.review)}" for r in flagged]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    a = ap.parse_args()
    res = run(a.src, a.out)
    print(f"{len(res)} PDFs -> {a.out / 'invoices.csv'}; flagged: {sum(1 for r in res if r.review)}")
