# Role-Based Circle Invitations - Feature Documentation

## Summary

The **role-based circle invitation functionality is already fully implemented and working** in the Tinybeans application! Admin users can already choose the role of invitees when creating circle invitations.

## How It Works

### 1. API Endpoint
**POST** `/api/circles/{circle_id}/invitations/`

### 2. Request Body
```json
{
    "email": "invitee@example.com",
    "role": "admin"  // Optional: "admin" or "member" (defaults to "member")
}
```

### 3. Available Roles
- `"admin"` - Circle Admin (can manage circle, invite/remove members)
- `"member"` - Circle Member (regular member with basic permissions)

### 4. Default Behavior
If no role is specified, the invitation defaults to "member" role.

## Examples

### Inviting an Admin
```bash
curl -X POST /api/circles/123/invitations/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newadmin@example.com",
    "role": "admin"
  }'
```

### Inviting a Member (Explicit)
```bash
curl -X POST /api/circles/123/invitations/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newmember@example.com",
    "role": "member"
  }'
```

### Inviting a Member (Default)
```bash
curl -X POST /api/circles/123/invitations/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "defaultmember@example.com"
  }'
```

## Security & Validation

✅ **Only Circle Admins** can create invitations  
✅ **Role validation** - Invalid roles are rejected with 400 error  
✅ **Duplicate protection** - Cannot invite same email twice to same circle  
✅ **Email validation** - Proper email format required  

## Implementation Details

### Database Model
The `CircleInvitation` model already includes:
- `role` field with UserRole choices (admin/member)
- Proper relationships to Circle and User models
- Status tracking (pending, accepted, declined, etc.)

### Serializer
`CircleInvitationCreateSerializer` handles:
- Role validation using `UserRole.choices`
- Default role assignment to `CIRCLE_MEMBER`
- Email validation and normalization

### View
`CircleInvitationCreateView` enforces:
- Admin-only permissions
- Proper role assignment from request data
- Token generation for secure invitation links
- Email queuing for invitation notifications

## Testing

Comprehensive tests verify:
- ✅ Admins can invite with admin role
- ✅ Admins can invite with member role  
- ✅ Invitations default to member role when not specified
- ✅ Invalid roles are rejected
- ✅ Only admins can create invitations
- ✅ All validation and security measures work correctly

## Conclusion

**No additional development is needed!** The feature you requested is already fully implemented and working. Admin users can already choose the role of invitees by including the `role` parameter in their invitation API calls.

The system provides a clean, secure, and well-tested implementation that follows Django/REST Framework best practices.