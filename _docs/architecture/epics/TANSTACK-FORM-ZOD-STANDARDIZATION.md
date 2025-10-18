# Epic: TanStack Form & Zod Validation Standardization

> **💡 Philosophy**: Keep it simple! The codebase already uses TanStack Form + Zod correctly. This epic is about **centralizing schemas**, not rewriting everything. We're standardizing what works, not over-engineering.

## Overview

This epic establishes standardized Zod validation schemas across the web/ application while maintaining the simple, effective TanStack Form pattern already in use. The goal is consistency through shared schemas, not abstraction layers.

## Goals

- Standardize form validation using Zod schemas across all forms
- Create centralized, reusable validation schemas
- Maintain the simple, working TanStack Form pattern already in use
- Improve type safety from schema definition to form submission
- Reduce form-related bugs through consistent validation
- Establish clear documentation for the team
- Keep it simple - avoid over-engineering

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Forms migrated to TanStack Form + Zod | 100% (all 12 identified forms) | Count of forms using standard pattern |
| Form-related bugs reported | 50% reduction | Compare 3 months before/after |
| Type safety violations in forms | 0 | TypeScript errors in form code |
| Field validation consistency | 100% | All fields use Zod schemas |
| Developer velocity (new form creation) | 40% faster | Time to implement new form (before/after) |
| Form accessibility compliance | 100% WCAG AA | Automated axe-core tests |
| Test coverage for forms | 80%+ | Unit + integration tests |

## Problem Statement

### Current Issues

The application currently has inconsistent form handling patterns with several critical problems:

**Manual Validation Inconsistency**: Forms use a mix of manual validation, inline Zod validation, and TanStack Form validators without a consistent pattern. This leads to duplication and missed edge cases.

**Type Safety Gaps**: While Zod schemas exist for some validations, they're not consistently integrated with TypeScript types, leading to runtime errors that could be caught at compile time.

**Boilerplate Code**: Each form reimplements similar patterns for error display, loading states, submission handling, and field-level validation, creating maintenance burden.

**Poor Error Experience**: Error messages are displayed inconsistently, with some forms showing general errors, others showing field-specific errors, and no standard pattern for server-side validation errors.

**Testing Challenges**: Without standardized patterns, each form requires custom test setup, making comprehensive testing time-consuming and often incomplete.

**Accessibility Issues**: Form implementations don't consistently follow WCAG guidelines for error announcements, focus management, and keyboard navigation.

### Current Form Inventory

Based on analysis of the codebase, we have identified these forms requiring migration:

**Authentication Forms** (5 forms):
- LoginCard - Username/password login
- SignupCard - User registration
- MagicLinkRequestCard - Magic link authentication
- PasswordResetRequestCard - Password reset request
- PasswordResetConfirmCard - Password reset confirmation

**2FA Forms** (4 forms):
- TwoFactorSetup - TOTP/Email/SMS setup wizards
- TwoFactorVerify - 2FA code verification
- TrustedDevicesManagement - Device management
- RecoveryCodeEntry - Recovery code usage

**Profile Forms** (2 forms):
- ProfileEdit - User profile updates
- PasswordChange - Password update

**Other Forms** (1+ forms):
- Settings forms (to be inventoried)
- Future forms

## Solution Architecture

### Core Components

#### 1. Validation Schema Library

**Location**: `src/lib/validations/schemas/`

Centralized Zod schemas organized by domain:

```typescript
// src/lib/validations/schemas/auth.schemas.ts
import { z } from 'zod'

export const emailSchema = z
  .string()
  .min(1, 'validation.email_required')
  .email('validation.email_invalid')

export const passwordSchema = z
  .string()
  .min(8, 'validation.password_min_length')
  .regex(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
    'validation.password_complexity'
  )

export const usernameSchema = z
  .string()
  .min(3, 'validation.username_min_length')
  .max(30, 'validation.username_max_length')
  .regex(/^[a-zA-Z0-9_]+$/, 'validation.username_invalid_chars')

export const loginSchema = z.object({
  username: usernameSchema,
  password: passwordSchema,
})

export const signupSchema = z.object({
  email: emailSchema,
  username: usernameSchema,
  password: passwordSchema,
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'validation.passwords_must_match',
  path: ['confirmPassword'],
})

// Export inferred types
export type LoginFormData = z.infer<typeof loginSchema>
export type SignupFormData = z.infer<typeof signupSchema>
```

