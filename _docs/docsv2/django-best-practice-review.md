## Django 5.2 Best Practices Review

### Scope
- Reviewed `mysite/config/settings`, `mysite/auth`, and `mysite/keeps` for alignment with current Django (5.2.x) conventions.
- Focused on security, configuration hygiene, and DRF usage that materially affect production behaviour.

### Recommended Improvements

1. **Adopt the `STORAGES` API and define explicit static/media roots**  
   - `mysite/config/settings/base.py` still relies on the legacy `DEFAULT_FILE_STORAGE` toggle (`mysite/config/settings/base.py:215-219`) and does not declare `STATIC_ROOT`/`MEDIA_ROOT`.  
   - Move to the Django 4.2+ `STORAGES` structure (while keeping `DEFAULT_FILE_STORAGE` temporarily for third-party compatibility) and add something like:
     ```python
     STORAGES = {
         "default": {
             "BACKEND": "django.core.files.storage.FileSystemStorage",
         },
         "staticfiles": {
             "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
         },
     }
     STATIC_URL = "static/"
     STATIC_ROOT = BASE_DIR / "staticfiles"
     MEDIA_ROOT = BASE_DIR / "media"
     ```
   - This unlocks Django’s newer storage pipeline, avoids `collectstatic` failures in CI/CD, and lets infrastructure know where build artefacts land.

2. **Enable consistent API pagination and developer-friendly renderers**  
   - REST framework settings omit `DEFAULT_PAGINATION_CLASS` and serve only `JSONRenderer` globally (`mysite/config/settings/base.py:237-257`). Large list endpoints such as keeps will return unbounded payloads, and the browsable API is unavailable even in `DEBUG`.  
   - Define pagination (for example `rest_framework.pagination.LimitOffsetPagination` with a sane `PAGE_SIZE`) and append `BrowsableAPIRenderer` conditionally when `DEBUG` is true to match DRF guidance.

3. **Fix DRF filter backends so search/order params actually work**  
   - `KeepListCreateView` advertises `search` and ordering support but registers only `DjangoFilterBackend` (`mysite/keeps/views/keeps.py:22-27`). Because `SearchFilter` and `OrderingFilter` are missing, requests silently ignore those query parameters.  
   - Update `filter_backends` to include `rest_framework.filters.SearchFilter` and `rest_framework.filters.OrderingFilter`.

4. **Restore machine-readable error codes for keep lookups**  
   - The keep convenience endpoints call `error_response` without the required `error` argument (`mysite/keeps/views/keeps.py:338-341` and `mysite/keeps/views/keeps.py:385-387`). In production this raises a `TypeError`, returning HTTP 500 instead of a user-friendly 4xx with translated messaging.  
   - Supply the code, e.g. `error_response('circle_not_found', [...])`, to ensure predictable API failures.

5. **Align refresh-token cookies with modern browser rules**  
   - `set_refresh_cookie` currently forces `SameSite='Strict'` whenever HTTPS is enabled (`mysite/auth/token_utils.py:124-131`). With a separate SPA origin this prevents refresh calls from sending the cookie, breaking silent auth flows on Chrome/Safari.  
   - Switch to `SameSite='None'` (with `secure=True`) when issuing cross-site cookies, keeping `Lax` for local debug builds.

6. **Remove the tracked SQLite database artefact**  
   - `mysite/db.sqlite3` is committed even though `.gitignore` excludes it. Keeping mutable databases under version control complicates migrations and can leak development data.  
   - Delete the file from Git history and rely on Postgres (or ephemeral SQLite via `USE_SQLITE_FALLBACK`) during development.

7. **Drop unused plaintext token column**  
   - `MagicLoginToken` still defines a `token` field (`mysite/auth/models.py:324-333`) that defaults to an empty string; only `token_hash` is read in the codebase. Removing the redundant column avoids accidental storage of unhashed secrets and simplifies the admin.

### Next Steps Checklist
- [ ] Update settings module with `STORAGES`, `STATIC_ROOT`, `MEDIA_ROOT`, and DRF pagination/renderers.
- [ ] Patch keep views to wire up filters and corrected `error_response` usage; add regression tests for the bug.
- [ ] Adjust refresh-token cookie policy and confirm SPA auth works across environments.
- [ ] Purge `mysite/db.sqlite3` from the repository and ensure developers recreate local databases via migrations.
- [ ] Generate a schema migration dropping `MagicLoginToken.token` (after confirming no data dependence).
