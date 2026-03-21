from __future__ import annotations

import logging

from django import forms
from wagtail.admin.panels import FieldPanel

from wagtail_dripdrop.cache import get_cached_custom_fields, get_cached_flows
from wagtail_dripdrop.mixins import CONTACT_TARGET_MODEL

logger = logging.getLogger(__name__)


class FlowSelect(forms.Select):
    """Select widget whose choices are populated from the cached flow list."""

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, choices=[])

    def get_context(self, name, value, attrs):
        self.choices = self._build_choices()
        return super().get_context(name, value, attrs)

    @staticmethod
    def _build_choices():
        choices = [("", "---------")]
        try:
            for flow in get_cached_flows():
                choices.append((str(flow.uuid), flow.name))
        except Exception:
            logger.exception("Failed to load DripDrop flows for chooser")
        return choices


class CustomFieldKeySelect(forms.Select):
    """Select widget whose choices are populated from cached custom field
    definitions filtered to the ``contacts.contact`` target model."""

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, choices=[])

    def get_context(self, name, value, attrs):
        self.choices = self._build_choices()
        return super().get_context(name, value, attrs)

    @staticmethod
    def _build_choices():
        choices = [("", "---------")]
        try:
            for cf in get_cached_custom_fields():
                if cf.target_model == CONTACT_TARGET_MODEL:
                    choices.append((cf.key, cf.display_name))
        except Exception:
            logger.exception("Failed to load DripDrop custom fields for chooser")
        return choices


def FlowChooserPanel():
    """Return a fresh FieldPanel for flow_uuid each time it's referenced."""
    return FieldPanel("flow_uuid", widget=FlowSelect)


def DripDropFieldMappingPanels():
    """Return panels for DripDrop field mapping on AbstractFormField subclasses."""
    return [
        FieldPanel("dripdrop_mapping"),
        FieldPanel("dripdrop_custom_field_key", widget=CustomFieldKeySelect),
    ]
