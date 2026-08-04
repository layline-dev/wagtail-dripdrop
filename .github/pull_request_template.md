## What does this change?

<!-- A short description, and the issue it closes if there is one. -->

## Checklist

- [ ] Tests added or updated
- [ ] `pytest`, `ruff check .`, and `ruff format --check .` pass locally
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] If a form field mapping was added or changed, `MAPPABLE_CONTACT_FIELDS`
      and `DripDropClient.create_contact_and_enroll` are still in sync
- [ ] If the model changed, the upgrade note says whether users need to run
      `makemigrations`
