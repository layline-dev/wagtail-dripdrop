from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import cache

from wagtail_dripdrop.client import get_client
from wagtail_dripdrop.settings import get_custom_field_cache_timeout, get_flow_cache_timeout

if TYPE_CHECKING:
    from dripdrop import CustomFieldDefinition, PublicFlow

FLOWS_CACHE_KEY = "dripdrop_flows"
CUSTOM_FIELDS_CACHE_KEY = "dripdrop_custom_fields"


def get_cached_flows() -> list[PublicFlow]:
    """Return the flow list from cache, fetching from the API on a miss."""
    flows = cache.get(FLOWS_CACHE_KEY)
    if flows is None:
        flows = refresh_flow_cache()
    return flows


def refresh_flow_cache() -> list[PublicFlow]:
    """Force-fetch flows from the API and update the cache."""
    client = get_client()
    flows = client.list_flows()
    cache.set(FLOWS_CACHE_KEY, flows, timeout=get_flow_cache_timeout())
    return flows


def invalidate_flow_cache() -> None:
    """Remove the cached flow list."""
    cache.delete(FLOWS_CACHE_KEY)


def get_cached_custom_fields() -> list[CustomFieldDefinition]:
    """Return custom field definitions from cache, fetching on a miss."""
    fields = cache.get(CUSTOM_FIELDS_CACHE_KEY)
    if fields is None:
        fields = refresh_custom_field_cache()
    return fields


def refresh_custom_field_cache() -> list[CustomFieldDefinition]:
    """Force-fetch custom field definitions from the API and update the cache."""
    client = get_client()
    fields = client.list_custom_fields()
    cache.set(CUSTOM_FIELDS_CACHE_KEY, fields, timeout=get_custom_field_cache_timeout())
    return fields


def invalidate_custom_field_cache() -> None:
    """Remove the cached custom field list."""
    cache.delete(CUSTOM_FIELDS_CACHE_KEY)
