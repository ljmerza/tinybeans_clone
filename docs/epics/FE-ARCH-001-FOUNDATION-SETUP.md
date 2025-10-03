# Epic 1: Frontend Architecture Foundation & Infrastructure Setup

**Epic ID**: FE-ARCH-001  
**Status**: Ready  
**Priority**: P1 - High Priority  
**Sprint**: Week 1  
**Estimated Effort**: 3 story points  
**Dependencies**: None  
**Related ADR**: [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)

---

## Epic Goal

Establish the foundational infrastructure for the new feature-based architecture without breaking existing functionality. This includes creating directory structures, updating build configurations, setting up development tools, and documenting the new patterns.

---

## Business Value

- **Developer Productivity**: Clear patterns reduce decision-making time
- **Code Quality**: Standardized structure improves maintainability
- **Team Velocity**: Faster onboarding and feature development
- **Technical Debt**: Prevents accumulation of inconsistent patterns

**Expected Impact**: 
- 30% reduction in "where does this go?" questions
- 50% faster file discovery time
- Zero new technical debt from unclear organization

---

## User Stories

### Story 1.1: Create Features Directory Structure

**As a** frontend developer  
**I want** a standardized `features/` directory structure  
**So that** I know where to place feature-specific code

**Acceptance Criteria:**
1. `src/features/` directory created with README
2. Template subdirectory structure documented
3. Structure doesn't break existing builds
4. Directory structure follows naming conventions
5. Documentation explains when to use features vs components

**Technical Notes:**
```bash
# Create base structure
web/src/
└── features/
    ├── README.md               # Documents feature organization
    ├── .gitkeep                # Ensures directory is tracked
    └── _template/              # Template for new features
        ├── index.ts            # Public exports
        ├── components/
        │   └── .gitkeep
        ├── hooks/
        │   └── .gitkeep
        ├── api/
        │   └── .gitkeep
        ├── types/
        │   └── .gitkeep
        └── utils/
            └── .gitkeep
```

**README.md Content:**
- Explanation of feature-based architecture
- When to create a new feature vs add to existing
- Naming conventions
- Import/export patterns
- Examples from the codebase

**Definition of Done:**
- [ ] Directory structure created
- [ ] README.md written and reviewed
- [ ] Template directory with all subdirectories
- [ ] Build succeeds (`npm run build`)
- [ ] No existing functionality broken

---

### Story 1.2: Update TypeScript Configuration

**As a** frontend developer  
**I want** TypeScript path aliases configured  
**So that** I can use clean imports like `@/features/auth`

**Acceptance Criteria:**
1. `tsconfig.json` updated with path aliases
2. Path aliases work in development
3. Path aliases work in production builds
4. IDE autocomplete works with new paths
5. No existing imports broken

**Technical Implementation:**

```json
// web/tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/features/*": ["./src/features/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/routes/*": ["./src/routes/*"]
    }
  }
}
```

**Validation:**
```typescript
// Test imports work
import { useLogin } from '@/features/auth'
import { Button } from '@/components/ui/button'
import { validateEmail } from '@/lib/validations'
```

**Definition of Done:**
- [ ] `tsconfig.json` updated
- [ ] TypeScript compiler accepts new paths
- [ ] IDE shows autocomplete for new paths
- [ ] `npm run build` succeeds
- [ ] `npm run dev` works with new paths
- [ ] No TypeScript errors introduced

---

### Story 1.3: Update Vite Build Configuration

**As a** frontend developer  
**I want** Vite configured with path aliases  
**So that** builds resolve imports correctly

**Acceptance Criteria:**
1. `vite.config.ts` updated with resolve aliases
2. Development server resolves new paths
3. Production builds resolve new paths
4. Hot module reload works with new structure
5. Build performance not degraded

**Technical Implementation:**

```typescript
// web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/features': path.resolve(__dirname, './src/features'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/lib': path.resolve(__dirname, './src/lib'),
      '@/routes': path.resolve(__dirname, './src/routes'),
    },
  },
})
```

