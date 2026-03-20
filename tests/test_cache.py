from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from wagtail_dripdrop.cache import (
    CACHE_KEY,
    get_cached_flows,
    invalidate_flow_cache,
    refresh_flow_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture()
def sample_flows():
    """Use plain dicts instead of MagicMock — LocMemCache requires picklable values."""
    return [
        {"uuid": "aaa-111", "name": "Flow A"},
        {"uuid": "bbb-222", "name": "Flow B"},
    ]


class TestGetCachedFlows:
    def test_returns_cached_value_on_hit(self, sample_flows):
        cache.set(CACHE_KEY, sample_flows)

        with patch("wagtail_dripdrop.cache.get_client") as mock_get:
            result = get_cached_flows()
            mock_get.assert_not_called()

        assert result == sample_flows

    def test_fetches_from_api_on_miss(self, sample_flows):
        mock_client = MagicMock()
        mock_client.list_flows.return_value = sample_flows

        with patch("wagtail_dripdrop.cache.get_client", return_value=mock_client):
            result = get_cached_flows()

        assert result == sample_flows
        assert cache.get(CACHE_KEY) == sample_flows


class TestRefreshFlowCache:
    def test_force_fetches_and_updates_cache(self, sample_flows):
        cache.set(CACHE_KEY, [])

        mock_client = MagicMock()
        mock_client.list_flows.return_value = sample_flows

        with patch("wagtail_dripdrop.cache.get_client", return_value=mock_client):
            result = refresh_flow_cache()

        assert result == sample_flows
        assert cache.get(CACHE_KEY) == sample_flows


class TestInvalidateFlowCache:
    def test_removes_cache_key(self, sample_flows):
        cache.set(CACHE_KEY, sample_flows)

        invalidate_flow_cache()

        assert cache.get(CACHE_KEY) is None
