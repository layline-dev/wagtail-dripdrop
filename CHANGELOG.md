# Changelog

## 0.1.0

- DripDrop API client with automatic 409 conflict handling
- Flow list caching via Django cache framework
- `DripDropFormMixin` for Wagtail `AbstractForm` pages
- `FlowChooserPanel` with dynamic flow dropdown
- Wagtail admin menu item to refresh flow cache
- Validation: requires `first_name` and at least one of `email`/`phone` when a flow is selected
