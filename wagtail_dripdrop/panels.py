from __future__ import annotations

import logging

from django import forms
from wagtail.admin.panels import FieldPanel

from wagtail_dripdrop.cache import get_cached_flows

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


def FlowChooserPanel():
    """Return a fresh FieldPanel for flow_uuid each time it's referenced."""
    return FieldPanel("flow_uuid", widget=FlowSelect)
