# PDF invoices to one checked table

[![test](https://github.com/CastelDazur/pdf-invoices-to-table/actions/workflows/test.yml/badge.svg)](https://github.com/CastelDazur/pdf-invoices-to-table/actions/workflows/test.yml)

You have a folder of PDF invoices from different suppliers. Each one looks different: other labels, other date and number formats. This script reads them all and gives you one table, plus a short list of the invoices a person should look at.

A bounded demo on made-up data.

## Run

Python 3.11 or newer. One dependency, `pypdf`.

```bash
pip install -r requirements.txt
python pdf_to_table.py input --out out
python -m unittest -v
```

On Windows, use `py` instead of `python`.

Tested in CI on Windows, macOS and Linux with Python 3.11, 3.12, 3.13 and 3.14: the unit tests, plus a byte-for-byte check that the sample gives exactly `expected_output/`.

## What you get

| File | What's in it |
|---|---|
| `invoices.csv` | One row per PDF: invoice number, date (YYYY-MM-DD), vendor, net, VAT, total, and a `needs_review` column |
| `report.md` | How many PDFs were read, how many are clean, and which ones need your decision and why |

## What it checks

- Finds the fields even when the labels differ: `Invoice No:` / `Facture n°` / `Invoice number`, `Subtotal` / `Total HT` / `Net amount`, and so on.
- Reads amounts written as `1,240.00`, `1 240,00 €` or `180,00 EUR`, and dates as `2026-09-03`, `14/09/2026` or `22.09.2026`.
- Copes with the odd characters PDFs often hide: non-breaking spaces, soft hyphens, en dashes.
- Checks that net + VAT equals the total.
- Flags a missing invoice number, an unreadable date or amount, and a total that doesn't add up.

Nothing is guessed. If something is missing or doesn't match, the value stays as printed and the row is flagged.

## The sample

`input/` has 6 made-up invoices. The suppliers use well-known placeholder names (Contoso, Fabrikam, Tailspin) so they cannot be mistaken for real companies. The PDFs were made by `make_samples.py` (needs `pymupdf` and the Arial font, so in practice Windows); you only need it to change the sample. Two have planted problems: one total doesn't match its lines, one invoice has no number. `expected_output/` is what the command above produces: 4 clean rows, 2 flagged.

## Limits

Works on PDFs that contain text. Scanned PDFs (pictures of paper) need OCR first; the script tells you when a PDF has no text layer. New layouts are handled by adding their labels to `LABELS` in `pdf_to_table.py`.

## Support scope

Issues are welcome for reproducible defects in this demo: a command from this README that fails, or output that differs from `expected_output/` on the bundled sample. Please include the Python version, OS and the exact command.

Adding your own invoice layouts, OCR for scanned PDFs or export to your accounting tool is separate work, not a bug fix.

## Using it on real invoices

Before real invoices are processed, the fields, the labels used by each supplier and the rounding rule for the total check are agreed in writing. The PDFs are only read, never changed, and every flagged row says why.

## License

[MIT](LICENSE)

---

[castel.studio](https://castel.studio/)
