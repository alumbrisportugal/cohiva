"""Application-level checks against the temporary restored MariaDB, never the live test DB."""

import os

import django
from django.conf import settings

os.environ["DJANGO_SETTINGS_MODULE"] = "cohiva.settings_living"
settings.DATABASES["default"].update(
    HOST="127.0.0.1", USER="root", PASSWORD=os.environ["MARIADB_ROOT_PASSWORD"]
)
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402

from geno.models import Contract  # noqa: E402

assert Contract.objects.count() >= 7
client = Client()
client.force_login(get_user_model().objects.get(username="living_test_admin"))
page = client.get("/geno/living/", secure=True)
assert page.status_code == 200
assert "Edifício fictício" in page.content.decode()
assert client.get("/geno/resident/portal/", secure=True).status_code == 200
client.logout()
assert client.get("/geno/living/", secure=True).status_code == 302
print("RESTORED_APPLICATION_PASS")
