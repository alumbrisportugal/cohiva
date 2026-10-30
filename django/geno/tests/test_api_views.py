import datetime
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.test import tag
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

import geno.tests.data as geno_testdata
from finance.accounting import Account, AccountingManager, AccountKey
from geno.api_views import Akonto, ContractViewSet, QRBill, RentalUnitViewSet, ResidentInvoiceViewSet
from geno.billing import get_income_account, get_receivables_account
from geno.models import Contract, Invoice, InvoiceCategory

from .base import GenoAdminTestCase


class AkontoViewTest(GenoAdminTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)

    def setUp(self):
        self.view = Akonto()
        self.view.billing_period_start = datetime.datetime(2020, 7, 1)
        self.view.billing_period_end = datetime.datetime(2021, 6, 30)
        self.view.invoice_category_nk_ausserordentlich = InvoiceCategory.objects.get(
            name="Nebenkosten Akonto ausserordentlich"
        )
        self.invoice_cat_rent = InvoiceCategory.objects.get(name="Mietzins wiederkehrend")

    def create_akonto_invoices(self, contract):
        fiaccount = Account.from_settings(AccountKey.NK).set_code(contract=contract)
        Invoice.objects.create(
            name="NK akonto test 1",
            amount=100,
            contract=contract,
            invoice_category=self.invoice_cat_rent,
            fin_account=fiaccount.code,
            date=datetime.date(2020, 8, 1),
        )
        Invoice.objects.create(
            name="NK akonto test 2",
            amount=200,
            contract=contract,
            invoice_category=self.invoice_cat_rent,
            fin_account=fiaccount.code,
            date=datetime.date(2020, 9, 1),
        )
        Invoice.objects.create(
            name="NK akonto ausserordentlich 1",
            amount=25,
            contract=contract,
            invoice_category=self.view.invoice_category_nk_ausserordentlich,
            invoice_type="Invoice",
            date=datetime.date(2020, 10, 15),
        )
        Invoice.objects.create(
            name="NK akonto ausserordentlich 2",
            amount=50,
            contract=contract,
            invoice_category=self.view.invoice_category_nk_ausserordentlich,
            invoice_type="Invoice",
            date=datetime.date(2020, 11, 15),
        )

    def create_billing_contract_and_invoices(self, contract):
        fiaccount = Account.from_settings(AccountKey.NK).set_code(contract=contract)
        billing_contract = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date(2020, 1, 1),
            billing_contract=contract,
        )
        billing_contract.rental_units.set([self.rentalunits[3]])
        billing_contract.contractors.set(self.addresses[0:2])
        billing_contract.save()
        Invoice.objects.create(
            name="NK akonto billing contract",
            amount=1000,
            contract=billing_contract,
            invoice_category=self.invoice_cat_rent,
            fin_account=fiaccount.code,
            date=datetime.date(2021, 1, 1),
        )
        Invoice.objects.create(
            name="NK akonto ausserordentlich billing contract",
            amount=1,
            contract=billing_contract,
            invoice_category=self.view.invoice_category_nk_ausserordentlich,
            invoice_type="Invoice",
            date=datetime.date(2021, 6, 1),
        )

    def test_get_akonto_for_contract(self):
        contract = self.contracts[0]
        self.view.contract_id = contract.id
        self.assertEqual(self.view.get_akonto_for_contract(), 0)

        self.create_akonto_invoices(contract)
        self.assertEqual(self.view.get_akonto_for_contract(), 100 + 200 + 25 + 50)

        self.view.contract_id = -1
        self.assertEqual(self.view.get_akonto_for_contract(), 0)

    def test_get_akonto_for_contract_date_ranges(self):
        contract = self.contracts[0]
        self.view.contract_id = contract.id
        self.create_akonto_invoices(contract)

        self.view.billing_period_start = datetime.datetime(2020, 7, 1)
        self.view.billing_period_end = datetime.datetime(2020, 9, 30)
        self.assertEqual(self.view.get_akonto_for_contract(), 100 + 200)

        self.view.billing_period_start = datetime.datetime(2020, 9, 1)
        self.view.billing_period_end = datetime.datetime(2021, 6, 30)
        self.assertEqual(self.view.get_akonto_for_contract(), 200 + 25 + 50)

    def test_get_akonto_for_contract_with_billing_contract(self):
        contract = self.contracts[0]
        self.view.contract_id = contract.id
        self.create_billing_contract_and_invoices(contract)
        self.assertEqual(self.view.get_akonto_for_contract(), 1000 + 1)

        self.create_akonto_invoices(contract)
        self.assertEqual(self.view.get_akonto_for_contract(), 100 + 200 + 25 + 50 + 1000 + 1)

    def test_get_akonto_for_all_contracts(self):
        self.assertEqual(self.view.get_akonto_for_all_contracts(), {})

        contract = self.contracts[0]
        self.create_akonto_invoices(contract)
        self.assertEqual(
            self.view.get_akonto_for_all_contracts(), {contract.id: 100 + 200 + 25 + 50}
        )
        self.create_billing_contract_and_invoices(contract)
        self.assertEqual(
            self.view.get_akonto_for_all_contracts(), {contract.id: 100 + 200 + 25 + 50 + 1000 + 1}
        )

        contract2 = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date(2020, 1, 1),
        )
        contract2.rental_units.set([self.rentalunits[4]])
        contract2.contractors.set([self.addresses[4]])
        contract2.save()
        self.create_akonto_invoices(contract2)
        fiaccount = Account.from_settings(AccountKey.NK).set_code(contract=contract2)
        Invoice.objects.create(
            name="NK akonto with postfix",
            amount=2000,
            contract=contract2,
            invoice_category=self.invoice_cat_rent,
            fin_account=fiaccount.code + "0099",
            date=datetime.date(2021, 2, 1),
        )
        self.assertEqual(
            self.view.get_akonto_for_all_contracts(),
            {
                contract.id: 100 + 200 + 25 + 50 + 1000 + 1,
                contract2.id: 100 + 200 + 25 + 50 + 2000,
            },
        )


