from __future__ import annotations

import datetime
import logging
from collections import Counter
from decimal import Decimal
from typing import Any, NamedTuple

import dripdrop
from django.core.exceptions import ValidationError
from django.db import models

from wagtail_dripdrop.client import get_client

logger = logging.getLogger(__name__)

CONTACT_TARGET_MODEL = "contacts.contact"
ENROLLMENT_TARGET_MODEL = "flows.flowenrollment"

CUSTOM_MAPPING = "custom"
ENROLLMENT_CUSTOM_MAPPING = "enrollment_custom"
CUSTOM_MAPPINGS = frozenset({CUSTOM_MAPPING, ENROLLMENT_CUSTOM_MAPPING})


class CustomFieldTarget(NamedTuple):
    """Where a custom-field mapping's definitions come from."""

    target_model: str
    #: Optgroup label used by ``panels.CustomFieldKeySelect``.
    group_label: str


#: Single source of truth for the two custom-field namespaces. Iteration order
#: is the order the groups appear in the admin key chooser.
CUSTOM_MAPPING_TARGETS = {
    CUSTOM_MAPPING: CustomFieldTarget(CONTACT_TARGET_MODEL, "Contact custom fields"),
    ENROLLMENT_CUSTOM_MAPPING: CustomFieldTarget(
        ENROLLMENT_TARGET_MODEL, "Enrollment custom fields"
    ),
}

#: Scalar ``CreateContactAndEnroll`` fields a form field may be mapped to, in
#: display order. This is deliberately an allowlist rather than a filter over
#: ``model_fields``: anything not named here is never forwarded by
#: :meth:`DripDropFormMixin._enroll_contact`, so letting a new SDK field appear
#: in the dropdown would silently discard whatever an editor mapped to it.
MAPPABLE_CONTACT_FIELDS = ("first_name", "last_name", "email", "phone")


def _build_mapping_choices():
    """Build the DripDrop mapping choices, labelled from the SDK model."""
    sdk_fields = dripdrop.CreateContactAndEnroll.model_fields
    missing = [name for name in MAPPABLE_CONTACT_FIELDS if name not in sdk_fields]
    if missing:
        logger.warning(
            "The installed dripdrop SDK has no %s field(s) on "
            "CreateContactAndEnroll; the matching form field mappings will "
            "not be offered.",
            ", ".join(missing),
        )

    choices = [("", "---------")]
    for name in MAPPABLE_CONTACT_FIELDS:
        if name in sdk_fields:
            choices.append((name, name.replace("_", " ").title()))
    choices.append((CUSTOM_MAPPING, "Custom Field"))
    choices.append((ENROLLMENT_CUSTOM_MAPPING, "Enrollment Custom Field"))
    return choices


def _coerce_custom_value(value: Any) -> Any:
    """Coerce a cleaned form value into something JSON-serialisable.

    Wagtail's form builder yields ``datetime`` objects for date fields and
    lists for checkbox/multi-select fields. Passing those through unchanged
    makes the API request fail to serialise, which would lose the submission.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else value
        return ", ".join(str(_coerce_custom_value(item)) for item in items)
    return str(value)


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
                {
                    "flow_uuid": (
                        "Your form field model must use DripDropFormFieldMixin "
                        "to enable field mapping."
                    )
                }
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

        contact_mappings = [m for m in mappings if m not in CUSTOM_MAPPINGS]
        for mapping, count in Counter(contact_mappings).items():
            if count > 1:
                label = _MAPPING_LABELS.get(mapping, mapping)
                errors.append(
                    f"Multiple form fields are mapped to '{label}'. "
                    "Each contact field can only be mapped once."
                )

        custom_entries = [(m, k) for m, k in field_data if m in CUSTOM_MAPPINGS]
        for mapping, key in custom_entries:
            if not key:
                label = _MAPPING_LABELS.get(mapping, mapping)
                errors.append(
                    f"A form field is mapped to '{label}' but no "
                    "custom field key is selected."
                )

        for (mapping, key), count in Counter(custom_entries).items():
            if key and count > 1:
                label = _MAPPING_LABELS.get(mapping, mapping)
                errors.append(
                    f"Multiple form fields are mapped to the '{label}' "
                    f"key '{key}'. Each custom field can only be mapped once."
                )

        for mapping in CUSTOM_MAPPING_TARGETS:
            keys = {k for m, k in custom_entries if m == mapping and k}
            if keys:
                errors.extend(_validate_custom_field_keys(mapping, keys))

        if errors:
            raise ValidationError({"flow_uuid": errors})

    def process_form_submission(self, form):
        submission = super().process_form_submission(form)

        if self.flow_uuid:
            self._enroll_contact(form.cleaned_data)

        return submission

    def _enroll_contact(self, data: dict) -> None:
        try:
            field_mappings = self.form_fields.exclude(dripdrop_mapping="").values_list(
                "clean_name", "dripdrop_mapping", "dripdrop_custom_field_key"
            )

            contact = {}
            custom_fields = {}
            enrollment_custom_fields = {}
            for clean_name, mapping, custom_key in field_mappings:
                value = data.get(clean_name)
                if mapping == CUSTOM_MAPPING and custom_key:
                    custom_fields[custom_key] = _coerce_custom_value(value)
                elif mapping == ENROLLMENT_CUSTOM_MAPPING and custom_key:
                    enrollment_custom_fields[custom_key] = _coerce_custom_value(value)
                elif mapping in MAPPABLE_CONTACT_FIELDS:
                    contact[mapping] = value

            client = get_client()
            client.create_contact_and_enroll(
                flow_uuid=self.flow_uuid,
                first_name=contact.get("first_name", ""),
                last_name=contact.get("last_name", ""),
                email=contact.get("email"),
                phone=contact.get("phone"),
                custom_fields=custom_fields or None,
                enrollment_custom_fields=enrollment_custom_fields or None,
            )
        except Exception:
            logger.exception(
                "Failed to enroll contact in DripDrop flow %s", self.flow_uuid
            )


def _validate_custom_field_keys(mapping: str, keys: set[str]) -> list[str]:
    from wagtail_dripdrop.cache import get_cached_custom_fields

    target_model = CUSTOM_MAPPING_TARGETS[mapping].target_model
    label = _MAPPING_LABELS.get(mapping, mapping)

    errors = []
    try:
        known_keys = {
            cf.key
            for cf in get_cached_custom_fields()
            if cf.target_model == target_model
        }
        for key in sorted(keys - known_keys):
            errors.append(
                f"There is no '{label}' called '{key}' in DripDrop. Create it "
                "in your DripDrop account before mapping form fields to it."
            )
    except Exception:
        logger.warning("Could not validate custom field keys against the DripDrop API.")
    return errors
