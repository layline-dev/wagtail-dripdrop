from __future__ import annotations

import pytest
from django.template.loader import get_template
from django.urls import reverse

from wagtail_dripdrop.wagtail_hooks import register_cache_menu_item

ICON_TEMPLATE = "wagtail_dripdrop/icons/dripdrop.svg"


class TestMenuIcon:
    def test_menu_item_uses_the_dripdrop_icon(self):
        assert register_cache_menu_item().icon_name == "dripdrop"

    def test_icon_is_in_the_admin_sprite(self):
        """``get_icons()`` returns the rendered sprite sheet, so the icon only
        renders in the menu if its symbol id appears there.

        ``wagtail.admin.icons`` only exists from Wagtail 6; the end-to-end
        sprite test below covers the same ground on every supported version.
        """
        icons = pytest.importorskip(
            "wagtail.admin.icons", reason="wagtail.admin.icons requires Wagtail 6+"
        )
        assert 'id="icon-dripdrop"' in icons.get_icons()

    def test_icon_template_is_installed_and_carries_matching_id(self):
        """Wagtail resolves a menu item's ``icon_name`` to an SVG whose
        ``id`` is ``icon-<name>``; a mismatch renders a blank icon."""
        rendered = get_template(ICON_TEMPLATE).render({})

        assert 'id="icon-dripdrop"' in rendered
        assert "<svg" in rendered


@pytest.mark.django_db
class TestIconEndToEnd:
    def test_sprite_endpoint_serves_the_icon(self, client, django_user_model):
        """Wagtail does not inline the sprite in the page; the admin JS pulls
        it from ``/admin/sprite/``, so that is the path the icon must reach."""
        user = django_user_model.objects.create_superuser(
            "root", "root@example.com", "pw"
        )
        client.force_login(user)

        response = client.get(reverse("wagtailadmin_sprite"))

        assert response.status_code == 200
        assert 'id="icon-dripdrop"' in response.content.decode()

    def test_menu_item_requests_the_icon(self, client, django_user_model):
        user = django_user_model.objects.create_superuser(
            "admin", "admin@example.com", "pw"
        )
        client.force_login(user)

        html = client.get(reverse("wagtailadmin_home")).content.decode()

        assert '"label": "DripDrop cache"' in html
        assert '"icon_name": "dripdrop"' in html


class TestMenuUrl:
    def test_menu_item_url_resolves(self):
        """The menu item is built with ``reverse_lazy``, so a missing URL
        registration only surfaces when the menu is rendered."""
        assert reverse("dripdrop_cache") == "/admin/dripdrop/cache/"

    def test_menu_item_points_at_the_cache_url(self):
        assert str(register_cache_menu_item().url) == reverse("dripdrop_cache")
