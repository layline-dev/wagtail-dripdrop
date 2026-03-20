import django
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.DJANGO_SETTINGS_MODULE = "tests.settings"
        django.setup()
