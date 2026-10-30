"""Regression guard for the sensitive contract API.

Static source guard; authenticated HTTP permission tests remain a release gate.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "django" / "geno" / "api_views.py"


class ContractAPIProtectionTests(unittest.TestCase):
    def test_contract_viewset_requires_admin_permission(self):
        code = SOURCE.read_text(encoding="utf-8")
        match = re.search(r"^class ContractViewSet\(.*?\):(?P<body>.*?)(?=^class |\Z)", code, re.M | re.S)
        self.assertIsNotNone(match, "ContractViewSet must exist")
        body = match.group("body")
        self.assertRegex(body, r"(?m)^\s+permission_classes\s*=\s*\[permissions\.IsAdminUser\]")
        self.assertNotRegex(body, r"(?m)^\s+permission_classes\s*=\s*\[permissions\.AllowAny\]")


if __name__ == "__main__":
    unittest.main()
