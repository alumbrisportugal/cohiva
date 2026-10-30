import datetime
from unittest.mock import patch

from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from geno.living import MODELS, NewTenancyForm
from geno.models import Address, Building, Contract, RentalUnit


@override_settings(ALUMBRIS_CURRENCY="EUR")
class LivingWorkflowTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "manager", password="test-password", is_staff=True
        )
        self.permissions = Permission.objects.filter(
            content_type__app_label="geno",
            codename__in=[f"{action}_{model}" for action in ("view", "add") for model in MODELS],
        )
        self.user.user_permissions.set(self.permissions)
        self.client.force_login(self.user)
        self.new_url = reverse("geno:living-new")
        self.data = {
            "building_name": "Edifício de ensaio",
            "street_name": "Rua de Teste",
            "city_zipcode": "2500-001",
            "city_name": "Caldas da Rainha",
            "unit_name": "A",
            "floor": "4",
            "area": "58.00",
            "rent": "700.00",
            "first_name": "Residente",
            "last_name": "Fictício",
            "email": "residente@example.invalid",
            "date": "2026-11-01",
            "date_end": "2029-10-31",
            "signed": "on",
        }

    def test_complete_workflow_and_refresh_do_not_duplicate(self):
        response = self.client.post(self.new_url, self.data)
        contract = Contract.objects.get()
        self.assertRedirects(response, reverse("geno:living-contract", args=[contract.pk]))
        unit = contract.rental_units.get()
        self.assertEqual(unit.rent_netto, 700)
        self.assertEqual(unit.billing_period, 1)
        self.assertEqual(unit.building.country, "PT")
        self.assertEqual(contract.contractors.get(), contract.main_contact)
        self.assertEqual(contract.state, "unterzeichnet")
        self.assertEqual(contract.send_qrbill, "none")
        self.assertTrue(
            LogEntry.objects.filter(
                actor=self.user, object_pk=str(contract.pk), content_type__model="contract"
            ).exists()
        )
        self.assertContains(self.client.get(response.url), "700")
        self.assertContains(
            self.client.get(reverse("geno:living-portfolio")), "Edifício de ensaio"
        )
        self.client.post(self.new_url, self.data)
        self.assertEqual(Contract.objects.count(), 1)
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(RentalUnit.objects.count(), 1)

    def test_existing_building_and_contact_are_reused(self):
        building = Building.objects.create(name="Existente", country="PT")
        person = Address.objects.create(name="Existente", country="PT")
        self.data.update(
            building=building.pk,
            address=person.pk,
            building_name="",
            first_name="",
            last_name="",
            email="",
            signed="",
        )
        self.client.post(self.new_url, self.data)
        self.assertEqual(Building.objects.count(), 1)
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(Contract.objects.get().state, "angeboten")
        self.assertEqual(Contract.objects.get().date, datetime.date(2026, 11, 1))

    def test_invalid_dates_money_and_duplicate_contact_do_not_write(self):
        Address.objects.create(email=self.data["email"])
        self.data.update(date_end="2026-01-01", rent="-1", city_zipcode="invalid")
        response = self.client.post(self.new_url, self.data)
        self.assertContains(response, "Confirma os dados")
        self.assertFalse(Contract.objects.exists())
        self.assertFalse(Building.objects.exists())
        self.assertFalse(RentalUnit.objects.exists())

    def test_transaction_rolls_back_every_record(self):
        form = NewTenancyForm(self.data)
        self.assertTrue(form.is_valid(), form.errors)
        with patch("geno.living.Contract.objects.create", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                form.save()
        self.assertFalse(Building.objects.exists())
        self.assertFalse(Address.objects.exists())
        self.assertFalse(RentalUnit.objects.exists())

    def test_anonymous_resident_and_staff_without_permissions_are_denied(self):
        urls = [
            self.new_url,
            reverse("geno:living-portfolio"),
            reverse("geno:living-contract", args=[999]),
        ]
        for url in urls:
            self.client.logout()
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(self.user)
        self.user.user_permissions.clear()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.user.user_permissions.set(self.permissions)
        self.user.is_staff = False
        self.user.save()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.new_url, self.data).status_code, 403)
        self.assertFalse(Contract.objects.exists())

    def test_read_permission_does_not_grant_write(self):
        self.user.user_permissions.remove(*self.permissions.filter(codename__startswith="add_"))
        self.assertEqual(self.client.get(reverse("geno:living-portfolio")).status_code, 200)
        self.assertEqual(self.client.get(self.new_url).status_code, 403)
        self.assertEqual(self.client.post(self.new_url, self.data).status_code, 403)

    @override_settings(ALUMBRIS_CURRENCY="CHF")
    def test_currency_opt_in_required(self):
        self.assertEqual(self.client.post(self.new_url, self.data).status_code, 403)

    def test_csrf_and_escape(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.new_url, self.data).status_code, 403)
        self.data["building_name"] = '<script>alert("x")</script>'
        response = self.client.post(self.new_url, self.data, follow=True)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_unique_unit_in_existing_building(self):
        building = Building.objects.create(name="Existente")
        RentalUnit.objects.create(building=building, name="A", rental_type="Wohnung")
        self.data.update(building=building.pk, building_name="")
        form = NewTenancyForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn("unit_name", form.errors)

    def test_each_required_permission_is_enforced_on_post(self):
        for permission in self.permissions:
            self.user.user_permissions.remove(permission)
            self.assertEqual(self.client.post(self.new_url, self.data).status_code, 403)
            self.user.user_permissions.add(permission)
        self.assertFalse(Contract.objects.exists())

    def test_missing_detail_and_invalid_post_preserve_records(self):
        self.assertEqual(
            self.client.get(reverse("geno:living-contract", args=[999])).status_code, 404
        )
        self.assertEqual(self.client.get(self.new_url).status_code, 200)
        self.assertFalse(Building.objects.exists())
        self.assertEqual(self.client.put(self.new_url, self.data).status_code, 405)

    def test_database_conflict_is_safe_and_retryable(self):
        with patch("geno.living.NewTenancyForm.save", side_effect=IntegrityError):
            response = self.client.post(self.new_url, self.data)
        self.assertContains(response, "Confirma os dados")
        self.assertFalse(Contract.objects.exists())
