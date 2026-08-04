from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_api_key():
    key = getattr(settings, "DRIPDROP_API_KEY", None)
    if not key:
        raise ImproperlyConfigured(
            "DRIPDROP_API_KEY must be set in your Django settings."
        )
    return key


def get_api_base_url():
    return getattr(settings, "DRIPDROP_API_BASE_URL", "https://api.dripdrop.dev")


def get_flow_cache_timeout():
    return getattr(settings, "DRIPDROP_FLOW_CACHE_TIMEOUT", 3600)


def get_custom_field_cache_timeout():
    return getattr(settings, "DRIPDROP_CUSTOM_FIELD_CACHE_TIMEOUT", 3600)


ENROLL_EXISTING = "enroll_existing"
CREATE_NEW = "create_new"
ON_DUPLICATE_CHOICES = frozenset({ENROLL_EXISTING, CREATE_NEW})


def get_on_duplicate_contact():
    """How to handle a submission matching an existing DripDrop contact.

    ``enroll_existing`` (default) lets the API return 409 and then enrolls the
    matched contact. ``create_new`` sends ``on_match="create"`` so DripDrop
    creates a second contact instead of matching.
    """
    value = getattr(settings, "DRIPDROP_ON_DUPLICATE_CONTACT", ENROLL_EXISTING)
    if value not in ON_DUPLICATE_CHOICES:
        raise ImproperlyConfigured(
            f"DRIPDROP_ON_DUPLICATE_CONTACT must be one of "
            f"{sorted(ON_DUPLICATE_CHOICES)}, got {value!r}."
        )
    return value
