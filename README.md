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

## Settings

| Setting | Required | Default | Description |
|---|---|---|---|
| `DRIPDROP_API_KEY` | Yes | — | Your DripDrop API key |
| `DRIPDROP_API_BASE_URL` | No | Production URL | Base URL for the DripDrop API |
| `DRIPDROP_FLOW_CACHE_TIMEOUT` | No | `3600` | Flow list cache timeout in seconds |

## Development

```bash
git clone https://github.com/layline-dev/wagtail-dripdrop.git
cd wagtail-dripdrop
pip install -e .[dev]
ruff check .
pytest
```
