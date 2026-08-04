from __future__ import annotations

from unittest.mock import MagicMock, patch

from wagtail_dripdrop.panels import CustomFieldKeySelect, FlowSelect


def _definition(key, display_name, target_model):
    return MagicMock(key=key, display_name=display_name, target_model=target_model)


class TestFlowSelect:
    def test_builds_choices_from_cache(self):
        # ``name`` is reserved by MagicMock's constructor, so set it after.
        flow = MagicMock(uuid="aaa-111")
        flow.name = "Flow A"
        flows = [flow]

        with patch("wagtail_dripdrop.panels.get_cached_flows", return_value=flows):
            choices = FlowSelect._build_choices()

        assert choices == [("", "---------"), ("aaa-111", "Flow A")]

    def test_api_failure_degrades_to_empty_choice(self):
        with patch(
            "wagtail_dripdrop.panels.get_cached_flows",
            side_effect=ConnectionError("API down"),
        ):
            choices = FlowSelect._build_choices()

        assert choices == [("", "---------")]


class TestCustomFieldKeySelect:
    def test_groups_by_target_model(self):
        definitions = [
            _definition("source", "Lead Source", "contacts.contact"),
            _definition("session", "Session", "flows.flowenrollment"),
            _definition("company", "Company", "contacts.contact"),
        ]

        with patch(
            "wagtail_dripdrop.panels.get_cached_custom_fields",
            return_value=definitions,
        ):
            choices = CustomFieldKeySelect._build_choices()

        assert choices == [
            ("", "---------"),
            (
                "Contact custom fields",
                [("source", "Lead Source"), ("company", "Company")],
            ),
            ("Enrollment custom fields", [("session", "Session")]),
        ]

    def test_omits_empty_groups(self):
        definitions = [_definition("source", "Lead Source", "contacts.contact")]

        with patch(
            "wagtail_dripdrop.panels.get_cached_custom_fields",
            return_value=definitions,
        ):
            choices = CustomFieldKeySelect._build_choices()

        assert choices == [
            ("", "---------"),
            ("Contact custom fields", [("source", "Lead Source")]),
        ]

    def test_ignores_unknown_target_models(self):
        definitions = [_definition("x", "X", "something.else")]

        with patch(
            "wagtail_dripdrop.panels.get_cached_custom_fields",
            return_value=definitions,
        ):
            choices = CustomFieldKeySelect._build_choices()

        assert choices == [("", "---------")]

    def test_api_failure_degrades_to_empty_choice(self):
        with patch(
            "wagtail_dripdrop.panels.get_cached_custom_fields",
            side_effect=ConnectionError("API down"),
        ):
            choices = CustomFieldKeySelect._build_choices()

        assert choices == [("", "---------")]
