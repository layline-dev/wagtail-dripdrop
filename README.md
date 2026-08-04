# wagtail-dripdrop

[![PyPI](https://img.shields.io/pypi/v/wagtail-dripdrop.svg)](https://pypi.org/project/wagtail-dripdrop/)
[![Python versions](https://img.shields.io/pypi/pyversions/wagtail-dripdrop.svg)](https://pypi.org/project/wagtail-dripdrop/)
[![CI](https://github.com/layline-dev/wagtail-dripdrop/actions/workflows/ci.yml/badge.svg)](https://github.com/layline-dev/wagtail-dripdrop/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/wagtail-dripdrop.svg)](LICENSE)

Connect Wagtail form pages to [DripDrop](https://dripdrop.dev) flows. When a form is submitted, wagtail-dripdrop creates or enrolls a contact in the selected flow using the DripDrop public API.

Supports Python 3.10–3.13, Django 4.2–6.0, and Wagtail 5.2–7.x.

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
from django.db import models
from wagtail.contrib.forms.models import AbstractForm, AbstractFormField
from modelcluster.fields import ParentalKey

from wagtail_dripdrop import (
    DripDropFieldMappingPanels,
    DripDropFormFieldMixin,
    DripDropFormMixin,
    FlowChooserPanel,
)


class FormField(DripDropFormFieldMixin, AbstractFormField):
    page = ParentalKey(
        "ContactPage", related_name="form_fields", on_delete=models.CASCADE
    )
    panels = AbstractFormField.panels + DripDropFieldMappingPanels()


class ContactPage(DripDropFormMixin, AbstractForm):
    content_panels = AbstractForm.content_panels + [FlowChooserPanel()]
```

### Field mapping

Each form field can be mapped to a DripDrop contact property via the **DripDrop mapping** dropdown in the Wagtail admin. The available contact mappings are First Name, Last Name, Email, and Phone.

Two mappings target custom fields, each backed by a different DripDrop target model:

| Mapping | Target model | Sent as |
|---|---|---|
| **Custom Field** | `contacts.contact` | `custom_fields` — values stored on the contact |
| **Enrollment Custom Field** | `flows.flowenrollment` | `enrollment_custom_fields` — values stored on the enrollment this submission creates |

Selecting either one reveals the **DripDrop custom field key** dropdown, which lists both sets of definitions grouped by target model. Keys are validated against the DripDrop API on save: the key must exist *and* belong to the target model implied by the mapping. Because the two are separate namespaces, the same key may legitimately exist on both.

Use **Enrollment Custom Field** for answers that describe this particular signup (a requested session, a referral code for this campaign) rather than the person — a repeat submitter gets one contact but a distinct value per enrollment.

When a flow is selected, the form requires:

- At least one field mapped to **First Name**
- At least one field mapped to **Email** or **Phone**

Each contact field, and each custom field key, may only be mapped once per form.

On submission, the contact is created and enrolled in the selected flow. Behaviour when the submission matches an existing contact is controlled by `DRIPDROP_ON_DUPLICATE_CONTACT` (see below).

### Duplicate contacts

By default DripDrop returns a 409 when a submission matches an existing contact under your account's dedupe strategy. wagtail-dripdrop then enrolls that matched contact via the enrollments endpoint, carrying any enrollment custom fields across.

Set `DRIPDROP_ON_DUPLICATE_CONTACT = "create_new"` to instead send `on_match="create"`, which tells DripDrop to create a second contact rather than matching. Use this only if your account genuinely wants duplicate contact records.

## Cache

Flow and custom field choices are cached using Django's cache framework. The cache refreshes automatically on a miss. You can inspect the cached flows and custom fields, or refresh both caches manually, from **Settings → DripDrop cache** in the Wagtail admin.

## Settings

| Setting | Required | Default | Description |
|---|---|---|---|
| `DRIPDROP_API_KEY` | Yes | — | Your DripDrop API key |
| `DRIPDROP_API_BASE_URL` | No | `https://api.dripdrop.dev` | Base URL for the DripDrop API |
| `DRIPDROP_FLOW_CACHE_TIMEOUT` | No | `3600` | Flow list cache timeout in seconds |
| `DRIPDROP_CUSTOM_FIELD_CACHE_TIMEOUT` | No | `3600` | Custom field list cache timeout in seconds |
| `DRIPDROP_ON_DUPLICATE_CONTACT` | No | `"enroll_existing"` | `"enroll_existing"` enrolls the matched contact; `"create_new"` sends `on_match="create"` |

`DRIPDROP_ON_DUPLICATE_CONTACT` is validated by Django's system check framework, so an invalid value fails `manage.py check` (`wagtail_dripdrop.E001`) rather than surfacing at the first form submission.

## Submitted values

Enrollment happens inside the form POST, and any error talking to DripDrop is logged and swallowed so that an API outage cannot break your form or lose the Wagtail-side submission record.

Values sent as custom fields are coerced to JSON-safe types first: dates and times become ISO 8601 strings, and multiple-choice answers are joined into a comma-separated string.

## Development

```bash
git clone https://github.com/layline-dev/wagtail-dripdrop.git
cd wagtail-dripdrop
pip install -e .[dev]
ruff check .
ruff format --check .
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and
[SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

Apache 2.0
