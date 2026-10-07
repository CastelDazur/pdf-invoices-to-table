import csv
import tempfile
import unittest
from pathlib import Path

from pdf_to_table import iso_date, normalize, parse_amount, run

HERE = Path(__file__).resolve().parent


class AmountTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_amount("1,240.00"), 1240.0)
        self.assertEqual(parse_amount("1 240,00"), 1240.0)
        self.assertEqual(parse_amount("180,00"), 180.0)
        self.assertEqual(parse_amount("64.50"), 64.5)

    def test_unreadable_is_none(self):
        self.assertIsNone(parse_amount("n/a"))
        self.assertIsNone(parse_amount("1.2.3"))

    def test_odd_spaces_and_dashes(self):
        self.assertEqual(normalize("INV\xad2026‑0141\xa0Date"), "INV-2026-0141 Date")

    def test_dates(self):
        self.assertEqual(iso_date("14/09/2026"), "2026-09-14")
        self.assertEqual(iso_date("22.09.2026"), "2026-09-22")
        self.assertIsNone(iso_date("31/02/2026"))


class SampleRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.rows = {r.file: r for r in run(HERE / "input", Path(cls.tmp.name))}
        cls.out = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_pdfs_read(self):
        self.assertEqual(len(self.rows), 6)

    def test_clean_invoice(self):
        r = self.rows["inv_001.pdf"]
        self.assertEqual((r.invoice_no, r.date, r.vendor), ("INV-2026-0141", "2026-09-03", "Contoso Supplies Ltd"))
        self.assertEqual((r.net, r.vat, r.total), ("214.00", "42.80", "256.80"))
        self.assertEqual(r.review, [])

    def test_vendor_keeps_legal_form(self):
        self.assertEqual(self.rows["inv_002.pdf"].vendor, "Atelier Fabrikam Création SARL")
        self.assertEqual(self.rows["inv_004.pdf"].vendor, "Tailspin Logistics GmbH")

    def test_european_formats(self):
        r = self.rows["inv_004.pdf"]
        self.assertEqual((r.date, r.net, r.total), ("2026-09-22", "1240.00", "1475.60"))

    def test_wrong_total_flagged_not_fixed(self):
        r = self.rows["inv_005.pdf"]
        self.assertEqual(r.total, "225.00")
        self.assertTrue(any("total says" in x for x in r.review))

    def test_missing_number_flagged(self):
        self.assertIn("invoice number not found", self.rows["inv_006.pdf"].review)

    def test_outputs_written(self):
        with (self.out / "invoices.csv").open(encoding="utf-8") as fh:
            self.assertEqual(len(list(csv.DictReader(fh))), 6)
        self.assertIn("Need your decision: 2", (self.out / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
