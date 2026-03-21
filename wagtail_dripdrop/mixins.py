from __future__ import annotations

import logging
from collections import Counter

import dripdrop
from django.core.exceptions import ValidationError
from django.db import models

from wagtail_dripdrop.client import get_client

logger = logging.getLogger(__name__)

CONTACT_TARGET_MODEL = "contacts.contact"
CUSTOM_MAPPING = "custom"
_CUSTOM_FIELDS_KEY = "custom_fields"


def _build_mapping_choices():
    """Derive contact field choices from the dripdrop SDK model."""
    choices = [("", "---------")]
    for name in dripdrop.CreateContactAndEnroll.model_fields:
        if name == _CUSTOM_FIELDS_KEY:
            continue
        choices.append((name, name.replace("_", " ").title()))
    choices.append((CUSTOM_MAPPING, "Custom Field"))
    return choices


DRIPDROP_MAPPING_CHOICES = _build_mapping_choices()
_MAPPING_LABELS = dict(DRIPDROP_MAPPING_CHOICES)


class DripDropFormFieldMixin(models.Model):
    """Mixin for Wagtail ``AbstractFormField`` subclasses that adds
    DripDrop field mapping to each form field.

    Usage::

        class FormField(DripDropFormFieldMixin, AbstractFormField):
            page = ParentalKey("ContactPage", related_name="form_fields")
            panels = AbstractFormField.panels + DripDropFieldMappingPanels()
    """

    dripdrop_mapping = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=DRIPDROP_MAPPING_CHOICES,
        verbose_name="DripDrop mapping",
    )
    dripdrop_custom_field_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="DripDrop custom field key",
    )

    class Meta:
        abstract = True


class DripDropFormMixin(models.Model):
    """Mixin for Wagtail ``AbstractForm`` subclasses that enrolls
    submitted contacts into a DripDrop flow.

    Requires form fields to use :class:`DripDropFormFieldMixin` so that
    each field can be mapped to a DripDrop contact property.

    Usage::

        from wagtail_dripdrop import DripDropFormMixin, FlowChooserPanel

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

        if not hasattr(self.form_fields.model, "dripdrop_mapping"):
            raise ValidationError(
                {"flow_uuid": (
                    "Your form field model must use DripDropFormFieldMixin "
                    "to enable field mapping."
                )}
            )

        field_data = list(
            self.form_fields.values_list(
                "dripdrop_mapping", "dripdrop_custom_field_key"
            )
        )

        errors = []
        mappings = [m for m, _ in field_data if m]

        if "first_name" not in mappings:
            errors.append(
                "A DripDrop flow is selected but no form field is mapped "
                "to 'First Name'."
            )
        if "email" not in mappings and "phone" not in mappings:
            errors.append(
                "A DripDrop flow is selected but at least one form field "
                "must be mapped to 'Email' or 'Phone'."
            )

        contact_mappings = [m for m in mappings if m != CUSTOM_MAPPING]
        for mapping, count in Counter(contact_mappings).items():
            if count > 1:
                label = _MAPPING_LABELS.get(mapping, mapping)
                errors.append(
                    f"Multiple form fields are mapped to '{label}'. "
                    "Each contact field can only be mapped once."
                )

        custom_entries = [(m, k) for m, k in field_data if m == CUSTOM_MAPPING]
        for _, key in custom_entries:
            if not key:
                errors.append(
                    "A form field is mapped to 'Custom Field' but no "
                    "custom field key is selected."
                )

        custom_keys = {k for _, k in custom_entries if k}
        if custom_keys:
            errors.extend(_validate_custom_field_keys(custom_keys))

        if errors:
            raise ValidationError({"flow_uuid": errors})

    def process_form_submission(self, form):
        submission = super().process_form_submission(form)

        if self.flow_uuid:
            self._enroll_contact(form.cleaned_data)

        return submission

    def _enroll_contact(self, data: dict) -> None:
        try:
            field_mappings = self.form_fields.exclude(
                dripdrop_mapping=""
            ).values_list(
                "clean_name", "dripdrop_mapping", "dripdrop_custom_field_key"
            )

            contact = {}
            custom_fields = {}
            for clean_name, mapping, custom_key in field_mappings:
                value = data.get(clean_name)
                if mapping == CUSTOM_MAPPING and custom_key:
                    custom_fields[custom_key] = value
                else:
                    contact[mapping] = value

            client = get_client()
            client.create_contact_and_enroll(
                flow_uuid=self.flow_uuid,
                first_name=contact.get("first_name", ""),
                last_name=contact.get("last_name", ""),
                email=contact.get("email"),
                phone=contact.get("phone"),
                custom_fields=custom_fields or None,
            )
        except Exception:
            logger.exception(
                "Failed to enroll contact in DripDrop flow %s", self.flow_uuid
            )


def _validate_custom_field_keys(keys: set[str]) -> list[str]:
    from wagtail_dripdrop.cache import get_cached_custom_fields

    errors = []
    try:
        known_keys = {
            cf.key
            for cf in get_cached_custom_fields()
            if cf.target_model == CONTACT_TARGET_MODEL
        }
        for key in sorted(keys - known_keys):
            errors.append(
                f"Custom field '{key}' does not exist in DripDrop. "
                "Create it in your DripDrop account before mapping "
                "form fields to it."
            )
    except Exception:
        logger.warning(
            "Could not validate custom field keys against the DripDrop API."
        )
    return errors
