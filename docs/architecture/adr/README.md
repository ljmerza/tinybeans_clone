# Architecture Decision Records (ADRs)

## Overview

This directory contains Architecture Decision Records (ADRs) for the Tinybeans project. ADRs document significant architectural decisions, including their context, alternatives considered, and consequences.

## Purpose

ADRs serve to:
- **Document** the reasoning behind architectural choices
- **Communicate** decisions to current and future team members
- **Preserve** the historical context of technical decisions
- **Prevent** revisiting already-decided issues
- **Enable** better onboarding for new developers

## ADR Process

### When to Write an ADR

Create an ADR when making decisions about:
- System architecture patterns or significant refactors
- Technology selection (frameworks, libraries, databases)
- API design and integration patterns
- Security and authentication mechanisms
- Data storage and processing strategies
- Development workflows and tooling
- Deployment and infrastructure choices

### How to Create an ADR

1. **Copy the Template**
   ```bash
   cp ADR-TEMPLATE.md ADR-XXX-YOUR-DECISION-TITLE.md
   ```

2. **Assign a Number**
   - Use the next sequential number (check existing ADRs)
   - Format: `ADR-XXX` (e.g., ADR-010, ADR-011)

3. **Write the ADR**
   - Start with Status: "Proposed"
   - Fill in all required sections
   - Be concise but complete
   - Include diagrams and code examples where helpful

4. **Review Process**
   - Share with relevant stakeholders (architect, tech leads, product)
   - Gather feedback and iterate
   - Update based on discussions

5. **Approval**
   - Get sign-offs from required approvers
   - Change Status to "Accepted"
   - Add approval signatures and dates

6. **Update Documentation**
   - Update this README with the new ADR
   - Link from main architecture.md if relevant
   - Commit and merge to main branch

## ADR Numbering Convention

- **ADR-001 to ADR-099**: Infrastructure and platform decisions
- **ADR-100 to ADR-199**: Backend architecture decisions
- **ADR-200 to ADR-299**: Frontend architecture decisions
- **ADR-300 to ADR-399**: Data and database decisions
- **ADR-400 to ADR-499**: Security and authentication decisions
- **ADR-500 to ADR-599**: DevOps and deployment decisions
- **ADR-600 to ADR-699**: Integration and API decisions
- **ADR-700 to ADR-799**: Performance and scalability decisions
- **ADR-800 to ADR-899**: Testing and quality decisions
- **ADR-900 to ADR-999**: Process and workflow decisions

## ADR Index

### Infrastructure & Platform

| ADR | Title | Status | Date | Summary |
|-----|-------|--------|------|---------|
| [ADR-001](./ADR-001-MEDIA-STORAGE-ARCHITECTURE.md) | Media Storage Architecture | Accepted | 2024-12-28 | Pluggable storage with MinIO for dev, S3 for prod |
| [ADR-002](./ADR-002-MEDIA-STORAGE-ARCHITECTURE.md) | Media Storage Architecture (Updated) | Accepted | 2024-12-29 | Enhanced media storage with async processing |

### Security & Authentication

| ADR | Title | Status | Date | Summary |
|-----|-------|--------|------|---------|
| [ADR-003](./ADR-003-TWO-FACTOR-AUTHENTICATION.md) | Two-Factor Authentication | Accepted | 2024-12-29 | TOTP, SMS, and email 2FA with recovery codes |
| [ADR-005](./ADR-005-CSRF-TOKEN-MANAGEMENT.md) | CSRF Token Management | Accepted | 2024-12-29 | CSRF protection strategy for SPA with Django backend |
| [ADR-010](./ADR-010-GOOGLE-OAUTH-INTEGRATION.md) | Google OAuth Integration | Proposed | 2025-01-12 | OAuth 2.0 with secure account linking and PKCE |

### Frontend Architecture

| ADR | Title | Status | Date | Summary |
|-----|-------|--------|------|---------|
| [ADR-004](./ADR-004-2FA-FRONTEND-IMPLEMENTATION.md) | 2FA Frontend Implementation | Accepted | 2024-12-29 | React components and flows for 2FA setup/verification |
| [ADR-009](./ADR-009-PHOTO-CALENDAR-REACT-LIBRARY.md) | Photo Calendar React Library | Accepted | 2024-12-30 | React-based photo calendar component selection |
| [ADR-011](./ADR-011-FRONTEND-FILE-ARCHITECTURE.md) | Frontend File Architecture | Proposed | 2025-01-15 | Feature-based organization with clear separation of routes and features |
| [ADR-012](./ADR-012-NOTIFICATION-STRATEGY.md) | Notification Strategy | Accepted | 2024-06-06 | Standardized backend messages & frontend-controlled presentation |

