# Frontend Architecture Migration Quick Guide

**Related ADR**: [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)

This guide provides practical steps for implementing the new feature-based frontend architecture.

## Quick Reference

```
OLD: src/modules/           NEW: src/features/
OLD: modules/login/routes.login.tsx    NEW: routes/login.tsx (thin) + features/auth/components/LoginForm.tsx
```

## Phase 1: Setup (Week 1)

### 1. Create Feature Structure

```bash
cd web/src
mkdir -p features/auth/{components,hooks,api,types,utils}
mkdir -p features/twofa/{components,hooks,api,types}
```

### 2. Update TypeScript Config

Edit `web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/features/*": ["./src/features/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"]
    }
  }
}
```

### 3. Update Vite Config

Edit `web/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/features': path.resolve(__dirname, './src/features'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/lib': path.resolve(__dirname, './src/lib'),
    },
  },
})
```

## Phase 2: Migrate Auth Feature (Week 2)

### Step 1: Move Components

```bash
# Move login components
mv src/modules/login/routes.login.tsx src/features/auth/components/LoginForm.tsx
mv src/modules/login/routes.signup.tsx src/features/auth/components/SignupForm.tsx

# Update these files to be components instead of route files
# Remove createFileRoute() calls
# Export as regular React components
```

### Step 2: Move Hooks

```bash
# Move hooks
mv src/modules/login/hooks.ts src/features/auth/hooks/
mv src/modules/login/useAuthCheck.ts src/features/auth/hooks/

# Split hooks.ts into individual files if needed
```

### Step 3: Move API and Types

```bash
# Move API client
mv src/modules/login/client.ts src/features/auth/api/authClient.ts

# Move types
mv src/modules/login/types.ts src/features/auth/types/auth.types.ts

# Move store
mv src/modules/login/store.ts src/features/auth/store/authStore.ts
```

### Step 4: Create Feature Index

Create `src/features/auth/index.ts`:

```typescript
// Components
export { LoginForm } from './components/LoginForm'
export { SignupForm } from './components/SignupForm'
export { MagicLinkForm } from './components/MagicLinkForm'

// Hooks
export { useLogin } from './hooks/useLogin'
export { useSignup } from './hooks/useSignup'
export { useAuthCheck } from './hooks/useAuthCheck'

// Types (only public ones)
export type { AuthUser, LoginCredentials, SignupData } from './types/auth.types'
```

### Step 5: Update Route Files

Edit `src/routes/login.tsx`:

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { LoginForm } from '@/features/auth'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6">
        <LoginForm />
      </div>
    </div>
  )
}
```

### Step 6: Update Imports

Search and replace imports across the codebase:

```bash
# Find all files importing from modules/login
grep -r "from '@/modules/login'" src/

# Update imports to use new feature structure
# Before: import { useLogin } from '@/modules/login/hooks'
# After:  import { useLogin } from '@/features/auth'
```

### Step 7: Test

```bash
npm run dev
# Test all login/signup flows
# Test magic link
# Verify no console errors
```

### Step 8: Clean Up

```bash
# Remove old modules/login directory
rm -rf src/modules/login
```

## Phase 3: Migrate 2FA Feature (Week 3)

Follow same pattern as Auth:

```bash
# 1. Create structure
mkdir -p src/features/twofa/{components,hooks,api,types}

# 2. Move files
mv src/modules/twofa/* src/features/twofa/

# 3. Organize into subdirectories
# components/ - all component files
# hooks/ - all hook files
# api/ - client.ts
# types/ - types.ts

# 4. Create index.ts with exports

# 5. Update route files in src/routes/2fa/

# 6. Update imports

# 7. Test thoroughly

# 8. Remove old modules/twofa/
```

## Component Conversion Template

### Before (Route File in modules/)

```typescript
// modules/login/routes.login.tsx
import { createRoute } from '@tanstack/react-router'
// ... lots of code ...

export const loginRoute = createRoute({
  path: '/login',
  component: LoginPage,
})

function LoginPage() {
  // ... component code ...
}
```

### After (Split into Route + Feature Component)

```typescript
// routes/login.tsx
import { createFileRoute } from '@tanstack/react-router'
import { LoginForm } from '@/features/auth'

export const Route = createFileRoute('/login')({
  component: () => (
    <div className="container">
      <LoginForm />
    </div>
  ),
})
```

```typescript
// features/auth/components/LoginForm.tsx
import { useLogin } from '../hooks/useLogin'

export function LoginForm() {
  // ... component code (moved from route file) ...
}
```

## Testing Checklist

After each migration phase:

- [ ] Run `npm run build` - should complete without errors
- [ ] Run `npm run dev` - should start without errors
- [ ] Test all routes manually
- [ ] Verify no console errors
- [ ] Check that hot reload works
- [ ] Verify imports are correct
- [ ] Run any existing tests

## Common Issues

### Issue: Import Path Not Found

**Problem**: `Cannot find module '@/features/auth'`

**Solution**: 
1. Check `tsconfig.json` has correct path aliases
2. Check `vite.config.ts` has correct resolve aliases
3. Restart dev server

### Issue: Circular Dependency

**Problem**: Feature components importing from each other

**Solution**:
- Check feature `index.ts` - only export what's needed externally
- Features should not import from other features
- Extract shared code to `src/lib/` or `src/components/`

### Issue: Route Not Working

**Problem**: Route doesn't load after migration

**Solution**:
1. Check route file uses `createFileRoute()` correctly
2. Verify route file is in correct location in `src/routes/`
3. Check that component is actually exported from feature
4. Verify imports are correct

## Validation Script

```bash
#!/bin/bash
# validate-structure.sh

echo "Validating frontend structure..."

# Check for duplicate route files
echo "Checking for duplicate routes..."
if ls src/modules/*/routes.*.tsx 2>/dev/null; then
  echo "❌ Found route files in modules/ - these should be in routes/"
  exit 1
fi

# Check features have index.ts
echo "Checking feature exports..."
for dir in src/features/*; do
  if [ ! -f "$dir/index.ts" ]; then
    echo "❌ Missing index.ts in $dir"
    exit 1
  fi
done

# Check no modules directory exists
if [ -d "src/modules" ]; then
  echo "⚠️  src/modules/ still exists - migration not complete"
fi

echo "✅ Structure validation passed!"
```

## Next Steps

1. **Review ADR-011** for full context and rationale
2. **Start with Phase 1** setup
3. **Migrate one feature at a time** (auth, then 2fa)
4. **Update documentation** as you go
5. **Get team feedback** after each phase

## Questions?

- Check [ADR-011](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md) for detailed decisions
- Review example structure in the ADR
- Look at existing migrated features as examples

---

**Last Updated**: 2025-01-15
**Status**: Ready to implement after ADR-011 is accepted
