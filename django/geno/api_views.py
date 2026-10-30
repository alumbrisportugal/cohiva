import copy
import logging
import os
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, User
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.http import FileResponse
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from stdnum.ch import esr

from credit_accounting.api_views import get_capabilities as credit_accounting_capabilities
from finance.accounting import Account, AccountingBook, AccountingManager, AccountKey, AccountRole
from geno.billing import (
    add_invoice,
    create_qrbill,
    get_reference_nr,
    render_qrbill,
)
from geno.models import Address, Building, Contract, Document, Invoice, InvoiceCategory, RentalUnit, ResidentMaintenanceRequest
from geno.serializers import (
    ContractSerializer,
    GroupSerializer,
    RentalUnitSerializer,
    ResidentContractSerializer,
    ResidentRentalUnitSerializer,
    ResidentInvoiceSerializer,
    ResidentContractDocumentSerializer,
    ResidentMaintenanceRequestSerializer,
    UserSerializer,
)
from geno.utils import (
    nformat,
)
from reservation.api_views import get_capabilities as reservation_capabilities

logger = logging.getLogger("geno")


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    # Restricted until fine-grained object-level permissions are verified.
    permission_classes = [permissions.IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    # Restricted until fine-grained object-level permissions are verified.
    permission_classes = [permissions.IsAdminUser]


class RentalUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Active rental units visible to staff or their current signed occupants."""

    queryset = RentalUnit.objects.filter(active=True)
    serializer_class = RentalUnitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return RentalUnitSerializer
        return ResidentRentalUnitSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        today = timezone.localdate()
        return (
            queryset.filter(
                Q(rentalunit_contracts__date_end__isnull=True)
                | Q(rentalunit_contracts__date_end__gte=today),
                rentalunit_contracts__state="unterzeichnet",
                rentalunit_contracts__date__lte=today,
                rentalunit_contracts__contractors__user=user,
            )
            .distinct()
        )


class ContractViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only contracts visible to staff or a current signed contractor.

    Filtering is server-side and applies to both list and detail actions.
    A resident cannot enumerate a former tenant's or another unit's records.
    """

    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return ContractSerializer
        return ResidentContractSerializer
    queryset = Contract.objects.filter(
        state__in=("unterzeichnet", "gekuendigt"), main_contract=None
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        today = timezone.localdate()
        return (
            queryset.filter(
                state="unterzeichnet",
                date__lte=today,
                contractors__user=user,
            )
            .filter(Q(date_end__isnull=True) | Q(date_end__gte=today))
            .distinct()
        )


class ResidentContractHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Former tenants may read only the headers of their own ended contracts."""

    queryset = Contract.objects.filter(
        state__in=("unterzeichnet", "gekuendigt"),
        date_end__isnull=False,
        main_contract=None,
    )
    serializer_class = ResidentContractSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().filter(date_end__lt=timezone.localdate())
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(contractors__user=self.request.user).distinct()


class ResidentOverviewView(APIView):
    """Privacy-limited dashboard counters built from the resident APIs.

    No financial totals or personally identifying co-tenant data are returned.
    Counts share exactly the same authorization queries as list/detail routes.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        def visible_count(viewset_class):
            viewset = viewset_class()
            viewset.request = request
            return viewset.get_queryset().count()

        return Response({
            "current_contracts": visible_count(ContractViewSet),
            "historical_contracts": visible_count(ResidentContractHistoryViewSet),
            "current_units": visible_count(RentalUnitViewSet),
            "current_invoices": visible_count(ResidentInvoiceViewSet),
            "historical_invoices": visible_count(ResidentInvoiceHistoryViewSet),
            "current_documents": visible_count(ResidentContractDocumentViewSet),
            "historical_documents": visible_count(ResidentContractDocumentHistoryViewSet),
        })


class ResidentPortfolioView(APIView):
    """Bounded, read-only portal snapshot with object-scoped resident records.

    This is intentionally separate from payment processing or official
    Portuguese fiscal documents. Each collection reuses the corresponding
    list/detail authorization query; no arbitrary object IDs are accepted.
    """

    permission_classes = [permissions.IsAuthenticated]
    MAX_ITEMS_PER_SECTION = 50

    def get(self, request):
        sections = (
            ("current_contracts", ContractViewSet, ResidentContractSerializer),
            ("historical_contracts", ResidentContractHistoryViewSet, ResidentContractSerializer),
            ("current_units", RentalUnitViewSet, ResidentRentalUnitSerializer),
            ("current_invoices", ResidentInvoiceViewSet, ResidentInvoiceSerializer),
            ("historical_invoices", ResidentInvoiceHistoryViewSet, ResidentInvoiceSerializer),
            ("current_documents", ResidentContractDocumentViewSet, ResidentContractDocumentSerializer),
            ("historical_documents", ResidentContractDocumentHistoryViewSet, ResidentContractDocumentSerializer),
        )
        payload = {}
        for key, viewset_class, serializer_class in sections:
            viewset = viewset_class()
            viewset.request = request
            queryset = viewset.get_queryset().order_by("pk")
            total = queryset.count()
            payload[key] = {
                "total": total,
                "items": serializer_class(
                    queryset[:self.MAX_ITEMS_PER_SECTION], many=True,
                ).data,
                "truncated": total > self.MAX_ITEMS_PER_SECTION,
            }
        return Response(payload)


class ResidentPortfolioSectionView(APIView):
    """Paginated read-only sections backed by the same tenant querysets.

    Explicit section names prevent arbitrary model access, and the page cap
    protects the endpoint from accidental unbounded database responses.
    """

    permission_classes = [permissions.IsAuthenticated]
    PAGE_SIZE = 25
    MAX_PAGE = 10000

    def get(self, request, section):
        sections = {
            "current-contracts": (ContractViewSet, ResidentContractSerializer),
            "historical-contracts": (ResidentContractHistoryViewSet, ResidentContractSerializer),
            "current-units": (RentalUnitViewSet, ResidentRentalUnitSerializer),
            "current-invoices": (ResidentInvoiceViewSet, ResidentInvoiceSerializer),
            "historical-invoices": (ResidentInvoiceHistoryViewSet, ResidentInvoiceSerializer),
            "current-documents": (ResidentContractDocumentViewSet, ResidentContractDocumentSerializer),
            "historical-documents": (ResidentContractDocumentHistoryViewSet, ResidentContractDocumentSerializer),
        }
        if section not in sections:
            from django.http import Http404

            raise Http404
        raw_page = request.query_params.get("page", "1")
        if not raw_page.isdecimal() or len(raw_page) > 5:
            raise ValidationError({"page": "Expected a positive integer."})
        page = int(raw_page)
        if not 1 <= page <= self.MAX_PAGE:
            raise ValidationError({"page": "Page is out of range."})
        viewset_class, serializer_class = sections[section]
        viewset = viewset_class()
        viewset.request = request
        queryset = viewset.get_queryset().order_by("pk")
        total = queryset.count()
        offset = (page - 1) * self.PAGE_SIZE
        items = serializer_class(
            queryset[offset: offset + self.PAGE_SIZE], many=True
        ).data
        return Response({
            "section": section,
            "page": page,
            "page_size": self.PAGE_SIZE,
            "total": total,
            "has_next": offset + self.PAGE_SIZE < total,
            "items": items,
        })


class ResidentTimelineView(APIView):
    """Tenant-authorized, bounded and filterable activity timeline.

    Only published document metadata and permitted invoice summaries are
    represented. This is not an official fiscal or payment history.
    """

    permission_classes = [permissions.IsAuthenticated]
    MAX_EVENTS = 30
    VALID_KINDS = (
        "invoice", "historical_invoice", "document", "historical_document",
    )

    def get(self, request):
        kinds = request.query_params.getlist("kind")
        # Reject duplicated or ambiguous scalar filters instead of silently
        # using the final value supplied by the client.
        for scalar in ("from_date", "to_date"):
            if len(request.query_params.getlist(scalar)) > 1:
                raise ValidationError({scalar: "Provide exactly one date."})
        if len(kinds) > len(self.VALID_KINDS):
            raise ValidationError({"kind": "Too many event types."})
        if any(kind not in self.VALID_KINDS for kind in kinds):
            raise ValidationError({"kind": "Unknown timeline event type."})
        selected = set(kinds or self.VALID_KINDS)
        date_filters = {}
        for parameter in ("from_date", "to_date"):
            raw = request.query_params.get(parameter)
            if raw is None:
                continue
            try:
                parsed = date.fromisoformat(raw)
                if parsed.isoformat() != raw:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({parameter: "Expected YYYY-MM-DD."})
            date_filters[parameter] = parsed
        if (date_filters.get("from_date") and date_filters.get("to_date")
                and date_filters["from_date"] > date_filters["to_date"]):
            raise ValidationError({"date_range": "Start date must precede end date."})
        sources = (
            ("invoice", ResidentInvoiceViewSet, "date", "name"),
            ("historical_invoice", ResidentInvoiceHistoryViewSet, "date", "name"),
            ("document", ResidentContractDocumentViewSet, "ts_created", "name"),
            ("historical_document", ResidentContractDocumentHistoryViewSet, "ts_created", "name"),
        )
        events = []
        for kind, viewset_class, date_field, title_field in sources:
            if kind not in selected:
                continue
            viewset = viewset_class()
            viewset.request = request
            queryset = viewset.get_queryset()
            lookup = date_field + "__date" if date_field == "ts_created" else date_field
            if "from_date" in date_filters:
                queryset = queryset.filter(**{lookup + "__gte": date_filters["from_date"]})
            if "to_date" in date_filters:
                queryset = queryset.filter(**{lookup + "__lte": date_filters["to_date"]})
            queryset = queryset.order_by("-" + date_field, "-pk")
            for item in queryset[:self.MAX_EVENTS]:
                timestamp = getattr(item, date_field)
                events.append({
                    "kind": kind,
                    "id": item.pk,
                    "title": getattr(item, title_field),
                    "date": timestamp.date().isoformat()
                    if isinstance(timestamp, datetime) else timestamp.isoformat(),
                })
        events.sort(
            key=lambda item: (item["date"], item["kind"], item["id"]),
            reverse=True,
        )
        return Response({
            "events": events[:self.MAX_EVENTS],
            "limit": self.MAX_EVENTS,
        })


class ResidentCapabilitiesView(APIView):
    """Machine-readable portal contract; does not confer authorization.

    Feature discovery reports route/schema support without exposing models,
    settings, monetary data or any tenant's records.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "api_version": 1,
            "read_only": True,
            "overview": True,
            "portfolio": {
                "enabled": True,
                "max_items_per_section": ResidentPortfolioView.MAX_ITEMS_PER_SECTION,
                "sections": (
                    "current-contracts", "historical-contracts", "current-units",
                    "current-invoices", "historical-invoices",
                    "current-documents", "historical-documents",
                ),
                "page_size": ResidentPortfolioSectionView.PAGE_SIZE,
            },
            "timeline": {
                "enabled": True,
                "max_events": ResidentTimelineView.MAX_EVENTS,
                "kinds": ResidentTimelineView.VALID_KINDS,
                "date_filters": ("from_date", "to_date"),
            },
            "document_download": False,
            "online_payments": False,
            "official_pt_tax_receipts": False,
        })


class ResidentMaintenanceRequestViewSet(viewsets.ModelViewSet):
    """Tenants create and read their own tickets; staff may triage.

    Residents cannot assign another resident, change ticket status, update
    existing requests or choose a rental unit without a current lease.
    """

    serializer_class = ResidentMaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = ResidentMaintenanceRequest.objects.select_related("rental_unit")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(resident=self.request.user)

    def perform_create(self, serializer):
        unit = serializer.validated_data["rental_unit"]
        current_units = RentalUnitViewSet()
        current_units.request = self.request
        if not current_units.get_queryset().filter(pk=unit.pk).exists():
            raise ValidationError({"rental_unit": "A fração não está associada a um contrato atual."})
        serializer.save(resident=self.request.user)


class ResidentInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Tenant-owned invoice summaries; no historic or cross-tenant access yet."""

    queryset = Invoice.objects.filter(active=True, contract__isnull=False)
    serializer_class = ResidentInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        today = timezone.localdate()
        return queryset.filter(
            Q(contract__date_end__isnull=True) | Q(contract__date_end__gte=today),
            contract__state="unterzeichnet",
            contract__date__lte=today,
            contract__contractors__user=user,
        ).distinct()


class ResidentInvoiceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Historical invoice summaries restricted to their original contract parties.

    Unlike the current invoice endpoint, this accepts ended signed/terminated
    contracts. Each invoice must have a date within the old contract period.
    It never grants access to documents belonging to a successor's contract.
    """

    queryset = Invoice.objects.filter(active=True, contract__isnull=False)
    serializer_class = ResidentInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset.filter(contract__date_end__lt=timezone.localdate())
        today = timezone.localdate()
        return queryset.filter(
            contract__state__in=("unterzeichnet", "gekuendigt"),
            contract__contractors__user=user,
            contract__date_end__lt=today,
            date__gte=F("contract__date"),
            date__lte=F("contract__date_end"),
        ).distinct()


class ResidentContractDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """Return contract document metadata, never raw document context or files."""

    serializer_class = ResidentContractDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Document.objects.filter(
            content_type=ContentType.objects.get_for_model(Contract),
            doctype__name__in=getattr(settings, "ALUMBRIS_RESIDENT_DOCUMENT_TYPES", ()),
            resident_visible=True,
        )
        user = self.request.user
        if user.is_staff:
            return queryset
        today = timezone.localdate()
        return queryset.filter(
            object_id__in=Contract.objects.filter(
                Q(date_end__isnull=True) | Q(date_end__gte=today),
                active=True,
                state="unterzeichnet",
                date__lte=today,
                contractors__user=user,
            ).values("pk")
        )


class ResidentContractDocumentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Historical document metadata only, limited to original ended contracts.

    This does not grant file download access. Document creation dates are not
    used to prove ownership: metadata remains bound to the original contract.
    """

    serializer_class = ResidentContractDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Document.objects.filter(
            content_type=ContentType.objects.get_for_model(Contract),
            doctype__name__in=getattr(settings, "ALUMBRIS_RESIDENT_DOCUMENT_TYPES", ()),
            resident_visible=True,
        )
        user = self.request.user
        today = timezone.localdate()
        if user.is_staff:
            return queryset.filter(
                object_id__in=Contract.objects.filter(date_end__lt=today).values("pk")
            )
        # GenericForeignKey prevents a direct join to contract dates. Restrict
        # to the original contracting party and ended contracts server-side.
        # Historical downloads require a separate, stricter authorization path.
        return queryset.filter(
            object_id__in=Contract.objects.filter(
                state__in=("unterzeichnet", "gekuendigt"),
                date_end__lt=today,
                contractors__user=user,
            ).values("pk")
        )


class Akonto(APIView):
    """
    Get paid akonto amount for contract and billing period.
    """

    permission_classes = [permissions.IsAdminUser, permissions.IsAuthenticated]  ## Only admins

    def get(self, request, format=None):
        if "billing_period_start" not in request.query_params:
            raise ValidationError("billing_period_start is required.")
        if "billing_period_end" not in request.query_params:
            raise ValidationError("billing_period_end is required.")
        self.billing_period_start = datetime.strptime(
            request.query_params["billing_period_start"], "%Y-%m-%d"
        )
        self.billing_period_end = datetime.strptime(
            request.query_params["billing_period_end"], "%Y-%m-%d"
        )
        self.invoice_category_nk_ausserordentlich = InvoiceCategory.objects.get(
            name="Nebenkosten Akonto ausserordentlich"
        )
        self.contract_id = None
        if "contract_id" in request.query_params:
            try:
                self.contract_id = int(request.query_params["contract_id"])
            except:
                raise ValidationError("contract_id must be an integer")
            akonto = self.get_akonto_for_contract()
        else:
            akonto = self.get_akonto_for_all_contracts()
        return Response({"akonto_billing": akonto})

    def get_akonto_for_contract(self):
        akonto_total = 0
        if self.contract_id >= 0:
            contract = Contract.objects.get(id=self.contract_id)
            fiaccount = Account.from_settings(AccountKey.NK).set_code(contract=contract)
            # Get payments from contract AND linked contracts in case there are invoices
            # before/after the billing contract has been changed!
            for c in Contract.objects.filter(Q(id=contract.id) | Q(billing_contract=contract)):
                akonto = Invoice.objects.filter(
                    contract=c,
                    fin_account=fiaccount.code,
                    date__gte=self.billing_period_start,
                    date__lte=self.billing_period_end,
                ).aggregate(Sum("amount"))
                if akonto["amount__sum"]:
                    akonto_total += akonto["amount__sum"]
            # Ausserordentliche Akonto-Zahlungen
            for c in Contract.objects.filter(Q(id=contract.id) | Q(billing_contract=contract)):
                akonto = Invoice.objects.filter(
                    contract=c,
                    invoice_category=self.invoice_category_nk_ausserordentlich,
                    invoice_type="Invoice",
                    date__gte=self.billing_period_start,
                    date__lte=self.billing_period_end,
                ).aggregate(Sum("amount"))
                if akonto["amount__sum"]:
                    akonto_total += akonto["amount__sum"]
        return akonto_total

    def get_akonto_for_all_contracts(self):
        ## Get invoices for NK-Akonto and NK-Ausserordentlich
        fiaccount = Account.from_settings(AccountKey.NK)
        akonto_invoices = Invoice.objects.filter(
            Q(fin_account__startswith=fiaccount.prefix)
            | Q(invoice_category=self.invoice_category_nk_ausserordentlich),
            invoice_type="Invoice",
            date__gte=self.billing_period_start,
            date__lte=self.billing_period_end,
        )

        ## Add akonto per contract (linked billing_contract are added to the main contract)
        akonto_total = {}
        for invoice in akonto_invoices:
            contract_id = getattr(invoice.contract.billing_contract, "id", invoice.contract.id)
            if contract_id in akonto_total:
                akonto_total[contract_id] += invoice.amount
            else:
                akonto_total[contract_id] = invoice.amount
        return akonto_total


class QRBill(APIView):
    """
    Create and return QRBill and execute corresponding accounting transactions.
    """

    ## Require token auth
    # authentication_classes = [authentication.TokenAuthentication]  ## Enable this for csrf_exempt?
    permission_classes = [permissions.IsAdminUser, permissions.IsAuthenticated]  ## Only admins
    # permission_classes = [permissions.IsAuthenticated] ## Allow all authenticated users

    def __init__(self, **kwargs):
        # Virtual contracts: Just do accounting, no invoice
        # Example: (configured in settings.FINANCIAL_ACCOUNTS)
        #      1 - Aufwand Gästezimmer [6700]
        #      2 - Aufwand Sitzungszimmer [6720]
        #      3 - Geschäftsstelle -> Büromiete [6500]
        #      4 - Holliger -> Nicht verteilbare NK [4581]  --> von dort manuell umbuchen / in Rechnung stellen
        #      5 - Allgemein -> Nicht verteilbare NK [4581] --> von dort manuell umbuchen / in Rechnung stellen
        #      6 - Leerstand -> NK Leerstand [4582]
        self.virtual_contract_accounts = {}
        for key, account in settings.FINANCIAL_ACCOUNTS.items():
            if account.get("role") == AccountRole.NK_VIRTUAL and "virtual_id" in account:
                self.virtual_contract_accounts[account["virtual_id"]] = Account.from_settings(key)
        self.invoice_id = None
        self.contract = None
        self.building = None
        self.address = None
        self.invoice_category = None
        self.context = {}
        self.dry_run = True
        self.dry_run_tag = "DRY-RUN: "
        self.invoice_date = date.today()
        super().__init__(**kwargs)

    def get_virtual_contract_account(self, virt_contract_id):
        account = copy.copy(self.virtual_contract_accounts[virt_contract_id])
        if self.contract:
            account.set_code(contract=self.contract)
        elif self.building:
            account.set_code(building=self.building)
        return account

    def get_akonto_qrbill(self, request):
        invoice_category = InvoiceCategory.objects.get(
            reference_id=13
        )  # Nebenkosten Akonto ausserordentlich
        ref_number = get_reference_nr(invoice_category, self.contract.id)

        self.context["qr_account"] = settings.FINANCIAL_ACCOUNTS[AccountKey.DEFAULT_DEBTOR]["iban"]
        self.context["qr_ref_number"] = ref_number
        self.context["qr_amount"] = None
        self.context["qr_debtor"] = self.address
        self.context["qr_extra_info"] = (
            "NK-Akontozahlung ausserordentlich, Vertrag %s" % self.contract.id
        )
        output_filename = "QR-ESR_%s_%s.pdf" % (invoice_category.name, esr.compact(ref_number))

        try:
            render_qrbill(None, self.context, output_filename)
        except Exception as e:
            logger.error(
                "Could not create QR-bill for NK-Akonto ausserordentlich for contract %s (id=%s): %s"
                % (self.contract, request.data["contract_id"], e)
            )
            raise ValidationError("Could not create qr slip.")
        if os.path.isfile("/tmp/%s" % output_filename):
            pdf_file = open("/tmp/%s" % output_filename, "rb")
            resp = FileResponse(
                pdf_file,
                content_type="application/pdf",
                as_attachment=True,
                filename=output_filename,
            )
            logger.info("Return QR-bill for NK-Akonto ausserordentlich: %s" % output_filename)
            return resp
        logger.error(
            "Could not create QR-bill for NK-Akonto ausserordentlich for contract %s (id=%s)"
            % (self.contract, request.data["contract_id"])
        )
        raise ValidationError("Could not create qr slip.")

    def do_accounting(self, request, book: AccountingBook):
        billing_period_end = datetime.strptime(request.data["billing_period_end"], "%Y-%m-%d")
        fiaccount_nk = Account.from_settings(AccountKey.NK).set_code(contract=self.contract)
        fiaccount_nk_receivables = Account.from_settings(AccountKey.NK_RECEIVABLES).set_code(
            contract=self.contract
        )
        if request.data["total_akonto"] > 0:
            ## Transaction: Forderungen>Nebenkosten [1104] -> Passive Abgenzung>NK-Akonto [2301]
            description = "NK-Abrechnung Verrechnung Akontozahlungen %s" % (self.contract)
            amount = request.data["total_akonto"]
            try:
                book.add_transaction(
                    amount,
                    fiaccount_nk,
                    fiaccount_nk_receivables,
                    billing_period_end.date(),
                    description,
                    autosave=False,
                )
            except Exception as e:
                raise ValidationError(
                    f"Konnte Buchung für {description} nicht erstellen: {e}"
                ) from None
            logger.info(
                "%sAdded transaction: Verrechnnung Akontozahlung CHF %s for contract %s (id=%s)."
                % (self.dry_run_tag, amount, self.contract, request.data["contract_id"])
            )

        total_amount = request.data["total_amount"]
        comment = request.data["comment"]
        if self.contract:
            ## Create invoice for difference (Forderungen>Nebenkosten [1104] -> Forderungen>Mieter [1102])

            ## Add invoice, this will save the book, i.e. also the transaction above.
            try:
                invoice = add_invoice(
                    None,
                    self.invoice_category,
                    self.invoice_category.name,
                    self.invoice_date,
                    total_amount,
                    book=book,
                    contract=self.contract,
                    dry_run=self.dry_run,
                    comment=comment,
                )
            except Exception as e:
                logger.error(
                    "Could not create invoice for contract %s (id=%s): %s"
                    % (self.contract, request.data["contract_id"], e)
                )
                raise ValidationError(
                    f"Konnte Rechnungs-Objekt für Vertrag ID {self.contract.id} nicht erzeugen."
                )
            logger.info(
                "%sAdded invoice %s for contract %s (id=%s): CHF %s / %s"
                % (
                    self.dry_run_tag,
                    self.invoice_category,
                    self.contract,
                    request.data["contract_id"],
                    total_amount,
                    invoice,
                )
            )
            if not self.dry_run:
                self.invoice_id = invoice.id
        else:
            virtual_account = self.get_virtual_contract_account(request.data["contract_id"])
            description = f"NK-Abrechnung {virtual_account.name}"
            try:
                book.add_transaction(
                    total_amount,
                    virtual_account,
                    fiaccount_nk_receivables,
                    billing_period_end.date(),
                    description,
                    autosave=not self.dry_run,
                )
            except Exception as e:
                raise ValidationError(
                    f"Konnte Buchung für {description} nicht erstellen: {e}"
                ) from None
            logger.info(
                "%sAdded transaction: %s CHF %s for virtual contract (id=%s)."
                % (self.dry_run_tag, description, total_amount, request.data["contract_id"])
            )

    def post(self, request):
        request.data["contract_id"] = int(request.data["contract_id"])

        if request.data["contract_id"] < 1:
            ## Virtual contract
            self.contract = None
            self.address = Address.objects.filter(organization=settings.GENO_NAME).first()
        else:
            self.contract = Contract.objects.get(id=request.data["contract_id"])
            self.address = self.contract.get_contact_address()
        if "building_id" in request.data:
            self.building = Building.objects.get(id=int(request.data["building_id"]))
        self.context = self.address.get_context()
        logger.debug(
            "Getting QR-bill for contract %s (id=%s)"
            % (self.contract, request.data["contract_id"])
        )

        if "get_akonto_qrbill" in request.data and request.data["get_akonto_qrbill"]:
            return self.get_akonto_qrbill(request)

        if "dry_run" in request.data and not request.data["dry_run"]:
            self.dry_run = False
            self.dry_run_tag = ""

        if "invoice_date" in request.data and request.data["invoice_date"]:
            self.invoice_date = date.fromisoformat(request.data["invoice_date"])

        self.invoice_category = InvoiceCategory.objects.get(
            reference_id=12
        )  # Nebenkostenabrechnung

        if "regenerate_invoice_id" in request.data:
            self.invoice_id = request.data["regenerate_invoice_id"]
        else:
            with AccountingManager() as book:
                self.do_accounting(request, book)

        return self.get_qrbill(request)

    def get_qrbill(self, request):
        if self.contract:
            if self.dry_run:
                self.invoice_id = 9999999999

            ref_number = get_reference_nr(self.invoice_category, self.contract.id, self.invoice_id)
            output_filename = "Rechnung_%s_%s_%s.pdf" % (
                self.invoice_category.name,
                self.invoice_date.strftime("%Y%m%d"),
                esr.compact(ref_number),
            )
            self.context["contract_info"] = self.contract.get_contract_label()
        else:
            ## Virtual contract
            self.invoice_id = 8888888888
            ref_number = get_reference_nr(None, 0, self.invoice_id)
            virtual_contract = self.virtual_contract_accounts[request.data["contract_id"]]
            output_filename = "NK_%s_%s.pdf" % (
                virtual_contract.name,
                self.invoice_date.strftime("%Y%m%d"),
            )
            self.context["contract_info"] = virtual_contract.name

        total_amount = request.data["total_amount"]
        if total_amount < 0:
            self.context["qr_amount"] = 0
            if self.contract and self.contract.bankaccount:
                self.context["extra_text"] = (
                    "Ohne anderslautenden Gegenbericht in den nächsten 30 Tagen, werden wir das Guthaben von CHF %s auf das bei uns registrierte Konto %s überweisen."
                    % (nformat(-1 * total_amount), self.contract.bankaccount)
                )
            else:
                self.context["extra_text"] = (
                    f"Wir bitten %s, uns die Kontoangaben für die Rückerstattung des Guthabens von CHF %s in den nächsten 30 Tagen mitzuteilen (am liebsten per Email an {settings.SERVER_EMAIL}). Vielen Dank!"
                    % (self.context["dich"], nformat(-1 * total_amount))
                )
        else:
            self.context["qr_amount"] = total_amount
            if "extra_text" in request.data:
                self.context["extra_text"] = request.data["extra_text"]

        if "betreff" in request.data:
            self.context["betreff"] = request.data["betreff"]
        else:
            self.context["betreff"] = "Rechnung %s" % self.invoice_category.name
        self.context["invoice_date"] = self.invoice_date.strftime("%d.%m.%Y")
        self.context["invoice_duedate"] = (self.invoice_date + relativedelta(months=2)).strftime(
            "%d.%m.%Y"
        )
        self.context["invoice_nr"] = self.invoice_id
        self.context["show_liegenschaft"] = True
        self.context["sect_rent"] = False
        self.context["sect_generic"] = True
        self.context["generic_info"] = request.data["bill_lines"]
        self.context["s_generic_total"] = nformat(total_amount)
        self.context["qr_extra_info"] = "Rechnung %s" % self.context["invoice_nr"]

        (ret, mails_sent, mail_recipient) = create_qrbill(
            ref_number,
            self.address,
            self.context,
            output_filename,
            render=True,
            dry_run=self.dry_run,
        )
        info = "%s CHF %s Nr. %s/%s, %s" % (
            self.address,
            total_amount,
            self.context["invoice_nr"],
            self.context["invoice_date"],
            self.context["betreff"],
        )
        if ret:
            logger.error("Fehler beim Erzeugen der Rechnung für %s: %s" % (info, ret))
            raise ValidationError("Fehler beim erzeugen der Rechnung für %s: %s" % (info, ret))
        else:
            pdf_file = open("/tmp/%s" % output_filename, "rb")
            resp = FileResponse(
                pdf_file,
                content_type="application/pdf",
                as_attachment=True,
                filename=output_filename,
            )
            logger.info("Returning QR-Bill %s" % output_filename)
            return resp


def get_capabilities(request, capabilities):
    capabilities["features"] = []
    if hasattr(request.user, "address"):
        roles = request.user.address.get_roles()
        if "user" in roles:
            capabilities["features"].append("calendar")
            capabilities["features"].append("reservation")
        if "member" in roles or "renter" in roles:
            capabilities["features"].append("chat")
            capabilities["features"].append("cloud")
        if "renter" in roles:
            capabilities["features"].append("report")
            capabilities["features"].append("docs")
            capabilities["features"].append("energy-monitoring")
        if "community" in roles or "renter" in roles:
            capabilities["features"].append("chat_community")
    return


class CapabilitiesView(APIView):
    """
    Get capabilities/permissions for user.
    """

    permission_classes = [permissions.AllowAny]
    # permission_classes = [permissions.IsAuthenticated] ## Only admins

    def get(self, request, format=None):
        capabilities = {}
        get_capabilities(request, capabilities)
        reservation_capabilities(request, capabilities)
        credit_accounting_capabilities(request, capabilities)
        return Response({"status": "OK", "capabilities": capabilities})
