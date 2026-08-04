from __future__ import annotations

from wagtail_dripdrop.checks import check_on_duplicate_contact


class TestOnDuplicateContactCheck:
    def test_default_passes(self, settings):
        del settings.DRIPDROP_ON_DUPLICATE_CONTACT
        assert check_on_duplicate_contact(None) == []

    def test_valid_value_passes(self, settings):
        settings.DRIPDROP_ON_DUPLICATE_CONTACT = "create_new"
        assert check_on_duplicate_contact(None) == []

    def test_invalid_value_is_reported(self, settings):
        settings.DRIPDROP_ON_DUPLICATE_CONTACT = "nonsense"

        errors = check_on_duplicate_contact(None)

        assert len(errors) == 1
        assert errors[0].id == "wagtail_dripdrop.E001"
        assert "nonsense" in errors[0].msg

    def test_check_is_registered_with_django(self):
        """Registration happens in ``AppConfig.ready``; without it the check
        never runs during ``manage.py check``."""
        from django.core.checks import registry

        assert check_on_duplicate_contact in registry.registry.get_checks()
