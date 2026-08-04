from django.apps import AppConfig
from django.core.checks import register


class WagtailDripdropConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtail_dripdrop"
    label = "wagtail_dripdrop"

    def ready(self):
        from wagtail_dripdrop.checks import check_on_duplicate_contact

        register(check_on_duplicate_contact)
