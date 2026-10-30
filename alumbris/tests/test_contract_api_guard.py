"""Static guard on sensitive Cohiva API endpoints.

Server-side authentication/authorization HTTP tests are required before release.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "django" / "geno" / "api_views.py"


class SensitiveAPIProtectionTests(unittest.TestCase):
    def test_all_sensitive_viewsets_restrict_to_staff(self):
        code = SOURCE.read_text(encoding="utf-8")
        for name in ("UserViewSet", "GroupViewSet", "RentalUnitViewSet", "ContractViewSet"):
            with self.subTest(viewset=name):
                match = re.search(
                    rf"^class {name}\(.*?\):(?P<body>.*?)(?=^class |\Z)",
                    code, re.M | re.S,
                )
                self.assertIsNotNone(match, name + " must exist")
                body = match.group("body")
                self.assertRegex(
                    body,
                    r"(?m)^\s+permission_classes\s*=\s*\[permissions\.IsAdminUser\]",
                )
                self.assertNotRegex(body, r"(?m)^\s+permission_classes\s*=\s*\[permissions\.AllowAny\]")


if __name__ == "__main__":
    unittest.main()
