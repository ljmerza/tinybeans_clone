# ADR Quick Reference

## 🎯 When Do I Need an ADR?

Ask yourself: **"Will this decision impact how others build or maintain the system?"**

### ✅ YES - Write an ADR for:
- Choosing a new technology, framework, or library
- Changing architectural patterns (e.g., moving from REST to GraphQL)
- Major refactoring decisions
- Database schema changes that affect multiple features
- Authentication/security mechanism changes
- API design patterns and conventions
- Infrastructure and deployment strategy changes
- Development workflow changes affecting the whole team

### ❌ NO - Skip ADR for:
- Bug fixes (document in commit messages)
- Minor UI changes
- Code style preferences (use linter rules instead)
- Temporary workarounds
- Implementation details within a single feature
- Configuration changes without architectural impact

---

## 📝 5-Minute ADR Guide

### Step 1: Copy Template (30 seconds)
```bash
cd docs/architecture/adr
cp ADR-TEMPLATE.md ADR-010-MY-DECISION.md
```

### Step 2: Fill Required Sections (3 minutes)

**Must fill:**
1. **Title**: Clear, descriptive (e.g., "Switch from Redux to TanStack Query")
2. **Status**: Start with "Proposed"
3. **Context**: Why is this decision needed? What's the problem?
4. **Decision**: What did you decide to do? Be specific.
5. **Alternatives**: What else did you consider? Why not those?
6. **Consequences**: What's the impact? (pros and cons)

**Optional but helpful:**
- Implementation plan
- Code examples
- Diagrams
- Risks and mitigations

### Step 3: Review & Approve (varies)
- Share with team
- Gather feedback
- Update based on input
- Get sign-offs
- Change status to "Accepted"

### Step 4: Finalize (1 minute)
- Add to README index
- Commit to repository
- Reference in architecture.md if relevant

---

## 📋 The 5 Essential Sections

### 1. Context
**What:** Describe the current situation and problem  
**Why:** Future readers need to understand the landscape  
**Length:** 3-5 paragraphs

```markdown
### Current State
- We're using Redux for all state management
- 80% of our state is server data
- Complex boilerplate for simple API calls

### Problem
- Too much boilerplate reduces developer velocity
- Cache invalidation is manual and error-prone
- No built-in loading/error states
```

### 2. Decision
**What:** The choice you made  
**Why:** This is the record of what was decided  
**Length:** 1-3 paragraphs + bullet points

```markdown
We will use TanStack Query for server state management
and TanStack Store only for client state.

Implementation:
- Migrate all API calls to TanStack Query hooks
- Use TanStack Store only for UI state (theme, sidebar, etc.)
- Complete migration in 2 sprints
```

### 3. Alternatives Considered
**What:** Other options you evaluated  
**Why:** Shows due diligence, helps future decisions  
**Length:** 2-4 alternatives

```markdown
### Alternative 1: Keep Redux
**Pros**: Team knows it, no migration cost
**Cons**: Boilerplate remains, cache management still manual
**Why Rejected**: Benefits don't outweigh long-term productivity

### Alternative 2: Use SWR
**Pros**: Smaller bundle size than TanStack Query
**Cons**: Less feature-rich, smaller ecosystem
**Why Rejected**: TanStack Query better TypeScript support
```

### 4. Consequences
**What:** Positive and negative impacts  
**Why:** Every decision has trade-offs  
**Length:** 3-6 bullet points each

```markdown
### Positive
- ✅ Automatic caching and refetching
- ✅ Built-in loading/error states
- ✅ 40% less boilerplate code

### Negative
- ⚠️ Learning curve for team
- ⚠️ Migration effort: 2 sprints
- ⚠️ Slightly larger bundle (+15KB)
```

### 5. Implementation Details
**What:** How to actually do it  
**Why:** Makes the ADR actionable  
**Length:** Code examples, diagrams, steps

```typescript
// Before (Redux)
const dispatch = useDispatch();
const loading = useSelector(state => state.users.loading);

// After (TanStack Query)
const { data, isLoading } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
});
```

---

## 🎨 ADR Template Cheat Sheet

