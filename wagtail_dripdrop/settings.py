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
