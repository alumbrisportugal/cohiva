"""Pure permission-matrix tests; real HTTP endpoint tests are still mandatory."""
import importlib.util
import sys
from datetime import date
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[2] / "django" / "geno"
for module in ("tenancy_period",):
    spec = importlib.util.spec_from_file_location("geno." + module, SRC / (module + ".py"))
    if "geno" not in sys.modules:
        import types
        pkg = types.ModuleType("geno")
        pkg.__path__ = [str(SRC)]
        sys.modules["geno"] = pkg
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)

spec = importlib.util.spec_from_file_location("geno.tenancy_access", SRC / "tenancy_access.py")
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.kw = dict(
            contractor_ids={1, 2},
            unit_ids={101},
            requested_unit_id=101,
            start=date(2026, 1, 1),
            end=date(2027, 1, 1),
            state="unterzeichnet",
            today=date(2026, 10, 30),
        )

    def allow(self, user, **override):
        data = dict(self.kw)
        data.update(override)
        return policy.can_access_contract(person_id=user, **data)

    def test_co_signatories_can_access(self):
        self.assertTrue(self.allow(1))
        self.assertTrue(self.allow(2))

    def test_another_apartment_or_tenant_denied(self):
        self.assertFalse(self.allow(3))
        self.assertFalse(self.allow(1, requested_unit_id=102))
        self.assertFalse(self.allow(3, requested_unit_id=102))

    def test_expired_future_cancelled_and_unsigned_denied(self):
        self.assertFalse(self.allow(1, end=date(2026, 10, 29)))
        self.assertFalse(self.allow(1, start=date(2026, 11, 1)))
        self.assertFalse(self.allow(1, state="ungueltig"))
        self.assertFalse(self.allow(1, state="angeboten"))

    def test_missing_identity_or_resources_denied(self):
        self.assertFalse(self.allow(None))
        self.assertFalse(self.allow(0))
        self.assertFalse(self.allow(True))
        self.assertFalse(self.allow(1, requested_unit_id=0))
        self.assertFalse(self.allow(1, unit_ids=set()))
        self.assertFalse(self.allow(1, contractor_ids=set()))

    def test_new_occupant_not_entitled_to_predecessor_contract(self):
        self.assertFalse(self.allow(4))
        self.assertTrue(self.allow(4, contractor_ids={4}, start=date(2026, 10, 1)))


if __name__ == "__main__":
    unittest.main()
