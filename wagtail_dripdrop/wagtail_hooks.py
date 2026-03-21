from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from wagtail_dripdrop.cache import refresh_custom_field_cache, refresh_flow_cache


class RefreshFlowCacheView(View):

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        refresh_flow_cache()
        refresh_custom_field_cache()
        messages.success(request, "DripDrop cache refreshed.")
        return HttpResponseRedirect(reverse("wagtailadmin_home"))


@hooks.register("register_admin_urls")
def register_admin_urls():
    from django.urls import path

    return [
        path(
            "dripdrop/refresh-cache/",
            RefreshFlowCacheView.as_view(),
            name="dripdrop_refresh_cache",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_cache_menu_item():
    return MenuItem(
        "Refresh DripDrop Cache",
        reverse_lazy("dripdrop_refresh_cache"),
        icon_name="refresh",
        order=10000,
    )