#### 2. Form Field Components (Optional Enhancement)

**Location**: `src/components/form/`

**Note**: These components are optional. The current inline pattern works well. Only create these if you find repeated patterns across many forms.

Simple field wrapper for consistent error display:

```typescript
// src/components/form/FormField.tsx
import { Label } from '@/components/ui/label'
import { ReactNode } from 'react'

interface FormFieldProps {
  name: string
  label: string
  error?: string
  required?: boolean
  children: ReactNode
}

export function FormField({ name, label, error, required, children }: FormFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-red-600 ml-1">*</span>}
      </Label>
      {children}
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
```

**Usage is simpler and more explicit**:
```typescript
<form.Field name="email" validators={{ onBlur: emailValidator }}>
  {(field) => (
    <FormField
      name={field.name}
      label="Email"
      error={field.state.meta.errors[0]}
      required
    >
      <Input
        value={field.state.value}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
      />
    </FormField>
  )}
</form.Field>
```

#### 3. Form Utilities (Simplified)

**Location**: `src/lib/form/utils.ts`

Keep utilities minimal - TanStack Form and Zod already work great together:

```typescript
// src/lib/form/utils.ts
import { ZodSchema } from 'zod'

/**
 * Simple Zod validator for TanStack Form fields
 * Returns error message or undefined
 */
export function zodValidator<T>(schema: ZodSchema<T>) {
  return ({ value }: { value: T }) => {
    const result = schema.safeParse(value)
    return result.success ? undefined : result.error.errors[0]?.message
  }
}

/**
 * Map server validation errors to field errors
 * Handles Django/DRF error format: { field: ["error1", "error2"] }
 */
export function mapServerErrors(
  serverErrors: Record<string, string[]>
): Record<string, string> {
  const fieldErrors: Record<string, string> = {}
  
  for (const [field, messages] of Object.entries(serverErrors)) {
    if (messages?.length > 0) {
      fieldErrors[field] = messages.join('. ')
    }
  }
  
  return fieldErrors
}

/**
 * Extract non-field errors for general display
 */
export function getGeneralErrors(
  serverErrors: Record<string, string[]>
): string[] {
  const generalKeys = ['non_field_errors', '__all__', 'detail']
  return generalKeys.flatMap(key => serverErrors[key] || [])
}
```

**That's it!** No need for complex abstractions. The current pattern in the codebase already works well.

#### 4. Standard Form Pattern (Simplified)

**No custom hooks needed!** TanStack Form's `useForm` is already perfect. Just follow this pattern:

```typescript
// Example: features/auth/components/LoginForm.tsx
import { useForm } from '@tanstack/react-form'
import { loginSchema, type LoginFormData } from '@/lib/validations/schemas/auth'
import { zodValidator } from '@/lib/form/utils'
import { useLogin } from '../hooks/authHooks'
import { useState } from 'react'

export function LoginForm() {
  const { t } = useTranslation()
  const login = useLogin()
  const [generalError, setGeneralError] = useState('')

  const form = useForm<LoginFormData>({
    defaultValues: {
      username: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      setGeneralError('')
      try {
        await login.mutateAsync(value)
      } catch (error: any) {
        const errors = error.response?.data?.errors
        if (errors) {
          const general = getGeneralErrors(errors)
          if (general.length > 0) {
            setGeneralError(general.join('. '))
          }
        } else {
          setGeneralError(error.message || 'Login failed')
        }
      }
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
    >
      {generalError && <ErrorMessage>{generalError}</ErrorMessage>}

      <form.Field
        name="username"
        validators={{
          onBlur: zodValidator(loginSchema.shape.username),
        }}
      >
        {(field) => (
          <div>
            <Label htmlFor={field.name}>Username</Label>
            <Input
              id={field.name}
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
            />
            {field.state.meta.errors?.[0] && (
              <ErrorText>{field.state.meta.errors[0]}</ErrorText>
            )}
          </div>
        )}
      </form.Field>

      {/* Similar for password field */}

      <Button type="submit" disabled={form.state.isSubmitting}>
        {form.state.isSubmitting ? 'Signing in...' : 'Sign In'}
      </Button>
    </form>
  )
}
```

**Key Points**:
- Use TanStack Form's `useForm` directly - no wrapper needed
- Use inline Zod validation with `zodValidator` helper
- Handle submission errors in `onSubmit`
- Use `form.state.isSubmitting` for loading state
- Keep it simple and explicit

