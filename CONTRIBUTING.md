# Contributing

Thanks for your interest in `wagtail-dripdrop`. Issues and pull requests are
welcome.

## Getting set up

```bash
git clone https://github.com/layline-dev/wagtail-dripdrop.git
cd wagtail-dripdrop
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a pull request

```bash
pytest              # the full suite
ruff check .        # lint
ruff format .       # formatting
```

CI runs all three across the supported Python, Django, and Wagtail matrix (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)). If you are changing
anything version-sensitive, it is worth testing against the oldest supported
combination locally:

```bash
pip install "wagtail~=5.2.0" "django~=4.2.0"
pytest
```

## Guidelines

- **Add a test.** Every behavioural change should come with one. The suite runs
  without network access — the DripDrop API is always mocked.
- **Never break form submission.** Enrollment happens inside a form POST. Errors
  talking to DripDrop must be logged and swallowed, never raised, so that an API
  outage cannot cost a site its leads. `DripDropClient.create_contact_and_enroll`
  returns `True`/`False` rather than raising, and it must stay that way.
- **Validate at the right time.** Configuration problems belong in
  [`checks.py`](wagtail_dripdrop/checks.py) so `manage.py check` catches them at
  deploy; editor mistakes belong in `DripDropFormMixin.clean()` so they surface
  in the admin.
- **Field mappings are an allowlist.** `MAPPABLE_CONTACT_FIELDS` in
  [`mixins.py`](wagtail_dripdrop/mixins.py) must stay in sync with what
  `DripDropClient.create_contact_and_enroll` actually forwards. Adding a mapping
  to one without the other silently drops submitted data.
- **Update the changelog** under an `Unreleased` heading.

## Releasing

Maintainers only:

1. Update the version in `pyproject.toml` and move the `Unreleased` changelog
   section under the new version number with today's date.
2. Merge to `main`.
3. Publish a GitHub release tagged `vX.Y.Z`. The
   [publish workflow](.github/workflows/publish.yml) builds and uploads to PyPI
   via trusted publishing.

## Code of conduct

Be decent to each other. Report unacceptable behaviour to dev@layline.dev.
