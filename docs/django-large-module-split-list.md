## Large Django Module Split Candidates

### Purpose
- Highlight Django modules/tests that have grown past ~390 lines and now mix multiple responsibilities.
- Give direction for where to split or refactor so future changes stay reviewable and merge-friendly.

### Selection Criteria
- Source files under `mysite/` that exceeded ~390 lines per `wc -l`.
- Priority ordering is by size (largest first) because conflicts and review pain scale with line count.
- Suggestions favor splitting along feature boundaries or extracting helpers into `services.py`.

### Candidates

| File | Lines | Why It Feels Overgrown | Suggested Refactor |
| --- | --- | --- | --- |
| ~~`mysite/auth/views/two_factor.py`~~ | ~~851~~ | ~~Completed: split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (all re-exported from `views/two_factor/__init__.py`).~~ | ~~Completed: split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (all re-exported from `views/two_factor/__init__.py`).~~ |
| ~~`mysite/auth/tests/test_2fa_api.py`~~ | ~~744~~ | ~~One monolithic test module covering every 2FA API permutation with sprawling fixtures.~~ | ~~Completed: replaced with `test_2fa_setup_api.py`, `test_2fa_management_api.py`, `test_2fa_recovery_api.py`, and `test_trusted_devices_api.py` plus a shared helper.~~ |
| ~~`mysite/auth/tests/test_2fa_services.py`~~ | ~~715~~ | ~~Completed: split into `test_otp_service.py`, `test_totp_service.py`, `test_recovery_code_service.py`, `test_trusted_device_service.py`, and `test_rate_limiting_service.py` with shared helpers in `conftest.py`.~~ | ~~Completed: split into `test_otp_service.py`, `test_totp_service.py`, `test_recovery_code_service.py`, `test_trusted_device_service.py`, and `test_rate_limiting_service.py` with shared helpers in `conftest.py`.~~ |
| ~~`mysite/users/tests/test_serializers.py`~~ | ~~580~~ | ~~Completed: split auth serializers to `auth/tests/test_auth_serializers.py` and user serializers to `test_user_serializers.py`, `test_circle_serializers.py`, and `test_child_profile_serializers.py`.~~ | ~~Completed: split auth serializers to `auth/tests/test_auth_serializers.py` and user serializers to `test_user_serializers.py`, `test_circle_serializers.py`, and `test_child_profile_serializers.py`.~~ |
| ~~`mysite/config/settings/base.py`~~ | ~~567~~ | ~~Completed: Core settings file was mixing auth, storage, Celery, DRF, and feature toggles, making merges noisy.~~ | ~~Completed: Extracted thematic settings modules (`settings/auth.py`, `settings/drf.py`, `settings/security.py`, `settings/storage.py`, `settings/celery.py`, `settings/cache.py`, `settings/email.py`) and imported them in `base.py`.~~ |
| ~~`mysite/users/tests/test_edge_cases.py`~~ | ~~521~~ | ~~Completed: Was acting as a dumping ground for diverse edge scenarios across multiple domains.~~ | ~~Completed: Relocated tests to feature-specific modules: `auth/tests/test_auth_edge_cases.py`, `circles/tests/test_circle_edge_cases.py`, `users/tests/test_child_profile_edge_cases.py`, `users/tests/test_notification_preferences.py`, and `users/tests/test_permission_edge_cases.py`.~~ |
| ~~`mysite/circles/views/invitations.py`~~ | ~~520~~ | ~~Completed: Was handling admin flows (create, cancel, resend) and invitee flows (respond, accept, finalize) in one module.~~ | ~~Completed: Split into `views/invitations/admin.py` (admin actions), `views/invitations/invitee.py` (user actions), and extracted shared logic to `services/invitation_service.py`. All views re-exported from `views/invitations/__init__.py` for backward compatibility.~~ |
| ~~`mysite/users/tests/test_invitation_roles.py`~~ | ~~508~~ | ~~Completed: Was a comprehensive test file covering serializers, admin permissions, and workflows in one place.~~ | ~~Completed: Split into `circles/tests/test_invitation_serializers.py` (validation logic), `circles/tests/test_invitation_admin_permissions.py` (admin CRUD operations), `circles/tests/test_invitation_workflow.py` (end-to-end flows), with shared fixtures in `circles/tests/conftest.py`. Also relocated from users/tests to circles/tests for better co-location.~~ |
| ~~`mysite/auth/services/google_oauth_service.py`~~ | ~~485~~ | ~~Completed: Service mixed PKCE state, token exchange, profile sync, and account linking concerns.~~ | ~~Completed: Extracted sub-services (`oauth/pkce_state_service.py`, `oauth/google_api_service.py`, `oauth/account_linking_service.py`) with main service reduced to 226 lines focused on orchestration.~~ |
| `mysite/auth/views/google.py` | 462 | Initiate, callback, error handling, and linking endpoints coexist, spreading shared helpers everywhere. | Move initiate/callback/link/unlink views into dedicated modules and reuse a `google_oauth/helpers.py`. |
| `mysite/auth/tests/test_2fa_login.py` | 444 | Combines happy-path login, lockouts, rate limits, and trusted-device flows. | Split into login success vs. lockout/rate-limit vs. trusted-device modules so regressions point to the right area. |
| `mysite/auth/tests/test_oauth_service.py` | 420 | Tests cover multiple providers and operations in one file, obscuring failures. | Separate per provider (Google, magic link) or per operation (initiate/callback/link) and dedupe fixtures. |
| `mysite/keeps/views/keeps.py` | 407 | Contains CRUD endpoints plus async upload orchestration and status polling. | Promote uploads/status endpoints into `views/uploads.py` and keep core CRUD logic in `views/keeps.py` or DRF viewsets. |
| `mysite/auth/views/account.py` | 392 | Profile, security, device, and notification settings are combined, complicating edits. | Break into `profile.py`, `security.py`, and `devices.py` modules while consolidating shared serializers/services. |

