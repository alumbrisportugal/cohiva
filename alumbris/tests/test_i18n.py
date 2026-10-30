"""Regression tests for the lightweight translation structure checker.

Run from repository root:
    python3 -m unittest discover -s alumbris/tests -p 'test_*.py'
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_pwa_i18n.py"
spec = importlib.util.spec_from_file_location("alumbris_i18n", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class TranslationCatalogTests(unittest.TestCase):
    def test_real_catalogs_match(self):
        en_keys, en_vars = checker.read_catalog(checker.BASE)
        pt_keys, pt_vars = checker.read_catalog(checker.TARGET)
        self.assertGreater(len(en_keys), 90)
        self.assertEqual(en_keys, pt_keys)
        self.assertEqual(en_vars, pt_vars)

    def test_swiss_qr_price_not_mislabelled_as_euro(self):
        """Until payment logic is adapted, the Swiss fallback must not claim EUR."""
        content = checker.TARGET.read_text(encoding="utf-8")
        self.assertIn("defaultCost: ' CHF 0.00'", content)
        self.assertNotIn("defaultCost: ' 0,00 €'", content)

    def test_detects_missing_keys_and_changed_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.ts"
            second = Path(tmp) / "second.ts"
            first.write_text("""export default {
  login: {
    title: 'Sign in with {site}',
    button: 'Sign in',
  },
}
""", encoding="utf-8")
            second.write_text("""export default {
  login: {
    title: 'Entrar com {app}',
  },
}
""", encoding="utf-8")
            original, vars_original = checker.read_catalog(first)
            translated, vars_translated = checker.read_catalog(second)
            self.assertIn("login.button", original - translated)
            self.assertNotEqual(vars_original["login.title"], vars_translated["login.title"])


if __name__ == "__main__":
    unittest.main()
