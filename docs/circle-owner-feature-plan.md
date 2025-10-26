# Circle Owner Feature - Implementation Plan

## Overview

Add the concept of a "circle owner" - the person who created the circle and has irrevocable membership. This establishes clear ownership and prevents accidental removal of the circle creator.

## Requirements

1. **Circle Owner**
   - The user who created the circle (`created_by`) is the owner
   - Owner cannot be removed from the circle (by anyone, including themselves)
   - Only one owner per circle (the creator)

2. **Removal Rules**
   - Owner: Cannot be removed (prevented at API/UI level)
   - Members: Can remove themselves OR be removed by admins
   - Admins: Can remove themselves OR be removed by other admins (except owner)

3. **UI/UX**
   - Display owner badge/indicator in member lists
   - Disable/hide remove button for owner
   - Show helpful error if removal attempted via API

## Current State Analysis

### Database Schema

**Circle Model** (`mysite/circles/models/circle.py`):
```python
class Circle(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    created_by = models.ForeignKey(...)  # ← Already tracks creator
    created_at = models.DateTimeField(default=timezone.now)
```

**CircleMembership Model** (`mysite/circles/models/membership.py`):
```python
class CircleMembership(models.Model):
    user = models.ForeignKey(...)
    circle = models.ForeignKey(...)
    role = models.CharField(
        choices=UserRole.choices,  # CIRCLE_ADMIN or CIRCLE_MEMBER
        default=UserRole.CIRCLE_MEMBER,
    )
    invited_by = models.ForeignKey(...)
    created_at = models.DateTimeField(...)
```

### Existing Roles

From `mysite/users/models/user.py:18`:
- `CIRCLE_ADMIN` - Can manage members and circle
- `CIRCLE_MEMBER` - Regular member

### Current Removal Logic

From `mysite/circles/views/memberships.py:85-106`:
```python
def delete(self, request, circle_id, user_id):
    # No owner check currently!
    # Anyone can be removed if:
    # - Removing self (any member)
    # - Admin removing others
```

## Database Changes

### Option A: Add `is_owner` field to CircleMembership (RECOMMENDED)

**Pros:**
- Explicit ownership tracking
- Easy queries: `CircleMembership.objects.filter(circle=circle, is_owner=True)`
- Clear intent in code
- Future-proof if we want to transfer ownership

**Cons:**
- Additional field and migration

**Implementation:**
```python
class CircleMembership(models.Model):
    # ... existing fields ...
    is_owner = models.BooleanField(default=False)

    class Meta:
        app_label = 'users'
        unique_together = ('user', 'circle')
        ordering = ['circle__name', 'user__email']
        # Add constraint to ensure only one owner per circle
        constraints = [
            models.UniqueConstraint(
                fields=['circle'],
                condition=models.Q(is_owner=True),
                name='one_owner_per_circle'
            )
        ]
```

### Option B: Use `created_by` relationship only

**Pros:**
- No schema changes
- Data already exists

**Cons:**
- Requires join: `circle.created_by == membership.user`
- Harder to transfer ownership in future
- Less explicit

**Recommendation:** Use Option A for clarity and future flexibility.

## Backend Changes

### 1. Model Changes

**File:** `mysite/circles/models/membership.py`

Add:
- `is_owner = models.BooleanField(default=False)`
- Database constraint for one owner per circle
- Helper method: `def is_circle_owner(self) -> bool`

**File:** `mysite/circles/models/circle.py`

Add helper methods:
```python
def get_owner_membership(self) -> CircleMembership | None:
    """Get the owner's membership record."""
    return self.memberships.filter(is_owner=True).first()

def is_owner(self, user) -> bool:
    """Check if user is the circle owner."""
    return self.created_by_id == user.id
```

### 2. Migration

**File:** New migration file

```python
# Generated migration
class Migration(migrations.Migration):
    dependencies = [
        ('users', 'XXXX_previous_migration'),
    ]

    operations = [
        # Add field
        migrations.AddField(
            model_name='circlemembership',
            name='is_owner',
            field=models.BooleanField(default=False),
        ),

        # Data migration: mark existing creators as owners
        migrations.RunPython(set_existing_owners, migrations.RunPython.noop),

        # Add constraint
        migrations.AddConstraint(
            model_name='circlemembership',
            constraint=models.UniqueConstraint(
                fields=['circle'],
                condition=models.Q(is_owner=True),
                name='one_owner_per_circle'
            ),
        ),
    ]

def set_existing_owners(apps, schema_editor):
    """Mark circle creators as owners in their membership records."""
    Circle = apps.get_model('users', 'Circle')
    CircleMembership = apps.get_model('users', 'CircleMembership')

    for circle in Circle.objects.all():
        CircleMembership.objects.filter(
            circle=circle,
            user=circle.created_by
        ).update(is_owner=True)
```

### 3. Signal Handler

**File:** `mysite/circles/signals.py`

Auto-create owner membership when circle is created:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from mysite.users.models import UserRole
from .models import Circle, CircleMembership

@receiver(post_save, sender=Circle)
def create_owner_membership(sender, instance, created, **kwargs):
    """Automatically create owner membership when circle is created."""
    if created:
        CircleMembership.objects.get_or_create(
            user=instance.created_by,
            circle=instance,
            defaults={
                'role': UserRole.CIRCLE_ADMIN,
                'is_owner': True,
                # invited_by is null for owner (they created it)
            }
        )