### Next Actions
- Pick the next production module (e.g., `mysite/circles/views/invitations.py`) and draft a concrete split plan plus ownership.
- After each refactor, add smoke tests (or reorganize existing ones) to confirm module boundaries stayed intact.

### Refactor Progress
- [x] `mysite/auth/views/two_factor.py` split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (re-exported via `mysite/auth/views/two_factor/__init__.py`).
- [x] `mysite/auth/tests/test_2fa_api.py` replaced with targeted modules per flow (`test_2fa_setup_api.py`, `test_2fa_management_api.py`, `test_2fa_recovery_api.py`, `test_trusted_devices_api.py`) plus `tests/helpers.py`.
- [x] `mysite/auth/tests/test_2fa_services.py` split into `test_otp_service.py`, `test_totp_service.py`, `test_recovery_code_service.py`, `test_trusted_device_service.py`, and `test_rate_limiting_service.py` with shared helpers in `conftest.py`.
- [x] `mysite/users/tests/test_serializers.py` split auth serializers to `auth/tests/test_auth_serializers.py` and user serializers to `test_user_serializers.py`, `test_circle_serializers.py`, and `test_child_profile_serializers.py`.
- [x] `mysite/config/settings/base.py` split into thematic modules (`auth.py`, `drf.py`, `security.py`, `storage.py`, `celery.py`, `cache.py`, `email.py`) with `base.py` importing from all modules.
- [x] `mysite/users/tests/test_edge_cases.py` split into feature-specific test modules (`auth/tests/test_auth_edge_cases.py`, `circles/tests/test_circle_edge_cases.py`, `users/tests/test_child_profile_edge_cases.py`, `users/tests/test_notification_preferences.py`, `users/tests/test_permission_edge_cases.py`).
- [x] `mysite/circles/views/invitations.py` split into `views/invitations/admin.py` (admin actions), `views/invitations/invitee.py` (invitee actions), with shared logic extracted to `services/invitation_service.py`. All views re-exported from `views/invitations/__init__.py`.
- [x] `mysite/users/tests/test_invitation_roles.py` split into `circles/tests/test_invitation_serializers.py` (serializer validation), `circles/tests/test_invitation_admin_permissions.py` (admin CRUD), `circles/tests/test_invitation_workflow.py` (end-to-end flows), with shared fixtures in `circles/tests/conftest.py`. Relocated from users/tests to circles/tests.
- [x] `mysite/auth/services/google_oauth_service.py` split into specialized sub-services in `oauth/` subdirectory: `pkce_state_service.py` (PKCE and state management, 175 lines), `google_api_service.py` (Google API interactions, 144 lines), and `account_linking_service.py` (account linking/unlinking, 213 lines). Main service reduced from 485 to 226 lines and now focuses on orchestration.
