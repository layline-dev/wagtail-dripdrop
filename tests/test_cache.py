from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from wagtail_dripdrop.cache import (
    CUSTOM_FIELDS_CACHE_KEY,
    FLOWS_CACHE_KEY,
    get_cached_custom_fields,
    get_cached_flows,
    invalidate_custom_field_cache,
    invalidate_flow_cache,
    refresh_custom_field_cache,
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


@pytest.fixture()
def sample_custom_fields():
    return [
        {"key": "source", "display_name": "Lead Source", "target_model": "contacts.contact"},
        {"key": "company", "display_name": "Company", "target_model": "contacts.contact"},
    ]


class TestGetCachedFlows:
    def test_returns_cached_value_on_hit(self, sample_flows):
        cache.set(FLOWS_CACHE_KEY, sample_flows)

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
        assert cache.get(FLOWS_CACHE_KEY) == sample_flows


class TestRefreshFlowCache:
    def test_force_fetches_and_updates_cache(self, sample_flows):
        cache.set(FLOWS_CACHE_KEY, [])

        mock_client = MagicMock()
        mock_client.list_flows.return_value = sample_flows

        with patch("wagtail_dripdrop.cache.get_client", return_value=mock_client):
            result = refresh_flow_cache()

        assert result == sample_flows
        assert cache.get(FLOWS_CACHE_KEY) == sample_flows


class TestInvalidateFlowCache:
    def test_removes_cache_key(self, sample_flows):
        cache.set(FLOWS_CACHE_KEY, sample_flows)

        invalidate_flow_cache()

        assert cache.get(FLOWS_CACHE_KEY) is None


class TestGetCachedCustomFields:
    def test_returns_cached_value_on_hit(self, sample_custom_fields):
        cache.set(CUSTOM_FIELDS_CACHE_KEY, sample_custom_fields)

        with patch("wagtail_dripdrop.cache.get_client") as mock_get:
            result = get_cached_custom_fields()
            mock_get.assert_not_called()

        assert result == sample_custom_fields

    def test_fetches_from_api_on_miss(self, sample_custom_fields):
        mock_client = MagicMock()
        mock_client.list_custom_fields.return_value = sample_custom_fields

        with patch("wagtail_dripdrop.cache.get_client", return_value=mock_client):
            result = get_cached_custom_fields()

        assert result == sample_custom_fields
        assert cache.get(CUSTOM_FIELDS_CACHE_KEY) == sample_custom_fields


class TestRefreshCustomFieldCache:
    def test_force_fetches_and_updates_cache(self, sample_custom_fields):
        cache.set(CUSTOM_FIELDS_CACHE_KEY, [])

        mock_client = MagicMock()
        mock_client.list_custom_fields.return_value = sample_custom_fields

        with patch("wagtail_dripdrop.cache.get_client", return_value=mock_client):
            result = refresh_custom_field_cache()

        assert result == sample_custom_fields
        assert cache.get(CUSTOM_FIELDS_CACHE_KEY) == sample_custom_fields


class TestInvalidateCustomFieldCache:
    def test_removes_cache_key(self, sample_custom_fields):
        cache.set(CUSTOM_FIELDS_CACHE_KEY, sample_custom_fields)

        invalidate_custom_field_cache()

        assert cache.get(CUSTOM_FIELDS_CACHE_KEY) is None