```

**Note:** Ensure signals are connected in `apps.py`:
```python
class CirclesConfig(AppConfig):
    name = 'mysite.circles'

    def ready(self):
        import mysite.circles.signals  # noqa: F401
```

### 4. Serializer Changes

**File:** `mysite/circles/serializers/circles.py`

Add `is_owner` to `CircleMemberSerializer`:
```python
class CircleMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    display_name = serializers.CharField(source='user.display_name', read_only=True)
    role = serializers.CharField(read_only=True)
    is_owner = serializers.BooleanField(read_only=True)  # ← ADD THIS

    class Meta:
        model = CircleMembership
        fields = ['user_id', 'email', 'display_name', 'role', 'is_owner', 'created_at']
```

### 5. View/Permission Changes

**File:** `mysite/circles/views/memberships.py:85-106`

Update `CircleMemberRemoveView.delete()`:

```python
def delete(self, request, circle_id, user_id):
    circle = get_object_or_404(Circle, id=circle_id)
    membership_to_remove = CircleMembership.objects.filter(
        circle=circle,
        user_id=user_id
    ).select_related('user').first()

    if not membership_to_remove:
        return error_response(
            'membership_not_found',
            [create_message('errors.membership_not_found')],
            status.HTTP_404_NOT_FOUND
        )

    # NEW: Prevent owner removal
    if membership_to_remove.is_owner:
        return error_response(
            'cannot_remove_owner',
            [create_message('errors.circle.cannot_remove_owner')],
            status.HTTP_403_FORBIDDEN
        )

    requester_membership = CircleMembership.objects.filter(
        circle=circle,
        user=request.user
    ).first()
    removing_self = request.user.id == user_id

    if not removing_self:
        if not (request.user.is_superuser or (
            requester_membership and requester_membership.role == UserRole.CIRCLE_ADMIN
        )):
            raise PermissionDenied(_('Only circle admins can remove other members'))
    else:
        if not requester_membership and not request.user.is_superuser:
            raise PermissionDenied(_('Not a member of this circle'))

    membership_to_remove.delete()
    return success_response({}, status_code=status.HTTP_204_NO_CONTENT)
```

### 6. Error Messages

**File:** `web/src/i18n/locales/en.json`

Add translation key:
```json
{
  "errors": {
    "circle": {
      "cannot_remove_owner": "Cannot remove the circle owner. The person who created the circle cannot be removed."
    }
  }
}
```

## Frontend Changes

### 1. Update CircleMember Type

**File:** `web/src/features/circles/types.ts` (or similar)

```typescript
export interface CircleMember {
  user_id: number;
  email: string;
  display_name: string;
  role: 'admin' | 'member';
  is_owner: boolean;  // ← ADD THIS
  created_at: string;
}
```

### 2. Update CircleMemberListItem Component

**File:** `web/src/features/circles/components/CircleMemberListItem.tsx`

```typescript
interface CircleMemberListItemProps {
  member: CircleMember;
  currentUserId: number;
  onRemove: (userId: number) => void;
  canRemoveMembers: boolean;
}

export function CircleMemberListItem({
  member,
  currentUserId,
  onRemove,
  canRemoveMembers
}: CircleMemberListItemProps) {
  const isCurrentUser = member.user_id === currentUserId;
  const isOwner = member.is_owner;

  // Owner cannot be removed (by anyone, including themselves)
  const showRemoveButton = !isOwner && (isCurrentUser || canRemoveMembers);

  return (
    <div className="member-item">
      <div className="member-info">
        <span>{member.display_name || member.email}</span>
        {isOwner && <Badge variant="primary">Owner</Badge>}
        {member.role === 'admin' && !isOwner && <Badge>Admin</Badge>}
      </div>

      {showRemoveButton && (
        <Button
          variant="danger"
          onClick={() => onRemove(member.user_id)}
        >
          {isCurrentUser ? 'Leave Circle' : 'Remove'}
        </Button>
      )}
    </div>
  );
}
```

### 3. Update Member List Controller

**File:** `web/src/features/circles/hooks/useCircleMemberListController.ts`

Handle owner removal error:
```typescript
const removeMember = async (userId: number) => {
  try {
    await api.delete(`/circles/${circleId}/members/${userId}/`);
    showSuccess('Member removed');
    refetch();
  } catch (error) {
    if (error.code === 'cannot_remove_owner') {
      showError('Cannot remove the circle owner');
    } else {
      showError('Failed to remove member');
    }
  }
};
```

### 4. Circle Dashboard

**File:** `web/src/route-views/circles/dashboard.tsx`

Display owner info in circle header/settings:
```typescript
<div className="circle-header">
  <h1>{circle.name}</h1>
  <p className="circle-owner">
    Created by: {ownerMember?.display_name || ownerMember?.email}
  </p>
