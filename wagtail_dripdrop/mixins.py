from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import models

from wagtail_dripdrop.client import get_client

logger = logging.getLogger(__name__)


class DripDropFormMixin(models.Model):
    """Mixin for Wagtail ``AbstractForm`` subclasses that enrolls
    submitted contacts into a DripDrop flow.

    Usage::

        from wagtail_dripdrop.mixins import DripDropFormMixin
        from wagtail_dripdrop.panels import FlowChooserPanel

        class ContactPage(DripDropFormMixin, AbstractForm):
            content_panels = AbstractForm.content_panels + [FlowChooserPanel()]
    """

    flow_uuid = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="DripDrop Flow UUID",
        help_text="Select a DripDrop flow to enroll contacts in on submission.",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self.flow_uuid:
            return

        field_names = set(
            self.form_fields.values_list("clean_name", flat=True)
        )

        errors = []
        if "first_name" not in field_names:
            errors.append(
                "A DripDrop flow is selected but the form is missing a "
                "'first_name' field."
            )
        if "email" not in field_names and "phone" not in field_names:
            errors.append(
                "A DripDrop flow is selected but the form needs at least one "
                "of 'email' or 'phone'."
            )
        if errors:
            raise ValidationError({"flow_uuid": errors})

    def process_form_submission(self, form):
        submission = super().process_form_submission(form)

        if self.flow_uuid:
            self._enroll_contact(form.cleaned_data)

        return submission

    def _enroll_contact(self, data: dict) -> None:
        try:
            client = get_client()
            client.create_contact_and_enroll(
                flow_uuid=self.flow_uuid,
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                email=data.get("email"),
                phone=data.get("phone"),
            )
        except Exception:
            logger.exception("Failed to enroll contact in DripDrop flow %s", self.flow_uuid)
