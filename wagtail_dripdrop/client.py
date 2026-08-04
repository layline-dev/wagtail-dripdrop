from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

import dripdrop

from wagtail_dripdrop.settings import (
    CREATE_NEW,
    get_api_base_url,
    get_api_key,
    get_on_duplicate_contact,
)

if TYPE_CHECKING:
    from dripdrop import CustomFieldDefinition, PublicFlow

logger = logging.getLogger(__name__)


class DripDropClient:
    """Wrapper around the dripdrop SDK that handles configuration,
    pagination, 409-conflict retry, and error logging."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._configuration = dripdrop.Configuration(
            host=base_url or get_api_base_url(),
            api_key={"ApiKeyAuth": api_key or get_api_key()},
        )

    def list_flows(self) -> list[PublicFlow]:
        """Return every flow for the account, handling pagination."""
        return self._paginate(dripdrop.FlowsApi)

    def list_custom_fields(self) -> list[CustomFieldDefinition]:
        """Return every custom field definition, handling pagination."""
        return self._paginate(dripdrop.CustomFieldsApi)

    def _paginate(self, api_class: type) -> list:
        with dripdrop.ApiClient(self._configuration) as api_client:
            api = api_class(api_client)
            results = []
            page = 1
            while True:
                response = api.list(page=page)
                results.extend(response.results)
                if response.next is None:
                    break
                page += 1
            return results

    def create_contact_and_enroll(
        self,
        flow_uuid: UUID | str,
        *,
        first_name: str,
        last_name: str = "",
        email: str | None = None,
        phone: str | None = None,
        custom_fields: dict[str, Any] | None = None,
        enrollment_custom_fields: dict[str, Any] | None = None,
    ) -> bool:
        """Create a contact and enroll them in a flow.

        ``custom_fields`` targets the contact; ``enrollment_custom_fields``
        targets the enrollment this call creates.

        When a contact already matches the account's dedupe strategy the
        behaviour depends on ``DRIPDROP_ON_DUPLICATE_CONTACT``: the default
        enrolls the matched contact, while ``create_new`` asks DripDrop to
        create a second contact via ``on_match``.

        Returns True on success, False on failure. Errors are logged but
        never raised so that form processing is not disrupted.
        """
        flow_uuid = UUID(str(flow_uuid))
        try:
            fields: dict[str, Any] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "custom_fields": custom_fields,
                "enrollment_custom_fields": enrollment_custom_fields,
            }
            # Only send on_match when opting out of the default matching
            # behaviour: an explicit null is serialised into the request body,
            # and the default path should look exactly as it did before the
            # setting existed.
            if get_on_duplicate_contact() == CREATE_NEW:
                fields["on_match"] = dripdrop.OnMatchEnum.CREATE

            with dripdrop.ApiClient(self._configuration) as api_client:
                data = dripdrop.CreateContactAndEnroll(**fields)
                dripdrop.FlowsApi(api_client).create_contact_and_enroll_create(
                    flow_uuid, data
                )
            return True
        except dripdrop.ApiException as exc:
            if exc.status == 409:
                return self._enroll_existing_contact(
                    flow_uuid, exc, enrollment_custom_fields
                )
            logger.error("DripDrop API error (%s): %s", exc.status, exc.reason)
            return False
        except Exception:
            logger.exception("Unexpected error calling DripDrop API")
            return False

    def _enroll_existing_contact(
        self,
        flow_uuid: UUID,
        exc: dripdrop.ApiException,
        enrollment_custom_fields: dict[str, Any] | None = None,
    ) -> bool:
        try:
            body = json.loads(exc.body)
            contact = body["contact"]
            contact_uuid = contact.get("uuid") if isinstance(contact, dict) else contact
            if not contact_uuid:
                raise KeyError("contact.uuid")
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.error(
                "Could not extract contact UUID from 409 response: %s", exc.body
            )
            return False

        try:
            with dripdrop.ApiClient(self._configuration) as api_client:
                enrollment = dripdrop.PublicFlowEnrollment.model_construct(
                    flow_uuid=flow_uuid,
                    contact_uuid=contact_uuid,
                    custom_fields=enrollment_custom_fields,
                )
                dripdrop.EnrollmentsApi(api_client).create(enrollment)
            return True
        except Exception:
            logger.exception(
                "Failed to enroll existing contact %s in flow %s",
                contact_uuid,
                flow_uuid,
            )
            return False


def get_client(
    api_key: str | None = None, base_url: str | None = None
) -> DripDropClient:
    return DripDropClient(api_key=api_key, base_url=base_url)