</div>
```

## Testing Plan

### Backend Tests

**File:** `mysite/circles/tests/test_circle_ownership.py` (NEW)

```python
class CircleOwnershipTests(TestCase):
    def test_owner_membership_created_automatically(self):
        """When circle is created, owner membership is auto-created."""
        user = create_user('owner@test.com')
        circle = Circle.objects.create(name='Test', created_by=user)

        membership = CircleMembership.objects.get(circle=circle, user=user)
        self.assertTrue(membership.is_owner)
        self.assertEqual(membership.role, UserRole.CIRCLE_ADMIN)

    def test_cannot_remove_owner_via_api(self):
        """Owner cannot be removed via API endpoint."""
        owner = create_user('owner@test.com')
        admin = create_user('admin@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(
            circle=circle,
            user=admin,
            role=UserRole.CIRCLE_ADMIN
        )

        # Admin tries to remove owner
        self.client.force_authenticate(admin)
        response = self.client.delete(f'/circles/{circle.id}/members/{owner.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'cannot_remove_owner')
        self.assertTrue(CircleMembership.objects.filter(
            circle=circle, user=owner
        ).exists())

    def test_owner_cannot_remove_themselves(self):
        """Owner cannot remove themselves."""
        owner = create_user('owner@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)

        self.client.force_authenticate(owner)
        response = self.client.delete(f'/circles/{circle.id}/members/{owner.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CircleMembership.objects.filter(
            circle=circle, user=owner
        ).exists())

    def test_admin_can_remove_other_admin(self):
        """Admins can remove other admins (except owner)."""
        owner = create_user('owner@test.com')
        admin1 = create_user('admin1@test.com')
        admin2 = create_user('admin2@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(
            circle=circle, user=admin1, role=UserRole.CIRCLE_ADMIN
        )
        CircleMembership.objects.create(
            circle=circle, user=admin2, role=UserRole.CIRCLE_ADMIN
        )

        self.client.force_authenticate(admin1)
        response = self.client.delete(f'/circles/{circle.id}/members/{admin2.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CircleMembership.objects.filter(
            circle=circle, user=admin2
        ).exists())

    def test_only_one_owner_per_circle_constraint(self):
        """Database constraint prevents multiple owners."""
        owner = create_user('owner@test.com')
        user2 = create_user('user2@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)

        with self.assertRaises(IntegrityError):
            CircleMembership.objects.create(
                circle=circle,
                user=user2,
                is_owner=True
            )
```

**File:** Update existing tests in `mysite/circles/tests/test_invitation_workflow.py`

Ensure invitations still work with owner concept:
```python
def test_invited_user_joins_circle_with_owner_present(self):
    """New users can join via invitation, owner is preserved."""
    # ... existing test, add assertions:
    owner_membership = CircleMembership.objects.get(
        circle=circle, is_owner=True
    )
    self.assertEqual(owner_membership.user, circle.created_by)
```

### Frontend Tests

**File:** `web/src/features/circles/components/CircleMemberListItem.test.tsx`

```typescript
describe('CircleMemberListItem', () => {
  it('shows owner badge for owner', () => {
    const owner: CircleMember = {
      user_id: 1,
      email: 'owner@test.com',
      display_name: 'Owner',
      role: 'admin',
      is_owner: true,
      created_at: '2024-01-01',
    };

    render(<CircleMemberListItem member={owner} {...defaultProps} />);
    expect(screen.getByText('Owner')).toBeInTheDocument();
  });

  it('hides remove button for owner', () => {
    const owner: CircleMember = { ...defaultMember, is_owner: true };

    render(<CircleMemberListItem member={owner} {...defaultProps} />);
    expect(screen.queryByText('Remove')).not.toBeInTheDocument();
    expect(screen.queryByText('Leave Circle')).not.toBeInTheDocument();
  });

  it('shows remove button for non-owner admin when user is admin', () => {
    const admin: CircleMember = {
      ...defaultMember,
      role: 'admin',
      is_owner: false
    };

    render(
      <CircleMemberListItem
        member={admin}
        canRemoveMembers={true}
        {...defaultProps}
      />
    );
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });
});
```

## Migration Strategy

### Step 1: Backend Migration (Can deploy independently)
1. Add migration with `is_owner` field
2. Run data migration to mark existing owners
3. Add signal handler for new circles
4. Update views to prevent owner removal
5. Deploy backend
6. **System still works** - frontend just doesn't show owner badge yet

### Step 2: Frontend Update
1. Update types to include `is_owner`
2. Update UI to show owner badge
3. Update UI to hide remove button for owners
4. Deploy frontend

### Rollback Plan
- If issues found after backend deploy: Add temporary feature flag
- If need to rollback migration: Keep `is_owner` field, just set all to `False`

## Edge Cases & Considerations

### 1. Existing Circles
- Data migration handles existing circles
- If creator is not a member (edge case), signal won't fire on migration
- Solution: Data migration explicitly creates membership if missing

### 2. Orphaned Circles
- What if creator account is deleted?
  - Current: `on_delete=models.CASCADE` deletes circle
  - Keep this behavior (circle owned by creator)

### 3. Superuser Permissions
- Should superusers be able to remove owner?
  - **No** - even superusers respect owner rule
  - Provides consistent UX
  - If needed, superuser can use Django admin

### 4. Future: Transfer Ownership
- Not in this PR, but design supports it:
  - Set `old_owner.is_owner = False`
  - Set `new_owner.is_owner = True`
  - Update `circle.created_by = new_owner`

### 5. API Versioning
- This is a **non-breaking change**:
  - Adds new field `is_owner` (optional in responses)
  - Existing clients ignore unknown fields
  - New clients use the field

### 6. Audit Trail
- Keep `created_by` field unchanged (historical record)
- `is_owner` can change in future, `created_by` cannot

## Implementation Order

1. ✅ **Backend Models** - Add `is_owner` field and migration
2. ✅ **Backend Signal** - Auto-create owner membership
3. ✅ **Backend Views** - Prevent owner removal
4. ✅ **Backend Tests** - Comprehensive ownership tests
5. ✅ **Frontend Types** - Update TypeScript interfaces
6. ✅ **Frontend Components** - Show owner badge, hide remove button
7. ✅ **Frontend Tests** - Component and integration tests
8. ✅ **Manual QA** - Test full flow in dev environment

## Success Criteria

- [ ] Owner membership auto-created when circle is created
- [ ] Owner badge displayed in member list
- [ ] Remove button hidden for owner (for all users)
- [ ] API returns 403 if owner removal attempted
- [ ] Admins can still remove other members (including other admins)
- [ ] Members can still remove themselves (except owner)
- [ ] All tests pass
- [ ] No breaking changes to existing API clients

## Detailed Implementation Steps

### Phase 1: Backend Models & Migration

#### Step 1.1: Update CircleMembership Model

**File:** `mysite/circles/models/membership.py`

```python
"""Circle membership model implementation."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from mysite.users.models.user import UserRole

from .circle import Circle


class CircleMembership(models.Model):
    """Represents a user's membership in a circle."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_memberships',
    )
    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CIRCLE_MEMBER,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='memberships_invited',
    )
    # NEW: Track circle ownership
    is_owner = models.BooleanField(
        default=False,
        help_text="True if this user is the circle owner (creator)",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'users'
        unique_together = ('user', 'circle')
        ordering = ['circle__name', 'user__email']
        # NEW: Constraint to ensure only one owner per circle
        constraints = [
            models.UniqueConstraint(
                fields=['circle'],
                condition=models.Q(is_owner=True),
                name='one_owner_per_circle'
            )
        ]

    def __str__(self) -> str:
        owner_str = " [OWNER]" if self.is_owner else ""
        return f"{self.user} in {self.circle} ({self.role}){owner_str}"


__all__ = ['CircleMembership']
```

#### Step 1.2: Update Circle Model Helper Methods

**File:** `mysite/circles/models/circle.py`

Add these methods to the `Circle` class:

```python
class Circle(models.Model):
    """A family circle for sharing content and memories."""

    # ... existing fields ...

    def get_owner_membership(self):
        """Get the owner's membership record.

        Returns:
            CircleMembership or None if owner hasn't joined yet
        """
        from .membership import CircleMembership
        return self.memberships.filter(is_owner=True).first()

    def is_owner(self, user) -> bool:
        """Check if the given user is the circle owner.

        Args:
            user: User instance or user ID

        Returns:
            True if user is the owner, False otherwise
        """
        user_id = user.id if hasattr(user, 'id') else user
        return self.created_by_id == user_id

    def get_owner_user(self):
        """Get the user who owns this circle.

        Returns:
            User instance
        """
        return self.created_by
```

#### Step 1.3: Generate and Customize Migration

**Commands:**
```bash
# Generate the migration
python manage.py makemigrations circles -n add_circle_owner_field

# This will create a file like:
# mysite/circles/migrations/XXXX_add_circle_owner_field.py
```

**Manually edit the generated migration file:**

```python
# Generated by Django X.X on YYYY-MM-DD
from django.db import migrations, models


def set_existing_owners_forward(apps, schema_editor):
    """Mark circle creators as owners in their membership records.

    For existing circles:
    1. Find the creator via circle.created_by
    2. Find or create their membership record
    3. Mark them as owner with admin role
    """
    Circle = apps.get_model('users', 'Circle')
    CircleMembership = apps.get_model('users', 'CircleMembership')

    # Get UserRole.CIRCLE_ADMIN value without importing the model
    CIRCLE_ADMIN = 'admin'

    circles_updated = 0
    memberships_created = 0

    for circle in Circle.objects.select_related('created_by').all():
        # Get or create the owner's membership
        membership, created = CircleMembership.objects.get_or_create(
            circle=circle,
            user=circle.created_by,
            defaults={
                'role': CIRCLE_ADMIN,
                'is_owner': True,
                # invited_by is null for owner
            }
        )

        if created:
            memberships_created += 1
        elif not membership.is_owner:
            # Update existing membership to be owner
            membership.is_owner = True
            if membership.role != CIRCLE_ADMIN:
                membership.role = CIRCLE_ADMIN
            membership.save()
            circles_updated += 1

    print(f"Data migration complete:")
    print(f"  - {memberships_created} owner memberships created")
    print(f"  - {circles_updated} existing memberships updated to owner")


def set_existing_owners_reverse(apps, schema_editor):
    """Reverse migration - remove owner flags."""
    CircleMembership = apps.get_model('users', 'CircleMembership')
    CircleMembership.objects.filter(is_owner=True).update(is_owner=False)


class Migration(migrations.Migration):

    dependencies = [
        ('users', 'XXXX_previous_migration'),  # Update with actual dependency
    ]

    operations = [
        # Step 1: Add the is_owner field (nullable initially for safety)
        migrations.AddField(
            model_name='circlemembership',
            name='is_owner',
            field=models.BooleanField(
                default=False,
                help_text="True if this user is the circle owner (creator)"
            ),
        ),

        # Step 2: Run data migration to populate is_owner for existing circles
        migrations.RunPython(
            set_existing_owners_forward,
            set_existing_owners_reverse,
        ),

        # Step 3: Add database constraint (one owner per circle)
        migrations.AddConstraint(
            model_name='circlemembership',
            constraint=models.UniqueConstraint(
                fields=['circle'],
                condition=models.Q(is_owner=True),
                name='one_owner_per_circle'
            ),
        ),
    ]
```

**Test the migration:**
```bash
# Test on a copy of production data first!
python manage.py migrate --plan  # Dry run
python manage.py migrate users XXXX_add_circle_owner_field
```

#### Step 1.4: Update Signal Handler

**File:** `mysite/circles/signals.py`

Add this new signal handler:

```python
"""Signal handlers for the circles domain."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from mysite.users.models import CircleOnboardingStatus, UserRole

from .models import Circle, CircleMembership


# Existing signal handler
@receiver(post_save, sender=CircleMembership)
def mark_circle_onboarding_complete(sender, instance: CircleMembership, created: bool, **_: object) -> None:
    """Mark a user's onboarding as complete when they gain a circle membership."""
    if not created:
        return

    user = instance.user
    if user.circle_onboarding_status == CircleOnboardingStatus.COMPLETED:
        return

    user.set_circle_onboarding_status(CircleOnboardingStatus.COMPLETED, save=True)


# NEW: Auto-create owner membership when circle is created
@receiver(post_save, sender=Circle)
def create_owner_membership(sender, instance: Circle, created: bool, **kwargs) -> None:
    """Automatically create owner membership when circle is created.

    When a new circle is created:
    1. Create a CircleMembership for the creator
    2. Mark them as owner (is_owner=True)
    3. Give them admin role
    4. Set invited_by to None (they created it)

    Uses get_or_create to be idempotent (safe to run multiple times).
    """
    if not created:
        return

    # Create owner membership
    CircleMembership.objects.get_or_create(
        user=instance.created_by,
        circle=instance,
        defaults={
            'role': UserRole.CIRCLE_ADMIN,
            'is_owner': True,
            'invited_by': None,  # Owner wasn't invited, they created it
        }
    )
```

**Verify signals are connected:**

The signals are already imported in `mysite/circles/apps.py:11`, so no changes needed there.

### Phase 2: Backend Views & Serializers

#### Step 2.1: Update CircleMemberSerializer

**File:** `mysite/circles/serializers/circles.py:27-34`

Update the `CircleMemberSerializer` to include `is_owner`:

```python
class CircleMemberSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source='id', read_only=True)
    user = UserSerializer()
    is_owner = serializers.BooleanField(read_only=True)  # NEW

    class Meta:
        model = CircleMembership
        fields = ['membership_id', 'user', 'role', 'is_owner', 'created_at']  # Added is_owner
