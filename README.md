# wagtail-dripdrop

Connect Wagtail form pages to [DripDrop](https://dripdrop.dev) flows. When a form is submitted, wagtail-dripdrop creates or enrolls a contact in the selected flow using the DripDrop public API.

## Installation

```bash
pip install wagtail-dripdrop
```

Add to your Django settings:

```python
INSTALLED_APPS = [
    # ...
    "wagtail_dripdrop",
    # ...
]
```

Configure your DripDrop API key:

```python
DRIPDROP_API_KEY = "your-api-key"
```

## Usage

Create a form page that enrolls submissions into a DripDrop flow:

```python
from wagtail.contrib.forms.models import AbstractForm, AbstractFormField
from modelcluster.fields import ParentalKey

from wagtail_dripdrop import (
    DripDropFieldMappingPanels,
    DripDropFormFieldMixin,
    DripDropFormMixin,
    FlowChooserPanel,
)


class FormField(DripDropFormFieldMixin, AbstractFormField):
    page = ParentalKey("ContactPage", related_name="form_fields", on_delete=models.CASCADE)
    panels = AbstractFormField.panels + DripDropFieldMappingPanels()


class ContactPage(DripDropFormMixin, AbstractForm):
    content_panels = AbstractForm.content_panels + [FlowChooserPanel()]
```

### Field mapping

Each form field can be mapped to a DripDrop contact property via the **DripDrop mapping** dropdown in the Wagtail admin. The available contact mappings (First Name, Last Name, Email, Phone) are derived from the DripDrop SDK.

Selecting **Custom Field** maps the form field to a DripDrop custom field. A second dropdown appears to select the custom field key. Custom field keys are validated against the DripDrop API on save — if a key does not exist, a validation error is raised.

When a flow is selected, the form requires:

- At least one field mapped to **First Name**
- At least one field mapped to **Email** or **Phone**

On submission, the contact is created and enrolled in the selected flow. If the contact already exists (409 response), they are automatically enrolled via the enrollments endpoint.

## Cache

Flow and custom field choices are cached using Django's cache framework. The cache refreshes automatically on a miss, or you can manually refresh it from the Wagtail admin menu ("Refresh DripDrop Cache").

## Settings

| Setting | Required | Default | Description |
|---|---|---|---|
| `DRIPDROP_API_KEY` | Yes | — | Your DripDrop API key |
| `DRIPDROP_API_BASE_URL` | No | `https://api.dripdrop.dev` | Base URL for the DripDrop API |
| `DRIPDROP_FLOW_CACHE_TIMEOUT` | No | `3600` | Flow list cache timeout in seconds |
| `DRIPDROP_CUSTOM_FIELD_CACHE_TIMEOUT` | No | `3600` | Custom field list cache timeout in seconds |

## Development

```bash
git clone https://github.com/layline-dev/wagtail-dripdrop.git
cd wagtail-dripdrop
pip install -e .[dev]
ruff check .
pytest
```

## License

Apache 2.0
