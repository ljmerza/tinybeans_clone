# Epic 4: Tooling, Validation & Documentation

**Epic ID**: FE-ARCH-004  
**Status**: Blocked (depends on FE-ARCH-003)  
**Priority**: P1 - High Priority  
**Sprint**: Week 4  
**Estimated Effort**: 4 story points  
**Dependencies**: FE-ARCH-003 (2FA Migration)  
**Related ADR**: [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)

---

## Epic Goal

Create developer tools, automation, validation rules, and comprehensive documentation to maintain the new architecture, prevent regression, and enable the team to work efficiently with the feature-based structure.

---

## Business Value

- **Maintainability**: Tools prevent architecture decay
- **Productivity**: Automation speeds up feature creation
- **Quality**: Validation catches violations early
- **Onboarding**: Documentation reduces ramp-up time

**Expected Impact**:
- 80% faster feature scaffolding
- Zero architecture violations in code reviews
- 50% reduction in onboarding time
- Consistent feature structure across team

---

## User Stories

### Story 4.1: Feature Generator CLI Tool

**As a** frontend developer  
**I want** a CLI tool to generate new features  
**So that** I can quickly scaffold features with correct structure

**Acceptance Criteria:**
1. CLI tool creates complete feature structure
2. Tool supports feature naming conventions
3. Generated files have proper imports
4. Tool is documented
5. Tool is available via npm script

**Implementation:**

```javascript
// scripts/generate-feature.js
import fs from 'fs'
import path from 'path'
import { input, select, confirm } from '@inquirer/prompts'

const FEATURES_DIR = 'src/features'

const TEMPLATES = {
  index: (featureName) => `/**
 * Public API for ${featureName} feature
 * 
 * Only export what other features/routes need to consume.
 */

// Components
export { ${toPascalCase(featureName)}Main } from './components/${toPascalCase(featureName)}Main'

// Hooks
export { use${toPascalCase(featureName)} } from './hooks/use${toPascalCase(featureName)}'

// Types (public only)
export type { ${toPascalCase(featureName)}Data } from './types'
`,

  component: (featureName) => `import { use${toPascalCase(featureName)} } from '../hooks/use${toPascalCase(featureName)}'

interface ${toPascalCase(featureName)}MainProps {
  // Add props
}

export function ${toPascalCase(featureName)}Main(props: ${toPascalCase(featureName)}MainProps) {
  const ${featureName} = use${toPascalCase(featureName)}()
  
  return (
    <div>
      {/* Add UI */}
    </div>
  )
}
`,

  hook: (featureName) => `import { useQuery } from '@tanstack/react-query'
import { ${featureName}Client } from '../api/${featureName}Client'

export function use${toPascalCase(featureName)}() {
  return useQuery({
    queryKey: ['${featureName}'],
    queryFn: () => ${featureName}Client.fetch(),
  })
}
`,

  api: (featureName) => `import { api } from '@/lib/api'
import type { ${toPascalCase(featureName)}Data } from '../types'

export const ${featureName}Client = {
  fetch: async (): Promise<${toPascalCase(featureName)}Data> => {
    const response = await api.get('/api/${featureName}/')
    return response.data
  },
}
`,

  types: (featureName) => `export interface ${toPascalCase(featureName)}Data {
  id: string
  // Add fields
}
`,

  readme: (featureName) => `# ${toPascalCase(featureName)} Feature

## Overview
[Describe what this feature does]

## Components
- \`${toPascalCase(featureName)}Main\` - [Description]

## Hooks
- \`use${toPascalCase(featureName)}\` - [Description]

## Usage
\`\`\`typescript
import { ${toPascalCase(featureName)}Main } from '@/features/${featureName}'

function MyPage() {
  return <${toPascalCase(featureName)}Main />
}
\`\`\`
`,
}

function toPascalCase(str) {
  return str
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')
}

function toKebabCase(str) {
  return str
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .toLowerCase()
}

