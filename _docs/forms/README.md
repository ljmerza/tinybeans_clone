# TanStack Form + Zod - Developer Guide

## Quick Start

### Creating a New Form

**1. Import the schema and helper:**
```typescript
import { zodValidator } from '@/lib/form/index.js'
import { mySchema, type MyFormData } from '@/lib/validations/schemas/my-schema.js'
import { useForm } from '@tanstack/react-form'
```

**2. Set up the form:**
```typescript
const form = useForm<MyFormData>({
  defaultValues: {
    email: '',
    password: '',
  },
  onSubmit: async ({ value }) => {
    await api.submitForm(value)
  },
})
```

**3. Add validated fields:**
```typescript
<form.Field
  name="email"
  validators={{
    onBlur: zodValidator(mySchema.shape.email),
  }}
>
  {(field) => (
    <div>
      <input
        value={field.state.value}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
      />
      {field.state.meta.errors?.[0] && (
        <span className="error">{field.state.meta.errors[0]}</span>
      )}
    </div>
  )}
</form.Field>
```

**That's it!** No custom hooks, no complex setup.

## Validation Schemas

### Available Schemas

Schemas are organized by feature for optimal code splitting:

```
lib/validations/schemas/
├── common.ts          # emailSchema, usernameSchema, passwordSchema, identifierSchema
├── login.ts           # loginSchema
├── signup.ts          # signupSchema (with password matching)
├── magic-link.ts      # magicLinkRequestSchema
├── password-reset.ts  # passwordResetRequestSchema, passwordResetConfirmSchema
└── twofa.ts          # verificationCodeSchema, phoneNumberSchema, deviceNameSchema
```

### Creating a New Schema

Create a new file for your feature:

```typescript
// lib/validations/schemas/my-feature.ts
import { z } from 'zod'
import { emailSchema } from './common.js' // Reuse common schemas

export const myFeatureSchema = z.object({
  email: emailSchema,
  customField: z.string().min(5, 'validation.custom_field_min'),
})

export type MyFeatureFormData = z.infer<typeof myFeatureSchema>
```

**Import only what you need:**
```typescript
// ✅ Good - specific import, better code splitting
import { myFeatureSchema } from '@/lib/validations/schemas/my-feature.js'

// ⚠️ OK but less optimal - loads all schemas
import { myFeatureSchema } from '@/lib/validations/schemas/index.js'
```

### Cross-Field Validation

Use Zod's `.refine()` for validation that depends on multiple fields:

```typescript
export const signupSchema = z
  .object({
    password: passwordSchema,
    password_confirm: z.string(),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: 'validation.passwords_must_match',
    path: ['password_confirm'], // Shows error on this field
  })
```

### Conditional Validation

```typescript
export const profileSchema = z.object({
  receiveEmails: z.boolean(),
  email: z.string().email().optional(),
}).refine(
  (data) => !data.receiveEmails || data.email,
  {
    message: 'Email required when notifications enabled',
    path: ['email'],
  }
)
```

## Form Utilities

### zodValidator

Converts Zod schema validation to TanStack Form format:

```typescript
import { zodValidator } from '@/lib/form'

// In your form field:
validators: {
  onBlur: zodValidator(mySchema.shape.fieldName),
  onChange: zodValidator(mySchema.shape.fieldName), // Can also validate on change
}
```

### Server Error Handling

Handle Django/DRF error responses:

```typescript
import { mapServerErrors, getGeneralErrors } from '@/lib/form'

try {
  await api.submit(value)
} catch (error: any) {
  const serverErrors = error.response?.data?.errors
  
  if (serverErrors) {
    // Map field-specific errors
    const fieldErrors = mapServerErrors(serverErrors)
    // { email: "This email is already taken", username: "Too short" }
    
    // Get general/non-field errors
    const generalErrors = getGeneralErrors(serverErrors)
    // ["Invalid request", "Another error"]
    
    if (generalErrors.length > 0) {
      setGeneralError(generalErrors.join('. '))
    }
  }
}
```

## Common Patterns

### Pattern 1: Simple Form

```typescript
import { useForm } from '@tanstack/react-form'
import { zodValidator } from '@/lib/form/index.js'
import { loginSchema, type LoginFormData } from '@/lib/validations/schemas/login.js'

function LoginForm() {
  const login = useLogin() // TanStack Query mutation

  const form = useForm<LoginFormData>({
    defaultValues: { username: '', password: '' },
    onSubmit: async ({ value }) => {
      await login.mutateAsync(value)
    },
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit() }}>
      <form.Field
        name="username"
        validators={{ onBlur: zodValidator(loginSchema.shape.username) }}
      >
        {(field) => (
          <div>
            <input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
            />
            {field.state.meta.errors?.[0] && (
              <span>{field.state.meta.errors[0]}</span>
            )}
          </div>
        )}
      </form.Field>
      
      <button type="submit" disabled={form.state.isSubmitting}>
        {form.state.isSubmitting ? 'Loading...' : 'Submit'}
      </button>
    </form>
  )
}
```

### Pattern 2: Form with Server Errors

```typescript
function SignupForm() {
  const [generalError, setGeneralError] = useState('')
  const signup = useSignup()

  const form = useForm<SignupFormData>({
    defaultValues: { username: '', email: '', password: '', password_confirm: '' },
    onSubmit: async ({ value }) => {
      setGeneralError('')
      try {
        await signup.mutateAsync(value)
      } catch (error: any) {
        const errors = error.response?.data?.errors
        if (errors) {
          const general = getGeneralErrors(errors)
          if (general.length > 0) {
            setGeneralError(general.join('. '))
          }
        } else {
          setGeneralError(error.message || 'Signup failed')
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

### Pattern 3: Accessible Form Field

```typescript
<form.Field
  name="email"
  validators={{ onBlur: zodValidator(schema.shape.email) }}