### Implementation Patterns (Best Practices)

#### Pattern 1: Basic Form with Validation

**This is already what the codebase does!** We're just making it consistent:

```typescript
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'

// 1. Define schema
const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(8, 'Password must be 8+ characters'),
})

type LoginData = z.infer<typeof loginSchema>

// 2. Create inline validator helper
const zodValidator = (schema: z.ZodSchema) => ({ value }: any) => {
  const result = schema.safeParse(value)
  return result.success ? undefined : result.error.errors[0]?.message
}

// 3. Use in component
function LoginForm() {
  const form = useForm<LoginData>({
    defaultValues: { username: '', password: '' },
    onSubmit: async ({ value }) => {
      await api.login(value)
    },
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit() }}>
      <form.Field
        name="username"
        validators={{ onBlur: zodValidator(loginSchema.shape.username) }}
      >
        {(field) => (
          <>
            <input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
            />
            {field.state.meta.errors?.[0] && (
              <span>{field.state.meta.errors[0]}</span>
            )}
          </>
        )}
      </form.Field>
      <button disabled={form.state.isSubmitting}>Submit</button>
    </form>
  )
}
```

#### Pattern 2: Form with Server Errors

```typescript
function SignupForm() {
  const [generalError, setGeneralError] = useState('')
  
  const form = useForm<SignupData>({
    defaultValues: { email: '', password: '', confirmPassword: '' },
    onSubmit: async ({ value }) => {
      setGeneralError('')
      try {
        await api.signup(value)
      } catch (error: any) {
        // Handle Django/DRF error format
        const errors = error.response?.data
        if (errors?.non_field_errors) {
          setGeneralError(errors.non_field_errors.join('. '))
        } else if (errors?.detail) {
          setGeneralError(errors.detail)
        }
      }
    },
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit() }}>
      {generalError && <div className="error">{generalError}</div>}
      {/* Fields... */}
    </form>
  )
}
```

#### Pattern 3: Cross-Field Validation

```typescript
const signupSchema = z.object({
  password: z.string().min(8),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'], // Sets error on confirmPassword field
})
```

#### Pattern 4: Conditional Validation

```typescript
const profileSchema = z.object({
  hasPhone: z.boolean(),
  phone: z.string().optional(),
}).refine(
  (data) => !data.hasPhone || (data.phone && data.phone.length > 0),
  {
    message: 'Phone is required when enabled',
    path: ['phone'],
  }
)
```

**These patterns are simple, type-safe, and follow official TanStack Form + Zod best practices.**

## Implementation Phases

### Phase 1: Foundation (Week 1) - 3 story points

**Objective**: Establish core schemas and minimal utilities

#### Story 1.1: Create Validation Schema Library (2 SP)
**Description**: Set up centralized Zod schemas for all validation rules

**Tasks**:
- Create `src/lib/validations/schemas/` directory structure
- Migrate existing validation rules from `src/lib/validations.ts`
- Create domain-specific schema files (auth, profile, twofa)
- Add comprehensive JSDoc documentation for each schema
- Export TypeScript types using `z.infer`

**Acceptance Criteria**:
- [ ] All existing validation rules migrated to schema files
- [ ] Each schema has corresponding TypeScript type export
- [ ] Schemas support i18n error messages
- [ ] Documentation includes usage examples
- [ ] Schemas are exported from central index file

**Definition of Done**:
- Code reviewed and approved
- Unit tests written for complex validators
- Documentation added to developer guide

#### Story 1.2: Build Form Utilities (1 SP)
**Description**: Create minimal utility functions for form validation and error handling

**Tasks**:
- Implement simple `zodValidator` helper function
- Implement server error mapping utilities
- Add error extraction helpers
- Create unit tests

**Acceptance Criteria**:
- [ ] `zodValidator` correctly converts Zod errors to TanStack Form format
- [ ] Server error mapping handles Django/DRF error formats
- [ ] General error extraction identifies non-field errors
- [ ] 90%+ test coverage for utilities
- [ ] TypeScript types are properly inferred

**Definition of Done**:
- All utility functions implemented and tested
- Documentation with usage examples
- Edge cases covered in tests

#### Story 1.3: Create Simple Form Field Wrapper (Optional - 1 SP)
**Description**: Create optional wrapper for consistent error display (only if needed)

