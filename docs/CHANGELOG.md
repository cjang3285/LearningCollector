# Changelog

## Unreleased

- Refactor: centralize DB access behind `storage.db_client` + `BaseSaver._execute`.
- Add `BaseParser` and update parsers to inherit it.
- Refactor savers to use `BaseSaver._execute`.
- Add `storage/repository.py` as DB helper shim; deprecate `storage/db_utils.py`.
- Canonicalize `GITHUB_USERNAMES` configuration; keep `GITHUB_USERNAME` as alias.
- Add `docs/REFACTORING.md` describing the changes.

