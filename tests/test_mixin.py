from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from wagtail_dripdrop.mixins import DripDropFormMixin


@pytest.fixture()
def mixin_instance():
    """Create a minimal DripDropFormMixin instance for testing."""
    instance = DripDropFormMixin.__new__(DripDropFormMixin)
    instance.flow_uuid = None
    return instance


class TestCleanValidation:
    def test_no_flow_uuid_passes(self, mixin_instance):
        mixin_instance.flow_uuid = None
        mixin_instance.clean()

    def test_missing_first_name_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_qs = MagicMock()
        mock_qs.values_list.return_value = ["email"]
        mixin_instance.form_fields = mock_qs

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "first_name" in str(exc_info.value)

    def test_missing_email_and_phone_raises(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_qs = MagicMock()
        mock_qs.values_list.return_value = ["first_name"]
        mixin_instance.form_fields = mock_qs

        with pytest.raises(ValidationError) as exc_info:
            mixin_instance.clean()

        assert "email" in str(exc_info.value)
        assert "phone" in str(exc_info.value)

    def test_valid_fields_passes(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_qs = MagicMock()
        mock_qs.values_list.return_value = ["first_name", "email"]
        mixin_instance.form_fields = mock_qs

        mixin_instance.clean()


class TestEnrollContact:
    def test_calls_client_with_correct_args(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_client = MagicMock()
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }

        with patch(
            "wagtail_dripdrop.mixins.get_client", return_value=mock_client
        ):
            mixin_instance._enroll_contact(data)

        mock_client.create_contact_and_enroll.assert_called_once_with(
            flow_uuid=mixin_instance.flow_uuid,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone=None,
        )

    def test_failure_does_not_raise(self, mixin_instance):
        mixin_instance.flow_uuid = uuid4()
        mock_client = MagicMock()
        mock_client.create_contact_and_enroll.side_effect = Exception("API down")

        with patch(
            "wagtail_dripdrop.mixins.get_client", return_value=mock_client
        ):
            # Should not raise
            mixin_instance._enroll_contact(
                {"first_name": "Jane", "email": "jane@example.com"}
            )

    def test_skipped_when_no_flow_uuid(self, mixin_instance):
        """Verify process_form_submission skips enrollment when flow_uuid is None."""
        mixin_instance.flow_uuid = None
        mock_form = MagicMock()
        mock_form.cleaned_data = {"first_name": "Jane"}

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
