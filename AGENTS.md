# Project Documentation

- Models are documented in `piecework/models.py` and `docs/models.md`.
- Domain knowledge is maintained in `docs/domain.md`.

## Migration Policy

- Do not create, generate, edit, delete, or rename Django migration files unless the user explicitly requests migration work.
- Do not run `manage.py makemigrations` or any equivalent migration-generation command unless explicitly requested.
- Do not run `manage.py migrate` or otherwise apply database schema changes unless explicitly requested.
- When changing models, leave migration creation to the user and only mention that a migration may be required.

## Testing Policy

- Prioritize tests that verify functionality, business behavior, and resulting state changes.
- Test outcomes such as records being created, updated, or deleted; status changes; calculations; validation; request-method restrictions; and error handling.
- Do not add tests for presentation that can be checked visually, such as rendered text, template selection, layout, or basic form display, unless the user explicitly requests them.
- Do not test redirects or redirect destinations unless the user explicitly requests redirect coverage.
- When a request is needed only to trigger behavior, call the test client without storing the response and assert the resulting state instead.
