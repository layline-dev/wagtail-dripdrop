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

from wagtail_dripdrop import DripDropFormMixin, FlowChooserPanel


class FormField(AbstractFormField):
    page = ParentalKey("ContactPage", related_name="form_fields", on_delete=models.CASCADE)


class ContactPage(DripDropFormMixin, AbstractForm):
    content_panels = AbstractForm.content_panels + [FlowChooserPanel()]
```

When editing the page in Wagtail admin, select a DripDrop flow from the dropdown. The form requires a `first_name` field and at least one of `email` or `phone` to be present when a flow is selected.

On submission, the contact is created and enrolled in the selected flow. If the contact already exists (409 response), they are automatically enrolled via the enrollments endpoint.

## Cache

Flow choices are cached using Django's cache framework. The cache refreshes automatically on miss, or you can manually refresh it from the Wagtail admin menu ("Refresh DripDrop Cache").

## Settings

| Setting | Required | Default | Description |
|---|---|---|---|
| `DRIPDROP_API_KEY` | Yes | — | Your DripDrop API key |
| `DRIPDROP_API_BASE_URL` | No | `https://api.dripdrop.dev` | Base URL for the DripDrop API |
| `DRIPDROP_FLOW_CACHE_TIMEOUT` | No | `3600` | Flow list cache timeout in seconds |

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
