# Epic: TanStack Form & Zod Validation Standardization

## Overview

This epic establishes standardized patterns for form management across the web/ application using TanStack Form v1.0 integrated with Zod validation schemas. This implementation directly supports ADR-013 (Frontend Architecture Modernization) by providing type-safe, maintainable form patterns that eliminate boilerplate and improve developer experience.

## Goals

- Standardize all form implementations using TanStack Form with Zod validation
- Create reusable form components and validation schemas
- Eliminate inconsistent manual validation patterns
- Improve type safety from schema definition to form submission
- Reduce form-related bugs through runtime validation
- Establish clear patterns for error handling and display
- Create developer documentation and migration guides

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

#### 2. Form Field Components

**Location**: `src/components/form/`

Reusable form field components that integrate TanStack Form with UI components:

```typescript
// src/components/form/FormInput.tsx
import { FieldApi } from '@tanstack/react-form'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface FormInputProps<T> {
  field: FieldApi<T, any, any, any>
  label: string
  type?: string
  placeholder?: string
  autoComplete?: string
  disabled?: boolean
  required?: boolean
  className?: string
}

export function FormInput<T>({
  field,
  label,
  type = 'text',
  placeholder,
  autoComplete,
  disabled,
  required,
  className,
}: FormInputProps<T>) {
  const hasError = field.state.meta.isTouched && field.state.meta.errors.length > 0

  return (
    <div className={className}>
      <Label 
        htmlFor={field.name} 
        className={hasError ? 'text-red-600' : ''}
      >
        {label}
        {required && <span className="text-red-600 ml-1">*</span>}
      </Label>
      <Input
        id={field.name}
        name={field.name}
        type={type}
        value={field.state.value as string}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
        placeholder={placeholder}
        autoComplete={autoComplete}
        disabled={disabled}
        required={required}
        aria-invalid={hasError}
        aria-describedby={hasError ? `${field.name}-error` : undefined}
        className={hasError ? 'border-red-500 focus:ring-red-500' : ''}
      />
      {hasError && (
        <p 
          id={`${field.name}-error`}
          className="mt-1 text-sm text-red-600"
          role="alert"
        >
          {field.state.meta.errors[0]}
        </p>
      )}
    </div>
  )
}
```

#### 3. Form Utilities

**Location**: `src/lib/form/`

Helper functions for common form operations:

```typescript
// src/lib/form/validators.ts
import { ZodSchema } from 'zod'
import { FieldValidatorFn } from '@tanstack/react-form'

/**
 * Create a TanStack Form validator from a Zod schema
 */
export function createZodValidator<T>(
  schema: ZodSchema<T>
): FieldValidatorFn<any, any, any, any, T> {
  return ({ value }) => {
    const result = schema.safeParse(value)
    if (result.success) {
      return undefined
    }
    return result.error.errors[0]?.message ?? 'Validation failed'
  }
}

/**
 * Validate entire form with Zod schema
 */
export function createFormValidator<T>(schema: ZodSchema<T>) {
  return (values: T) => {
    const result = schema.safeParse(values)
    if (result.success) {
      return undefined
    }
    
    // Convert Zod errors to field errors
    const fieldErrors: Record<string, string> = {}
    for (const error of result.error.errors) {
      const path = error.path.join('.')
      if (!fieldErrors[path]) {
        fieldErrors[path] = error.message
      }
    }
    return fieldErrors
  }
}

// src/lib/form/serverErrors.ts
/**
 * Map server validation errors to form field errors
 */
export function mapServerErrors(
  serverErrors: Record<string, string[]>,
  t: (key: string) => string
): Record<string, string> {
  const fieldErrors: Record<string, string> = {}
  
  for (const [field, messages] of Object.entries(serverErrors)) {
    // Translate error messages if they are i18n keys
    const translatedMessages = messages.map(msg => 
      msg.startsWith('validation.') ? t(msg) : msg
    )
    fieldErrors[field] = translatedMessages.join('. ')
  }
  
  return fieldErrors
}

/**
 * Extract non-field errors from server response
 */
export function extractGeneralErrors(
  serverErrors: Record<string, string[]>
): string[] {
  const nonFieldKeys = ['__all__', 'non_field_errors', 'detail']
  const generalErrors: string[] = []
  
  for (const key of nonFieldKeys) {
    if (serverErrors[key]) {
      generalErrors.push(...serverErrors[key])
    }
  }
  
  return generalErrors
}
```

#### 4. Form Hooks

**Location**: `src/lib/form/hooks/`

Custom hooks for common form patterns:

```typescript
// src/lib/form/hooks/useStandardForm.ts
import { useForm, FormOptions } from '@tanstack/react-form'
import { ZodSchema } from 'zod'
import { useState } from 'react'
import { createFormValidator, mapServerErrors, extractGeneralErrors } from '../validators'
import { useTranslation } from 'react-i18next'

interface UseStandardFormOptions<TData> extends Omit<FormOptions<TData>, 'onSubmit'> {
  schema: ZodSchema<TData>
  onSubmit: (data: TData) => Promise<void>
  onSuccess?: () => void
  onError?: (error: any) => void
}

export function useStandardForm<TData>({
  schema,
  onSubmit,
  onSuccess,
  onError,
  ...options
}: UseStandardFormOptions<TData>) {
  const { t } = useTranslation()
  const [generalError, setGeneralError] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<TData>({
    ...options,
    onSubmit: async ({ value }) => {
      setGeneralError('')
      setIsSubmitting(true)

      try {
        // Client-side validation
        const validationResult = schema.safeParse(value)
        if (!validationResult.success) {
          const firstError = validationResult.error.errors[0]
          setGeneralError(t(firstError.message))
          return
        }

        // Submit to server
        await onSubmit(value)
        onSuccess?.()
      } catch (error: any) {
        console.error('Form submission error:', error)

        // Handle server validation errors
        if (error.response?.data?.errors) {
          const serverErrors = error.response.data.errors
          
          // Map field errors
          const fieldErrors = mapServerErrors(serverErrors, t)
          // TODO: Set field errors on form
          
          // Extract general errors
          const generalErrors = extractGeneralErrors(serverErrors)
          if (generalErrors.length > 0) {
            setGeneralError(generalErrors.join('. '))
          }
        } else {
          setGeneralError(error.message || t('errors.submission_failed'))
        }

        onError?.(error)
      } finally {
        setIsSubmitting(false)
      }
    },
  })

  return {
    form,
    generalError,
    setGeneralError,
    isSubmitting,
  }
}
```

### Implementation Patterns

#### Standard Form Pattern

```typescript
// Example: features/auth/components/LoginForm.tsx
import { useStandardForm } from '@/lib/form/hooks/useStandardForm'
import { FormInput } from '@/components/form/FormInput'
import { loginSchema, LoginFormData } from '@/lib/validations/schemas/auth.schemas'
import { createZodValidator } from '@/lib/form/validators'
import { useLogin } from '../hooks/authHooks'
import { Button } from '@/components/ui/button'
import { StatusMessage } from '@/components/StatusMessage'

export function LoginForm() {
  const { t } = useTranslation()
  const login = useLogin()

  const { form, generalError, isSubmitting } = useStandardForm<LoginFormData>({
    defaultValues: {
      username: '',
      password: '',
    },
    schema: loginSchema,
    onSubmit: async (data) => {
      await login.mutateAsync(data)
    },
    onSuccess: () => {
      // Navigate or show success message
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        e.stopPropagation()
        form.handleSubmit()
      }}
      className="space-y-4"
      noValidate
    >
      {generalError && (
        <StatusMessage variant="error" role="alert">
          {generalError}
        </StatusMessage>
      )}

      <form.Field
        name="username"
        validators={{
          onBlur: createZodValidator(loginSchema.shape.username),
        }}
      >
        {(field) => (
          <FormInput
            field={field}
            label={t('auth.login.username')}
            autoComplete="username"
            required
          />
        )}
      </form.Field>

      <form.Field
        name="password"
        validators={{
          onBlur: createZodValidator(loginSchema.shape.password),
        }}
      >
        {(field) => (
          <FormInput
            field={field}
            label={t('auth.login.password')}
            type="password"
            autoComplete="current-password"
            required
          />
        )}
      </form.Field>

      <Button 
        type="submit" 
        className="w-full" 
        disabled={isSubmitting}
      >
        {isSubmitting ? t('auth.login.signing_in') : t('auth.login.sign_in')}
      </Button>
    </form>
  )
}
```

## Implementation Phases

### Phase 1: Foundation (Week 1) - 5 story points

**Objective**: Establish core infrastructure and patterns

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

#### Story 1.2: Build Form Utilities (2 SP)
**Description**: Create utility functions for form validation and error handling

**Tasks**:
- Implement `createZodValidator` function
- Implement `createFormValidator` function
- Implement server error mapping utilities
- Add error extraction helpers
- Create comprehensive unit tests

**Acceptance Criteria**:
- [ ] Validators correctly convert Zod errors to TanStack Form format
- [ ] Server error mapping handles all backend error formats
- [ ] General error extraction identifies non-field errors
- [ ] 90%+ test coverage for utilities
- [ ] TypeScript types are properly inferred