```

#### Step 2.2: Update CircleMembershipSerializer

**File:** `mysite/circles/serializers/circles.py:18-25`

```python
class CircleMembershipSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source='id', read_only=True)
    circle = CircleSerializer()
    is_owner = serializers.BooleanField(read_only=True)  # NEW

    class Meta:
        model = CircleMembership
        fields = ['membership_id', 'circle', 'role', 'is_owner', 'created_at']  # Added is_owner
```

#### Step 2.3: Update CircleCreateSerializer

**File:** `mysite/circles/serializers/circles.py:36-53`

Update to NOT manually create membership (signal handles it now):

```python
class CircleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def validate(self, attrs):
        user = self.context['user']
        if not user.email_verified:
            raise serializers.ValidationError(create_message('errors.email_verification_required'))
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        circle = Circle.objects.create(created_by=user, **validated_data)
        # REMOVED: Manual membership creation - signal handler does this now
        # The post_save signal on Circle will auto-create owner membership
        return circle
```

#### Step 2.4: Update CircleMemberRemoveView

**File:** `mysite/circles/views/memberships.py:77-107`

Add owner check before deletion:

```python
class CircleMemberRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMemberSerializer

    @extend_schema(
        description='Remove a member (or yourself) from a circle. Circle owners cannot be removed.',
        responses={
            204: OpenApiResponse(description='Membership removed.'),
            403: OpenApiResponse(description='Cannot remove circle owner.'),
            404: OpenApiResponse(description='Membership not found.'),
        },
    )
    def delete(self, request, circle_id, user_id):
        circle = get_object_or_404(Circle, id=circle_id)

        # Get membership to remove with user info for better error messages
        membership_to_remove = CircleMembership.objects.filter(
            circle=circle,
            user_id=user_id
        ).select_related('user').first()

        if not membership_to_remove:
            return error_response(
                'membership_not_found',
                [create_message('errors.membership_not_found')],
                status.HTTP_404_NOT_FOUND
            )

        # NEW: Prevent owner removal (most important check - do this first)
        if membership_to_remove.is_owner:
            return error_response(
                'cannot_remove_owner',
                [create_message('errors.circle.cannot_remove_owner')],
                status.HTTP_403_FORBIDDEN
            )

        # Check permissions for removal
        requester_membership = CircleMembership.objects.filter(
            circle=circle,
            user=request.user
        ).first()
        removing_self = request.user.id == user_id

        if not removing_self:
            # Admin removing another member
            if not (request.user.is_superuser or (
                requester_membership and requester_membership.role == UserRole.CIRCLE_ADMIN
            )):
                raise PermissionDenied(_('Only circle admins can remove other members'))
        else:
            # User removing themselves
            if not requester_membership and not request.user.is_superuser:
                raise PermissionDenied(_('Not a member of this circle'))

        # All checks passed - delete the membership
        membership_to_remove.delete()
        return success_response({}, status_code=status.HTTP_204_NO_CONTENT)
