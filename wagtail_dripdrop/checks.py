from __future__ import annotations

from django.core.checks import Error
from django.core.exceptions import ImproperlyConfigured

from wagtail_dripdrop.settings import ON_DUPLICATE_CHOICES, get_on_duplicate_contact


def check_on_duplicate_contact(app_configs, **kwargs):
    """Validate ``DRIPDROP_ON_DUPLICATE_CONTACT`` at check time.

    The setting is otherwise read on the form-submission path, where errors
    are swallowed so that a DripDrop outage cannot break a form. A typo would
    therefore silently drop every enrollment; surfacing it through the checks
    framework means ``manage.py check`` catches it at deploy instead.
    """
    try:
        get_on_duplicate_contact()
    except ImproperlyConfigured as exc:
        return [
            Error(
                str(exc),
                hint=(
                    "Set DRIPDROP_ON_DUPLICATE_CONTACT to one of "
                    f"{sorted(ON_DUPLICATE_CHOICES)}, or remove it to use "
                    "the default."
                ),
                id="wagtail_dripdrop.E001",
            )
        ]
    return []
