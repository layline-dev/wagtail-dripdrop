# Changelog

## 0.2.0

- `DripDropFormFieldMixin` for mapping form fields to DripDrop contact properties
- `DripDropFieldMappingPanels()` with custom field key select widget
- Contact field mapping choices derived from the DripDrop SDK model
- Custom field support via `custom_fields` parameter on `create_contact_and_enroll()`
- Custom field definition caching and validation against the DripDrop API
- `list_custom_fields()` client method with automatic pagination
- Cache refresh now includes both flows and custom field definitions
- Validation checks field mappings instead of field names

## 0.1.0

- DripDrop API client with automatic 409 conflict handling
- Flow list caching via Django cache framework
- `DripDropFormMixin` for Wagtail `AbstractForm` pages
- `FlowChooserPanel` with dynamic flow dropdown
- Wagtail admin menu item to refresh flow cache
- Validation: requires `first_name` and at least one of `email`/`phone` when a flow is selected