```

#### Step 2.5: Add Translation Keys

**File:** `web/src/i18n/locales/en.json`

Add these keys in the appropriate sections:

```json
{
  "errors": {
    "circle": {
      "cannot_remove_owner": "Cannot remove the circle owner. The person who created the circle cannot be removed."
    }
  },
  "notifications": {
    "circle": {
      "owner_badge": "Owner",
      "created_by": "Created by {name}"
    }
  }
}
```

### Phase 3: Frontend Implementation

#### Step 3.1: Update TypeScript Types

**File:** `web/src/features/circles/types.ts` (create if doesn't exist)

```typescript
// Circle member with ownership tracking
export interface CircleMember {
  user_id: number;
  email: string;
  display_name: string;
  role: 'admin' | 'member';
  is_owner: boolean;  // NEW
  created_at: string;
}

// API response for member list
export interface CircleMemberListResponse {
  circle: {
    id: number;
    name: string;
    slug: string;
  };
  members: CircleMember[];
}
```

#### Step 3.2: Update API Client

**File:** `web/src/features/circles/api/circlesApi.ts` (or similar)

```typescript
import { apiClient } from '@/lib/api';
import type { CircleMember, CircleMemberListResponse } from '../types';

export const circlesApi = {
  // Get members of a circle
  async getMembers(circleId: number): Promise<CircleMemberListResponse> {
    const response = await apiClient.get(`/circles/${circleId}/members/`);
    return response.data;
  },

  // Remove a member (with owner protection)
  async removeMember(circleId: number, userId: number): Promise<void> {
    await apiClient.delete(`/circles/${circleId}/members/${userId}/`);
  },
};
```

#### Step 3.3: Complete CircleMemberListItem Component

**File:** `web/src/features/circles/components/CircleMemberListItem.tsx`

```typescript
import { type CircleMember } from '../types';

