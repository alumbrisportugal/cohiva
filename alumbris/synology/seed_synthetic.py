"""Execute via manage.py shell ONLY on disposable staging; refuses any other settings."""

import datetime
import json
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.authtoken.models import Token

from geno.models import Address, Building, Contract, RentalUnit

if settings.SETTINGS_MODULE != "cohiva.settings_living":
    raise RuntimeError("Synthetic seed requires the isolated staging settings")

with transaction.atomic():
    User = get_user_model()
    credentials_path = Path("/data/test-credentials.json")
    if credentials_path.exists() or User.objects.filter(username="living_test_admin").exists():
        raise RuntimeError("Seed already exists; do not silently reset credentials")
    password = secrets.token_urlsafe(32)
    User.objects.create_superuser("living_test_admin", "admin@example.invalid", password)
    records = []
    for index in range(1, 8):
        resident_password = secrets.token_urlsafe(32)
        user = User.objects.create_user(f"living_resident_{index}", password=resident_password)
        person = Address.objects.create(
            user=user,
            first_name="Residente",
            name=f"Fictício {index}",
            email=f"resident-{index}@example.invalid",
            country="PT",
        )
        building = Building.objects.create(name=f"Edifício fictício {index}", country="PT")
        unit = RentalUnit.objects.create(
            building=building,
            name=f"T{index}",
            rental_type="Wohnung",
            rent_netto=700,
            billing_period=1,
        )
        contract = Contract.objects.create(
            main_contact=person,
            date=datetime.date(2026, 1, 1),
            date_end=datetime.date(2030, 12, 31),
            state="unterzeichnet",
            send_qrbill="none",
        )
        contract.contractors.add(person)
        contract.rental_units.add(unit)
        records.append(
            {
                "token": Token.objects.create(user=user).key,
                "username": user.username,
                "password": resident_password,
                "unit": unit.pk,
                "contract": contract.pk,
            }
        )
    # File is persisted on the staging data volume, never in source or reports.
    credentials_path.write_text(
        json.dumps({"username": "living_test_admin", "password": password, "residents": records})
    )
    credentials_path.chmod(0o600)
print("SEEDED_7_SYNTHETIC_TENANCIES")