### Minimal ADR (10 minutes)
Fill these sections only:
- Title & Status
- Context (why needed)
- Decision (what chosen)
- Alternatives (what else considered)
- Consequences (pros/cons)

### Standard ADR (30 minutes)
Add to minimal:
- Implementation plan
- Code examples
- Testing strategy
- Migration path

### Comprehensive ADR (1-2 hours)
Add to standard:
- Architecture diagrams
- Performance analysis
- Security implications
- Monitoring plan
- Success criteria

---

## 💡 Pro Tips

### Writing Tips
1. **Start with Context**: Write the "Context" section first, it's easiest
2. **Use Examples**: Code snippets are worth 1000 words
3. **Be Specific**: "Use TanStack Query" not "Improve state management"
4. **Include Numbers**: "Reduces bundle by 40KB" not "Smaller bundle"
5. **Link Everything**: Reference other ADRs, docs, external resources

### Common Mistakes
1. ❌ **Too Late**: Writing ADR after implementation
   - ✅ **Fix**: Write while deciding, even if "Proposed"

2. ❌ **Too Abstract**: "We will improve performance"
   - ✅ **Fix**: "We will implement Redis caching for user queries"

3. ❌ **No Alternatives**: Only documents chosen option
   - ✅ **Fix**: Show 2-3 alternatives you considered

4. ❌ **Missing Consequences**: Only lists benefits
   - ✅ **Fix**: Include trade-offs and costs

5. ❌ **No Code Examples**: Pure prose
   - ✅ **Fix**: Add actual code/config snippets

### Review Checklist
Before submitting for review:
- [ ] Title is clear and specific
- [ ] Context explains the "why"
- [ ] Decision is unambiguous
- [ ] 2+ alternatives documented
- [ ] Both pros and cons listed
- [ ] Code examples included (if applicable)
- [ ] Diagrams added (if helpful)
- [ ] Status is "Proposed"

---

## 🔍 Finding Relevant ADRs

### By Number Range
- **001-099**: Infrastructure (storage, deployment)
- **100-199**: Backend architecture
- **200-299**: Frontend architecture
- **300-399**: Data/database
- **400-499**: Security/auth

### By Topic
```bash
# Search ADR titles
ls docs/architecture/adr/ | grep -i "authentication"

# Search ADR content
grep -r "TanStack Query" docs/architecture/adr/

# View ADR index
cat docs/architecture/adr/README.md
```

---

## 🚀 Quick Templates

### Technology Selection ADR

```markdown
# ADR-XXX: Use [Technology] for [Purpose]

## Context
Current technology: [Current]
Problems: [Issues with current approach]
Requirements: [What we need]

## Decision
We will use [New Technology] because:
- [Reason 1]
- [Reason 2]

## Alternatives
1. [Alternative 1]: Rejected because [reason]
2. [Alternative 2]: Rejected because [reason]

## Consequences
Positive: [Benefits]
Negative: [Costs/Trade-offs]
```

### Pattern/Practice ADR

```markdown
# ADR-XXX: Adopt [Pattern] for [Use Case]

## Context
Current approach: [How it's done now]
Issues: [What's problematic]

## Decision
Pattern: [Pattern name]
Application: [Where/how to use]

## Example
[Code showing pattern in action]

## Consequences
Better: [Improvements]
Worse: [Drawbacks]
```

### Migration ADR

```markdown
# ADR-XXX: Migrate from [Old] to [New]

## Context
Legacy system: [What exists]
Why change: [Problems/limitations]

## Decision
Migration approach: [Strategy]
Timeline: [Phases and dates]

## Migration Path
Phase 1: [Steps]
Phase 2: [Steps]

## Rollback Plan
[How to revert if needed]
```

---

## 📚 Further Reading

- **Full Template**: See `ADR-TEMPLATE.md`
- **Real Examples**: Check existing ADRs (001-009)
- **Index**: See `README.md` for complete list
- **Architecture**: Reference `docs/architecture.md`

---

**Remember**: ADRs are living documents. They don't need to be perfect, just complete enough to be useful. Start with the minimal template and add more as needed!