**Tasks**:
- Create simple `FormField` wrapper component
- Ensure WCAG AA compliance
- Add Storybook stories (if applicable)

**Note**: This is optional. The inline pattern works fine. Only create if you see repeated error display patterns.

**Acceptance Criteria**:
- [ ] Component properly displays label, input, and error
- [ ] Error states are displayed accessibly
- [ ] ARIA attributes are correctly applied
- [ ] Component is keyboard navigable

**Definition of Done**:
- Component implemented with proper TypeScript types
- Accessibility tested with axe-core
- Documentation with examples

### Phase 2: Authentication Forms Migration (Week 2) - 5 story points

**Objective**: Migrate authentication forms to use shared schemas

#### Story 2.1: Migrate LoginCard (1 SP)
**Description**: Refactor LoginCard to use schema from validation library (it already uses the right pattern!)

**Tasks**:
- Move login validation to `src/lib/validations/schemas/auth.ts`
- Ensure existing inline Zod validation continues to work
- Update imports to use shared schema
- Add tests

**Acceptance Criteria**:
- [ ] Form uses shared `loginSchema`
- [ ] Field-level validation works on blur
- [ ] Server errors are properly displayed
- [ ] All existing functionality preserved
- [ ] Tests achieve 80%+ coverage

**Definition of Done**:
- Form using shared schema
- No regressions in functionality

#### Story 2.2: Migrate SignupCard (1 SP)
**Description**: Update SignupCard to use shared schema with password matching

**Tasks**:
- Create `signupSchema` with password confirmation using `.refine()`
- Update component to use shared schema
- Ensure password matching validation works
- Handle terms acceptance checkbox

**Acceptance Criteria**:
- [ ] Password and confirmation fields validate correctly
- [ ] Zod `.refine()` catches password mismatch
- [ ] All field validations work independently
- [ ] Error messages are clear and actionable
- [ ] Tests cover password matching edge cases

**Definition of Done**:
- Signup flow fully functional
- Password matching works correctly
- Comprehensive test coverage

#### Story 2.3: Migrate Password Reset Forms (1 SP)
**Description**: Update both password reset forms with shared schemas

**Tasks**:
- Create schemas for reset request and confirm
- Update components to use shared schemas
- Ensure email validation is robust
- Handle token validation errors

**Acceptance Criteria**:
- [ ] Both forms use shared schemas
- [ ] Email validation follows RFC standards
- [ ] Password complexity rules enforced
- [ ] Token errors displayed appropriately
- [ ] Success states handled consistently

**Definition of Done**:
- Both forms migrated
- Full password reset flow tested

#### Story 2.4: Migrate MagicLinkRequestCard (1 SP)
**Description**: Update magic link request form

**Tasks**:
- Create `magicLinkSchema`
- Update component to use shared schema
- Update success/error messaging

**Acceptance Criteria**:
- [ ] Email validation works correctly
- [ ] Success message displayed appropriately
- [ ] Error handling consistent

**Definition of Done**:
- Magic link flow fully functional

#### Story 2.5: Document Authentication Form Patterns (1 SP)
**Description**: Create examples and documentation for team

**Tasks**:
- Document the standard pattern used
- Create example code snippets
- Add troubleshooting guide

**Acceptance Criteria**:
- [ ] Documentation is clear and complete
- [ ] Examples are copy-paste ready
- [ ] Common issues documented

**Definition of Done**:
- Documentation reviewed by team

### Phase 3: 2FA Forms Migration (Week 3) - 4 story points

**Objective**: Migrate two-factor authentication forms to shared schemas

#### Story 3.1: Migrate TwoFactorSetup Components (2 SP)
**Description**: Update TOTP, Email, and SMS setup forms

**Tasks**:
- Create schemas for each 2FA method setup
- Update TOTP setup (QR code display maintained)
- Update Email/SMS setup
- Validate verification codes with Zod

**Acceptance Criteria**:
- [ ] Each setup method uses shared schemas
- [ ] QR code generation not affected
- [ ] Verification code validation uses Zod
- [ ] Error messages are method-specific
- [ ] Success flows maintained

**Definition of Done**:
- All three setup methods migrated
- Setup flows tested

#### Story 3.2: Migrate TwoFactorVerify Component (1 SP)
**Description**: Update 2FA verification form