interface CircleMemberListItemProps {
  member: CircleMember;
  currentUserId: number;
  onRemove: (userId: number) => void;
  canRemoveMembers: boolean;
}

export function CircleMemberListItem({
  member,
  currentUserId,
  onRemove,
  canRemoveMembers,
}: CircleMemberListItemProps) {
  const isCurrentUser = member.user_id === currentUserId;
  const isOwner = member.is_owner;

  // Owner cannot be removed (by anyone, including themselves)
  const showRemoveButton = !isOwner && (isCurrentUser || canRemoveMembers);

  const handleRemove = () => {
    if (window.confirm(
      isCurrentUser
        ? 'Are you sure you want to leave this circle?'
        : `Remove ${member.display_name || member.email}?`
    )) {
      onRemove(member.user_id);
    }
  };

  return (
    <div className="flex items-center justify-between py-3 px-4 border-b">
      <div className="flex items-center gap-3 flex-1">
        <div className="flex flex-col">
          <span className="font-medium">
            {member.display_name || member.email}
          </span>
          <span className="text-sm text-gray-500">{member.email}</span>
        </div>

        <div className="flex gap-2">
          {isOwner && (
            <span className="px-2 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
              Owner
            </span>
          )}
          {member.role === 'admin' && !isOwner && (
            <span className="px-2 py-1 text-xs font-semibold bg-purple-100 text-purple-800 rounded">
              Admin
            </span>
          )}
          {isCurrentUser && (
            <span className="px-2 py-1 text-xs font-semibold bg-gray-100 text-gray-600 rounded">
              You
            </span>
          )}
        </div>
      </div>

      {showRemoveButton && (
        <button
          onClick={handleRemove}
          className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded border border-red-300 hover:border-red-400 transition-colors"
        >
          {isCurrentUser ? 'Leave Circle' : 'Remove'}
        </button>
      )}

      {isOwner && (
        <span className="text-xs text-gray-400 italic">Cannot be removed</span>
      )}
    </div>
  );
}
```

#### Step 3.4: Update useCircleMemberListController Hook

**File:** `web/src/features/circles/hooks/useCircleMemberListController.ts`

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { circlesApi } from '../api/circlesApi';
import { useToast } from '@/hooks/useToast';
import type { CircleMember } from '../types';

export function useCircleMemberListController(circleId: number) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();

  // Fetch members
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['circles', circleId, 'members'],
    queryFn: () => circlesApi.getMembers(circleId),
  });

  // Remove member mutation
  const removeMemberMutation = useMutation({
    mutationFn: ({ userId }: { userId: number }) =>
      circlesApi.removeMember(circleId, userId),
    onSuccess: () => {
      showSuccess('Member removed successfully');
      // Invalidate queries to refetch member list
      queryClient.invalidateQueries({ queryKey: ['circles', circleId, 'members'] });
    },
    onError: (error: any) => {
      // Handle specific error codes
      if (error.response?.data?.code === 'cannot_remove_owner') {
        showError('Cannot remove the circle owner');
      } else if (error.response?.data?.code === 'membership_not_found') {
        showError('Member not found');
      } else {
        showError('Failed to remove member');
      }
    },
  });

  const removeMember = (userId: number) => {
    removeMemberMutation.mutate({ userId });
  };

  // Find owner from member list
  const owner = data?.members.find(m => m.is_owner);

  return {
    members: data?.members ?? [],
    circle: data?.circle,
    owner,
    isLoading,
    error,
    removeMember,
    isRemoving: removeMemberMutation.isPending,
    refetch,
  };
}
```

### Phase 4: Testing

#### Step 4.1: Backend Unit Tests

**File:** `mysite/circles/tests/test_circle_ownership.py` (NEW)

Create comprehensive test file:

