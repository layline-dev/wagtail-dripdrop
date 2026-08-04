from __future__ import annotations

import datetime
import json
import logging
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import dripdrop
import pytest
from django.core.exceptions import ValidationError

from wagtail_dripdrop.mixins import (
    CUSTOM_MAPPINGS,
    DRIPDROP_MAPPING_CHOICES,
    MAPPABLE_CONTACT_FIELDS,
    DripDropFormMixin,
    _build_mapping_choices,
    _coerce_custom_value,
)


def _make_form_fields(mappings):
    """Build a mock form_fields manager from a list of (mapping, custom_key) tuples.

    The mock model has a ``dripdrop_mapping`` attribute so the hasattr
    check in ``clean()`` passes.
    """
    mock_model = type("MockFormField", (), {"dripdrop_mapping": ""})
    qs = MagicMock()
    qs.model = mock_model
    qs.values_list.return_value = mappings
    return qs


def _make_enrollment_fields(field_data):
    """Build a mock form_fields manager for ``_enroll_contact``.

    *field_data* is a list of ``(clean_name, mapping, custom_key)`` tuples.
    """
    qs = MagicMock()
    filtered = MagicMock()
    filtered.values_list.return_value = field_data
    qs.exclude.return_value = filtered
    return qs


@pytest.fixture()
def mixin_instance():
    instance = DripDropFormMixin.__new__(DripDropFormMixin)
    instance.flow_uuid = None
    return instance


class TestMappingChoices:
    def test_offers_contact_scalar_fields(self):
        values = [value for value, _ in DRIPDROP_MAPPING_CHOICES]
        assert {"first_name", "last_name", "email", "phone"} <= set(values)

    def test_excludes_non_mappable_sdk_fields(self):
        """``custom_fields``/``enrollment_custom_fields`` are dicts fed by the
        custom mappings, and ``on_match`` is a request option — none of them
        are selectable per form field."""
        values = {value for value, _ in DRIPDROP_MAPPING_CHOICES}
        assert "custom_fields" not in values
        assert "enrollment_custom_fields" not in values
        assert "on_match" not in values

    def test_offers_both_custom_mappings(self):
        values = [value for value, _ in DRIPDROP_MAPPING_CHOICES]
        assert "custom" in values
        assert "enrollment_custom" in values

    def test_only_offers_fields_the_client_forwards(self):
        """The choices are an allowlist, not a filter over the SDK model. A
        field the client does not forward must never be selectable, or an
        editor's mapping would be silently dropped at submission time."""
        values = {value for value, _ in DRIPDROP_MAPPING_CHOICES if value}
        assert values == set(MAPPABLE_CONTACT_FIELDS) | CUSTOM_MAPPINGS

    def test_new_sdk_fields_do_not_leak_into_choices(self, monkeypatch):
        """Guards the upgrade path: dripdrop adding a field to
        ``CreateContactAndEnroll`` must not change the dropdown."""
        monkeypatch.setattr(
            dripdrop.CreateContactAndEnroll,
            "model_fields",
            {**dripdrop.CreateContactAndEnroll.model_fields, "tags": object()},
        )

        values = {value for value, _ in _build_mapping_choices()}

        assert "tags" not in values

    def test_field_missing_from_sdk_is_skipped_with_a_warning(
        self, monkeypatch, caplog
    ):
        fields = {
            name: field
            for name, field in dripdrop.CreateContactAndEnroll.model_fields.items()
            if name != "phone"
        }
        monkeypatch.setattr(dripdrop.CreateContactAndEnroll, "model_fields", fields)

        with caplog.at_level(logging.WARNING):
            values = {value for value, _ in _build_mapping_choices()}

        assert "phone" not in values
        assert "phone" in caplog.text


