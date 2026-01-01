# Refactoring Summary

This file summarizes the refactors made on branch `claude/remove-hardcoded-values-1zpoY`.

Changes
- Introduced `BaseParser` (`parse/base_parser.py`) and updated parsers to inherit it.
- Introduced `BaseSaver` (`storage/base_saver.py`) with `_execute()` to centralize DB access.
- Added `storage/db_client.py` as a connection shim and updated `storage/db_utils.py` to use it.
- Added `storage/repository.py` to wrap higher-level DB helpers for collectors.
- Refactored concrete savers to use `BaseSaver._execute()`:
  - `storage/github_saver.py`
  - `storage/baekjoon_saver.py`
  - `storage/ai_chat_saver.py`
- Canonicalized GitHub usernames to `GITHUB_USERNAMES` list while keeping `GITHUB_USERNAME` as compatibility alias.

Why
- Reduce duplicated DB connection/commit/close code and centralize error handling.
- Lower coupling between collectors/parsers/savers and the DB implementation.
- Provide standard parser/saver base classes for easier maintenance and extension.

Migration Notes
- Call sites that used `storage.db_utils` should prefer `storage.repository` or `BaseSaver` for DB access.
- `GITHUB_USERNAME` continues to work for backward compatibility; prefer `GITHUB_USERNAMES` going forward.

How to run tests
```
.venv\Scripts\python tests/run_all_tests.py
```

Status
- All tests passed locally: 47 tests (45 passed, 2 skipped).

Deprecation Notice
- `storage/db_utils.py` is now deprecated and delegates to `storage.repository`.
  - New code should import `storage.repository` or use `BaseSaver` for DB access.
  - `storage/db_utils` will be removed in a future breaking release; migrate callers accordingly.

CHANGELOG & PR
- A `docs/CHANGELOG.md` entry was added and a branch pushed. Consider opening a PR with this branch.
