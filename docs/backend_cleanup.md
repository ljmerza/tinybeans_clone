# Backend Cleanup Opportunities

This note captures backend cleanups that surfaced during a quick sweep. Each item links to the file or line that needs attention and a suggested next step.

## High Priority
- ~~`mysite/keeps/tasks.py:126` — `generate_image_sizes` saves the thumbnail twice and discards the first key while leaving `thumbnail_key`/`gallery_key` unused. Capture the return value from a single `storage.save` call (or pass the derived key explicitly) so we do not upload duplicate objects or leak temp names.~~
- ~~`mysite/keeps/tasks.py:203` — `cleanup_failed_uploads` logs `failed_uploads.count()` after deleting records, so the log always reports `0`. Record the queryset count before the loop (or increment a counter) to reflect how many rows were actually removed.~~
- ~~`mysite/auth/services/trusted_device_service.py:145` — Email notifications on trusted-device registration swallow all exceptions with a bare `except` and no logging. Log the exception (or narrow the exception type) so operations teams can diagnose email delivery failures.~~

## Medium Priority
- ~~`mysite/users/models/__init__.py:16` — The redundant `generate_unique_slug = generate_unique_slug` assignment and duplicated entry in `__all__` can be removed to avoid linter noise and confusion over legacy aliases.~~
- ~~`mysite/keeps/tasks.py:3` — Drop the unused `tempfile` import; it has been obsolete since the task stopped using temp files directly.~~
- ~~`mysite/users/tests/test_serializers.py:3` & `:525` — Remove the unused `authenticate` import and the leftover debug `print`, otherwise pytest output becomes noisy when the test fails.~~

## Low Priority
- `mysite/keeps/views.py:1` and `mysite/messaging/views.py:1` — Delete the stub view modules that only import `render`; the real views live in the package modules, and these placeholders invite accidental imports.
- `mysite/keeps/tasks.py:232` — The TODOs for video validation, virus scanning, and content analysis are still open; consider breaking them into follow-up tickets if they remain in scope.
