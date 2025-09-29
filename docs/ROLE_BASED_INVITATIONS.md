# Role-Based Circle Invitations

## Summary

The **role-based circle invitation functionality is already fully implemented** in the Tinybeans application. Admin users can choose the role of invitees when creating circle invitations.

## API Usage

**Endpoint:** `POST /api/circles/{circle_id}/invitations/`

**Request Body:**
```json
{
    "email": "invitee@example.com",
    "role": "admin"  // Optional: "admin" or "member" (defaults to "member")
}
```

**Available Roles:**
- `"admin"` - Circle Admin (can manage circle, invite/remove members)
- `"member"` - Circle Member (regular member with basic permissions)

## Examples

### Invite an Admin
```json
{
    "email": "newadmin@example.com",
    "role": "admin"
}
```

### Invite a Member (explicit)
```json
{
    "email": "newmember@example.com",
    "role": "member"
}
```

### Invite a Member (default)
```json
{
    "email": "defaultmember@example.com"
    // No role specified - defaults to "member"
}
```

## Security & Validation

- ✅ **Admin-only permissions** - Only Circle Admins can create invitations
- ✅ **Role validation** - Invalid roles are rejected with 400 error
- ✅ **Duplicate protection** - Cannot invite same email twice to same circle
- ✅ **Email validation** - Proper email format required

## Implementation

The feature is implemented across:

1. **Database Model**: `CircleInvitation.role` field with UserRole choices
2. **Serializer**: `CircleInvitationCreateSerializer` with role validation and defaults
3. **API View**: `CircleInvitationCreateView` with admin permissions and proper role assignment
4. **Tests**: Comprehensive test coverage in `test_invitation_roles.py`

## Testing

The test suite verifies:
- ✅ Serializer-level role validation and defaults
- ✅ API-level role assignment for both admin and member roles
- ✅ Permission enforcement (admin-only)
- ✅ Error handling for invalid roles

**Run tests:**
```bash
python manage.py test users.tests.test_invitation_roles
```