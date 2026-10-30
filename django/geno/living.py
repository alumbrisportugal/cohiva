"""Small residential workflow over Cohiva's existing models, without a second ledger."""

from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import Address, Building, Contract, RentalUnit

MODELS = ("building", "rentalunit", "address", "contract")


def require_management(user, write=False):
    permissions = [f"geno.view_{model}" for model in MODELS]
    if write:
        permissions += [f"geno.add_{model}" for model in MODELS]
    if not user.is_active or not user.is_staff or not user.has_perms(permissions):
        raise PermissionDenied
    # Currency is not stored on upstream RentalUnit. Never relabel an existing CHF instance.
    if getattr(settings, "ALUMBRIS_CURRENCY", None) != "EUR":
        raise PermissionDenied("Este percurso exige uma instalação dedicada em EUR.")


class NewTenancyForm(forms.Form):
    building = forms.ModelChoiceField(
        Building.objects.filter(active=True), label="Edifício existente", required=False
    )
    building_name = forms.CharField(label="Nome do novo edifício", max_length=100, required=False)
    street_name = forms.CharField(label="Rua", max_length=100, required=False)
    house_number = forms.CharField(label="Número de porta", max_length=100, required=False)
    city_zipcode = forms.RegexField(
        r"^\d{4}-\d{3}$",
        label="Código postal",
        required=False,
        error_messages={"invalid": "Usa o formato 0000-000."},
    )
    city_name = forms.CharField(label="Localidade", max_length=100, required=False)
    unit_name = forms.CharField(label="Identificação da fração", max_length=255)
    floor = forms.CharField(label="Piso", max_length=50, required=False)
    area = forms.DecimalField(
        label="Área (m²)",
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        required=False,
    )
    rent = forms.DecimalField(
        label="Renda mensal (€)", min_value=Decimal("0.01"), max_digits=10, decimal_places=2
    )
    address = forms.ModelChoiceField(
        Address.objects.all(), label="Inquilino existente", required=False
    )
    first_name = forms.CharField(label="Nome próprio", max_length=100, required=False)
    last_name = forms.CharField(label="Apelido", max_length=150, required=False)
    email = forms.EmailField(label="Email", max_length=254, required=False)
    date = forms.DateField(
        label="Início do contrato", widget=forms.DateInput(attrs={"type": "date"})
    )
    date_end = forms.DateField(
        label="Fim do contrato", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    signed = forms.BooleanField(label="Contrato já assinado pelas partes", required=False)

    def clean(self):
        data = super().clean()
        building = data.get("building")
        if not building and not data.get("building_name"):
            self.add_error(
                "building_name", "Seleciona um edifício ou indica o nome do novo edifício."
            )
        if building and data.get("building_name"):
            self.add_error(
                "building_name", "Seleciona apenas um edifício existente ou um novo edifício."
            )
        if not building and Building.objects.filter(name=data.get("building_name", "")).exists():
            self.add_error(
                "building_name", "Já existe um edifício com este nome. Seleciona-o acima."
            )
        if (
            building
            and RentalUnit.objects.filter(building=building, name=data.get("unit_name")).exists()
        ):
            self.add_error("unit_name", "Esta fração já existe neste edifício.")
        if not data.get("address"):
            for field in ("first_name", "last_name", "email"):
                if not data.get(field):
                    self.add_error(
                        field, "Preenche os dados do novo inquilino ou seleciona um existente."
                    )
            if data.get("email") and Address.objects.filter(email__iexact=data["email"]).exists():
                self.add_error("email", "Já existe um contacto com este email. Seleciona-o acima.")
        elif any(data.get(field) for field in ("first_name", "last_name", "email")):
            self.add_error(
                "address", "Seleciona um contacto existente ou preenche um novo contacto."
            )
        if data.get("date_end") and data.get("date") and data["date_end"] < data["date"]:
            self.add_error("date_end", "O fim não pode ser anterior ao início do contrato.")
        return data

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        building = data["building"] or Building.objects.create(
            name=data["building_name"],
            street_name=data["street_name"],
            house_number=data["house_number"],
            city_zipcode=data["city_zipcode"],
            city_name=data["city_name"],
            country="PT",
        )
        address = data["address"] or Address.objects.create(
            first_name=data["first_name"],
            name=data["last_name"],
            email=data["email"],
            country="PT",
        )
        unit = RentalUnit.objects.create(
            building=building,
            name=data["unit_name"],
            floor=data["floor"],
            area=data["area"],
            rental_type="Wohnung",
            rent_netto=data["rent"],
            billing_period=1,
        )
        contract = Contract.objects.create(
            main_contact=address,
            date=data["date"],
            date_end=data["date_end"],
            state="unterzeichnet" if data["signed"] else "angeboten",
            send_qrbill="none",
        )
        contract.contractors.add(address)
        contract.rental_units.add(unit)
        return contract


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def new_tenancy(request):
    require_management(request.user, write=True)
    form = NewTenancyForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            contract = form.save()
        except IntegrityError:
            form.add_error(
                None, "O edifício ou a fração já existe. Confirma os dados antes de repetir."
            )
        else:
            return redirect("geno:living-contract", pk=contract.pk)
    return render(request, "geno/living/new.html", {"form": form})


@login_required
@never_cache
@require_http_methods(["GET"])
def portfolio(request):
    require_management(request.user)
    contracts = Contract.objects.prefetch_related(
        "contractors", "rental_units__building"
    ).order_by("-pk")
    page = Paginator(contracts, 25).get_page(request.GET.get("page"))
    return render(request, "geno/living/portfolio.html", {"page": page})


@login_required
@never_cache
@require_http_methods(["GET"])
def contract_detail(request, pk):
    from django.shortcuts import get_object_or_404

    require_management(request.user)
    contract = get_object_or_404(
        Contract.objects.prefetch_related("contractors", "rental_units__building"), pk=pk
    )
    return render(request, "geno/living/contract.html", {"contract": contract})
