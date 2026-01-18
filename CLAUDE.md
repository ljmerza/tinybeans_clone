# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

### Full Stack (Docker)
```bash
docker compose up --build              # Start all services
docker compose exec web python manage.py migrate  # Run migrations
docker compose exec web python manage.py test --settings=mysite.test_settings  # Run backend tests
docker compose restart web             # Restart after env changes
```

### Backend (Django)
```bash
python manage.py test --settings=mysite.test_settings  # Run all tests
python manage.py test users.tests.test_models --settings=mysite.test_settings  # Run specific test file
pytest                                 # Alternative test runner (uses pytest.ini)
ruff check .                           # Lint
ruff format .                          # Format
python manage.py shell_plus            # Django shell with auto-imports
python manage.py seed_demo_data        # Reseed demo data
```

### Frontend (React/Vite)
```bash
cd web
npm run dev                            # Dev server on port 3000
npm run build                          # Production build (vite build + tsc)
npm run test                           # Run Vitest tests
biome lint                             # Lint
npx biome format --write               # Format
npm run check                          # Full check (custom fetch check + biome)
pnpx shadcn@latest add <component>     # Add shadcn component
```

## Architecture Overview

### Backend (Django 5.2 + DRF)
- **`mysite/`**: Main Django project with modular apps
  - `auth/` - JWT auth, OAuth 2.0 (Google), 2FA (TOTP/SMS/email), magic links, trusted devices
  - `users/` - User management and profiles
  - `circles/` - Group/family management, memberships, invitations
  - `keeps/` - Photo/video moments with async upload pipeline, MinIO/S3 storage, thumbnails
  - `messaging/` - Notifications
  - `emails/` - Email dispatcher with templates
  - `config/settings/` - Modular settings (base, local, production, etc.)
- **API**: REST via DRF with Spectacular OpenAPI docs at `/api/docs/`
- **Async**: Celery workers + Beat scheduler, Flower monitoring
- **Storage**: PostgreSQL, Redis (cache/tokens/rate-limiting), MinIO (media)

### Frontend (React 19 + Vite)
- **`web/src/`**: React SPA
  - `routes/` - TanStack Router file-based routing (auto-generates `routeTree.gen.ts`)
  - `route-views/` - Page components
  - `features/` - Feature modules (auth, keeps, circles)
  - `components/` - Shared UI (shadcn + Tailwind + Radix)
  - `lib/` - Utilities, hooks, API clients
- **State**: TanStack Query (server), TanStack Store (client), TanStack Form
- **Styling**: Tailwind CSS 4.0 with shadcn components
- **Testing**: Vitest + Testing Library + MSW for mocking

### Key Services (Docker Compose)
| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django API |
| web-frontend | 3000 | Vite dev server |
| postgres | 5432 | Database |
| redis | 6379 | Cache/broker |
| flower | 5555 | Celery monitoring |
| minio | 9000/9001 | S3-compatible storage |
| mailpit | 8025 | SMTP testing |

## Backend Coding Standards

### Code Organization
Each Django app follows this structure:
- `models/` - Split by domain (e.g., `two_factor.py`, `google.py`)
- `views/` - Organized by feature with `@extend_schema()` for OpenAPI docs
- `serializers/` - Grouped by feature, separate read/write serializers
- `services/` - Business logic layer (e.g., `TwoFactorService`, `TrustedDeviceService`)
- `tests/` - With `conftest.py` for shared fixtures

### Naming Conventions
- **Models**: Singular PascalCase (`User`, `Keep`, `TwoFactorSettings`)
- **Serializers**: Suffixed `*Serializer` (`SignupSerializer`, `KeepCreateSerializer`)
- **Views**: Suffixed by operation (`*ListCreateView`, `*VerifyView`)
- **Services**: Suffixed `*Service` with static methods for utilities
- **Private methods**: Prefixed with `_` (`_hash_otp()`, `_get_encryption_key()`)

### Response Format
All API responses use standardized format with i18n support:
```python
from mysite.notification_utils import success_response, error_response, create_message

# Success
success_response(data={'user': user_data}, messages=[create_message('auth.signup.success')])

# Error
error_response(error='validation_failed', messages=[create_message('errors.email_invalid')], status_code=400)
```

### Service Layer Pattern
Business logic lives in service classes, not views:
```python
class TwoFactorService:
    @staticmethod
    def generate_otp() -> str:
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    @staticmethod
    def verify_totp(user, code: str) -> bool:
        # Verification logic
```

### Celery Task Pattern
```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_email_task(self, *, to_email: str, template_id: str, context: dict):
    # Task implementation
```

### Token Storage Pattern
Single-use tokens use Redis cache with TTL:
```python
from mysite.auth.token_utils import store_token, pop_token
token = store_token('password_reset', {'user_id': user.id}, ttl=3600)
payload = pop_token('password_reset', token)  # Returns and deletes
```

