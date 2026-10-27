# Project Documentation

- Models are documented in `piecework/models.py` and `docs/models.md`.
- Domain knowledge is maintained in `docs/domain.md`.

## Migration Policy

- Do not create, generate, edit, delete, or rename Django migration files unless the user explicitly requests migration work.
- Do not run `manage.py makemigrations` or any equivalent migration-generation command unless explicitly requested.
- Do not run `manage.py migrate` or otherwise apply database schema changes unless explicitly requested.
- When changing models, leave migration creation to the user and only mention that a migration may be required.
