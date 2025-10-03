# Documentation Index

This directory contains all project documentation organized by topic.

## 📁 Directory Structure

### [architecture/](./architecture/)
Architecture decisions, ADRs, and API documentation

#### [architecture/adr/](./architecture/adr/)
Architecture Decision Records (ADRs)
- Media storage architecture decisions
- Two-factor authentication architecture
- Frontend implementation decisions
- CSRF token management

**Key Files:**
- [ADR-001-MEDIA-STORAGE-ARCHITECTURE.md](./architecture/adr/ADR-001-MEDIA-STORAGE-ARCHITECTURE.md)
- [ADR-002-MEDIA-STORAGE-ARCHITECTURE.md](./architecture/adr/ADR-002-MEDIA-STORAGE-ARCHITECTURE.md)
- [ADR-003-TWO-FACTOR-AUTHENTICATION.md](./architecture/adr/ADR-003-TWO-FACTOR-AUTHENTICATION.md)
- [ADR-004-2FA-FRONTEND-IMPLEMENTATION.md](./architecture/adr/ADR-004-2FA-FRONTEND-IMPLEMENTATION.md)
- [ADR-005-CSRF-TOKEN-MANAGEMENT.md](./architecture/adr/ADR-005-CSRF-TOKEN-MANAGEMENT.md)
- [ADR-009-PHOTO-CALENDAR-REACT-LIBRARY.md](./architecture/adr/ADR-009-PHOTO-CALENDAR-REACT-LIBRARY.md)

#### [architecture/api/](./architecture/api/)
API schemas and documentation
- API endpoint definitions
- Request/response schemas

**Key Files:**
- [KEEPS_API_SCHEMA.md](./architecture/api/KEEPS_API_SCHEMA.md) - Keeps API schema documentation

**Other Files:**
- [SERVICES.md](./architecture/SERVICES.md) - Services overview

---

### [features/](./features/)
Feature-specific implementation documentation

#### [features/2fa/](./features/2fa/)
Two-Factor Authentication (2FA) implementation documentation
- Implementation guides and status
- Frontend implementation details
- Troubleshooting guides
- Phase completion summaries

**Key Files:**
- [2FA_DOCUMENTATION_INDEX.md](./features/2fa/2FA_DOCUMENTATION_INDEX.md) - Main 2FA documentation index
- [2FA_IMPLEMENTATION_GUIDE.md](./features/2fa/2FA_IMPLEMENTATION_GUIDE.md) - Step-by-step implementation guide
- [2FA_TROUBLESHOOTING.md](./features/2fa/2FA_TROUBLESHOOTING.md) - Common issues and solutions

#### [features/media-storage/](./features/media-storage/)
Media storage implementation documentation
- MinIO integration
- Storage architecture implementation

**Key Files:**
- [MEDIA_STORAGE_IMPLEMENTATION_SUMMARY.md](./features/media-storage/MEDIA_STORAGE_IMPLEMENTATION_SUMMARY.md)
- [MINIO_MEDIA_STORAGE_SUMMARY.md](./features/media-storage/MINIO_MEDIA_STORAGE_SUMMARY.md)

#### [features/oauth/](./features/oauth/)
OAuth implementation documentation
- Google OAuth integration
- Security analysis
- Architecture decisions

**Key Files:**
- [GOOGLE_OAUTH_ARCHITECTURE.md](./features/oauth/GOOGLE_OAUTH_ARCHITECTURE.md)
- [GOOGLE_OAUTH_IMPLEMENTATION.md](./features/oauth/GOOGLE_OAUTH_IMPLEMENTATION.md)
- [GOOGLE_OAUTH_SECURITY_ANALYSIS.md](./features/oauth/GOOGLE_OAUTH_SECURITY_ANALYSIS.md)

---

### [guides/](./guides/)
Project guides, planning, and security documentation

#### [guides/planning/](./guides/planning/)
Project planning and enhancement proposals
- Feature enhancement ideas
- Development plans
- Technical decision documentation

**Key Files:**
- [TINYBEANS_KEEPS_COMPLETE_SUMMARY.md](./guides/planning/TINYBEANS_KEEPS_COMPLETE_SUMMARY.md) - Complete project summary
- [USERS_APP_ENHANCEMENT_IDEAS.md](./guides/planning/USERS_APP_ENHANCEMENT_IDEAS.md)
- [email_queue_plan.md](./guides/planning/email_queue_plan.md)
- [users_app_plan.md](./guides/planning/users_app_plan.md)
- [TANSTACK_QUERY_VS_STORE.md](./guides/planning/TANSTACK_QUERY_VS_STORE.md)

#### [guides/security/](./guides/security/)
Security audits, fixes, and improvements
- Security audit reports
- Implementation status
- Quick start guides for security features

**Key Files:**
- [SECURITY_AUDIT.md](./guides/security/SECURITY_AUDIT.md) - Main security audit
- [README_SECURITY_AUDIT.md](./guides/security/README_SECURITY_AUDIT.md)
- [SECURITY_IMPROVEMENTS_QUICKSTART.md](./guides/security/SECURITY_IMPROVEMENTS_QUICKSTART.md)
- [SECURITY_FIXES.md](./guides/security/SECURITY_FIXES.md)
- [CSRF_403_FIX.md](./guides/security/CSRF_403_FIX.md) - CSRF 403 error fixes
- [auth_app_security_review.md](./guides/security/auth_app_security_review.md)
- [SECURITY_ENHANCEMENTS_SUMMARY.md](./guides/security/SECURITY_ENHANCEMENTS_SUMMARY.md)
- [SECURITY_IMPLEMENTATION_SUMMARY.md](./guides/security/SECURITY_IMPLEMENTATION_SUMMARY.md)

---

## 📋 Quick Navigation

- **New to the project?** Start with [TINYBEANS_KEEPS_COMPLETE_SUMMARY.md](./guides/planning/TINYBEANS_KEEPS_COMPLETE_SUMMARY.md)
- **Setting up 2FA?** Check [2FA_DOCUMENTATION_INDEX.md](./features/2fa/2FA_DOCUMENTATION_INDEX.md)
- **Understanding architecture?** Review the [architecture/adr/](./architecture/adr/) folder
- **Security concerns?** See [SECURITY_IMPROVEMENTS_QUICKSTART.md](./guides/security/SECURITY_IMPROVEMENTS_QUICKSTART.md)
- **API reference?** Visit [KEEPS_API_SCHEMA.md](./architecture/api/KEEPS_API_SCHEMA.md)

## 📝 Contributing to Documentation

When adding new documentation:
1. Place files in the appropriate subdirectory
2. Update this README.md with links to important new documents
3. Follow existing naming conventions
4. Keep documentation up-to-date with code changes