**Definition of Done**:
- All utility functions implemented and tested
- Documentation with usage examples
- Edge cases covered in tests

#### Story 1.3: Create Reusable Form Components (1 SP)
**Description**: Build accessible form field components

**Tasks**:
- Create `FormInput` component
- Create `FormTextarea` component
- Create `FormSelect` component
- Create `FormCheckbox` component
- Ensure WCAG AA compliance
- Add Storybook stories (if applicable)

**Acceptance Criteria**:
- [ ] All components properly integrate with TanStack Form
- [ ] Error states are displayed accessibly
- [ ] Components support all common HTML attributes
- [ ] ARIA attributes are correctly applied
- [ ] Components are keyboard navigable
- [ ] Focus management works correctly

**Definition of Done**:
- Components implemented with proper TypeScript types
- Accessibility tested with axe-core
- Visual regression tests added

### Phase 2: Authentication Forms Migration (Week 2) - 8 story points

**Objective**: Migrate all authentication-related forms to standard pattern

#### Story 2.1: Migrate LoginCard (2 SP)
**Description**: Convert LoginCard to use standardized form pattern

**Tasks**:
- Update LoginCard to use `useStandardForm` hook
- Apply `loginSchema` for validation
- Use `FormInput` components
- Update error handling to use standardized pattern
- Add comprehensive tests

**Acceptance Criteria**:
- [ ] Form uses TanStack Form with Zod validation
- [ ] Field-level validation works on blur
- [ ] Server errors are properly displayed
- [ ] Accessibility maintained or improved
- [ ] All existing functionality preserved
- [ ] Tests achieve 80%+ coverage

**Definition of Done**:
- Form migrated and tested
- Visual appearance unchanged
- No regressions in functionality

#### Story 2.2: Migrate SignupCard (2 SP)
**Description**: Convert SignupCard with password confirmation pattern

**Tasks**:
- Create `signupSchema` with password matching
- Implement custom validation for password confirmation
- Update component to use standard pattern
- Handle terms acceptance checkbox
- Add form-level validation

**Acceptance Criteria**:
- [ ] Password and confirmation fields validate correctly
- [ ] Form-level validation catches password mismatch
- [ ] All field validations work independently
- [ ] Error messages are clear and actionable
- [ ] Tests cover password matching edge cases

**Definition of Done**:
- Signup flow fully functional
- Password matching works correctly
- Comprehensive test coverage

#### Story 2.3: Migrate Password Reset Forms (2 SP)
**Description**: Convert both password reset request and confirm forms

**Tasks**:
- Create schemas for reset request (email) and confirm (password)
- Migrate PasswordResetRequestCard
- Migrate PasswordResetConfirmCard
- Ensure email validation is robust
- Handle token validation errors

**Acceptance Criteria**:
- [ ] Both forms use standardized patterns
- [ ] Email validation follows RFC standards
- [ ] Password complexity rules enforced
- [ ] Token errors displayed appropriately
- [ ] Success states handled consistently

**Definition of Done**:
- Both forms migrated and tested
- Full password reset flow tested end-to-end

#### Story 2.4: Migrate MagicLinkRequestCard (2 SP)
**Description**: Convert magic link request form

**Tasks**:
- Create `magicLinkSchema`
- Migrate component to standard pattern
- Update success/error messaging
- Test with various email formats

**Acceptance Criteria**:
- [ ] Email validation works correctly
- [ ] Success message displayed appropriately
- [ ] Error handling matches standard pattern
- [ ] Loading states properly managed

**Definition of Done**:
- Magic link flow fully functional
- Error cases well handled

### Phase 3: 2FA Forms Migration (Week 3) - 6 story points

**Objective**: Migrate two-factor authentication forms

#### Story 3.1: Migrate TwoFactorSetup Components (3 SP)
**Description**: Convert TOTP, Email, and SMS setup wizards

**Tasks**:
- Create schemas for each 2FA method setup
- Migrate TOTP setup with QR code display
- Migrate Email/SMS setup with code verification
- Implement multi-step form pattern if needed
- Validate verification codes with proper format

**Acceptance Criteria**:
- [ ] Each setup method uses standardized form
- [ ] QR code generation not affected
- [ ] Verification code validation uses Zod
- [ ] Error messages are specific to method
- [ ] Success flows maintained

**Definition of Done**:
- All three setup methods migrated
- End-to-end setup flows tested

#### Story 3.2: Migrate TwoFactorVerify Component (2 SP)
**Description**: Convert 2FA verification form

**Tasks**:
- Create `verificationCodeSchema`
- Migrate verification component
- Handle remember device checkbox
- Implement proper code masking/formatting
- Test verification flow