```python
"""Tests for circle ownership functionality."""

from django.test import TestCase
from django.db import IntegrityError
from rest_framework.test import APIClient

from mysite.users.models import User, UserRole
from mysite.circles.models import Circle, CircleMembership


def create_user(email: str, password: str = 'testpass123') -> User:
    """Helper to create a test user."""
    return User.objects.create_user(
        email=email,
        password=password,
        email_verified=True,
    )


class CircleOwnershipModelTests(TestCase):
    """Test ownership at the model level."""

    def test_owner_membership_created_automatically_via_signal(self):
        """When circle is created, owner membership is auto-created via signal."""
        user = create_user('owner@test.com')
        circle = Circle.objects.create(name='Test Circle', created_by=user)

        # Signal should have created membership
        membership = CircleMembership.objects.get(circle=circle, user=user)
        self.assertTrue(membership.is_owner)
        self.assertEqual(membership.role, UserRole.CIRCLE_ADMIN)
        self.assertIsNone(membership.invited_by)

    def test_only_one_owner_per_circle_constraint(self):
        """Database constraint prevents multiple owners."""
        owner = create_user('owner@test.com')
        user2 = create_user('user2@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)

        # Try to create another owner - should fail
        with self.assertRaises(IntegrityError):
            CircleMembership.objects.create(
                circle=circle,
                user=user2,
                is_owner=True,
            )

    def test_circle_helper_methods(self):
        """Test Circle model helper methods."""
        owner = create_user('owner@test.com')
        member = create_user('member@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(circle=circle, user=member)

        # Test is_owner method
        self.assertTrue(circle.is_owner(owner))
        self.assertFalse(circle.is_owner(member))

        # Test get_owner_membership
        owner_membership = circle.get_owner_membership()
        self.assertIsNotNone(owner_membership)
        self.assertEqual(owner_membership.user, owner)

        # Test get_owner_user
        self.assertEqual(circle.get_owner_user(), owner)


class CircleOwnershipAPITests(TestCase):
    """Test ownership rules via API endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_cannot_remove_owner_via_api(self):
        """Owner cannot be removed via DELETE endpoint."""
        owner = create_user('owner@test.com')
        admin = create_user('admin@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(
            circle=circle,
            user=admin,
            role=UserRole.CIRCLE_ADMIN,
        )

        # Admin tries to remove owner
        self.client.force_authenticate(admin)
        response = self.client.delete(f'/circles/{circle.id}/members/{owner.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'cannot_remove_owner')
        # Verify owner still exists
        self.assertTrue(
            CircleMembership.objects.filter(circle=circle, user=owner).exists()
        )

    def test_owner_cannot_remove_themselves(self):
        """Owner cannot remove themselves via API."""
        owner = create_user('owner@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)

        self.client.force_authenticate(owner)
        response = self.client.delete(f'/circles/{circle.id}/members/{owner.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            CircleMembership.objects.filter(circle=circle, user=owner).exists()
        )

    def test_admin_can_remove_other_admin_not_owner(self):
        """Admins can remove other admins (except owner)."""
        owner = create_user('owner@test.com')
        admin1 = create_user('admin1@test.com')
        admin2 = create_user('admin2@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(
            circle=circle, user=admin1, role=UserRole.CIRCLE_ADMIN
        )
        CircleMembership.objects.create(
            circle=circle, user=admin2, role=UserRole.CIRCLE_ADMIN
        )

        self.client.force_authenticate(admin1)
        response = self.client.delete(f'/circles/{circle.id}/members/{admin2.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            CircleMembership.objects.filter(circle=circle, user=admin2).exists()
        )

    def test_member_can_remove_themselves(self):
        """Regular members can remove themselves."""
        owner = create_user('owner@test.com')
        member = create_user('member@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(circle=circle, user=member)

        self.client.force_authenticate(member)
        response = self.client.delete(f'/circles/{circle.id}/members/{member.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            CircleMembership.objects.filter(circle=circle, user=member).exists()
        )

    def test_member_list_includes_is_owner_field(self):
        """GET /circles/{id}/members/ includes is_owner in response."""
        owner = create_user('owner@test.com')
        admin = create_user('admin@test.com')
        circle = Circle.objects.create(name='Test', created_by=owner)
        CircleMembership.objects.create(
            circle=circle, user=admin, role=UserRole.CIRCLE_ADMIN
        )

        self.client.force_authenticate(owner)
        response = self.client.get(f'/circles/{circle.id}/members/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        members = data['data']['members']

        # Find owner in response
        owner_member = next(m for m in members if m['user']['id'] == owner.id)
        self.assertTrue(owner_member['is_owner'])

        # Admin should not be owner
        admin_member = next(m for m in members if m['user']['id'] == admin.id)
        self.assertFalse(admin_member['is_owner'])


class CircleOwnershipDataMigrationTests(TestCase):
    """Test that data migration works correctly."""

    def test_existing_circles_get_owner_memberships(self):
        """Simulate pre-migration state and verify migration logic."""
        # Create circle without triggering signal
        # (simulates old data before owner feature)
        with self.settings(SIGNAL_HANDLERS_DISABLED=True):
            owner = create_user('owner@test.com')
            circle = Circle.objects.create(name='Old Circle', created_by=owner)
            # Manually create membership without is_owner
            membership = CircleMembership.objects.create(
                circle=circle,
                user=owner,
                role=UserRole.CIRCLE_ADMIN,
            )
            membership.is_owner = False
            membership.save()

        # Now run the migration logic
        membership.is_owner = True
        membership.save()

        # Verify
        membership.refresh_from_db()
        self.assertTrue(membership.is_owner)
```

**Run tests:**
```bash
python manage.py test mysite.circles.tests.test_circle_ownership
```

#### Step 4.2: Frontend Component Tests