### Backend Architecture

| ADR | Title | Status | Date | Summary |
|-----|-------|--------|------|---------|
| [ADR-006](./ADR-006-LOGGING-FRAMEWORK.md) | Logging Framework | Accepted | 2024-12-30 | Structured logging strategy with Django |
| [ADR-007](./ADR-007-DOMAIN-LAYERING.md) | Domain Layering | Accepted | 2024-12-30 | Django app organization by domain boundaries |
| [ADR-008](./ADR-008-EMAIL-TEMPLATE-SYSTEM.md) | Email Template System | Accepted | 2024-12-30 | Email rendering and delivery with Celery |

## ADR Statuses

- **Proposed**: Under discussion, feedback being gathered
- **Accepted**: Approved and in effect
- **Deprecated**: No longer recommended but still in use
- **Superseded**: Replaced by another ADR (reference the new one)

## Templates and Examples

### Templates
- [ADR-TEMPLATE.md](./ADR-TEMPLATE.md) - Blank template for new ADRs

### Example ADRs
- [ADR-001-MEDIA-STORAGE-ARCHITECTURE.md](./ADR-001-MEDIA-STORAGE-ARCHITECTURE.md) - Comprehensive example with all sections
- [ADR-005-CSRF-TOKEN-MANAGEMENT.md](./ADR-005-CSRF-TOKEN-MANAGEMENT.md) - Security decision example

## Best Practices

### Writing ADRs

1. **Be Specific**: Document concrete decisions, not general principles
2. **Explain Context**: Future readers need to understand the situation
3. **Consider Alternatives**: Show you evaluated multiple options
4. **Be Honest About Consequences**: Include both positive and negative impacts
5. **Include Examples**: Code snippets, diagrams, and configurations help
6. **Keep It Timeless**: Write so it makes sense years later

### Maintaining ADRs

1. **Don't Modify Accepted ADRs**: Create new ADRs that supersede old ones
2. **Update Status Only**: Change status to Deprecated/Superseded as needed
3. **Link Related ADRs**: Create a web of related decisions
4. **Review Periodically**: Ensure ADRs remain accurate and relevant

### Common Pitfalls to Avoid

- ❌ Writing ADRs after implementation is complete
- ❌ Making ADRs too abstract or philosophical
- ❌ Skipping the alternatives section
- ❌ Not documenting consequences
- ❌ Writing ADRs that are too long (aim for 2-3 pages)
- ❌ Forgetting to update this index

## Quick Start Guide

### Creating Your First ADR

```bash
# 1. Copy template
cd docs/architecture/adr
cp ADR-TEMPLATE.md ADR-010-YOUR-DECISION.md

# 2. Edit with your favorite editor
vim ADR-010-YOUR-DECISION.md

# 3. Fill in these sections at minimum:
#    - Context (what problem you're solving)
#    - Decision (what you decided to do)
#    - Alternatives Considered (what else you looked at)
#    - Consequences (positive and negative impacts)

# 4. Set status to "Proposed" initially

# 5. Share for review (create PR or share in team chat)

# 6. After approval, update status to "Accepted"

# 7. Update this README index

# 8. Commit and push
git add .
git commit -m "docs: Add ADR-010 for [decision name]"
git push
```

## Tools and Resources

### Recommended Tools
- **Mermaid**: For architecture diagrams (supported in GitHub/GitLab)
- **PlantUML**: Alternative for complex diagrams
- **ADR Tools**: CLI tool for managing ADRs (`npm install -g adr-log`)

### External Resources
- [ADR GitHub Organization](https://adr.github.io/)
- [Architecture Decision Records (Martin Fowler)](https://martinfowler.com/articles/documenting-architecture-decisions.html)
- [ADR Tools Collection](https://github.com/npryce/adr-tools)

## Questions?

If you have questions about:
- **When to write an ADR**: Ask the architect or tech lead
- **How to fill in a section**: Look at existing ADRs as examples
- **Approval process**: Follow the team's decision-making workflow
- **Technical content**: Discuss in architecture review meetings

## Contributing

When adding ADRs:
1. Follow the template structure
2. Use clear, professional language
3. Include practical examples
4. Update this README index
5. Link related ADRs
6. Get required approvals before marking as "Accepted"

---

**Last Updated**: 2025-01-15  
**Maintainer**: Architecture Team  
**Total ADRs**: 12 (including template)

