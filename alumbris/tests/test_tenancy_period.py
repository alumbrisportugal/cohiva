"""Contract-period classification tests. No Django database required."""
from datetime import date
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "django" / "geno" / "tenancy_period.py"
spec = importlib.util.spec_from_file_location("alumbris_tenancy_period", SOURCE)
mod = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class ContractPeriodTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 30)

    def check(self, expected, start, end, state):
        self.assertEqual(mod.contract_period(start=start, end=end, state=state, today=self.today), expected)

    def test_current_signed_contract(self):
        self.check(mod.ContractPeriod.CURRENT, date(2026, 1, 1), date(2027, 1, 1), "unterzeichnet")

    def test_future_contract_not_current(self):
        self.check(mod.ContractPeriod.FUTURE, date(2026, 11, 1), None, "unterzeichnet")

    def test_expired_contract_not_current(self):
        self.check(mod.ContractPeriod.EXPIRED, date(2024, 1, 1), date(2026, 10, 29), "unterzeichnet")

    def test_null_end_allowed(self):
        self.check(mod.ContractPeriod.CURRENT, date(2024, 1, 1), None, "unterzeichnet")

    def test_end_date_is_inclusive(self):
        self.check(mod.ContractPeriod.CURRENT, date(2024, 1, 1), self.today, "unterzeichnet")

    def test_invalid_date_interval(self):
        self.check(mod.ContractPeriod.INVALID, date(2027, 1, 1), date(2026, 1, 1), "unterzeichnet")

    def test_unsigned_not_current(self):
        self.check(mod.ContractPeriod.UNSIGNED, date(2026, 1, 1), None, "angeboten")

    def test_cancelled_not_current(self):
        self.check(mod.ContractPeriod.INVALID, date(2026, 1, 1), None, "ungueltig")

    def test_termination_notice_requires_review(self):
        self.check(mod.ContractPeriod.INVALID, date(2026, 1, 1), date(2027, 1, 1), "gekuendigt")

if __name__ == "__main__":
    unittest.main()
