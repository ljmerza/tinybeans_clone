# Documentation Index

This directory contains all project documentation organized by topic.

## 📁 Directory Structure

### [2fa/](./2fa/)
Two-Factor Authentication (2FA) implementation documentation
- Implementation guides and status
- Frontend implementation details
- Troubleshooting guides
- Phase completion summaries

**Key Files:**
- [2FA_DOCUMENTATION_INDEX.md](./2fa/2FA_DOCUMENTATION_INDEX.md) - Main 2FA documentation index
- [2FA_IMPLEMENTATION_GUIDE.md](./2fa/2FA_IMPLEMENTATION_GUIDE.md) - Step-by-step implementation guide
- [2FA_TROUBLESHOOTING.md](./2fa/2FA_TROUBLESHOOTING.md) - Common issues and solutions

### [adr/](./adr/)
Architecture Decision Records (ADRs)
- Media storage architecture decisions
- Two-factor authentication architecture
- Frontend implementation decisions

**Key Files:**
- [ADR-001-MEDIA-STORAGE-ARCHITECTURE.md](./adr/ADR-001-MEDIA-STORAGE-ARCHITECTURE.md)
- [ADR-002-MEDIA-STORAGE-ARCHITECTURE.md](./adr/ADR-002-MEDIA-STORAGE-ARCHITECTURE.md)
- [ADR-003-TWO-FACTOR-AUTHENTICATION.md](./adr/ADR-003-TWO-FACTOR-AUTHENTICATION.md)
- [ADR-004-2FA-FRONTEND-IMPLEMENTATION.md](./adr/ADR-004-2FA-FRONTEND-IMPLEMENTATION.md)

### [api/](./api/)
API schemas and documentation
- API endpoint definitions
- Request/response schemas

**Key Files:**
- [KEEPS_API_SCHEMA.md](./api/KEEPS_API_SCHEMA.md) - Keeps API schema documentation

### [media-storage/](./media-storage/)
Media storage implementation documentation
- MinIO integration
- Storage architecture implementation

**Key Files:**
- [MEDIA_STORAGE_IMPLEMENTATION_SUMMARY.md](./media-storage/MEDIA_STORAGE_IMPLEMENTATION_SUMMARY.md)
- [MINIO_MEDIA_STORAGE_SUMMARY.md](./media-storage/MINIO_MEDIA_STORAGE_SUMMARY.md)

### [oauth/](./oauth/)
OAuth implementation documentation
- Google OAuth integration
- Security analysis
- Architecture decisions

**Key Files:**
- [GOOGLE_OAUTH_ARCHITECTURE.md](./oauth/GOOGLE_OAUTH_ARCHITECTURE.md)
- [GOOGLE_OAUTH_IMPLEMENTATION.md](./oauth/GOOGLE_OAUTH_IMPLEMENTATION.md)
- [GOOGLE_OAUTH_SECURITY_ANALYSIS.md](./oauth/GOOGLE_OAUTH_SECURITY_ANALYSIS.md)

### [planning/](./planning/)
Project planning and enhancement proposals
- Feature enhancement ideas
- Development plans
- Technical decision documentation

**Key Files:**
- [TINYBEANS_KEEPS_COMPLETE_SUMMARY.md](./planning/TINYBEANS_KEEPS_COMPLETE_SUMMARY.md) - Complete project summary
- [USERS_APP_ENHANCEMENT_IDEAS.md](./planning/USERS_APP_ENHANCEMENT_IDEAS.md)
- [email_queue_plan.md](./planning/email_queue_plan.md)
- [users_app_plan.md](./planning/users_app_plan.md)
- [TANSTACK_QUERY_VS_STORE.md](./planning/TANSTACK_QUERY_VS_STORE.md)

### [security/](./security/)
Security audits, fixes, and improvements
- Security audit reports
- Implementation status
- Quick start guides for security features

**Key Files:**
- [SECURITY_AUDIT.md](./security/SECURITY_AUDIT.md) - Main security audit
- [README_SECURITY_AUDIT.md](./security/README_SECURITY_AUDIT.md)
- [SECURITY_IMPROVEMENTS_QUICKSTART.md](./security/SECURITY_IMPROVEMENTS_QUICKSTART.md)
- [SECURITY_FIXES.md](./security/SECURITY_FIXES.md)
- [CSRF_403_FIX.md](./security/CSRF_403_FIX.md) - CSRF 403 error fixes

## 📋 Quick Navigation

- **New to the project?** Start with [TINYBEANS_KEEPS_COMPLETE_SUMMARY.md](./planning/TINYBEANS_KEEPS_COMPLETE_SUMMARY.md)
- **Setting up 2FA?** Check [2FA_DOCUMENTATION_INDEX.md](./2fa/2FA_DOCUMENTATION_INDEX.md)
- **Understanding architecture?** Review the [adr/](./adr/) folder
- **Security concerns?** See [SECURITY_IMPROVEMENTS_QUICKSTART.md](./security/SECURITY_IMPROVEMENTS_QUICKSTART.md)
- **API reference?** Visit [KEEPS_API_SCHEMA.md](./api/KEEPS_API_SCHEMA.md)

## 📝 Contributing to Documentation

When adding new documentation:
1. Place files in the appropriate subdirectory
2. Update this README.md with links to important new documents
3. Follow existing naming conventions
4. Keep documentation up-to-date with code changes