async function generateFeature() {
  console.log('🎨 Feature Generator\n')
  
  // Get feature name
  const featureName = await input({
    message: 'Feature name (kebab-case):',
    validate: (input) => {
      if (!/^[a-z][a-z0-9-]*$/.test(input)) {
        return 'Feature name must be lowercase with hyphens (e.g., user-profile)'
      }
      return true
    },
  })
  
  // Get feature type
  const featureType = await select({
    message: 'Feature type:',
    choices: [
      { name: 'Full Stack (components + API + hooks)', value: 'full' },
      { name: 'Component Only (UI components)', value: 'component' },
      { name: 'API Only (data fetching)', value: 'api' },
    ],
  })
  
  // Confirm creation
  const featurePath = path.join(FEATURES_DIR, featureName)
  const shouldCreate = await confirm({
    message: `Create feature at ${featurePath}?`,
    default: true,
  })
  
  if (!shouldCreate) {
    console.log('❌ Cancelled')
    return
  }
  
  // Create directories
  const dirs = ['components', 'types']
  if (featureType === 'full' || featureType === 'api') {
    dirs.push('hooks', 'api')
  }
  
  for (const dir of dirs) {
    fs.mkdirSync(path.join(featurePath, dir), { recursive: true })
  }
  
  // Create files
  fs.writeFileSync(
    path.join(featurePath, 'index.ts'),
    TEMPLATES.index(featureName)
  )
  
  fs.writeFileSync(
    path.join(featurePath, 'README.md'),
    TEMPLATES.readme(featureName)
  )
  
  fs.writeFileSync(
    path.join(featurePath, 'components', `${toPascalCase(featureName)}Main.tsx`),
    TEMPLATES.component(featureName)
  )
  
  fs.writeFileSync(
    path.join(featurePath, 'types', 'index.ts'),
    TEMPLATES.types(featureName)
  )
  
  if (featureType === 'full' || featureType === 'api') {
    fs.writeFileSync(
      path.join(featurePath, 'hooks', `use${toPascalCase(featureName)}.ts`),
      TEMPLATES.hook(featureName)
    )
    
    fs.writeFileSync(
      path.join(featurePath, 'api', `${featureName}Client.ts`),
      TEMPLATES.api(featureName)
    )
  }
  
  console.log('\n✅ Feature created successfully!')
  console.log(`\n📁 Location: ${featurePath}`)
  console.log('\n📝 Next steps:')
  console.log('  1. Implement your feature logic')
  console.log('  2. Update the README.md')
  console.log('  3. Create route files if needed')
  console.log(`  4. Import from: @/features/${featureName}\n`)
}

generateFeature().catch(console.error)
```

**Package.json:**
```json
{
  "scripts": {
    "generate:feature": "node scripts/generate-feature.js"
  },
  "devDependencies": {
    "@inquirer/prompts": "^3.0.0"
  }
}
```

**Usage:**
```bash
npm run generate:feature
# Follow prompts to create new feature
```

**Definition of Done:**
- [ ] Generator script created
- [ ] Script generates complete structure
- [ ] Templates include best practices
- [ ] Script documented
- [ ] NPM script added
- [ ] Team trained on usage

---

### Story 4.2: ESLint Architecture Boundary Rules

**As a** frontend developer  
**I want** ESLint rules that enforce architecture boundaries  
**So that** violations are caught during development

**Acceptance Criteria:**
1. ESLint rules prevent feature-to-feature imports
2. Rules enforce index.ts exports
3. Rules prevent route files from containing logic
4. Rules are documented
5. CI enforces rules

**Implementation:**

```javascript
// eslint.config.js (or .eslintrc.js)
module.exports = {
  // ... existing config
  
  plugins: ['boundaries'],
  
  settings: {
    'boundaries/elements': [
      {
        type: 'feature',
        pattern: 'src/features/*',
        mode: 'folder',
      },
      {
        type: 'route',
        pattern: 'src/routes/*',
        mode: 'file',
      },
      {
        type: 'component',
        pattern: 'src/components/*',
        mode: 'file',
      },
      {
        type: 'lib',
        pattern: 'src/lib/*',
        mode: 'file',
      },
    ],
    'boundaries/ignore': ['**/*.test.tsx', '**/*.test.ts'],
  },
  
  rules: {
    // Prevent features from importing other features directly
    'boundaries/element-types': [
      'error',
      {
        default: 'disallow',
        rules: [
          {
            from: 'feature',
            allow: ['component', 'lib'],
          },
          {
            from: 'route',
            allow: ['feature', 'component', 'lib'],
          },
          {
            from: 'component',
            allow: ['component', 'lib'],
          },
          {
            from: 'lib',
            allow: ['lib'],
          },
        ],
      },
    ],
    
    // Enforce imports from feature index only
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['@/features/*/components/*', '@/features/*/hooks/*', '@/features/*/api/*'],
            message: 'Import from feature index (@/features/{feature}) instead of internals',
          },
        ],
      },
    ],
  },
}
```

**Custom ESLint Rule:**
```javascript
// scripts/eslint-rules/no-logic-in-routes.js
module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Prevent business logic in route files',
      category: 'Best Practices',
    },
    messages: {
      noLogicInRoutes: 'Route files should not contain business logic. Move to feature components or hooks.',
    },
  },
  
  create(context) {
    return {
      CallExpression(node) {
        const filename = context.getFilename()
        
        // Only check route files
        if (!filename.includes('/routes/')) return
        
        // Check for common logic patterns
        const isLogic = node.callee.name === 'useMutation' ||
                       node.callee.name === 'useState' ||
                       (node.callee.property && node.callee.property.name === 'post')
        
        if (isLogic) {
          context.report({
            node,
            messageId: 'noLogicInRoutes',
          })
        }
      },
    }
  },
}
```

**Definition of Done:**
- [ ] ESLint boundaries plugin configured
- [ ] Rules prevent cross-feature imports
- [ ] Rules enforce index.ts usage
- [ ] Custom rules implemented
- [ ] CI runs ESLint checks
- [ ] Documentation updated

---

### Story 4.3: CI/CD Validation Pipeline

**As a** development team  
**I want** automated validation in CI/CD  
**So that** architecture violations are caught before merge

**Acceptance Criteria:**
1. CI runs feature structure validation
2. CI runs ESLint boundary checks
3. CI fails on architecture violations
4. Results clearly show violations
5. Documentation on fixing violations

**GitHub Actions Workflow:**

```yaml
# .github/workflows/frontend-architecture-validation.yml
name: Frontend Architecture Validation