**Testing:**
- Create test feature with imports
- Verify HMR works
- Build production bundle
- Check bundle size (should be similar)

**Definition of Done:**
- [ ] `vite.config.ts` updated
- [ ] Dev server starts without errors
- [ ] Production build succeeds
- [ ] HMR works with new paths
- [ ] Bundle size within 5% of current
- [ ] Source maps work correctly

---

### Story 1.4: Create Feature Template and Documentation

**As a** frontend developer  
**I want** a template and guide for creating new features  
**So that** all features follow consistent patterns

**Acceptance Criteria:**
1. Feature template directory created
2. Documentation explains feature structure
3. Examples show import/export patterns
4. Guidelines for component organization
5. Rules for feature boundaries

**Deliverables:**

**1. Feature Template (`src/features/_template/`):**
```typescript
// index.ts
/**
 * Public API for [Feature Name] feature
 * 
 * Only export what other features/routes need to consume.
 * Keep internal implementation details private.
 */

// Components
export { MainComponent } from './components/MainComponent'

// Hooks
export { useFeatureAction } from './hooks/useFeatureAction'

// Types (only public types)
export type { FeatureData, FeatureConfig } from './types'

// Do NOT export:
// - Internal components
// - Internal utilities
// - API client implementations (expose hooks instead)
```

**2. Feature Creation Guide:**
```markdown
# Creating a New Feature

## When to Create a Feature
- Contains 3+ related components
- Has dedicated business logic
- Represents a distinct domain concept
- Will be used across multiple routes

## Structure
feature-name/
├── index.ts              # Public exports ONLY
├── components/           # Feature-specific components
│   ├── MainComponent.tsx # Exported
│   └── Internal.tsx      # Internal only
├── hooks/                # Custom hooks
│   └── useFeatureAction.ts
├── api/                  # API client functions
│   └── featureClient.ts
├── types/                # TypeScript definitions
│   └── index.ts
└── utils/                # Feature utilities
    └── helpers.ts

## Naming Conventions
- Features: lowercase-with-dashes (e.g., user-profile)
- Components: PascalCase (e.g., UserProfile.tsx)
- Hooks: camelCase with 'use' prefix (e.g., useUserProfile.ts)
- Types: PascalCase (e.g., UserProfileData)

## Import Patterns
✅ Good: import { LoginForm } from '@/features/auth'
❌ Bad:  import { LoginForm } from '@/features/auth/components/LoginForm'

## Export Rules
- Export through index.ts ONLY
- Keep implementation details private
- Document public API with JSDoc
```

**Definition of Done:**
- [ ] Template directory with example files created
- [ ] Documentation written and reviewed
- [ ] Code examples tested
- [ ] Naming conventions documented
- [ ] Import/export patterns clear
- [ ] Boundary rules explained

---

### Story 1.5: Setup Development Tools and Validation

**As a** frontend developer  
**I want** automated tools to validate feature structure  
**So that** the architecture stays consistent

**Acceptance Criteria:**
1. NPM script to validate feature structure
2. Pre-commit hook checks feature organization
3. Documentation on running validation
4. CI integration plan documented
5. Clear error messages for violations

**Validation Script:**

