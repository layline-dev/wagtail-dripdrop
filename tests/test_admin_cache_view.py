from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse
from wagtail import hooks

from wagtail_dripdrop.cache import CUSTOM_FIELDS_CACHE_KEY, FLOWS_CACHE_KEY
from wagtail_dripdrop.wagtail_hooks import DripDropCacheView, register_cache_menu_item

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _staff_user(is_staff=True):
    return get_user_model().objects.create_user(
        username=f"staff-{is_staff}",
        email="staff@example.com",
        password="password",
        is_staff=is_staff,
        is_superuser=is_staff,
    )


def _request(method="get", *, is_staff=True):
    factory = RequestFactory()
    request = getattr(factory, method)("/admin/dripdrop/cache/")
    request.user = _staff_user(is_staff=is_staff)
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class TestDripDropCacheView:
    def test_get_renders_current_cached_flows_and_custom_fields(self):
        cache.set(FLOWS_CACHE_KEY, [{"uuid": "flow-1", "name": "Welcome Flow"}])
        cache.set(
            CUSTOM_FIELDS_CACHE_KEY,
            [
                {
                    "key": "source",
                    "display_name": "Lead Source",
                    "target_model": "contacts.contact",
                }
            ],
        )

        response = DripDropCacheView.as_view()(_request())

        assert response.status_code == 200
        content = response.rendered_content
        assert "Welcome Flow" in content
        assert "flow-1" in content
        assert "Lead Source" in content
        assert "source" in content

    def test_get_renders_empty_cache_state(self):
        response = DripDropCacheView.as_view()(_request())

        assert response.status_code == 200
        content = response.rendered_content
        assert "Flow cache is empty" in content
        assert "Custom field cache is empty" in content

    def test_post_refreshes_cache_and_redirects(self):
        flows = [{"uuid": "flow-1", "name": "Welcome Flow"}]
        fields = [{"key": "source", "display_name": "Lead Source"}]

        with (
            patch("wagtail_dripdrop.wagtail_hooks.refresh_flow_cache", return_value=flows)
            as mock_refresh_flows,
            patch(
                "wagtail_dripdrop.wagtail_hooks.refresh_custom_field_cache",
                return_value=fields,
            ) as mock_refresh_fields,
        ):
            response = DripDropCacheView.as_view()(_request("post"))

        assert response.status_code == 302
        assert response.url == reverse("dripdrop_cache")
        mock_refresh_flows.assert_called_once_with()
        mock_refresh_fields.assert_called_once_with()

    def test_non_staff_user_denied(self):
        request = _request(is_staff=False)

        with pytest.raises(PermissionDenied):
            DripDropCacheView.as_view()(request)


class TestDripDropCacheMenu:
    def test_registers_under_settings_menu_not_main_menu(self):
        settings_hooks = hooks.get_hooks("register_settings_menu_item")
        admin_hooks = hooks.get_hooks("register_admin_menu_item")

        assert register_cache_menu_item in settings_hooks
        assert register_cache_menu_item not in admin_hooks

    def test_settings_menu_item_points_to_cache_page(self):
        item = register_cache_menu_item()

        assert item.label == "DripDrop cache"
        assert item.url == reverse("dripdrop_cache")
