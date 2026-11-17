import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "extract_sec_companyfacts.py"

class SecCompanyfactsExtractorTest(unittest.TestCase):
    def test_quarterly_fact_normalization_and_balance_sheet_tieout(self):
        accession = "0001045810-26-000075"
        base = {
            "accn": accession, "form": "10-Q", "filed": "2026-08-26",
            "fy": 2027, "fp": "Q2", "end": "2026-07-26"
        }
        def duration(value):
            return dict(base, start="2026-04-27", val=value)
        def instant(value):
            return dict(base, val=value)
        facts = {
            "Revenues": {"units": {"USD": [duration(100000000)]}},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [duration(100000000)]}},
            "Assets": {"units": {"USD": [instant(500000000)]}},
            "Liabilities": {"units": {"USD": [instant(200000000)]}},
            "StockholdersEquity": {"units": {"USD": [instant(300000000)]}},
        }
        payload = {"facts": {"us-gaap": facts}}
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            fixture = tmp / "companyfacts.json"
            out = tmp / "out"
            fixture.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input-json", str(fixture), "--output-dir", str(out)],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)
            with (out / "Normalized_Financials_Long.csv").open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            revenue = [r for r in rows if r["line_item_id"] == "revenue"]
            self.assertEqual(len(revenue), 1, "alternate revenue concepts must not duplicate one canonical line")
            self.assertEqual(revenue[0]["period_end"], "2026-07-26")
            self.assertEqual(revenue[0]["period_type"], "quarterly")
            self.assertEqual(float(revenue[0]["normalized_value"]), 100.0)
            with (out / "Validation_Checks.csv").open(newline="", encoding="utf-8") as f:
                checks = list(csv.DictReader(f))
            self.assertTrue(any(row["result"] == "PASS" for row in checks))
            with (out / "QA_Flags.csv").open(newline="", encoding="utf-8") as f:
                flags = list(csv.DictReader(f))
            self.assertEqual(len(flags), 0)

if __name__ == "__main__":
    unittest.main()
