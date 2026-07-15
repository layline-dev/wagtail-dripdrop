from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from wagtail_dripdrop.cache import (
    CUSTOM_FIELDS_CACHE_KEY,
    FLOWS_CACHE_KEY,
    refresh_custom_field_cache,
    refresh_flow_cache,
)


class DripDropCacheView(TemplateView):
    template_name = "wagtail_dripdrop/cache.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flows = cache.get(FLOWS_CACHE_KEY)
        custom_fields = cache.get(CUSTOM_FIELDS_CACHE_KEY)
        context.update({
            "flows": flows,
            "custom_fields": custom_fields,
            "flows_cached": flows is not None,
            "custom_fields_cached": custom_fields is not None,
            "flow_count": len(flows or []),
            "custom_field_count": len(custom_fields or []),
        })
        return context

    def post(self, request, *args, **kwargs):
        try:
            flows = refresh_flow_cache()
            custom_fields = refresh_custom_field_cache()
        except Exception as exc:
            messages.error(request, f"Unable to refresh DripDrop cache: {exc}")
        else:
            messages.success(
                request,
                (
                    "DripDrop cache refreshed "
                    f"({len(flows)} flows, {len(custom_fields)} custom fields)."
                ),
            )
        return HttpResponseRedirect(reverse("dripdrop_cache"))


@hooks.register("register_admin_urls")
def register_admin_urls():
    from django.urls import path

    return [
        path(
            "dripdrop/cache/",
            DripDropCacheView.as_view(),
            name="dripdrop_cache",
        ),
    ]


@hooks.register("register_settings_menu_item")
def register_cache_menu_item():
    return MenuItem(
        "DripDrop cache",
        reverse_lazy("dripdrop_cache"),
        icon_name="refresh",
        order=900,
    )