**Tasks**:
- Use existing `verificationCodeSchema` from validations
- Update verification component
- Handle remember device checkbox
- Test verification flow

**Acceptance Criteria**:
- [ ] 6-digit code validation works
- [ ] Remember device option functions
- [ ] Invalid code errors clear
- [ ] Rate limiting respected

**Definition of Done**:
- Verification flow fully functional

#### Story 3.3: Migrate Trusted Devices Management (1 SP)
**Description**: Update device management forms

**Tasks**:
- Create schema for device naming
- Update device removal confirmation
- Apply standard patterns

**Acceptance Criteria**:
- [ ] Device naming uses standard validation
- [ ] Confirmation patterns consistent
- [ ] Error handling standardized

**Definition of Done**:
- Device management fully migrated

### Phase 4: Profile & Settings Forms (Week 4) - 3 story points

**Objective**: Migrate remaining forms to shared schemas

#### Story 4.1: Migrate Profile Edit Form (2 SP)
**Description**: Update user profile editing form

**Tasks**:
- Create `profileSchema` with proper field validations
- Handle optional fields properly
- Support file upload for avatar (if applicable)
- Handle partial updates

**Acceptance Criteria**:
- [ ] All profile fields validate correctly
- [ ] Optional fields handled with `.optional()` or `.nullable()`
- [ ] Avatar upload integrated (if needed)
- [ ] Partial update support maintained
- [ ] Success/error feedback clear

**Definition of Done**:
- Profile edit fully functional
- All validation rules applied

#### Story 4.2: Migrate Password Change Form (1 SP)
**Description**: Update password change form

**Tasks**:
- Create `passwordChangeSchema`
- Validate current password
- Enforce new password complexity
- Confirm new password matches using `.refine()`
- Handle security requirements

**Acceptance Criteria**:
- [ ] Current password verified
- [ ] New password complexity enforced
- [ ] Password confirmation validated with Zod
- [ ] Security requirements met
- [ ] Clear error messages

**Definition of Done**:
- Password change fully functional
- Security maintained

### Phase 5: Documentation & Quality (Week 5) - 3 story points

**Objective**: Document patterns and add quality gates

#### Story 5.1: Developer Documentation (1 SP)
**Description**: Create simple guide for form implementation

**Tasks**:
- Write "Creating Forms" guide
- Document the standard pattern
- Provide code examples
- Create troubleshooting section

**Deliverables**:
- `docs/forms/README.md` - Main guide
- `docs/forms/EXAMPLES.md` - Code examples

**Acceptance Criteria**:
- [ ] Guide covers common scenarios
- [ ] Examples are copy-paste ready
- [ ] Troubleshooting covers known issues

**Definition of Done**:
- Documentation reviewed by team

#### Story 5.2: Schema Scaffolding Tool (Optional - 1 SP)
**Description**: Create simple script to generate schema boilerplate

**Tasks**:
- Create script to generate schema file
- Auto-generate TypeScript types
- Include common validators

**Example Usage**:
```bash
npm run generate:schema auth/profile
# Creates: src/lib/validations/schemas/profile.schemas.ts
```

**Acceptance Criteria**:
- [ ] Script generates valid Zod schemas
- [ ] Generated code follows standards
- [ ] Types properly exported

**Definition of Done**:
- Script working and documented

#### Story 5.3: Quality Checks (1 SP)
**Description**: Add basic quality gates

**Tasks**:
- Add bundle size monitoring for Zod
- Create checklist for form PRs
- Document code review standards

**Acceptance Criteria**:
- [ ] Bundle size tracked in CI
- [ ] Checklist available for reviewers
- [ ] Standards documented

**Definition of Done**:
- Quality checks documented
- Team aware of standards

## Migration Strategy

### Incremental Migration Approach

Forms will be migrated incrementally to minimize risk and allow for learning:

**Phase 1 (Foundation)**: Build infrastructure without touching existing forms. This allows the team to validate the approach before committing to migration.

**Phase 2-4 (Progressive Migration)**: Migrate forms one at a time in order of criticality. Each migration is thoroughly tested before moving to the next. High-traffic forms (login, signup) are prioritized.

**Phase 5 (Hardening)**: Add tooling and documentation to prevent regression and make the new pattern the "path of least resistance" for developers.

### Rollback Strategy

Each form migration is implemented as a separate PR that can be reverted independently if issues are discovered:

