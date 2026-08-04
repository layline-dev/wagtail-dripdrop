from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import dripdrop
import pytest

from wagtail_dripdrop.client import DripDropClient


@pytest.fixture()
def client():
    return DripDropClient(api_key="test-key", base_url="https://test.example.com")


class TestListFlows:
    def test_returns_all_flows_single_page(self, client):
        flow = MagicMock(spec=dripdrop.PublicFlow)
        paginated = MagicMock(results=[flow], next=None)

        with patch.object(dripdrop.FlowsApi, "list", return_value=paginated):
            result = client.list_flows()

        assert result == [flow]

    def test_paginates_through_multiple_pages(self, client):
        flow_a = MagicMock(spec=dripdrop.PublicFlow)
        flow_b = MagicMock(spec=dripdrop.PublicFlow)
        page1 = MagicMock(results=[flow_a], next="http://next")
        page2 = MagicMock(results=[flow_b], next=None)

        with patch.object(dripdrop.FlowsApi, "list", side_effect=[page1, page2]):
            result = client.list_flows()

        assert result == [flow_a, flow_b]


class TestListCustomFields:
    def test_returns_all_fields_single_page(self, client):
        field = MagicMock(spec=dripdrop.CustomFieldDefinition)
        paginated = MagicMock(results=[field], next=None)

        with patch.object(dripdrop.CustomFieldsApi, "list", return_value=paginated):
            result = client.list_custom_fields()

        assert result == [field]

    def test_paginates_through_multiple_pages(self, client):
        field_a = MagicMock(spec=dripdrop.CustomFieldDefinition)
        field_b = MagicMock(spec=dripdrop.CustomFieldDefinition)
        page1 = MagicMock(results=[field_a], next="http://next")
        page2 = MagicMock(results=[field_b], next=None)

        with patch.object(dripdrop.CustomFieldsApi, "list", side_effect=[page1, page2]):
            result = client.list_custom_fields()

        assert result == [field_a, field_b]


class TestCreateContactAndEnroll:
    def test_success(self, client):
        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is True
        mock_create.assert_called_once()

    def test_passes_custom_fields(self, client):
        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
                custom_fields={"source": "web"},
            )

        data = mock_create.call_args[0][1]
        assert data.custom_fields == {"source": "web"}

    def test_passes_enrollment_custom_fields(self, client):
        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
                custom_fields={"source": "web"},
                enrollment_custom_fields={"requested_session": "Morning"},
            )

        data = mock_create.call_args[0][1]
        assert data.custom_fields == {"source": "web"}
        assert data.enrollment_custom_fields == {"requested_session": "Morning"}

    def test_omits_on_match_by_default(self, client):
        """An explicit ``on_match=None`` is serialised into the request body as
        a null, so the default path must not set the field at all."""
        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        data = mock_create.call_args[0][1]
        assert data.on_match is None
        assert "on_match" not in data.to_dict()

    def test_create_new_sends_on_match(self, client, settings):
        settings.DRIPDROP_ON_DUPLICATE_CONTACT = "create_new"

        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert mock_create.call_args[0][1].on_match == dripdrop.OnMatchEnum.CREATE

    def test_invalid_on_duplicate_setting_is_contained(self, client, settings):
        """``create_contact_and_enroll`` promises never to raise, so a bad
        setting must not escape into form processing. The system check in
        ``wagtail_dripdrop.checks`` is what surfaces it, at deploy time."""
        settings.DRIPDROP_ON_DUPLICATE_CONTACT = "nonsense"

        with patch.object(
            dripdrop.FlowsApi, "create_contact_and_enroll_create"
        ) as mock_create:
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is False
        mock_create.assert_not_called()

    @pytest.mark.parametrize("contact_payload", ["uuid", "object"])
    def test_409_retries_enrollment(self, client, contact_payload):
        flow_uuid = uuid4()
        contact_uuid = str(uuid4())
        contact = (
            contact_uuid
            if contact_payload == "uuid"
            else {"uuid": contact_uuid, "email": "existing@example.com"}
        )

        conflict_exc = dripdrop.ApiException(
            status=409,
            body=json.dumps({"contact": contact}),
        )

        with (
            patch.object(
                dripdrop.FlowsApi,
                "create_contact_and_enroll_create",
                side_effect=conflict_exc,
            ),
            patch.object(dripdrop.EnrollmentsApi, "create") as mock_enroll,
        ):
            result = client.create_contact_and_enroll(
                flow_uuid=flow_uuid,
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is True
        mock_enroll.assert_called_once()
        enrollment = mock_enroll.call_args[0][0]
        assert str(enrollment.contact_uuid) == contact_uuid

    def test_409_missing_contact_uuid_returns_false(self, client):
        conflict_exc = dripdrop.ApiException(
            status=409, body=json.dumps({"contact": {"email": "existing@example.com"}})
        )

        with patch.object(
            dripdrop.FlowsApi,
            "create_contact_and_enroll_create",
            side_effect=conflict_exc,
        ):
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is False

    def test_409_retry_carries_enrollment_custom_fields(self, client):
        conflict_exc = dripdrop.ApiException(
            status=409,
            body=json.dumps({"contact": str(uuid4())}),
        )

        with (
            patch.object(
                dripdrop.FlowsApi,
                "create_contact_and_enroll_create",
                side_effect=conflict_exc,
            ),
            patch.object(dripdrop.EnrollmentsApi, "create") as mock_enroll,
        ):
            client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
                enrollment_custom_fields={"requested_session": "Morning"},
            )

        enrollment = mock_enroll.call_args[0][0]
        assert enrollment.custom_fields == {"requested_session": "Morning"}

    def test_409_bad_body_returns_false(self, client):
        conflict_exc = dripdrop.ApiException(status=409, body="not json")

        with patch.object(
            dripdrop.FlowsApi,
            "create_contact_and_enroll_create",
            side_effect=conflict_exc,
        ):
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is False

    def test_non_409_api_error_returns_false(self, client):
        exc = dripdrop.ApiException(status=500, reason="Server Error")

        with patch.object(
            dripdrop.FlowsApi,
            "create_contact_and_enroll_create",
            side_effect=exc,
        ):
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is False

    def test_unexpected_exception_returns_false(self, client):
        with patch.object(
            dripdrop.FlowsApi,
            "create_contact_and_enroll_create",
            side_effect=ConnectionError("timeout"),
        ):
            result = client.create_contact_and_enroll(
                flow_uuid=uuid4(),
                first_name="Jane",
                email="jane@example.com",
            )

        assert result is False