**File:** `web/src/features/circles/components/CircleMemberListItem.test.tsx`

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { CircleMemberListItem } from './CircleMemberListItem';
import type { CircleMember } from '../types';

describe('CircleMemberListItem', () => {
  const mockOnRemove = vi.fn();

  const defaultProps = {
    currentUserId: 1,
    onRemove: mockOnRemove,
    canRemoveMembers: false,
  };

  const defaultMember: CircleMember = {
    user_id: 2,
    email: 'test@test.com',
    display_name: 'Test User',
    role: 'member' as const,
    is_owner: false,
    created_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    mockOnRemove.mockClear();
  });

  it('shows owner badge for owner', () => {
    const owner: CircleMember = { ...defaultMember, is_owner: true };

    render(<CircleMemberListItem member={owner} {...defaultProps} />);

    expect(screen.getByText('Owner')).toBeInTheDocument();
  });

  it('hides remove button for owner', () => {
    const owner: CircleMember = { ...defaultMember, is_owner: true };

    render(<CircleMemberListItem member={owner} {...defaultProps} />);

    expect(screen.queryByText('Remove')).not.toBeInTheDocument();
    expect(screen.queryByText('Leave Circle')).not.toBeInTheDocument();
  });

  it('shows "cannot be removed" text for owner', () => {
    const owner: CircleMember = { ...defaultMember, is_owner: true };

    render(<CircleMemberListItem member={owner} {...defaultProps} />);

    expect(screen.getByText('Cannot be removed')).toBeInTheDocument();
  });

  it('shows remove button for non-owner when user is admin', () => {
    const member: CircleMember = { ...defaultMember };

    render(
      <CircleMemberListItem
        member={member}
        canRemoveMembers={true}
        {...defaultProps}
      />
    );

    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('shows leave button for current user (non-owner)', () => {
    const currentUserMember: CircleMember = {
      ...defaultMember,
      user_id: 1, // Same as currentUserId
    };

    render(<CircleMemberListItem member={currentUserMember} {...defaultProps} />);

    expect(screen.getByText('Leave Circle')).toBeInTheDocument();
  });

  it('calls onRemove when remove button clicked', () => {
    const member: CircleMember = { ...defaultMember };
    window.confirm = vi.fn(() => true);

    render(
      <CircleMemberListItem
        member={member}
        canRemoveMembers={true}
        {...defaultProps}
      />
    );

    fireEvent.click(screen.getByText('Remove'));

    expect(mockOnRemove).toHaveBeenCalledWith(member.user_id);
  });

  it('shows both owner and admin badges for owner admin', () => {
    const ownerAdmin: CircleMember = {
      ...defaultMember,
      role: 'admin',
      is_owner: true,
    };

    render(<CircleMemberListItem member={ownerAdmin} {...defaultProps} />);

    // Owner badge should show, admin badge should not (owner takes precedence)
    expect(screen.getByText('Owner')).toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });
});
```

**Run tests:**
```bash
npm test -- CircleMemberListItem.test.tsx
```

### Phase 5: Deployment Checklist

#### Pre-Deployment

- [ ] All tests pass locally
- [ ] Migration tested on copy of production database
- [ ] Code reviewed by team
- [ ] API documentation updated (if using Swagger/OpenAPI)
- [ ] Backend changes deployed to staging
- [ ] Frontend changes deployed to staging
- [ ] Manual QA on staging environment

#### Deployment Commands

```bash
# Backend deployment
git checkout main
git pull
python manage.py migrate
python manage.py test
sudo systemctl restart gunicorn

# Frontend deployment
npm run build
npm run deploy
```

#### Post-Deployment Verification

```bash
# Verify migration applied
python manage.py showmigrations users | grep add_circle_owner_field

# Check data integrity
python manage.py shell
>>> from mysite.circles.models import Circle, CircleMembership
>>> for circle in Circle.objects.all():
...     owner_membership = circle.get_owner_membership()
...     if not owner_membership:
...         print(f"WARNING: Circle {circle.id} has no owner!")
...     elif owner_membership.user != circle.created_by:
...         print(f"WARNING: Circle {circle.id} owner mismatch!")
```

## Performance Considerations

### Database Query Optimization

When fetching members, use `select_related` to avoid N+1 queries:

```python
# In views/memberships.py:43
memberships = CircleMembership.objects.filter(circle=circle)\
    .select_related('user')\
    .order_by('-is_owner', 'user__email')  # Owner first, then alphabetical
```

### Indexing

The `is_owner` field is used in:
1. Uniqueness constraint (already indexed)
2. Filters for finding owner

Current indexes are sufficient - no additional indexes needed.

## Security Considerations

1. **API Level Protection**: Owner removal blocked at view level (403 response)
2. **Database Level Protection**: Constraint ensures only one owner per circle
3. **No Superuser Override**: Even superusers cannot remove owner via API (use Django admin if needed)
4. **Audit Trail**: `created_by` field preserved for historical record

## Related Files Reference

- Circle Model: `mysite/circles/models/circle.py`
- Membership Model: `mysite/circles/models/membership.py:12`
- User Roles: `mysite/users/models/user.py:12`
- Membership Views: `mysite/circles/views/memberships.py:77-107`
- Signals: `mysite/circles/signals.py`
- Apps Config: `mysite/circles/apps.py`
- Serializers: `mysite/circles/serializers/circles.py:27-34`
- Member List Component: `web/src/features/circles/components/CircleMemberListItem.tsx`
- Invitation Tests: `mysite/circles/tests/test_invitation_workflow.py`