### Rate Limiting
Apply via decorator:
```python
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=False))
def post(self, request):
    if getattr(request, 'limited', False):
        return rate_limit_response()
```

### Test Fixtures
Use `conftest.py` for shared fixtures:
```python
@pytest.fixture
def mock_email_send():
    with patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_code') as mock:
        yield mock

def create_user(email='test@example.com', password='testpass', **extra):
    return User.objects.create_user(email=email, password=password, **extra)
```

## Frontend Coding Standards

### Feature Structure
Each feature is self-contained:
```
features/auth/
├── api/           # queryKeys.ts, services.ts
├── hooks/         # useLogin.ts, useSignup.ts
├── components/    # LoginCard.tsx, SignupCard.tsx
├── context/       # AuthSessionProvider.tsx
├── guards/        # routeGuards.ts
├── store/         # authStore.ts (TanStack Store)
├── types/         # Feature types
└── index.ts       # Public exports
```

### TanStack Query Patterns
Query key factory pattern:
```typescript
const circleKeysFactory = createQueryKeyFactory(["circles"] as const);
export const circleKeys = {
  all: () => circleKeysFactory.root(),
  list: () => circleKeysFactory.tag("list"),
  detail: (id: string) => circleKeysFactory.tag("detail", id),
};
```

Mutations with toast metadata:
```typescript
useMutation({
  mutationFn: (body) => authServices.login(body),
  meta: {
    toast: {
      useResponseMessages: true,
      success: { key: "auth.login.success", status: 200 },
      error: { key: "auth.login.failed", status: 400 },
    },
  },
});
```

### Form Handling (TanStack Form + Zod)
```typescript
const form = useForm({
  defaultValues: { email: "", password: "" },
  onSubmit: async ({ value }) => {
    await login.mutateAsync(value);
  },
});

<form.Field
  name="email"
  validators={{ onBlur: zodValidator(loginSchema.shape.email) }}
>
  {(field) => (
    <FormField field={field} label={t("auth.login.email")}>
      {({ id, field: fieldApi }) => (
        <Input id={id} value={fieldApi.state.value} onChange={(e) => fieldApi.handleChange(e.target.value)} />
      )}
    </FormField>
  )}
</form.Field>
```

### Route Guards
```typescript
export async function requireAuth({ context }: { context: GuardContext }) {
  const user = await resolveSessionUser(context.queryClient);
  if (!user) {
    throw redirect({ to: "/login", search: { redirect: window.location.pathname } });
  }
}
```

### API Client Pattern
Centralized client with auth handling:
```typescript
export const authApi = createApiClient({
  getAuthToken: () => authStore.state.accessToken,
  onUnauthorized: async () => await refreshAccessToken(),
});

// Service layer
export const authServices = {
  login: (body: LoginRequest) => authApi.post<ApiResponseWithMessages<LoginResponse>>("/auth/login/", body),
};
```

### i18n Message Handling
API returns i18n keys that frontend translates:
```typescript
const { showAsToast, getFieldErrors, getGeneral } = useApiMessages();

// Show API messages as toast
showAsToast(response.messages, 200);

// Extract field-specific errors for form display
const fieldErrors = getFieldErrors(error.messages);
```

### Auth State Model
Three-state authentication:
- `"unknown"` - App bootstrapping
- `"guest"` - No access token
- `"authenticated"` - Has token + valid session

Access token stored in-memory only (TanStack Store), refresh token in HTTP-only cookie.

### File Naming
- **Components**: PascalCase (`LoginCard.tsx`)
- **Hooks**: `use` prefix (`useLogin.ts`)
- **Routes**: kebab-case (`verify-email.tsx`)
- **Tests**: Colocated as `*.test.tsx`

## Testing

Backend tests use `mysite.test_settings` which provides:
- In-memory cache (no Redis required)
- Synchronous Celery execution
- In-memory email backend

Frontend tests use `renderWithQueryClient` helper for proper provider wrapping.

## Demo Accounts

All use password `password123`:
- `superadmin@example.com` - Full admin
- `guardian@example.com` - Circle admin ("Guardian Family")
- `member@example.com` - Circle member
- `solo@example.com` - No circle memberships

## Key Documentation

- `DEVELOPMENT.md` - Local setup, Google OAuth config, environment variables
- `AGENTS.md` - Project overview for AI agents, BMAD-METHOD integration
- `_docs/` - Extended architecture docs, feature specs, ADRs

## UI Patterns

- Use `Layout.Loading` for pending states (supports `layout="inline|section|fullscreen"`)
- Use `Layout.Error` for recoverable errors with action buttons
- Deprecated: `LoadingState`, `StandardError` (kept for backward compatibility)
