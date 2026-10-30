from django.contrib.auth.models import Group, User
from rest_framework import serializers

from .models import Contract, Document, Invoice, RentalUnit, ResidentMaintenanceRequest


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class RentalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalUnit
        fields = [
            "id",
            "url",
            "name",
            "label",
            "label_short",
            "rental_type",
            "rooms",
            "min_occupancy",
            "building",
            "floor",
            "area",
            "area_balcony",
            "area_add",
            "height",
            "volume",
            "rent_total",
            "rent_netto",
            "rent_year",
            "nk",
            "nk_flat",
            "nk_electricity",
            "share",
            "depot",
            "note",
            "description",
            "status",
            "adit_serial",
            "comment",
            "ts_created",
            "ts_modified",
        ]


## Alternative: HyperlinkedModelSerializer
## -> uses hyperlinks to represent relationships, rather than primary keys.
class ContractSerializer(serializers.ModelSerializer):
    contact_formal = serializers.SerializerMethodField()

    def get_contact_formal(self, obj):
        adr = obj.get_contact_address()
        if adr:
            return adr.formal
        return True

    class Meta:
        model = Contract
        fields = [
            "id",
            "url",
            "contractors",
            "main_contact",
            "rental_units",
            "state",
            "date",
            "date_end",
            "date_since",
            "billing_date_start",
            "billing_date_end",
            "rent_reduction",
            "rent_reservation",
            "share_reduction",
            "send_qrbill",
            "billing_contract",
            "note",
            "comment",
            "ts_created",
            "ts_modified",
            "contact_formal",
        ]
        ## exclude unused fields: 'children', 'children_old', 'import_id',
        ## 'links', 'backlinks'


class ResidentRentalUnitSerializer(serializers.ModelSerializer):
    """Minimal resident-facing fields; no intercom IDs or admin comments."""

    class Meta:
        model = RentalUnit
        fields = [
            "id", "name", "label", "label_short", "rental_type",
            "building", "floor", "area", "rooms",
        ]


class ResidentContractSerializer(serializers.ModelSerializer):
    """Conservative projection: no unrelated party IDs or financial notes."""

    class Meta:
        model = Contract
        fields = [
            "id", "rental_units", "state", "date", "date_end",
        ]


class ResidentInvoiceSerializer(serializers.ModelSerializer):
    """Minimal invoice summary, not an official Portuguese tax receipt."""

    class Meta:
        model = Invoice
        fields = ["id", "contract", "name", "date", "amount", "year", "month"]
        read_only_fields = fields


class ResidentContractDocumentSerializer(serializers.ModelSerializer):
    """Metadata only; document data and template are never included."""

    class Meta:
        model = Document
        fields = ["id", "name", "doctype", "ts_created"]
        read_only_fields = fields


class ResidentMaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentMaintenanceRequest
        fields = [
            "id", "rental_unit", "title", "description", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indica um assunto.")
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Descreve o problema com pelo menos 10 caracteres.")
        return value