```javascript
// scripts/validate-features.js
import fs from 'fs'
import path from 'path'

const FEATURES_DIR = 'src/features'
const REQUIRED_FILES = ['index.ts']
const ALLOWED_DIRS = ['components', 'hooks', 'api', 'types', 'utils', 'store']

function validateFeature(featurePath) {
  const errors = []
  const featureName = path.basename(featurePath)
  
  // Skip template and hidden directories
  if (featureName.startsWith('_') || featureName.startsWith('.')) {
    return []
  }
  
  // Check required files
  for (const file of REQUIRED_FILES) {
    const filePath = path.join(featurePath, file)
    if (!fs.existsSync(filePath)) {
      errors.push(`${featureName}: Missing required file ${file}`)
    }
  }
  
  // Check for unexpected directories
  const dirs = fs.readdirSync(featurePath, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name)
    
  for (const dir of dirs) {
    if (!ALLOWED_DIRS.includes(dir)) {
      errors.push(`${featureName}: Unexpected directory ${dir}`)
    }
  }
  
  // Check index.ts only exports from allowed paths
  const indexPath = path.join(featurePath, 'index.ts')
  if (fs.existsSync(indexPath)) {
    const content = fs.readFileSync(indexPath, 'utf-8')
    // Check for direct file imports (should go through subdirs)
    if (content.includes(`from './${featureName}`)) {
      errors.push(`${featureName}: index.ts should not export from root files`)
    }
  }
  
  return errors
}

function validateAllFeatures() {
  const features = fs.readdirSync(FEATURES_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => path.join(FEATURES_DIR, d.name))
  
  const allErrors = []
  for (const feature of features) {
    allErrors.push(...validateFeature(feature))
  }
  
  if (allErrors.length > 0) {
    console.error('❌ Feature validation errors:')
    allErrors.forEach(err => console.error(`  - ${err}`))
    process.exit(1)
  }
  
  console.log('✅ All features valid!')
}

validateAllFeatures()
```

**Package.json Scripts:**
```json
{
  "scripts": {
    "validate:features": "node scripts/validate-features.js",
    "validate:all": "npm run lint && npm run validate:features && npm run type-check"
  }
}
```

**Definition of Done:**
- [ ] Validation script created
- [ ] NPM scripts added
- [ ] Script runs successfully on current code
- [ ] Error messages are clear and helpful
- [ ] Documentation updated
- [ ] CI integration planned (for Epic 4)

---

## Technical Debt

### Identified
- None (this epic creates foundation)

### Introduced
- None expected (additive changes only)

---

## Testing Strategy

### Manual Testing
- [ ] Create test feature using template
- [ ] Verify imports work from test feature
- [ ] Build project successfully
- [ ] Run dev server successfully
- [ ] Verify HMR works

### Automated Testing
- [ ] Validation script passes
- [ ] TypeScript compilation succeeds
- [ ] No linting errors introduced
- [ ] All existing tests still pass

### Integration Testing
- [ ] Existing routes still load
- [ ] Existing components still work
- [ ] No console errors in browser
- [ ] Build output similar to before

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Path aliases break existing imports | High | Low | Test thoroughly before committing, keep old paths working |
| Build configuration issues | High | Low | Test both dev and prod builds extensively |
| Team confusion about new structure | Medium | Medium | Clear documentation, training session |
| IDE doesn't support new paths | Medium | Low | Document IDE configuration for common editors |

---

## Definition of Done

### Epic Level
- [ ] All 5 stories completed
- [ ] Directory structure created and documented
- [ ] TypeScript and Vite configs updated
- [ ] Validation tools working
- [ ] Documentation complete
- [ ] All existing tests passing
- [ ] Build succeeds without errors
- [ ] Team walkthrough completed

### Code Quality
- [ ] No linting errors
- [ ] No TypeScript errors
- [ ] Code reviewed and approved
- [ ] Documentation reviewed

### Deployment
- [ ] Changes merged to main
- [ ] No production issues
- [ ] Rollback plan documented

---

## Dependencies

**Blocks**: FE-ARCH-002 (Auth Migration)

**Blocked By**: None

---

## Resources

### Documentation
- [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
- [Frontend Migration Guide](../../web/docs/FRONTEND-MIGRATION-GUIDE.md)
- [TanStack Router Docs](https://tanstack.com/router/latest)

### Team
- **Lead**: Senior Frontend Developer
- **Reviewers**: Tech Lead, Frontend Team
- **Stakeholders**: Development Team

---

**Last Updated**: 2025-01-15  
**Epic Owner**: Architecture Team
