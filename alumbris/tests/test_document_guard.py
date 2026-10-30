"""Static regression check for legacy document regeneration route.

This is NOT a substitute for authenticated HTTP tests with fixtures.
"""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "django" / "geno" / "views.py"


class LegacyDocumentRouteTests(unittest.TestCase):
    def test_document_regeneration_requires_staff_and_permission(self):
        code = SOURCE.read_text(encoding="utf-8")
        start = code.index("def documents(request, doctype, obj_id, action):")
        end = code.index("\nclass ", start)
        block = code[start:end]
        self.assertIn('request.user.is_staff', block)
        self.assertIn('request.user.has_perm("geno.add_document")', block)
        self.assertIn('request.user.has_perm("geno.regenerate_document")', block)
        self.assertIn('pk=obj_id, doctype=doctype_obj', block)


if __name__ == "__main__":
    unittest.main()