**Acceptance Criteria**:
- [ ] 6-digit code validation works
- [ ] Code formatting/masking applied
- [ ] Remember device option functions
- [ ] Invalid code errors clear
- [ ] Rate limiting respected

**Definition of Done**:
- Verification flow fully functional
- Security considerations maintained

#### Story 3.3: Migrate Trusted Devices Management (1 SP)
**Description**: Update device management forms

**Tasks**:
- Create schema for device naming
- Update device removal confirmation
- Apply standard patterns to any inputs

**Acceptance Criteria**:
- [ ] Device naming uses standard validation
- [ ] Confirmation patterns consistent
- [ ] Error handling standardized

**Definition of Done**:
- Device management fully migrated

### Phase 4: Profile & Settings Forms (Week 4) - 5 story points

**Objective**: Migrate remaining forms

#### Story 4.1: Migrate Profile Edit Form (3 SP)
**Description**: Convert user profile editing form

**Tasks**:
- Create comprehensive `profileSchema`
- Handle optional fields properly
- Implement conditional validation (if needed)
- Support file upload for avatar
- Handle partial updates

**Acceptance Criteria**:
- [ ] All profile fields validate correctly
- [ ] Optional fields handled properly
- [ ] Avatar upload integrated (if needed)
- [ ] Partial update support maintained
- [ ] Success/error feedback clear

**Definition of Done**:
- Profile edit fully functional
- All validation rules applied

#### Story 4.2: Migrate Password Change Form (2 SP)
**Description**: Convert password change form with current password verification

**Tasks**:
- Create `passwordChangeSchema` with three fields
- Validate current password
- Enforce new password complexity
- Confirm new password matches
- Handle security requirements

**Acceptance Criteria**:
- [ ] Current password verified
- [ ] New password complexity enforced
- [ ] Password confirmation validated
- [ ] Security requirements met
- [ ] Clear error messages

**Definition of Done**:
- Password change fully functional
- Security maintained or improved

### Phase 5: Documentation & Tooling (Week 5) - 3 story points

**Objective**: Create comprehensive documentation and developer tools

#### Story 5.1: Developer Documentation (1 SP)
**Description**: Create comprehensive guide for form implementation

**Tasks**:
- Write "Creating Forms" guide
- Document standard patterns
- Provide code examples
- Create troubleshooting section
- Add API reference for utilities

**Deliverables**:
- `docs/forms/README.md` - Main guide
- `docs/forms/PATTERNS.md` - Common patterns
- `docs/forms/MIGRATION.md` - Migration guide
- Code examples in docs/forms/examples/

**Acceptance Criteria**:
- [ ] Guide covers all common scenarios
- [ ] Examples are copy-paste ready
- [ ] Troubleshooting covers known issues
- [ ] API reference is complete

**Definition of Done**:
- Documentation reviewed by team
- Examples tested and working

#### Story 5.2: Form Generator CLI Tool (1 SP)
**Description**: Create CLI tool to scaffold new forms

**Tasks**:
- Create form template generator
- Support different form types (basic, multi-step, etc.)
- Auto-generate schema boilerplate
- Generate component with standard pattern
- Include test template

**Example Usage**:
```bash
npm run generate:form auth/login
# Creates:
# - src/features/auth/components/LoginForm.tsx
# - src/lib/validations/schemas/auth.schemas.ts (if not exists)
# - src/features/auth/components/__tests__/LoginForm.test.tsx
```

**Acceptance Criteria**:
- [ ] Tool generates working form component
- [ ] Generated code follows standards
- [ ] Schema is properly typed
- [ ] Tests scaffold is included

**Definition of Done**:
- CLI tool working and documented
- Team trained on usage

#### Story 5.3: Linting & Quality Gates (1 SP)
**Description**: Add automated checks for form patterns

**Tasks**:
- Create ESLint rule to detect non-standard forms
- Add pre-commit hook for form validation
- Create CI check for form standards
- Add bundle size monitoring for form deps

**Acceptance Criteria**:
- [ ] ESLint detects old form patterns
- [ ] CI fails on non-compliant forms
- [ ] Bundle size tracked
- [ ] Documentation for bypassing rules (if needed)

**Definition of Done**:
- Quality gates active in CI/CD
- Team aware of new checks

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

**Total Duration**: 5 weeks (27 story points)

### Budget Considerations

- No additional software costs (all dependencies already in place)
- Training time: ~4 hours team-wide
- Documentation time: ~8 hours
- Code review time: ~2 hours per form migration

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

**Total Estimated Hours**: 52 hours (~1.3 sprints for one developer)

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
