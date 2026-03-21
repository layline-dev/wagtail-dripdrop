from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from wagtail_dripdrop.mixins import DripDropFormMixin


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
        mixin_instance.form_fields = _make_form_fields([
            ("email", ""),
        ])

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "First Name" in str(exc_info.value)

    def test_missing_email_and_phone_mapping_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
        ])

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "Email" in str(exc_info.value)
        assert "Phone" in str(exc_info.value)

    def test_valid_mappings_pass(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("email", ""),
        ])

        mixin_instance.clean()

    def test_duplicate_contact_mapping_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("first_name", ""),
            ("email", ""),
        ])

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "Multiple form fields" in str(exc_info.value)

    def test_custom_mapping_without_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("email", ""),
            ("custom", ""),
        ])

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "custom field key" in str(exc_info.value).lower()

    def test_unknown_custom_field_key_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("email", ""),
            ("custom", "nonexistent_key"),
        ])

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
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("email", ""),
            ("custom", "source"),
        ])

        mock_cf = MagicMock(key="source", target_model="contacts.contact")
        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            return_value=[mock_cf],
        ):
            mixin_instance.clean()

    def test_custom_field_api_failure_does_not_block_save(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_form_fields([
            ("first_name", ""),
            ("email", ""),
            ("custom", "source"),
        ])

        with patch(
            "wagtail_dripdrop.cache.get_cached_custom_fields",
            side_effect=ConnectionError("API unavailable"),
        ):
            mixin_instance.clean()


class TestEnrollContact:
    def test_maps_contact_fields_correctly(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields([
            ("your_name", "first_name", ""),
            ("surname", "last_name", ""),
            ("email_address", "email", ""),
        ])
        mock_client = MagicMock()

        with patch(
            "wagtail_dripdrop.mixins.get_client", return_value=mock_client
        ):
            mixin_instance._enroll_contact({
                "your_name": "Jane",
                "surname": "Doe",
                "email_address": "jane@example.com",
            })

        mock_client.create_contact_and_enroll.assert_called_once_with(
            flow_uuid=mixin_instance.flow_uuid,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone=None,
            custom_fields=None,
        )

    def test_maps_custom_fields(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields([
            ("name", "first_name", ""),
            ("email", "email", ""),
            ("how_heard", "custom", "lead_source"),
        ])
        mock_client = MagicMock()

        with patch(
            "wagtail_dripdrop.mixins.get_client", return_value=mock_client
        ):
            mixin_instance._enroll_contact({
                "name": "Jane",
                "email": "jane@example.com",
                "how_heard": "Google",
            })

        mock_client.create_contact_and_enroll.assert_called_once_with(
            flow_uuid=mixin_instance.flow_uuid,
            first_name="Jane",
            last_name="",
            email="jane@example.com",
            phone=None,
            custom_fields={"lead_source": "Google"},
        )

    def test_failure_does_not_raise(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mixin_instance.form_fields = _make_enrollment_fields([
            ("name", "first_name", ""),
            ("email", "email", ""),
        ])
        mock_client = MagicMock()
        mock_client.create_contact_and_enroll.side_effect = Exception("API down")

        with patch(
            "wagtail_dripdrop.mixins.get_client", return_value=mock_client
        ):
            mixin_instance._enroll_contact({
                "name": "Jane",
                "email": "jane@example.com",
            })

    def test_skipped_when_no_flow_uuid(self, mixin_instance):
        mixin_instance.flow_uuid = None
        mock_form = MagicMock()
        mock_form.cleaned_data = {"name": "Jane"}

        with patch(
            "wagtail_dripdrop.mixins.get_client"
        ) as mock_get_client:
            with patch.object(
                DripDropFormMixin.__bases__[0],
                "process_form_submission",
                create=True,
                return_value=MagicMock(),
            ):
                mixin_instance.process_form_submission(mock_form)

        mock_get_client.assert_not_called()