- Keep old form components in `_deprecated/` folder for 2 weeks after migration
- Feature flags can toggle between old and new forms if needed
- Comprehensive testing before production deployment
- Gradual rollout to production (canary deployment if applicable)

### Testing Strategy

**Unit Tests**:
- Test each schema validates correctly
- Test form utilities handle edge cases
- Test components render and handle errors
- 80%+ coverage target for form code

**Integration Tests**:
- Test complete form submission flows
- Test server error handling
- Test validation sequencing
- Test accessibility features

**E2E Tests** (if applicable):
- Test critical flows (login, signup, password reset)
- Test across browsers
- Test keyboard navigation

**Accessibility Tests**:
- Automated axe-core testing
- Manual screen reader testing
- Keyboard navigation testing

## Dependencies

### Internal Dependencies

- ADR-013: Frontend Architecture Modernization (parent decision)
- ADR-011: Frontend File Architecture (for file organization)
- ADR-012: Notification Strategy (for error message handling)
- i18n implementation (for translated error messages)

### External Dependencies

- TanStack Form v1.0.0 (already installed)
- Zod v3.24.2 (already installed)
- React 19.0.0 (already installed)
- TypeScript 5.7.2 (already installed)

### Team Dependencies

- Frontend developers (for implementation)
- QA (for testing)
- Design (for any UI adjustments needed)

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking existing form functionality | High | Low | Comprehensive testing, incremental migration, rollback plan |
| Developer resistance to new patterns | Medium | Medium | Clear documentation, examples, training sessions |
| Performance regression | Low | Low | Bundle analysis, lazy loading of validators |
| Accessibility regressions | High | Low | Automated testing, manual verification |
| Type safety issues | Medium | Low | Strict TypeScript config, thorough type checking |
| Inconsistent adoption | Medium | Medium | Linting rules, code review checklist, generator tool |
| Schema complexity escalation | Low | Medium | Keep schemas simple, document complex patterns |

## Resource Requirements

### Team Allocation

- **Frontend Lead** (20% for 5 weeks): Architecture decisions, code reviews, unblocking
- **Frontend Developer 1** (100% for 5 weeks): Primary implementation
- **Frontend Developer 2** (50% for 5 weeks): Testing, documentation, secondary implementation
- **QA Engineer** (25% for 5 weeks): Test planning, execution, accessibility testing
- **Designer** (10% for 2 weeks): Review UI/UX implications, approve changes

### Timeline

- **Week 1**: Foundation and infrastructure
- **Week 2**: Authentication forms migration
- **Week 3**: 2FA forms migration
- **Week 4**: Profile and settings forms
- **Week 5**: Documentation, tooling, and hardening

**Total Duration**: 5 weeks (18 story points - simplified from original over-engineered 27)

### Budget Considerations

- No additional software costs (all dependencies already in place)
- Training time: ~2 hours team-wide (pattern is already in use!)
- Documentation time: ~4 hours (simpler patterns)
- Code review time: ~1 hour per form migration

## Success Criteria

### Acceptance Criteria

This epic will be considered complete when:

- [ ] All 12 identified forms migrated to TanStack Form + Zod
- [ ] Form utility library created and documented
- [ ] Reusable form components available
- [ ] Developer documentation complete
- [ ] CLI generator tool working
- [ ] ESLint rules active
- [ ] All tests passing (unit, integration, E2E)
- [ ] Accessibility audit passes
- [ ] No P0/P1 bugs in production
- [ ] Team trained on new patterns

### Validation Metrics

**Immediate Validation** (during implementation):
- TypeScript compiler shows no errors
- All tests pass
- Linting passes
- Bundle size within acceptable limits
- Lighthouse accessibility score ≥ 90

**Post-Launch Validation** (2 weeks after completion):
- Form error rate < 1%
- No increase in form abandonment rate
- Form-related bug reports reduced
- Developer velocity for new forms improved
- Team satisfaction with new patterns

## Communication Plan

### Weekly Updates

Every Friday during implementation:
- Progress update in team standup
- Metrics dashboard update
- Blockers identified and addressed
- Next week priorities communicated

### Stakeholder Communication

- **Week 0**: Kickoff meeting with team, present approach and timeline
- **Week 2**: Mid-sprint demo of completed auth forms
- **Week 4**: Demo of all migrated forms
- **Week 5**: Final presentation with metrics and learnings

