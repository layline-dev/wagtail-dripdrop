# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-08-04

Requires `dripdrop>=0.1.1`.

**Supported versions:** Python 3.10–3.13, Django 4.2–6.0, Wagtail 5.2–7.x, each covered by CI. The minimum supported Wagtail is now 5.2 (previously an untested `>=5.0`); Wagtail 5.0 and 5.1 are end-of-life.

- **Fixed:** `enrollment_custom_fields` and `on_match`, added to `CreateContactAndEnroll` in dripdrop 0.1.1, leaked into the **DripDrop mapping** dropdown as selectable choices. Mapping choices are now an explicit allowlist of the fields the client actually forwards, so a future SDK release cannot reintroduce the problem
- **Fixed:** a field mapped to a custom mapping with no key selected was sent as a contact property named `custom`; it is now skipped
- **Fixed:** custom field values that Wagtail's form builder produces as non-JSON types — `datetime` from date fields, lists from checkbox and multi-select fields — failed to serialise and silently lost the whole submission. Values are now coerced: dates and times to ISO 8601, multiple choices to a comma-separated string
- **Fixed:** `on_match` was serialised as an explicit `null` on every request under the default setting. It is now omitted unless `create_new` is configured, leaving the default request body unchanged from 0.2.1
- Enrollment custom field support: new **Enrollment Custom Field** mapping targeting `flows.flowenrollment`, sent as `enrollment_custom_fields`
- Custom field key dropdown now lists contact and enrollment definitions grouped by target model
- Custom field keys are validated against the target model implied by their mapping, not against `contacts.contact` alone
- Validation rejects mapping two form fields to the same custom field key
- `DRIPDROP_ON_DUPLICATE_CONTACT` setting selects between enrolling a matched contact (default, unchanged) and `on_match="create"`. It is validated by Django's system check framework (`wagtail_dripdrop.E001`), so a bad value fails `manage.py check` at deploy rather than dropping enrollments at runtime
- The 409 enroll-existing path now carries enrollment custom fields through to the enrollment
- **Fixed:** the **DripDrop cache** settings menu item used `icon_name="refresh"`, which is not a Wagtail icon, so no icon rendered. A DripDrop icon is now registered via `register_icons` and used instead

Upgrading: `dripdrop_mapping` gains a choice, so run `makemigrations` in your project to pick up the new choices on your `AbstractFormField` subclass. No data migration is needed — existing `custom` mappings keep their contact-scoped meaning.

## [0.2.1] - 2026-07-15

- Fix existing-contact enrollment when the DripDrop API returns a full contact object in the 409 conflict response
- Add a Wagtail Settings → DripDrop cache page showing cached flows and custom fields
- Move manual cache refresh out of the main admin nav and into the DripDrop cache settings page

## [0.2.0] - 2026-03-21

- `DripDropFormFieldMixin` for mapping form fields to DripDrop contact properties
- `DripDropFieldMappingPanels()` with custom field key select widget
- Contact field mapping choices derived from the DripDrop SDK model
- Custom field support via `custom_fields` parameter on `create_contact_and_enroll()`
- Custom field definition caching and validation against the DripDrop API
- `list_custom_fields()` client method with automatic pagination
- Cache refresh now includes both flows and custom field definitions
- Validation checks field mappings instead of field names

## [0.1.0] - 2026-03-20

- DripDrop API client with automatic 409 conflict handling
- Flow list caching via Django cache framework
- `DripDropFormMixin` for Wagtail `AbstractForm` pages
- `FlowChooserPanel` with dynamic flow dropdown
- Wagtail admin menu item to refresh flow cache
- Validation: requires `first_name` and at least one of `email`/`phone` when a flow is selected

[Unreleased]: https://github.com/layline-dev/wagtail-dripdrop/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/layline-dev/wagtail-dripdrop/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/layline-dev/wagtail-dripdrop/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/layline-dev/wagtail-dripdrop/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/layline-dev/wagtail-dripdrop/releases/tag/v0.1.0
