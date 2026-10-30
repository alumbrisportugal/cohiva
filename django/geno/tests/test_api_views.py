import datetime
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.test import override_settings, tag
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

import geno.tests.data as geno_testdata
from finance.accounting import Account, AccountingManager, AccountKey
from geno.api_views import Akonto, ContractViewSet, QRBill, RentalUnitViewSet, ResidentInvoiceHistoryViewSet, ResidentInvoiceViewSet, ResidentContractDocumentViewSet, ResidentContractDocumentHistoryViewSet, ResidentContractHistoryViewSet, ResidentOverviewView, ResidentPortfolioView, ResidentPortfolioSectionView, ResidentTimelineView, ResidentCapabilitiesView, ResidentMaintenanceRequestViewSet, ResidentMaintenanceCommentViewSet
from geno.billing import get_income_account, get_receivables_account
from geno.models import Contract, Document, DocumentType, Invoice, InvoiceCategory, ResidentMaintenanceRequest, ResidentMaintenanceComment

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


class AlumbrisFormerTenantInvoiceHistoryAPITest(GenoAdminTestCase):
    """Old occupants keep only period-bound invoice summaries of their contract."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.former = get_user_model().objects.create_user(username="alumbris_former")
        cls.successor = get_user_model().objects.create_user(username="alumbris_successor")
        cls.addresses[0].user = cls.former
        cls.addresses[0].save(update_fields=["user"])
        cls.addresses[2].user = cls.successor
        cls.addresses[2].save(update_fields=["user"])
        cls.old_contract = Contract.objects.create(
            state="gekuendigt",
            date=datetime.date(2024, 1, 1),
            date_end=datetime.date(2025, 12, 31),
        )
        cls.old_contract.contractors.add(cls.addresses[0])
        cls.old_contract.rental_units.add(cls.rentalunits[2])
        cls.new_contract = Contract.objects.create(
            state="unterzeichnet",
            date=datetime.date(2026, 1, 1),
        )
        cls.new_contract.contractors.add(cls.addresses[2])
        cls.new_contract.rental_units.add(cls.rentalunits[2])
        category = InvoiceCategory.objects.get(name="Mietzins wiederkehrend")
        cls.old_invoice = Invoice.objects.create(
            name="Historical rent",
            date=datetime.date(2025, 11, 1), amount=650,
            contract=cls.old_contract, invoice_category=category,
        )
        cls.successor_invoice = Invoice.objects.create(
            name="New resident rent",
            date=datetime.date(2026, 8, 1), amount=700,
            contract=cls.new_contract, invoice_category=category,
        )
        cls.out_of_period = Invoice.objects.create(
            name="Outside contractual period",
            date=datetime.date(2026, 1, 1), amount=650,
            contract=cls.old_contract, invoice_category=category,
        )

    def call(self, user, pk=None):
        view = ResidentInvoiceHistoryViewSet.as_view(
            {"get": "retrieve" if pk is not None else "list"}
        )
        request = APIRequestFactory().get("/api/v1/geno/resident-invoice-history/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    def test_former_tenant_sees_only_owned_historical_period(self):
        result = self.call(self.former)
        self.assertEqual(result.status_code, 200)
        ids = {entry["id"] for entry in result.data["results"]}
        self.assertIn(self.old_invoice.id, ids)
        self.assertNotIn(self.successor_invoice.id, ids)
        self.assertNotIn(self.out_of_period.id, ids)
        self.assertEqual(self.call(self.former, self.successor_invoice.id).status_code, 404)
        self.assertEqual(self.call(self.former, self.out_of_period.id).status_code, 404)

    def test_successor_cannot_read_predecessor_history(self):
        self.assertEqual(self.call(self.successor, self.old_invoice.id).status_code, 404)


@override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_test_contract_doc",))
class AlumbrisContractDocumentMetadataTest(GenoAdminTestCase):
    """A tenant only sees contract-linked document titles, never data blobs."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.resident = get_user_model().objects.create_user(username="alumbris_docs_resident")
        cls.other = get_user_model().objects.create_user(username="alumbris_docs_other")
        cls.addresses[0].user = cls.resident
        cls.addresses[0].save(update_fields=["user"])
        cls.type = DocumentType.objects.create(name="alumbris_test_contract_doc")
        Contract.objects.filter(pk=cls.contracts[0].pk).update(active=True)
        cls.own = Document.objects.create(
            resident_visible=True,
            name="Own contract", doctype=cls.type, data='{"private":"never expose"}',
            content_object=cls.contracts[0],
        )
        cls.unrelated = Contract.objects.create(
            date=datetime.date.today(), state="unterzeichnet",
        )
        cls.unrelated.contractors.add(cls.addresses[2])
        cls.unrelated.rental_units.add(cls.rentalunits[3])
        cls.foreign = Document.objects.create(
            name="Another resident", doctype=cls.type, data='{"private":"secret"}',
            content_object=cls.unrelated,
        )

    def call(self, user, pk=None):
        view = ResidentContractDocumentViewSet.as_view(
            {"get": "retrieve" if pk is not None else "list"}
        )
        request = APIRequestFactory().get("/api/v1/geno/resident-contract-document/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=())
    def test_default_deny_exposes_no_document_metadata(self):
        self.assertEqual(self.call(self.resident).data["count"], 0)
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 404)

    def test_private_document_hidden_even_with_allowed_type(self):
        private = Document.objects.create(
            name="Internal note", doctype=self.type, resident_visible=False,
            data='{"secret":true}', content_object=self.contracts[0],
        )
        self.assertEqual(self.call(self.resident, private.id).status_code, 404)
        self.assertNotIn(
            private.id,
            {entry["id"] for entry in self.call(self.resident).data["results"]},
        )

    def test_inactive_contract_hides_current_document(self):
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 200)
        Contract.objects.filter(pk=self.contracts[0].pk).update(active=False)
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 404)

    def test_contract_termination_removes_current_document(self):
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 200)
        contract = self.contracts[0]
        contract.date_end = datetime.date(2025, 12, 31)
        contract.save(update_fields=["date_end"])
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 404)

    def test_invalid_contract_state_blocks_current_document(self):
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 200)
        contract = self.contracts[0]
        contract.state = "ungueltig"
        contract.save(update_fields=["state"])
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 404)

    def test_revocation_immediately_removes_current_document(self):
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 200)
        self.own.resident_visible = False
        self.own.save(update_fields=["resident_visible"])
        self.assertEqual(self.call(self.resident, self.own.id).status_code, 404)

    def test_own_metadata_only(self):
        result = self.call(self.resident)
        self.assertEqual(result.status_code, 200)
        ids = {row["id"] for row in result.data["results"]}
        self.assertIn(self.own.id, ids)
        self.assertNotIn(self.foreign.id, ids)
        self.assertEqual(self.call(self.resident, self.foreign.id).status_code, 404)
        self.assertEqual(self.call(self.other, self.own.id).status_code, 404)
        detail = self.call(self.resident, self.own.id)
        self.assertEqual(set(detail.data), {"id", "name", "doctype", "ts_created"})
        self.assertNotIn("data", detail.data)


