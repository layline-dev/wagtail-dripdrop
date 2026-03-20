from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import cache

from wagtail_dripdrop.client import get_client
from wagtail_dripdrop.settings import get_flow_cache_timeout

if TYPE_CHECKING:
    from dripdrop import PublicFlow

CACHE_KEY = "dripdrop_flows"


def get_cached_flows() -> list[PublicFlow]:
    """Return the flow list from cache, fetching from the API on a miss."""
    flows = cache.get(CACHE_KEY)
    if flows is None:
        flows = refresh_flow_cache()
    return flows


def refresh_flow_cache() -> list[PublicFlow]:
    """Force-fetch flows from the API and update the cache."""
    client = get_client()
    flows = client.list_flows()
    cache.set(CACHE_KEY, flows, timeout=get_flow_cache_timeout())
    return flows


def invalidate_flow_cache() -> None:
    """Remove the cached flow list."""
    cache.delete(CACHE_KEY)