class QRBillAPIViewTest(GenoAdminTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = QRBill()
        self.view.contract = self.contracts[0]
        self.view.address = self.view.contract.get_contact_address()
        self.view.context = self.view.address.get_context()
        self.view.dry_run = False
        self.view.invoice_category = InvoiceCategory.objects.get(
            reference_id=12
        )  # Nebenkostenabrechnung
        self.view.invoice_date = datetime.date(2021, 10, 10)
        self.fiaccount_nk_receivables = Account.from_settings(AccountKey.NK_RECEIVABLES).set_code(
            contract=self.view.contract
        )
        self.fiaccount_nk = Account.from_settings(AccountKey.NK).set_code(
            contract=self.view.contract
        )

    def test_get_virtual_contract_account(self):
        with self.assertRaises(KeyError):
            self.view.get_virtual_contract_account(1)
        self.assertEqual(
            self.view.get_virtual_contract_account(-1),
            Account.from_settings(AccountKey.NK_VIRTUAL_1).set_code(self.view.contract),
        )
        self.assertEqual(
            self.view.get_virtual_contract_account(-3),
            Account.from_settings(AccountKey.NK_VIRTUAL_3).set_code(self.view.contract),
        )

    def build_request(self, modified_data=None):
        data = {
            "contract_id": self.view.contract.id if self.view.contract else 0,
            "billing_period_end": "2021-06-30",
            "total_akonto": 0,
            "total_amount": 100,
            "comment": "QRBill test",
            "bill_lines": [],
        }
        if modified_data is not None:
            data.update(modified_data)
        request = self.factory.post("/geno/qrbill/", data, content_type="application/json")
        return self.view.initialize_request(request)

    def test_do_accounting_without_akonto(self):
        request = self.build_request()
        with AccountingManager(book_type_id="dum") as book:
            book._db = {}
            self.view.do_accounting(request, book)
            self.assertEqual(len(book._db), 1)

            created_invoice = Invoice.objects.get(id=self.view.invoice_id)
            self.assertEqual(created_invoice.amount, 100)
            self.assertTrue(created_invoice.fin_transaction_ref.startswith("dum_"))
            self.assertEqual(
                created_invoice.fin_account,
                get_income_account(self.view.invoice_category, None, self.view.contract).code,
            )
            self.assertEqual(
                created_invoice.fin_account_receivables,
                get_receivables_account(self.view.invoice_category, self.view.contract).code,
            )
            self.assertEqual(created_invoice.invoice_type, "Invoice")
            self.assertEqual(created_invoice.invoice_category, self.view.invoice_category)
            self.assertEqual(created_invoice.name, "Nebenkostenabrechnung")
            self.assertEqual(created_invoice.contract, self.view.contract)
            self.assertEqual(created_invoice.date, datetime.date(2021, 10, 10))

    def test_do_accounting_with_akonto(self):
        request = self.build_request({"total_akonto": 50})
        with AccountingManager(book_type_id="dum") as book:
            book._db = {}
            self.view.do_accounting(request, book)
            self.assertEqual(len(book._db), 2)

            created_invoice = Invoice.objects.get(id=self.view.invoice_id)
            self.assertEqual(created_invoice.amount, 100)

            tr = book.get_transaction(book.build_transaction_id(list(book._db.keys())[0]))
            for split in tr.splits:
                if split.amount == -50:
                    self.assertEqual(split.account, self.fiaccount_nk_receivables)
                elif split.amount == 50:
                    self.assertEqual(split.account, self.fiaccount_nk)
                else:
                    raise ValueError("Amount should be 50")
            self.assertEqual(tr.date, datetime.date(2021, 6, 30))
            self.assertEqual(
                tr.description, f"NK-Abrechnung Verrechnung Akontozahlungen {self.view.contract}"
            )

    def test_do_accounting_virtual_contract(self):
        self.view.contract = None
        request = self.build_request({"contract_id": -1})
        with AccountingManager(book_type_id="dum") as book:
            book._db = {}
            self.view.do_accounting(request, book)
            self.assertEqual(len(book._db), 1)
            self.assertEqual(self.view.invoice_id, None)
            tr = book.get_transaction(book.build_transaction_id(list(book._db.keys())[0]))
            for split in tr.splits:
                if split.amount == -100:
                    self.assertEqual(split.account, self.fiaccount_nk_receivables)
                elif split.amount == 100:
                    self.assertEqual(split.account, self.view.get_virtual_contract_account(-1))
                else:
                    raise ValueError("Amount should be 100")
            self.assertEqual(tr.date, datetime.date(2021, 6, 30))

    @patch("geno.api_views.QRBill.do_accounting")
    def test_post_dry_run(self, mock_do_accounting):
        test_view = QRBill()
        ret = test_view.post(self.build_request())
        self.assertEqual(test_view.dry_run, True)
        mock_do_accounting.assert_called_once()
        self.assertTrue(isinstance(ret, FileResponse))
        ret.file_to_stream.close()

        ret = test_view.post(self.build_request({"dry_run": False}))
        self.assertEqual(test_view.dry_run, False)
        self.assertEqual(mock_do_accounting.call_count, 2)
        self.assertTrue(isinstance(ret, FileResponse))
        ret.file_to_stream.close()

    def test_get_qrbill_virtual_contract_file_name(self):
        self.view.contract = None
        ret = self.view.get_qrbill(self.build_request({"contract_id": -1}))
        self.assertEqual(ret.filename, "NK_Gästezimmer_20211010.pdf")
        self.assertEqual(self.view.context["contract_info"], "Gästezimmer")
        self.assertTrue(isinstance(ret, FileResponse))
        ret.file_to_stream.close()

    @tag("slow-test")
    def test_get_akonto_qrbill(self):
        request = self.factory.post("/geno/qrbill/", {"contract_id": 0})
        pdf_file = self.view.get_akonto_qrbill(request)
        self.assertInPDF(
            pdf_file.file_to_stream,
            [
                "Zahlbar durch\nAnna Muster\nBeispielweg 1\nCH-3000 Bern\n",
                (
                    "Konto / Zahlbar an\n"
                    "CH77 3000 0001 2500 9423 9\n"
                    "Genossenschaft Musterweg\n"
                    "Musterweg 1\n"
                    "CH-3000 Bern\n"
                ),
            ],
        )
        pdf_file.file_to_stream.close()


class ContractViewSetTest(GenoAdminTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        user_model = get_user_model()
        cls.user = user_model.objects.get(username="superuser")

    def test_subcontracts_are_excluded_in_api_view(self):
        Contract.objects.create(
            state="unterzeichnet", date=datetime.date(2020, 1, 1), main_contract=self.contracts[0]
        )
        factory = APIRequestFactory()
        view = ContractViewSet.as_view({"get": "list"})
        request = factory.get(reverse("contract-list"))
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.render().content)
        self.assertEqual(data["count"], 1)


class AlumbrisResidentContractAPITest(GenoAdminTestCase):
    """Database-backed permission tests for list and retrieve endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.resident = get_user_model().objects.create_user(
            username="alumbris_resident", password="not-a-real-secret"
        )
        cls.stranger = get_user_model().objects.create_user(
            username="alumbris_stranger", password="not-a-real-secret"
        )
        cls.addresses[0].user = cls.resident
        cls.addresses[0].save(update_fields=["user"])
        cls.future_contract = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date.today() + datetime.timedelta(days=10),
        )
        cls.future_contract.contractors.add(cls.addresses[0])
        cls.future_contract.rental_units.add(cls.rentalunits[2])
        cls.elsewhere_contract = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date.today() - datetime.timedelta(days=10),
        )
        cls.elsewhere_contract.contractors.add(cls.addresses[2])
        cls.elsewhere_contract.rental_units.add(cls.rentalunits[3])

    def call(self, user, detail_id=None):
        factory = APIRequestFactory()
        action = {"get": "retrieve"} if detail_id is not None else {"get": "list"}
        view = ContractViewSet.as_view(action)
        request = factory.get("/api/v1/geno/contract/")
        if user is not None:
            force_authenticate(request, user=user)
        if detail_id is None:
            return view(request)
        return view(request, pk=detail_id)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    def test_resident_contract_response_hides_private_fields(self):
        response = self.call(self.resident)
        self.assertEqual(response.status_code, 200)
        entry = next(row for row in response.data["results"] if row["id"] == self.contracts[0].id)
        self.assertEqual(set(entry), {"id", "rental_units", "state", "date", "date_end"})
        self.assertNotIn("contractors", entry)
        self.assertNotIn("comment", entry)

    def test_resident_sees_only_current_own_contract(self):
        response = self.call(self.resident)
        self.assertEqual(response.status_code, 200)
        ids = {entry["id"] for entry in response.data["results"]}
        self.assertIn(self.contracts[0].id, ids)
        self.assertNotIn(self.future_contract.id, ids)
        self.assertNotIn(self.elsewhere_contract.id, ids)

    def test_resident_cannot_retrieve_other_or_future_contract(self):
        self.assertEqual(self.call(self.resident, self.elsewhere_contract.id).status_code, 404)
        self.assertEqual(self.call(self.resident, self.future_contract.id).status_code, 404)

    def test_expired_and_cancelled_contracts_not_exposed(self):
        old = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date(2024, 1, 1),
            date_end=datetime.date.today() - datetime.timedelta(days=1),
        )
        old.contractors.add(self.addresses[0])
        old.rental_units.add(self.rentalunits[4])
        cancelled = Contract.objects.create(
            state="gekuendigt",
            date=datetime.date.today() - datetime.timedelta(days=5),
            date_end=datetime.date.today() + datetime.timedelta(days=5),
        )
        cancelled.contractors.add(self.addresses[0])
        cancelled.rental_units.add(self.rentalunits[5])
        result = self.call(self.resident)
        ids = {entry["id"] for entry in result.data["results"]}
        self.assertNotIn(old.id, ids)
        self.assertNotIn(cancelled.id, ids)
        self.assertEqual(self.call(self.resident, old.id).status_code, 404)
        self.assertEqual(self.call(self.resident, cancelled.id).status_code, 404)

    def test_staff_can_list_contracts(self):
        admin = get_user_model().objects.get(username="superuser")
        response = self.call(admin)
        self.assertEqual(response.status_code, 200)
        ids = {entry["id"] for entry in response.data["results"]}
        self.assertIn(self.contracts[0].id, ids)
        self.assertIn(self.future_contract.id, ids)
        self.assertIn(self.elsewhere_contract.id, ids)

    def test_contract_without_primary_address_user_not_exposed(self):
        result = self.call(self.stranger)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["count"], 0)

    def test_stranger_has_no_contracts(self):
        response = self.call(self.stranger)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(self.call(self.stranger, self.contracts[0].id).status_code, 404)


class AlumbrisResidentRentalUnitAPITest(GenoAdminTestCase):
    """Real DRF list/detail checks against contract-linked rental units."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.resident = get_user_model().objects.create_user(username="alumbris_unit_resident")
        cls.other = get_user_model().objects.create_user(username="alumbris_unit_other")
        cls.addresses[0].user = cls.resident
        cls.addresses[0].save(update_fields=["user"])

    def call(self, user, pk=None):
        factory = APIRequestFactory()
        view = RentalUnitViewSet.as_view({"get": "retrieve" if pk is not None else "list"})
        request = factory.get("/api/v1/geno/rentalunit/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_unauthenticated_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    def test_resident_unit_response_hides_internal_fields(self):
        response = self.call(self.resident)
        self.assertEqual(response.status_code, 200)
        entry = response.data["results"][0]
        self.assertEqual(
            set(entry),
            {"id", "name", "label", "label_short", "rental_type",
             "building", "floor", "area", "rooms"},
        )
        self.assertNotIn("adit_serial", entry)
        self.assertNotIn("comment", entry)
        self.assertNotIn("depot", entry)

    def test_resident_only_sees_own_units(self):
        result = self.call(self.resident)
        self.assertEqual(result.status_code, 200)
        ids = {entry["id"] for entry in result.data["results"]}
        self.assertEqual(ids, {unit.id for unit in self.rentalunits[:2]})
        self.assertEqual(self.call(self.resident, self.rentalunits[2].id).status_code, 404)

    def test_unrelated_user_denied(self):
        result = self.call(self.other)
        self.assertEqual(result.data["count"], 0)
        self.assertEqual(self.call(self.other, self.rentalunits[0].id).status_code, 404)

    def test_future_contract_does_not_grant_unit_access(self):
        contract = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date.today() + datetime.timedelta(days=30),
        )
        contract.contractors.add(self.addresses[0])
        contract.rental_units.add(self.rentalunits[2])
        self.assertEqual(self.call(self.resident, self.rentalunits[2].id).status_code, 404)


class AlumbrisResidentInvoiceAPITest(GenoAdminTestCase):
    """HTTP-level isolation and projection of invoice summaries."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.resident = get_user_model().objects.create_user(username="alumbris_invoice_resident")
        cls.stranger = get_user_model().objects.create_user(username="alumbris_invoice_stranger")
        cls.addresses[0].user = cls.resident
        cls.addresses[0].save(update_fields=["user"])
        category = InvoiceCategory.objects.get(name="Mietzins wiederkehrend")
        cls.own = Invoice.objects.create(
            name="Rent", date=datetime.date.today(), amount=700,
            contract=cls.contracts[0], invoice_category=category,
        )
        other_contract = Contract.objects.create(
            date=datetime.date.today(), state="unterzeichnet",
        )
        other_contract.contractors.add(cls.addresses[2])
        other_contract.rental_units.add(cls.rentalunits[2])
        cls.foreign = Invoice.objects.create(
            name="Another resident's rent", date=datetime.date.today(),
            amount=900, contract=other_contract, invoice_category=category,
        )

    def call(self, user, pk=None):
        view = ResidentInvoiceViewSet.as_view(
            {"get": "retrieve" if pk is not None else "list"}
        )
        request = APIRequestFactory().get("/api/v1/geno/resident-invoice/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    def test_other_invoice_not_visible(self):
        result = self.call(self.resident)
        self.assertEqual(result.status_code, 200)
        ids = {row["id"] for row in result.data["results"]}
        self.assertIn(self.own.id, ids)
        self.assertNotIn(self.foreign.id, ids)
        self.assertEqual(self.call(self.resident, self.foreign.id).status_code, 404)
        self.assertEqual(self.call(self.stranger, self.own.id).status_code, 404)

    def test_expired_future_and_cancelled_invoice_access_denied(self):
        for state, start, end in (
            ("unterzeichnet", datetime.date(2020, 1, 1),
             datetime.date.today() - datetime.timedelta(days=1)),
            ("unterzeichnet", datetime.date.today() + datetime.timedelta(days=1), None),
            ("gekuendigt", datetime.date(2020, 1, 1), None),
            ("ungueltig", datetime.date(2020, 1, 1), None),
        ):
            with self.subTest(state=state, start=start, end=end):
                contract = Contract.objects.create(
                    state=state, date=start, date_end=end,
                )
                contract.contractors.add(self.addresses[0])
                contract.rental_units.add(self.rentalunits[3])
                invoice = Invoice.objects.create(
                    name="Restricted period invoice",
                    date=datetime.date.today(), amount=500,
                    contract=contract,
                    invoice_category=self.own.invoice_category,
                )
                self.assertEqual(self.call(self.resident, invoice.id).status_code, 404)
                self.assertNotIn(
                    invoice.id,
                    {row["id"] for row in self.call(self.resident).data["results"]},
                )

    def test_invoice_projection_excludes_accounting_fields(self):
        response = self.call(self.resident, self.own.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {"id", "contract", "name", "date", "amount", "year", "month"},
        )
        self.assertNotIn("fin_transaction_ref", response.data)