@override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_old_contract_doc",))
class AlumbrisFormerTenantDocumentMetadataTest(GenoAdminTestCase):
    """Metadata for previous tenancy does not cross into the successor's contract."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.former = get_user_model().objects.create_user(username="alumbris_former_docs")
        cls.successor = get_user_model().objects.create_user(username="alumbris_successor_docs")
        cls.addresses[0].user = cls.former
        cls.addresses[0].save(update_fields=["user"])
        cls.addresses[2].user = cls.successor
        cls.addresses[2].save(update_fields=["user"])
        old = Contract.objects.create(
            state="gekuendigt",
            date=datetime.date(2024, 1, 1),
            date_end=datetime.date(2025, 12, 31),
        )
        old.contractors.add(cls.addresses[0])
        old.rental_units.add(cls.rentalunits[2])
        current = Contract.objects.create(
            state="unterzeichnet", date=datetime.date(2026, 1, 1),
        )
        current.contractors.add(cls.addresses[2])
        current.rental_units.add(cls.rentalunits[2])
        category = DocumentType.objects.create(name="alumbris_old_contract_doc")
        cls.old_doc = Document.objects.create(
            resident_visible=True,
            name="Previous lease", doctype=category, data='{"private":"former"}',
            content_object=old,
        )
        cls.new_doc = Document.objects.create(
            name="Successor lease", doctype=category, data='{"private":"successor"}',
            content_object=current,
        )

    def call(self, user, pk=None):
        view = ResidentContractDocumentHistoryViewSet.as_view(
            {"get": "retrieve" if pk is not None else "list"}
        )
        request = APIRequestFactory().get("/api/v1/geno/resident-contract-document-history/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=())
    def test_default_deny_historical_metadata(self):
        self.assertEqual(self.call(self.former).data["count"], 0)
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 404)

    def test_ended_contract_remains_visible_to_its_former_tenant(self):
        contract = self.old_doc.content_object
        self.assertLess(contract.date_end, datetime.date.today())
        self.assertFalse(Contract.objects.get(pk=contract.pk).active)
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 200)

    def test_revocation_immediately_removes_historical_document(self):
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 200)
        self.old_doc.resident_visible = False
        self.old_doc.save(update_fields=["resident_visible"])
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 404)

    def test_invalidated_historical_contract_is_not_accessible(self):
        contract = self.old_doc.content_object
        contract.state = "ungueltig"
        contract.save(update_fields=["state"])
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 404)

    def test_document_type_revocation_immediately_blocks_historical_access(self):
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 200)
        with override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=()):
            self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 404)

    def test_reassignment_of_original_contract_party_blocks_history(self):
        contract = self.old_doc.content_object
        contract.contractors.remove(self.addresses[0])
        self.assertEqual(self.call(self.former, self.old_doc.id).status_code, 404)

    def test_former_can_list_own_metadata_not_successor(self):
        response = self.call(self.former)
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data["results"]}
        self.assertIn(self.old_doc.id, ids)
        self.assertNotIn(self.new_doc.id, ids)
        self.assertEqual(self.call(self.former, self.new_doc.id).status_code, 404)
        self.assertEqual(self.call(self.successor, self.old_doc.id).status_code, 404)
        self.assertEqual(
            set(self.call(self.former, self.old_doc.id).data),
            {"id", "name", "doctype", "ts_created"},
        )


class AlumbrisResidentPortalOverviewTest(GenoAdminTestCase):
    """One dashboard summary, no cross-tenant contract or invoice details."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.former = get_user_model().objects.create_user(username="alumbris_overview_former")
        cls.successor = get_user_model().objects.create_user(username="alumbris_overview_successor")
        cls.stranger = get_user_model().objects.create_user(username="alumbris_overview_stranger")
        cls.addresses[0].user = cls.former
        cls.addresses[0].save(update_fields=["user"])
        cls.addresses[2].user = cls.successor
        cls.addresses[2].save(update_fields=["user"])
        cls.old_contract = Contract.objects.create(
            state="gekuendigt", date=datetime.date(2024, 1, 1),
            date_end=datetime.date(2025, 12, 31),
        )
        cls.old_contract.contractors.add(cls.addresses[0])
        cls.old_contract.rental_units.add(cls.rentalunits[2])
        cls.new_contract = Contract.objects.create(
            state="unterzeichnet", date=datetime.date(2026, 1, 1),
        )
        cls.new_contract.contractors.add(cls.addresses[2])
        cls.new_contract.rental_units.add(cls.rentalunits[2])
        category = InvoiceCategory.objects.get(name="Mietzins wiederkehrend")
        cls.old_invoice = Invoice.objects.create(
            name="Former resident rent", date=datetime.date(2025, 11, 1),
            amount=650, contract=cls.old_contract, invoice_category=category,
        )
        cls.new_invoice = Invoice.objects.create(
            name="Successor resident rent", date=datetime.date(2026, 8, 1),
            amount=700, contract=cls.new_contract, invoice_category=category,
        )

    def history(self, user, pk=None):
        view = ResidentContractHistoryViewSet.as_view(
            {"get": "retrieve" if pk is not None else "list"}
        )
        request = APIRequestFactory().get("/api/v1/geno/resident-contract-history/")
        if user is not None:
            force_authenticate(request, user=user)
        return view(request, pk=pk) if pk is not None else view(request)

    def overview(self, user):
        request = APIRequestFactory().get("/api/v1/geno/resident-overview/")
        if user is not None:
            force_authenticate(request, user=user)
        return ResidentOverviewView.as_view()(request)

    def test_anonymous_denied_on_both_routes(self):
        self.assertIn(self.history(None).status_code, (401, 403))
        self.assertIn(self.overview(None).status_code, (401, 403))

    def test_historical_contract_owned_only_by_original_party(self):
        response = self.history(self.former)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.old_contract.pk, {row["id"] for row in response.data["results"]})
        self.assertEqual(self.history(self.former, self.old_contract.pk).status_code, 200)
        self.assertEqual(self.history(self.successor, self.old_contract.pk).status_code, 404)
        self.assertEqual(self.history(self.stranger, self.old_contract.pk).status_code, 404)
        self.assertEqual(self.history(self.former, self.new_contract.pk).status_code, 404)
        self.assertEqual(
            set(self.history(self.former, self.old_contract.pk).data),
            {"id", "rental_units", "state", "date", "date_end"},
        )

    def test_void_contract_excluded_from_historical_endpoint(self):
        self.old_contract.state = "ungueltig"
        self.old_contract.save(update_fields=["state"])
        self.assertEqual(self.history(self.former, self.old_contract.pk).status_code, 404)

    def test_dashboard_updates_immediately_after_document_publication_and_revocation(self):
        doctype = DocumentType.objects.create(name="alumbris_overview_safe_doc")
        doc = Document.objects.create(
            name="Tenant contract summary",
            doctype=doctype,
            resident_visible=False,
            content_object=self.old_contract,
            data='{"sensitive":"not returned"}',
        )
        with override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=(doctype.name,)):
            self.assertEqual(self.overview(self.former).data["historical_documents"], 0)
            doc.resident_visible = True
            doc.save(update_fields=["resident_visible"])
            self.assertEqual(self.overview(self.former).data["historical_documents"], 1)
            self.assertEqual(self.overview(self.successor).data["historical_documents"], 0)
            doc.resident_visible = False
            doc.save(update_fields=["resident_visible"])
            self.assertEqual(self.overview(self.former).data["historical_documents"], 0)

    def test_dashboard_recomputes_counts_when_contract_is_void(self):
        self.assertEqual(self.overview(self.former).data["historical_contracts"], 1)
        self.old_contract.state = "ungueltig"
        self.old_contract.save(update_fields=["state"])
        result = self.overview(self.former)
        self.assertEqual(result.data["historical_contracts"], 0)
        self.assertEqual(result.data["historical_invoices"], 0)

    def test_dashboard_only_returns_counts_and_preserves_tenant_isolation(self):
        former = self.overview(self.former)
        successor = self.overview(self.successor)
        stranger = self.overview(self.stranger)
        self.assertEqual(former.status_code, 200)
        self.assertEqual(successor.status_code, 200)
        self.assertEqual(stranger.status_code, 200)
        self.assertEqual(former.data["historical_contracts"], 1)
        self.assertEqual(former.data["historical_invoices"], 1)
        self.assertEqual(successor.data["historical_contracts"], 0)
        self.assertEqual(successor.data["historical_invoices"], 0)
        self.assertEqual(stranger.data["current_invoices"], 0)
        self.assertEqual(stranger.data["historical_invoices"], 0)
        self.assertEqual(
            set(former.data),
            {"current_contracts", "historical_contracts", "current_units",
             "current_invoices", "historical_invoices",
             "current_documents", "historical_documents", "maintenance_requests"},
        )
        self.assertNotIn("amount", str(former.data))
        self.assertNotIn("data", str(former.data))