on:
  pull_request:
    paths:
      - 'web/src/**'
  push:
    branches:
      - main

jobs:
  validate-architecture:
    name: Validate Frontend Architecture
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'web/package-lock.json'
      
      - name: Install dependencies
        working-directory: web
        run: npm ci
      
      - name: Validate Feature Structure
        working-directory: web
        run: npm run validate:features
      
      - name: ESLint Boundary Checks
        working-directory: web
        run: npm run lint:boundaries
      
      - name: TypeScript Compilation
        working-directory: web
        run: npm run type-check
      
      - name: Check for Legacy Imports
        working-directory: web
        run: |
          echo "Checking for legacy module imports..."
          if grep -r "from '@/modules/" src/; then
            echo "❌ Found imports from old modules directory!"
            echo "Please use @/features/* instead"
            exit 1
          fi
          echo "✅ No legacy imports found"
      
      - name: Generate Architecture Report
        if: failure()
        working-directory: web
        run: |
          echo "## Architecture Validation Failed 🔴" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Please check the logs above for specific violations." >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Common fixes:" >> $GITHUB_STEP_SUMMARY
          echo "- Use feature index imports: \`@/features/{feature}\`" >> $GITHUB_STEP_SUMMARY
          echo "- Don't import between features directly" >> $GITHUB_STEP_SUMMARY
          echo "- Keep route files thin" >> $GITHUB_STEP_SUMMARY
```

**Package.json Scripts:**
```json
{
  "scripts": {
    "validate:features": "node scripts/validate-features.js",
    "lint:boundaries": "eslint src --ext .ts,.tsx --config eslint.boundaries.js",
    "validate:all": "npm run validate:features && npm run lint:boundaries && npm run type-check",
    "type-check": "tsc --noEmit"
  }
}
```

**Definition of Done:**
- [ ] GitHub Actions workflow created
- [ ] All validation steps working
- [ ] CI fails on violations
- [ ] Clear error messages
- [ ] Documentation for fixes
- [ ] Team aware of CI checks

---

### Story 4.4: Comprehensive Architecture Documentation

**As a** frontend developer  
**I want** complete documentation of the architecture  
**So that** I can understand and follow patterns

**Acceptance Criteria:**
1. Architecture guide created
2. Feature creation guide updated
3. Common patterns documented
4. Examples provided
5. Troubleshooting guide created

**Documentation to Create:**

**1. Architecture Overview (`web/docs/ARCHITECTURE.md`):**
```markdown
# Frontend Architecture Guide

## Overview
This frontend uses a feature-based architecture for scalability and maintainability.

## Directory Structure
\`\`\`
src/
├── routes/          File-based routing (TanStack Router)
├── features/        Feature modules (business logic)
├── components/      Shared UI components
└── lib/            Shared utilities
\`\`\`

## Features
Features are self-contained modules that encapsulate related functionality.

### When to Create a Feature
- Contains 3+ related components
- Has dedicated business logic
- Represents a distinct domain
- Used across multiple routes

### Feature Structure
[Detail the standard structure]

### Feature Boundaries
[Explain import rules]

## Routes
Routes are thin wrappers that compose feature components.

### Route Responsibilities
- URL definition
- Layout composition
- Feature component orchestration
- Route-level data loading

### Route Anti-Patterns
- ❌ Business logic in route files
- ❌ Direct API calls in routes
- ❌ Complex state management

## Common Patterns
[Document standard patterns]

## Best Practices
[List architectural best practices]
```