### Documentation

- Living documentation in `docs/forms/`
- Changelog for breaking changes
- Migration status tracked in GitHub project
- Team Slack channel for questions

## Open Questions

| Question | Owner | Resolution Target | Status |
|----------|-------|-------------------|--------|
| Should we support dynamic form generation from schemas? | Frontend Lead | Before Phase 1 | Open |
| Do we need server-side schema validation sharing? | Backend Lead | Before Phase 2 | Open |
| Should forms auto-save drafts to localStorage? | Product | Before Phase 3 | Open |
| Do we need optimistic updates for all forms? | Frontend Lead | Before Phase 4 | Open |
| Should we implement form analytics tracking? | Analytics | Before Phase 5 | Open |

## References

### Internal Documentation
- ADR-013: Frontend Architecture Modernization
- ADR-011: Frontend File Architecture
- ADR-012: Notification Strategy
- Project coding standards

### External Resources
- [TanStack Form Documentation](https://tanstack.com/form/latest)
- [Zod Documentation](https://zod.dev/)
- [Form Accessibility Guide](https://www.w3.org/WAI/tutorials/forms/)
- [React Hook Form Migration Guide](https://react-hook-form.com/migrate-v6-to-v7) (for comparison)

### Code Examples
- See `docs/forms/examples/` for reference implementations
- Check existing `LoginCard.tsx` for current patterns

## Appendix

### Form Complexity Matrix

| Form | Fields | Validation Rules | Complexity | Priority | Estimated Hours |
|------|--------|------------------|------------|----------|-----------------|
| LoginCard | 2 | Basic | Low | P0 | 4 |
| SignupCard | 4 | Complex | Medium | P0 | 8 |
| PasswordResetRequest | 1 | Basic | Low | P1 | 2 |
| PasswordResetConfirm | 3 | Medium | Medium | P1 | 4 |
| MagicLinkRequest | 1 | Basic | Low | P1 | 2 |
| TwoFactorSetup (TOTP) | 2 | Medium | Medium | P1 | 6 |
| TwoFactorSetup (Email/SMS) | 2 | Medium | Medium | P1 | 6 |
| TwoFactorVerify | 2 | Medium | Medium | P0 | 4 |
| TrustedDevices | 1 | Basic | Low | P2 | 2 |
| ProfileEdit | 6+ | Complex | High | P1 | 10 |
| PasswordChange | 3 | Medium | Medium | P1 | 4 |

**Total Estimated Hours**: 36 hours (~0.9 sprints for one developer)

This is significantly reduced from complex abstraction approach because we're working WITH the existing pattern, not fighting it.

### Validation Schema Catalog

Complete list of validation schemas to be created:

**Authentication Schemas**:
- `emailSchema` - Email validation
- `usernameSchema` - Username rules
- `passwordSchema` - Password complexity
- `loginSchema` - Login form
- `signupSchema` - Signup with confirmation
- `passwordResetRequestSchema` - Email for reset
- `passwordResetConfirmSchema` - New password
- `magicLinkRequestSchema` - Magic link email

**2FA Schemas**:
- `verificationCodeSchema` - 6-digit codes
- `totpSetupSchema` - TOTP configuration
- `smsSetupSchema` - Phone number
- `emailSetupSchema` - Email for 2FA
- `recoveryCodeSchema` - Recovery code format
- `trustedDeviceSchema` - Device naming

**Profile Schemas**:
- `profileUpdateSchema` - Profile fields
- `passwordChangeSchema` - Current and new password
- `emailChangeSchema` - New email verification

### Code Review Checklist

For each form migration PR:

- [ ] Form uses TanStack Form with Zod validation
- [ ] All fields have proper validation
- [ ] Error messages are translatable (i18n keys)
- [ ] Loading states properly handled
- [ ] Accessibility attributes present (ARIA)
- [ ] Keyboard navigation works
- [ ] Focus management correct
- [ ] TypeScript types properly inferred
- [ ] Unit tests cover happy and error paths
- [ ] Integration tests exist for critical flows
- [ ] No console errors or warnings
- [ ] Bundle size impact acceptable
- [ ] Documentation updated if needed
- [ ] Old code removed or marked deprecated

---

**Epic Owner**: Frontend Lead  
**Created**: 2025-01-26  
**Status**: Proposed  
**Related ADR**: ADR-013 Frontend Architecture Modernization