class AlumbrisResidentPortfolioIntegrationTest(GenoAdminTestCase):
    """Portable snapshot: authorized objects, limits and private-field exclusion."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.tenant = get_user_model().objects.create_user(username="alumbris_portfolio_tenant")
        cls.stranger = get_user_model().objects.create_user(username="alumbris_portfolio_stranger")
        cls.addresses[0].user = cls.tenant
        cls.addresses[0].save(update_fields=["user"])
        cls.owned_contract = cls.contracts[0]
        cls.type = DocumentType.objects.create(name="alumbris_portfolio_test")
        cls.visible_doc = Document.objects.create(
            name="Visible lease", data='{"private":"never"}',
            resident_visible=True, doctype=cls.type,
            content_object=cls.owned_contract,
        )
        cls.private_doc = Document.objects.create(
            name="Private note", data='{"private":"hidden"}',
            resident_visible=False, doctype=cls.type,
            content_object=cls.owned_contract,
        )

    def call(self, user):
        request = APIRequestFactory().get("/api/v1/geno/resident-portfolio/")
        if user is not None:
            force_authenticate(request, user=user)
        return ResidentPortfolioView.as_view()(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_portfolio_test",))
    def test_only_visible_owned_document_and_safe_fields(self):
        response = self.call(self.tenant)
        self.assertEqual(response.status_code, 200)
        docs = response.data["current_documents"]
        self.assertEqual(docs["total"], 1)
        self.assertEqual(docs["items"][0]["id"], self.visible_doc.pk)
        self.assertNotIn("data", docs["items"][0])
        self.assertNotIn("template", docs["items"][0])
        self.assertNotIn("comment", docs["items"][0])
        self.assertNotIn(self.private_doc.pk, [row["id"] for row in docs["items"]])
        self.assertEqual(
            set(response.data),
            {"current_contracts", "historical_contracts", "current_units",
             "current_invoices", "historical_invoices",
             "current_documents", "historical_documents"},
        )
        for section in response.data.values():
            self.assertEqual(set(section), {"total", "items", "truncated"})
            self.assertGreaterEqual(section["total"], len(section["items"]))
            self.assertEqual(section["truncated"], section["total"] > 50)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_portfolio_test",))
    def test_cross_tenant_snapshot_is_empty_for_stranger(self):
        result = self.call(self.stranger)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(all(section["total"] == 0 for section in result.data.values()))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_portfolio_test",))
    def test_document_revocation_reflected_without_stale_snapshot(self):
        self.assertEqual(self.call(self.tenant).data["current_documents"]["total"], 1)
        self.visible_doc.resident_visible = False
        self.visible_doc.save(update_fields=["resident_visible"])
        self.assertEqual(self.call(self.tenant).data["current_documents"]["total"], 0)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_portfolio_test",))
    def test_portfolio_caps_each_collection_to_fifty(self):
        with patch.object(ResidentPortfolioView, "MAX_ITEMS_PER_SECTION", 1):
            result = self.call(self.tenant)
        contracts = result.data["current_contracts"]
        self.assertLessEqual(len(contracts["items"]), 1)
        self.assertEqual(contracts["truncated"], contracts["total"] > 1)


class AlumbrisResidentPortfolioPaginationTest(GenoAdminTestCase):
    """The seven page endpoints must share tenant authorization."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.tenant = get_user_model().objects.create_user(username="alumbris_paginated_tenant")
        cls.stranger = get_user_model().objects.create_user(username="alumbris_paginated_stranger")
        cls.addresses[0].user = cls.tenant
        cls.addresses[0].save(update_fields=["user"])
        cls.type = DocumentType.objects.create(name="alumbris_page_test")
        cls.doc = Document.objects.create(
            name="Available metadata", data='{"secret":"hidden"}',
            resident_visible=True, doctype=cls.type,
            content_object=cls.contracts[0],
        )

    def call(self, user, section="current-documents", page="1"):
        request = APIRequestFactory().get(
            "/api/v1/geno/resident-portfolio/sections/" + section + "/",
            {"page": page},
        )
        if user is not None:
            force_authenticate(request, user=user)
        return ResidentPortfolioSectionView.as_view()(request, section=section)

    def test_anonymous_and_unknown_sections_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))
        self.assertEqual(self.call(self.tenant, section="admin-invoices").status_code, 404)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_page_test",))
    def test_page_one_exposes_only_authorized_metadata(self):
        owned = self.call(self.tenant)
        self.assertEqual(owned.status_code, 200)
        self.assertEqual(owned.data["total"], 1)
        self.assertEqual(owned.data["items"][0]["id"], self.doc.pk)
        self.assertEqual(set(owned.data["items"][0]), {"id", "name", "doctype", "ts_created"})
        other = self.call(self.stranger)
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.data["total"], 0)

    def test_invalid_page_values_rejected(self):
        for value in ("0", "-1", "NaN", "10001", "9" * 500):
            self.assertEqual(self.call(self.tenant, page=value).status_code, 400)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_page_test",))
    def test_revocation_and_out_of_range_page(self):
        self.assertEqual(self.call(self.tenant, page="2").data["items"], [])
        self.assertFalse(self.call(self.tenant, page="1").data["has_next"])
        self.doc.resident_visible = False
        self.doc.save(update_fields=["resident_visible"])
        self.assertEqual(self.call(self.tenant).data["total"], 0)