**2. Feature Creation Guide** (update existing)

**3. Common Patterns Guide (`web/docs/PATTERNS.md`):**
```markdown
# Common Frontend Patterns

## Data Fetching Pattern
[Standard TanStack Query usage]

## Form Handling Pattern
[Standard TanStack Form usage]

## Component Composition
[How to compose features]

## State Management
[When to use stores vs query cache]

## Error Handling
[Standard error patterns]
```

**4. Troubleshooting Guide (`web/docs/TROUBLESHOOTING.md`):**
```markdown
# Architecture Troubleshooting

## Import Errors
### "Cannot find module '@/features/...'"
**Problem**: TypeScript can't resolve feature import
**Solution**:
1. Check tsconfig.json has correct paths
2. Restart TypeScript server
3. Verify feature exports from index.ts

### "Must import from feature index"
**Problem**: ESLint rule violation
**Solution**: Change `@/features/auth/components/LoginForm` to `@/features/auth`

## Feature Structure Issues
[Document common issues]

## Build/Dev Server Issues
[Document solutions]
```

**5. Team Onboarding Guide (`web/docs/ONBOARDING.md`):**
```markdown
# Frontend Onboarding Guide

## Day 1: Architecture Understanding
1. Read ARCHITECTURE.md
2. Explore existing features
3. Try generating a test feature

## Day 2: Development Workflow
1. Create a feature
2. Add components
3. Create routes
4. Test locally

## Day 3: Best Practices
1. Review PATTERNS.md
2. Study code reviews
3. Pair with team member

## Reference Materials
[Links to all docs]
```

**Definition of Done:**
- [ ] All documentation created
- [ ] Documentation reviewed
- [ ] Examples tested
- [ ] Links working
- [ ] Team walkthrough completed

---

### Story 4.5: Team Training and Knowledge Transfer

**As a** development team  
**I want** training on the new architecture  
**So that** everyone can work effectively

**Acceptance Criteria:**
1. Training session conducted
2. Architecture documented
3. Q&A session completed
4. Feedback collected
5. Documentation updated based on feedback

**Training Plan:**

**Session 1: Architecture Overview (1 hour)**
- Presentation on new architecture
- Walk through directory structure
- Explain feature boundaries
- Demo feature generator

**Session 2: Hands-On Workshop (2 hours)**
- Create a feature together
- Migrate a small component
- Add route and test
- Review validation tools

**Session 3: Q&A and Best Practices (1 hour)**
- Answer team questions
- Discuss edge cases
- Share best practices
- Collect feedback

**Training Materials:**
- Slide deck presentation
- Live coding examples
- Practice exercises
- Cheat sheet handout

**Post-Training:**
- Office hours for questions
- Code review support
- Documentation updates

**Definition of Done:**
- [ ] Training sessions completed
- [ ] All team members attended
- [ ] Materials shared
- [ ] Feedback collected
- [ ] Action items from feedback addressed
- [ ] Team confident with new structure

---

## Testing Strategy

### Tool Testing
- [ ] Feature generator creates valid features
- [ ] Validation script catches violations
- [ ] ESLint rules catch boundary violations
- [ ] CI pipeline runs all checks

### Documentation Testing
- [ ] All code examples compile
- [ ] All links work
- [ ] Examples can be copy-pasted
- [ ] Documentation is clear

### Integration Testing
- [ ] Full workflow from feature creation to deployment
- [ ] Validation catches real violations
- [ ] Tools work on actual codebase

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Team resistance to tools | Medium | Low | Show value early, get feedback |
| False positive violations | Medium | Medium | Tune rules carefully, allow overrides |
| Tools slow down development | Low | Low | Optimize performance, cache results |
| Documentation out of date | Medium | High | Include in code review checklist |

---

## Dependencies

**Requires**: FE-ARCH-003 (2FA Migration)

**Blocks**: None (final epic)

---

## Definition of Done

### Epic Level
- [ ] All 5 stories completed
- [ ] Feature generator working
- [ ] ESLint rules enforcing
- [ ] CI validation passing
- [ ] Documentation complete
- [ ] Team trained

### Quality Checks
- [ ] Tools tested on real codebase
- [ ] Documentation reviewed
- [ ] No false positives in validation
- [ ] Team feedback positive

### Long-term Success
- [ ] Tools being used regularly
- [ ] No architecture violations in PRs
- [ ] New features follow patterns
- [ ] Team velocity maintained/improved

---

**Last Updated**: 2025-01-15  
**Epic Owner**: Architecture Team
