from importlib.metadata import version

__version__ = version("wagtail-dripdrop")


def __getattr__(name):
    if name == "DripDropClient":
        from wagtail_dripdrop.client import DripDropClient
        return DripDropClient
    if name == "get_client":
        from wagtail_dripdrop.client import get_client
        return get_client
    if name == "DripDropFormMixin":
        from wagtail_dripdrop.mixins import DripDropFormMixin
        return DripDropFormMixin
    if name == "DripDropFormFieldMixin":
        from wagtail_dripdrop.mixins import DripDropFormFieldMixin
        return DripDropFormFieldMixin
    if name == "FlowChooserPanel":
        from wagtail_dripdrop.panels import FlowChooserPanel
        return FlowChooserPanel
    if name == "DripDropFieldMappingPanels":
        from wagtail_dripdrop.panels import DripDropFieldMappingPanels
        return DripDropFieldMappingPanels
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DripDropClient",
    "DripDropFieldMappingPanels",
    "DripDropFormFieldMixin",
    "DripDropFormMixin",
    "FlowChooserPanel",
    "get_client",
]