class TestCoerceCustomValue:
    """Wagtail's form builder yields values that are not JSON-serialisable;
    passing them through unchanged would fail the request and lose the lead."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Google", "Google"),
            (42, 42),
            (True, True),
            (None, None),
            (3.5, 3.5),
            (Decimal("19.99"), 19.99),
            (datetime.date(2026, 3, 1), "2026-03-01"),
            (datetime.time(9, 30), "09:30:00"),
            (["A", "B"], "A, B"),
            (("A", "B"), "A, B"),
            ({"B", "A"}, "A, B"),
            ([datetime.date(2026, 3, 1)], "2026-03-01"),
        ],
    )
    def test_coercion(self, value, expected):
        assert _coerce_custom_value(value) == expected

    def test_datetime_is_isoformatted(self):
        value = datetime.datetime(2026, 3, 1, 9, 30)
        assert _coerce_custom_value(value) == "2026-03-01T09:30:00"

    def test_result_is_json_serialisable(self):
        payload = {
            "date": _coerce_custom_value(datetime.date(2026, 3, 1)),
            "choices": _coerce_custom_value(["A", "B"]),
            "amount": _coerce_custom_value(Decimal("19.99")),
        }
        assert json.loads(json.dumps(payload)) == {
            "date": "2026-03-01",
            "choices": "A, B",
            "amount": 19.99,
        }


class TestCleanValidation:
    def test_no_flow_uuid_passes(self, mixin_instance):
        mixin_instance.flow_uuid = None
        mixin_instance.clean()

    def test_missing_field_mixin_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_model = type("PlainFormField", (), {})
        qs = MagicMock()
        qs.model = mock_model
        mixin_instance.form_fields = qs

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "DripDropFormFieldMixin" in str(exc_info.value)

    def test_missing_first_name_mapping_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("email", ""),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "First Name" in str(exc_info.value)

    def test_missing_email_and_phone_mapping_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "Email" in str(exc_info.value)
        assert "Phone" in str(exc_info.value)

    def test_valid_mappings_pass(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
            ]
        )

        mixin_instance.clean()

    def test_duplicate_contact_mapping_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("first_name", ""),
                ("email", ""),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "Multiple form fields" in str(exc_info.value)

    def test_custom_mapping_without_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", ""),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "custom field key" in str(exc_info.value).lower()

    def test_unknown_custom_field_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", "nonexistent_key"),
            ]
        )

        mock_cf = MagicMock(key="source", target_model="contacts.contact")
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            with pytest.raises(ValidationError) as exc_info:
                mixin_instance.clean()

        assert "nonexistent_key" in str(exc_info.value)

    def test_valid_custom_field_key_passes(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", "source"),
            ]
        )

        mock_cf = MagicMock(key="source", target_model="contacts.contact")
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            mixin_instance.clean()

    def test_enrollment_custom_field_validated_against_enrollment_target(
        self, mixin_instance
    ):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("enrollment_custom", "requested_session"),
            ]
        )

        mock_cf = MagicMock(
            key="requested_session", target_model="flows.flowenrollment"
        )
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            mixin_instance.clean()

    def test_contact_key_rejected_for_enrollment_mapping(self, mixin_instance):
        """A contact-targeted definition is not valid for the enrollment
        mapping, even though the key exists in DripDrop."""
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("enrollment_custom", "source"),
            ]
        )

        mock_cf = MagicMock(key="source", target_model="contacts.contact")
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            with pytest.raises(ValidationError) as exc_info:
                mixin_instance.clean()

        assert "source" in str(exc_info.value)

    def test_duplicate_custom_field_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", "source"),
                ("custom", "source"),
            ]
        )

        mock_cf = MagicMock(key="source", target_model="contacts.contact")
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            with pytest.raises(ValidationError) as exc_info:
                mixin_instance.clean()

        assert "only be mapped once" in str(exc_info.value)

    def test_same_key_on_both_targets_is_allowed(self, mixin_instance):
        """Contact and enrollment custom fields are separate namespaces."""
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", "source"),
                ("enrollment_custom", "source"),
            ]
        )

        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[
                MagicMock(key="source", target_model="contacts.contact"),
                MagicMock(key="source", target_model="flows.flowenrollment"),
            ],
        ):
            mixin_instance.clean()

    def test_enrollment_custom_mapping_without_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("enrollment_custom", ""),
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "custom field key" in str(exc_info.value).lower()

    def test_custom_field_api_failure_does_not_block_save(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields(
            [
                ("first_name", ""),
                ("email", ""),
                ("custom", "source"),
            ]
        )

        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            side_effect=ConnectionError("API unavailable"),
        ):
            mixin_instance.clean()


class TestEnrollContact:
    def test_maps_contact_fields_correctly(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("your_name", "first_name", ""),
                ("surname", "last_name", ""),
                ("email_address", "email", ""),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "your_name": "Jane",
                    "surname": "Doe",
                    "email_address": "jane@example.com",
                }
            )

        mock_client.create_contact_and_enroll.assert_called_once_with(
            flow_uuid=mixin_instance.flow_uuid,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone=None,
            custom_fields=None,
            enrollment_custom_fields=None,
        )

    def test_maps_custom_fields(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("email", "email", ""),
                ("how_heard", "custom", "lead_source"),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "name": "Jane",
                    "email": "jane@example.com",
                    "how_heard": "Google",
                }
            )

        mock_client.create_contact_and_enroll.assert_called_once_with(
            flow_uuid=mixin_instance.flow_uuid,
            first_name="Jane",
            last_name="",
            email="jane@example.com",
            phone=None,
            custom_fields={"lead_source": "Google"},
            enrollment_custom_fields=None,
        )

    def test_maps_enrollment_custom_fields_separately(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("email", "email", ""),
                ("how_heard", "custom", "lead_source"),
                ("session", "enrollment_custom", "requested_session"),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "name": "Jane",
                    "email": "jane@example.com",
                    "how_heard": "Google",
                    "session": "Morning",
                }
            )

        kwargs = mock_client.create_contact_and_enroll.call_args.kwargs
        assert kwargs["custom_fields"] == {"lead_source": "Google"}
        assert kwargs["enrollment_custom_fields"] == {"requested_session": "Morning"}

    def test_custom_mapping_without_key_is_not_sent_as_contact_field(
        self, mixin_instance
    ):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("orphan", "custom", ""),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact({"name": "Jane", "orphan": "x"})

        kwargs = mock_client.create_contact_and_enroll.call_args.kwargs
        assert kwargs["custom_fields"] is None
        assert kwargs["enrollment_custom_fields"] is None

    def test_non_serialisable_values_are_coerced(self, mixin_instance):
        """A Wagtail date field yields ``datetime.date`` and a checkboxes field
        yields a list; both must reach the client JSON-ready."""
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("email", "email", ""),
                ("start_date", "enrollment_custom", "start_date"),
                ("interests", "custom", "interests"),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "name": "Jane",
                    "email": "jane@example.com",
                    "start_date": datetime.date(2026, 3, 1),
                    "interests": ["Sailing", "Racing"],
                }
            )

        kwargs = mock_client.create_contact_and_enroll.call_args.kwargs
        assert kwargs["custom_fields"] == {"interests": "Sailing, Racing"}
        assert kwargs["enrollment_custom_fields"] == {"start_date": "2026-03-01"}
        json.dumps([kwargs["custom_fields"], kwargs["enrollment_custom_fields"]])

    def test_unknown_mapping_is_not_sent_as_a_contact_field(self, mixin_instance):
        """Defence in depth for the allowlist: a mapping persisted by an older
        version (or a hand-edited row) must not be forwarded blindly."""
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("email", "email", ""),
                ("legacy", "tags", ""),
            ]
        )
        mock_client = MagicMock()

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "name": "Jane",
                    "email": "jane@example.com",
                    "legacy": "vip",
                }
            )

        kwargs = mock_client.create_contact_and_enroll.call_args.kwargs
        assert "tags" not in kwargs
        assert kwargs["first_name"] == "Jane"

    def test_failure_does_not_raise(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields(
            [
                ("name", "first_name", ""),
                ("email", "email", ""),
            ]
        )
        mock_client = MagicMock()
        mock_client.create_contact_and_enroll.side_effect = Exception("API down")

        with patch("wagtail_dripdrop.mixins.get_client", return_value=mock_client):
            mixin_instance._enroll_contact(
                {
                    "name": "Jane",
                    "email": "jane@example.com",
                }
            )

    def test_skipped_when_no_flow_uuid(self, mixin_instance):
        mixin_instance.flow_uuid = None
        mock_form = MagicMock()
        mock_form.cleaned_data = {"name": "Jane"}

        with patch("wagtail_dripdrop.mixins.get_client") as mock_get_client:
            with patch.object(
                DripDropFormMixin.__bases__[0],
                "process_form_submission",
                create=True,
                return_value=MagicMock(),
            ):
                mixin_instance.process_form_submission(mock_form)

        mock_get_client.assert_not_called()
