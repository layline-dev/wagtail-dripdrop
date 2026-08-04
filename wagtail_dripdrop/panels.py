from __future__ import annotations

import logging

from django import forms
from wagtail.admin.panels import FieldPanel

from wagtail_dripdrop.cache import get_cached_custom_fields, get_cached_flows
from wagtail_dripdrop.mixins import CUSTOM_MAPPING_TARGETS

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


#: Optgroup label for each custom-field target model, in display order. Derived
#: from the mapping definitions so the chooser and validation cannot disagree.
CUSTOM_FIELD_GROUPS = tuple(CUSTOM_MAPPING_TARGETS.values())


class CustomFieldKeySelect(forms.Select):
    """Select widget whose choices are populated from cached custom field
    definitions, grouped by target model.

    Contact and enrollment definitions are both offered; which group is valid
    for a given form field depends on its DripDrop mapping, and is enforced by
    ``DripDropFormMixin.clean()``.
    """

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, choices=[])

    def get_context(self, name, value, attrs):
        self.choices = self._build_choices()
        return super().get_context(name, value, attrs)

    @staticmethod
    def _build_choices():
        choices = [("", "---------")]
        try:
            definitions = get_cached_custom_fields()
        except Exception:
            logger.exception("Failed to load DripDrop custom fields for chooser")
            return choices

        for target_model, group_label in CUSTOM_FIELD_GROUPS:
            group = [
                (cf.key, cf.display_name)
                for cf in definitions
                if cf.target_model == target_model
            ]
            if group:
                choices.append((group_label, group))
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