>
  {(field) => {
    const hasError = field.state.meta.isTouched && field.state.meta.errors?.[0]
    
    return (
      <div>
        <label htmlFor={field.name}>Email</label>
        <input
          id={field.name}
          name={field.name}
          type="email"
          value={field.state.value}
          onChange={(e) => field.handleChange(e.target.value)}
          onBlur={field.handleBlur}
          aria-invalid={hasError ? 'true' : 'false'}
          aria-describedby={hasError ? `${field.name}-error` : undefined}
        />
        {hasError && (
          <span id={`${field.name}-error`} role="alert">
            {field.state.meta.errors[0]}
          </span>
        )}
      </div>
    )
  }}
</form.Field>
```

## Best Practices

### DO ✅

- **Import specific schemas** for better code splitting
- **Use `z.infer` for types** instead of manual type definitions
- **Validate on blur** for better UX (users get feedback after leaving field)
- **Use i18n keys** in error messages (`'validation.email_required'`)
- **Handle loading states** with `form.state.isSubmitting`
- **Clear errors** before resubmitting
- **Keep schemas in separate files** by feature

### DON'T ❌

- **Don't create inline schemas** - use centralized schemas
- **Don't manually validate** - use `zodValidator` helper
- **Don't skip error display** - always show field errors to users
- **Don't validate on every keystroke** - use `onBlur` unless specific reason
- **Don't create custom form hooks** - `useForm` is already perfect
- **Don't put all schemas in one file** - splits them by feature

## TypeScript Tips

### Type Inference

Let Zod infer your types automatically:

```typescript
const mySchema = z.object({
  email: z.string().email(),
  age: z.number().min(18),
})

// ✅ Good - automatic type inference
type MyFormData = z.infer<typeof mySchema>
// Result: { email: string; age: number }

// ❌ Bad - manual type definition that can get out of sync
type MyFormData = {
  email: string
  age: number
}
```

### Optional Fields

```typescript
const schema = z.object({
  email: z.string().email(),
  phone: z.string().optional(), // phone?: string | undefined
  website: z.string().nullable(), // website: string | null
})
```

### Default Values

```typescript
const schema = z.object({
  notifications: z.boolean().default(true),
  theme: z.enum(['light', 'dark']).default('light'),
})
```

## Testing

### Testing Schemas

```typescript
import { describe, test, expect } from 'vitest'
import { loginSchema } from '@/lib/validations/schemas/login'

describe('loginSchema', () => {
  test('validates correct data', () => {
    const result = loginSchema.safeParse({
      username: 'testuser',
      password: 'password123',
    })
    expect(result.success).toBe(true)
  })

  test('rejects short password', () => {
    const result = loginSchema.safeParse({
      username: 'testuser',
      password: 'short',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.errors[0].path).toEqual(['password'])
    }
  })
})
```

### Testing Forms

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginForm } from './LoginForm'

test('shows validation error for empty username', async () => {
  const user = userEvent.setup()
  render(<LoginForm />)
  
  const input = screen.getByLabelText(/username/i)
  await user.click(input)
  await user.tab() // Trigger onBlur
  
  expect(screen.getByText(/username is required/i)).toBeInTheDocument()
})
```

## Troubleshooting

### "Failed to resolve import"

**Problem**: Vite can't find schema files

**Solution**: Make sure imports use `.js` extensions:
```typescript
// ✅ Correct
import { schema } from './schemas/my-schema.js'

// ❌ Wrong
import { schema } from './schemas/my-schema'
```

### Validation Not Triggering

**Problem**: Errors don't show on blur

**Solution**: Check that you're using `field.handleBlur`:
```typescript
<input
  onBlur={field.handleBlur} // ← Required!
  value={field.state.value}
  onChange={(e) => field.handleChange(e.target.value)}
/>
```

### Type Errors with Schema

**Problem**: TypeScript complains about form data types

**Solution**: Make sure you're using the inferred type:
```typescript
const form = useForm<MyFormData>({ // ← Add type parameter
  defaultValues: { ... },
})
```

## FAQ

**Q: Should I use `onChange` or `onBlur` for validation?**

A: Use `onBlur` for better UX. Users get feedback after leaving the field, not on every keystroke.

**Q: Can I add custom validation?**

A: Yes! Use Zod's `.refine()` method:
```typescript
z.string().refine(val => val.includes('@'), {
  message: 'Must contain @',
})
```

**Q: How do I handle async validation (checking if email exists)?**

A: Do this on the server side. Client-side async validation creates race conditions.

**Q: Should I create a wrapper component for form fields?**

A: Only if you have many repeated patterns. Start with inline and extract later if needed.

**Q: Can I use this with React Hook Form?**

A: No, this is TanStack Form specific. They have different APIs.

## Resources

- [TanStack Form Docs](https://tanstack.com/form/latest)
- [Zod Documentation](https://zod.dev/)
- [Schema Examples](/docs/forms/EXAMPLES.md)
- [Implementation Progress](/docs/forms/IMPLEMENTATION-PROGRESS.md)
- [Epic Details](/docs/architecture/epics/TANSTACK-FORM-ZOD-STANDARDIZATION.md)

---

**Need help?** Ask in the team channel or check existing forms in `features/auth/components` for examples.