class AlumbrisResidentTimelineTest(GenoAdminTestCase):
    """Timeline only includes current tenant events and published documents."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.tenant = get_user_model().objects.create_user(username="alumbris_timeline_tenant")
        cls.stranger = get_user_model().objects.create_user(username="alumbris_timeline_stranger")
        cls.addresses[0].user = cls.tenant
        cls.addresses[0].save(update_fields=["user"])
        cls.type = DocumentType.objects.create(name="alumbris_timeline_document")
        cls.visible = Document.objects.create(
            name="Lease published", doctype=cls.type,
            data='{"secret":"never return"}', resident_visible=True,
            content_object=cls.contracts[0],
        )
        cls.private = Document.objects.create(
            name="Internal memo", doctype=cls.type,
            data='{"secret":"private"}', resident_visible=False,
            content_object=cls.contracts[0],
        )

    def call(self, user, params=None):
        request = APIRequestFactory().get("/api/v1/geno/resident-timeline/", params or {})
        if user is not None:
            force_authenticate(request, user=user)
        return ResidentTimelineView.as_view()(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_timeline_document",))
    def test_timeline_includes_only_own_published_document(self):
        result = self.call(self.tenant)
        self.assertEqual(result.status_code, 200)
        document_events = [event for event in result.data["events"] if event["kind"] == "document"]
        self.assertIn(self.visible.pk, [event["id"] for event in document_events])
        self.assertNotIn(self.private.pk, [event["id"] for event in document_events])
        self.assertEqual(self.call(self.stranger).data["events"], [])
        self.assertTrue(all(
            set(event) == {"kind", "id", "title", "date"}
            for event in result.data["events"]
        ))
        self.assertEqual(result.data["limit"], 30)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_timeline_document",))
    def test_revocation_immediately_excludes_document_from_timeline(self):
        self.assertTrue(any(e["id"] == self.visible.pk and e["kind"] == "document"
                            for e in self.call(self.tenant).data["events"]))
        self.visible.resident_visible = False
        self.visible.save(update_fields=["resident_visible"])
        self.assertFalse(any(e["id"] == self.visible.pk and e["kind"] == "document"
                             for e in self.call(self.tenant).data["events"]))

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_timeline_document",))
    def test_category_filter_does_not_expose_private_or_cross_tenant_events(self):
        documents = self.call(self.tenant, {"kind": "document"})
        self.assertEqual(documents.status_code, 200)
        self.assertTrue(documents.data["events"])
        self.assertTrue(all(item["kind"] == "document" for item in documents.data["events"]))
        self.assertNotIn(self.private.pk, [item["id"] for item in documents.data["events"]])
        self.assertEqual(self.call(self.stranger, {"kind": "document"}).data["events"], [])
        invoices = self.call(self.tenant, {"kind": "invoice"})
        self.assertEqual(invoices.status_code, 200)
        self.assertTrue(all(item["kind"] == "invoice" for item in invoices.data["events"]))

    def test_unknown_categories_rejected(self):
        for kind in ("admin", "all", "", "../", "payments"):
            self.assertEqual(self.call(self.tenant, {"kind": kind}).status_code, 400)

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_timeline_document",))
    def test_multiple_categories_filter_and_publish_revocation(self):
        result = self.call(self.tenant, {"kind": ["document", "historical_document"]})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(all(item["kind"] in ("document", "historical_document")
                            for item in result.data["events"]))
        self.visible.resident_visible = False
        self.visible.save(update_fields=["resident_visible"])
        result = self.call(self.tenant, {"kind": "document"})
        self.assertEqual(result.data["events"], [])

    @override_settings(ALUMBRIS_RESIDENT_DOCUMENT_TYPES=("alumbris_timeline_document",))
    def test_date_range_filters_documents_on_database_side(self):
        today = datetime.date.today().isoformat()
        same_day = self.call(self.tenant, {"kind": "document", "from_date": today, "to_date": today})
        self.assertEqual(same_day.status_code, 200)
        self.assertIn(self.visible.pk, [item["id"] for item in same_day.data["events"]])
        old = self.call(self.tenant, {"kind": "document", "to_date": "2020-01-01"})
        self.assertEqual(old.status_code, 200)
        self.assertEqual(old.data["events"], [])

    def test_ambiguous_or_excessive_filter_parameters_rejected(self):
        cases = (
            {"from_date": ["2025-01-01", "2026-01-01"]},
            {"to_date": ["2025-01-01", "2026-01-01"]},
            {"kind": ["invoice", "invoice", "invoice", "invoice", "invoice"]},
        )
        for params in cases:
            self.assertEqual(self.call(self.tenant, params).status_code, 400)

    def test_invalid_date_range_inputs_rejected(self):
        for params in (
            {"from_date": "2020-99-99"},
            {"to_date": "../"},
            {"from_date": "2025-01-02", "to_date": "2025-01-01"},
            {"from_date": "2025-1-1"},
        ):
            self.assertEqual(self.call(self.tenant, params).status_code, 400)


class AlumbrisResidentCapabilitiesTest(GenoAdminTestCase):
    """Feature discovery is authenticated and explicitly read-only."""

    def call(self, user):
        request = APIRequestFactory().get("/api/v1/geno/resident-capabilities/")
        if user is not None:
            force_authenticate(request, user=user)
        return ResidentCapabilitiesView.as_view()(request)

    def test_anonymous_denied(self):
        self.assertIn(self.call(None).status_code, (401, 403))

    def test_capabilities_do_not_advertise_unimplemented_services(self):
        tenant = get_user_model().objects.create_user(username="alumbris_capabilities_tenant")
        result = self.call(tenant)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["read_only"])
        self.assertEqual(result.data["portfolio"]["page_size"], 25)
        self.assertEqual(result.data["timeline"]["max_events"], 30)
        self.assertFalse(result.data["document_download"])
        self.assertFalse(result.data["online_payments"])
        self.assertFalse(result.data["official_pt_tax_receipts"])
        self.assertEqual(len(result.data["portfolio"]["sections"]), 7)
        self.assertEqual(len(result.data["timeline"]["kinds"]), 4)
        self.assertNotIn("tenant", str(result.data))
        self.assertNotIn("password", str(result.data))


class AlumbrisResidentPortalPageTest(GenoAdminTestCase):
    """HTML portal requires login and never embeds raw tenancy data."""

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("geno:resident-portal"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_authenticated_resident_can_open_portal(self):
        user = get_user_model().objects.create_user(username="alumbris_page_visitor")
        self.client.force_login(user)
        response = self.client.get(reverse("geno:resident-portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alumbris Living")
        self.assertContains(response, "resident-overview/")
        self.assertContains(response, "resident-portfolio/sections/")
        self.assertContains(response, "Sem registos nesta categoria")
        self.assertNotContains(response, "password", status_code=200)

    def test_portal_has_no_server_embedded_resident_records(self):
        user = get_user_model().objects.create_user(username="alumbris_no_inline_data")
        self.client.force_login(user)
        response = self.client.get(reverse("geno:resident-portal"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"private_document_data", response.content)
        self.assertNotIn(b"resident_visible", response.content)

    def test_portal_has_maintenance_form_and_csrf_cookie(self):
        user = get_user_model().objects.create_user(username="alumbris_repair_page")
        self.client.force_login(user)
        response = self.client.get(reverse("geno:resident-portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="maintenance-form"')
        self.assertContains(response, 'id="maintenance-unit"')
        self.assertContains(response, 'id="maintenance-list"')
        self.assertContains(response, 'resident-maintenance/')
        self.assertContains(response, 'X-CSRFToken')
        self.assertIn("csrftoken", response.cookies)

    def test_portal_has_safe_rendering_and_pagination_controls(self):
        user = get_user_model().objects.create_user(username="alumbris_portal_controls")
        self.client.force_login(user)
        response = self.client.get(reverse("geno:resident-portal"))
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode()
        self.assertIn('textContent', markup)
        self.assertIn('aria-live', markup)
        self.assertIn('id="previous"', markup)
        self.assertIn('id="next"', markup)
        self.assertIn('credentials:"same-origin"', markup)
        self.assertNotIn('innerHTML', markup)


class AlumbrisResidentMaintenanceRequestTest(GenoAdminTestCase):
    """Resident maintenance is writable only for a currently occupied unit."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.tenant = get_user_model().objects.create_user(username="alumbris_repair_tenant")
        cls.other = get_user_model().objects.create_user(username="alumbris_repair_other")
        cls.addresses[0].user = cls.tenant
        cls.addresses[0].save(update_fields=["user"])

    def call(self, user, method="get", payload=None, pk=None):
        factory = APIRequestFactory()
        request = factory.post("/api/v1/geno/resident-maintenance/", payload or {}, format="json") if method == "post" else factory.get("/api/v1/geno/resident-maintenance/")
        if user is not None:
            force_authenticate(request, user=user)
        action = {"post": "create"} if method == "post" else {"get": "retrieve" if pk is not None else "list"}
        view = ResidentMaintenanceRequestViewSet.as_view(action)
        return view(request, pk=pk) if pk is not None else view(request)

    def test_anonymous_cannot_read_or_create(self):
        self.assertIn(self.call(None).status_code, (401, 403))
        self.assertIn(self.call(None, "post", {"rental_unit": self.rentalunits[0].pk, "title": "Avaria", "description": "Falta eletricidade no quarto."}).status_code, (401, 403))

    def test_owner_can_create_and_read_ticket_but_other_cannot(self):
        response = self.call(self.tenant, "post", {
            "rental_unit": self.rentalunits[0].pk,
            "title": "  Torneira avariada  ",
            "description": "A torneira da cozinha perde água continuamente.",
            "status": "resolved",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "open")
        self.assertEqual(response.data["title"], "Torneira avariada")
        pk = response.data["id"]
        self.assertEqual(self.call(self.tenant, pk=pk).status_code, 200)
        self.assertEqual(self.call(self.other, pk=pk).status_code, 404)
        self.assertEqual(self.call(self.other).data["count"], 0)
        ticket = ResidentMaintenanceRequest.objects.get(pk=pk)
        self.assertEqual(ticket.resident, self.tenant)

    def test_resident_cannot_impersonate_another_ticket_owner(self):
        response = self.call(self.tenant, "post", {
            "rental_unit": self.rentalunits[0].pk,
            "resident": self.other.pk,
            "title": "Problema de canalização",
            "description": "Há uma fuga de água na canalização da cozinha.",
            "status": "closed",
        })
        self.assertEqual(response.status_code, 201)
        ticket = ResidentMaintenanceRequest.objects.get(pk=response.data["id"])
        self.assertEqual(ticket.resident_id, self.tenant.pk)
        self.assertEqual(ticket.status, "open")
        self.assertEqual(self.call(self.other, pk=ticket.pk).status_code, 404)

    def test_unrelated_rental_unit_and_short_description_rejected(self):
        for unit in (self.rentalunits[3].pk,):
            response = self.call(self.tenant, "post", {
                "rental_unit": unit, "title": "Pedido", "description": "Problema com a porta.",
            })
            self.assertEqual(response.status_code, 400)
        response = self.call(self.tenant, "post", {
            "rental_unit": self.rentalunits[0].pk, "title": "Pedido", "description": "Curto",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ResidentMaintenanceRequest.objects.count(), 0)

    def test_staff_can_read_ticket_but_cannot_create_through_adminless_api(self):
        ticket = ResidentMaintenanceRequest.objects.create(
            resident=self.tenant, rental_unit=self.rentalunits[0],
            title="Avaria elétrica", description="O interruptor do corredor não funciona.",
        )
        staff = get_user_model().objects.create_user(
            username="alumbris_maintenance_staff", is_staff=True,
        )
        self.assertEqual(self.call(staff, pk=ticket.pk).status_code, 200)
        self.assertEqual(self.call(staff).data["count"], 1)

    def test_admin_rental_unit_change_page_with_ticket_renders(self):
        ticket = ResidentMaintenanceRequest.objects.create(
            resident=self.tenant, rental_unit=self.rentalunits[0],
            title="Porta danificada", description="A porta da entrada já não fecha bem.",
        )
        response = self.client.get(
            reverse("admin:geno_rentalunit_change", args=[self.rentalunits[0].pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ResidentMaintenanceRequest.objects.filter(pk=ticket.pk).exists())

    def test_dashboard_maintenance_count_is_owner_scoped(self):
        request = APIRequestFactory().get("/api/v1/geno/resident-overview/")
        force_authenticate(request, user=self.tenant)
        before = ResidentOverviewView.as_view()(request)
        self.assertEqual(before.data["maintenance_requests"], 0)
        ResidentMaintenanceRequest.objects.create(
            resident=self.tenant, rental_unit=self.rentalunits[0],
            title="Alarme avariado",
            description="O alarme da entrada está continuamente a disparar.",
        )
        after = ResidentOverviewView.as_view()(request)
        self.assertEqual(after.data["maintenance_requests"], 1)
        other_request = APIRequestFactory().get("/api/v1/geno/resident-overview/")
        force_authenticate(other_request, user=self.other)
        self.assertEqual(
            ResidentOverviewView.as_view()(other_request).data["maintenance_requests"], 0
        )

    def test_staff_can_read_but_cannot_submit_tickets(self):
        staff = get_user_model().objects.create_user(
            username="alumbris_repair_staff_create", is_staff=True,
        )
        response = self.call(staff, "post", {
            "rental_unit": self.rentalunits[0].pk,
            "title": "Pedido administrativo",
            "description": "O equipamento está a precisar de reparação.",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ResidentMaintenanceRequest.objects.count(), 0)

    def test_non_owner_cannot_update_existing_ticket(self):
        ticket = ResidentMaintenanceRequest.objects.create(
            resident=self.tenant, rental_unit=self.rentalunits[0],
            title="Problema", description="A janela não fecha corretamente.",
        )
        request = APIRequestFactory().patch(
            "/api/v1/geno/resident-maintenance/%s/" % ticket.pk,
            {"status": "closed"}, format="json",
        )
        force_authenticate(request, user=self.other)
        view = ResidentMaintenanceRequestViewSet.as_view({"patch": "partial_update"})
        self.assertEqual(view(request, pk=ticket.pk).status_code, 405)


class AlumbrisResidentMaintenanceCommentTest(GenoAdminTestCase):
    """Ticket conversations must never cross tenant boundaries."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        geno_testdata.create_contracts(cls)
        cls.tenant = get_user_model().objects.create_user(username="alumbris_comment_tenant")
        cls.other = get_user_model().objects.create_user(username="alumbris_comment_other")
        cls.ticket = ResidentMaintenanceRequest.objects.create(
            resident=cls.tenant, rental_unit=cls.rentalunits[0],
            title="Janela partida", description="A janela do quarto não fecha bem.",
        )

    def call(self, user, method="get", data=None, pk=None):
        factory = APIRequestFactory()
        if method == "post":
            request = factory.post("/api/v1/geno/resident-maintenance-comments/", data or {}, format="json")
        else:
            request = factory.get("/api/v1/geno/resident-maintenance-comments/")
        if user is not None:
            force_authenticate(request, user=user)
        action = {"post": "create"} if method == "post" else {"get": "retrieve" if pk else "list"}
        view = ResidentMaintenanceCommentViewSet.as_view(action)
        return view(request, pk=pk) if pk else view(request)

    def test_anonymous_and_stranger_cannot_create(self):
        payload = {"ticket": self.ticket.pk, "message": "Quando será a reparação?"}
        self.assertIn(self.call(None, "post", payload).status_code, (401, 403))
        self.assertEqual(self.call(self.other, "post", payload).status_code, 400)
        self.assertEqual(ResidentMaintenanceComment.objects.count(), 0)

    def test_resident_comment_is_readable_only_by_owner(self):
        response = self.call(self.tenant, "post", {
            "ticket": self.ticket.pk, "author": self.other.pk,
            "message": "A janela continua por reparar.",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], self.tenant.pk)
        comment = ResidentMaintenanceComment.objects.get(pk=response.data["id"])
        self.assertEqual(comment.author_id, self.tenant.pk)
        self.assertEqual(self.call(self.tenant, pk=comment.pk).status_code, 200)
        self.assertEqual(self.call(self.other, pk=comment.pk).status_code, 404)
        self.assertEqual(self.call(self.other).data["count"], 0)

    def test_closed_ticket_rejects_new_comments(self):
        self.ticket.status = "closed"
        self.ticket.save(update_fields=["status"])
        response = self.call(self.tenant, "post", {
            "ticket": self.ticket.pk, "message": "Nova mensagem",
        })
        self.assertEqual(response.status_code, 400)

    def test_staff_requires_ticket_permission(self):
        staff = get_user_model().objects.create_user(
            username="alumbris_comment_staff", is_staff=True,
        )
        payload = {"ticket": self.ticket.pk, "message": "Intervenção agendada."}
        self.assertEqual(self.call(staff, "post", payload).status_code, 400)
        self.assertEqual(self.call(staff).data["count"], 0)
