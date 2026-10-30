"""Static regression guard; HTTP tests are required before release."""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "django" / "geno" / "api_views.py"


def viewset_body(code, name):
    match = re.search(
        rf"^class {name}\(.*?\):(?P<body>.*?)(?=^class |\Z)",
        code, re.M | re.S,
    )
    if match is None:
        raise AssertionError(name + " must exist")
    return match.group("body")


class SensitiveAPIProtectionTests(unittest.TestCase):
    def test_administrative_viewsets_restrict_to_staff(self):
        code = SOURCE.read_text(encoding="utf-8")
        for name in ("UserViewSet", "GroupViewSet", "RentalUnitViewSet"):
            with self.subTest(viewset=name):
                body = viewset_body(code, name)
                self.assertRegex(
                    body, r"(?m)^\s+permission_classes\s*=\s*\[permissions\.IsAdminUser\]"
                )

    def test_contracts_restricted_to_authenticated_current_contractors(self):
        code = SOURCE.read_text(encoding="utf-8")
        body = viewset_body(code, "ContractViewSet")
        self.assertRegex(
            body, r"(?m)^\s+permission_classes\s*=\s*\[permissions\.IsAuthenticated\]"
        )
        for required in (
            "def get_queryset(self):",
            "if user.is_staff:",
            "contractors__user=user",
            'state="unterzeichnet"',
            "date__lte=today",
            "date_end__gte=today",
            "date_end__isnull=True",
            ".distinct()",
        ):
            with self.subTest(required=required):
                self.assertIn(required, body)


if __name__ == "__main__":
    unittest.main()
