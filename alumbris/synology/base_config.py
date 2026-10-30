"""Configuration for a disposable, dedicated EUR staging installation only."""

import os

INSTALL_DIR = "/data"
DB_PREFIX = "living"
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOSTNAME = "db"
PROD_HOSTNAME = "living-test"
DOMAIN = "example.invalid"
USE_WHITENOISE = True
SITE_NAME = SITE_NICKNAME = ORG_NAME = "Alumbris Living — Ensaio"
SITE_SECRET = os.environ["DJANGO_SECRET_KEY"]
ORG_ADDRESS_STREET_NAME = ORG_ADDRESS_HOUSE_NUMBER = ""
ORG_ADDRESS_CITY_ZIPCODE = ORG_ADDRESS_CITY_NAME = ""
ORG_ADDRESS_COUNTRY = "Portugal"
ADMINS = (("Test administrator", "admin@example.invalid"),)
CASHCTRL_API_TOKEN = CASHCTRL_TENANT = ""
CASHCTRL_CUSTOM_FIELD_CREATED_BY_COHIVA = "customField1"
FEATURES = ["api", "portal", "reservation", "report", "credit_accounting", "website", "cms"]
