# Device Areas Feature

## Overview

The Device Areas feature provides functionality to manage and organize trusted devices by assigning them to physical areas or locations (e.g., Living Room, Office, Kitchen). This is particularly useful for:

- Organizing devices by physical location in Home Assistant or similar systems
- Automatically syncing unassigned devices to a default area
- Bulk management of device locations
- Tracking which devices are used in which areas

## Models

### DeviceArea

Represents a physical area or location where devices can be assigned.

**Fields:**
- `name` (CharField, unique): Name of the area
- `description` (TextField, optional): Description of the area
- `is_default` (BooleanField): Whether this is the default area for unassigned devices
- `created_at` (DateTimeField): When the area was created
- `updated_at` (DateTimeField): When the area was last updated

**Features:**
- Only one area can be marked as default at a time
- Automatically manages default area exclusivity

### DeviceAreaAssignment

Links trusted devices to areas.

**Fields:**
- `device` (OneToOneField → TrustedDevice): The device being assigned
- `area` (ForeignKey → DeviceArea): The area the device is assigned to
- `assigned_by` (ForeignKey → User): User who made the assignment
- `assigned_at` (DateTimeField): When the assignment was made
- `updated_at` (DateTimeField): When the assignment was last updated

**Features:**
- Each device can only be assigned to one area
- Tracks who made the assignment and when

## API Endpoints

### Device Areas

#### List Areas
```
GET /api/device-areas/areas/
```
Returns all device areas with device counts.

#### Create Area
```
POST /api/device-areas/areas/
{
  "name": "Living Room",
  "description": "Main living area",
  "is_default": false
}
```

#### Sync Unassigned Devices
```
POST /api/device-areas/areas/sync_unassigned/
```
Automatically assigns all devices without an area to the default area. Creates a default area if one doesn't exist.

**Response:**
```json
{
  "message": "Synced 3 devices to Default Area",
  "default_area_id": 1,
  "default_area_name": "Default Area",
  "devices_synced": 3,
  "default_area_created": true
}
```

#### Assign Devices to Area
```
POST /api/device-areas/areas/{area_id}/assign_devices/
{
  "device_ids": [1, 2, 3],
  "area_id": 1
}
```
Bulk assign multiple devices to a specific area.

**Response:**
```json
{
  "message": "Assigned 3 devices to Living Room",
  "area_id": 1,
  "area_name": "Living Room",
  "assignments_created": 2,
  "assignments_updated": 1
}
```

### Device Area Assignments

#### List Assignments
```
GET /api/device-areas/assignments/
```
Returns all device area assignments. Regular users only see their own devices.

#### Create Assignment
```
POST /api/device-areas/assignments/
{
  "device": 1,
  "area": 2
}
```

#### List Unassigned Devices
```
GET /api/device-areas/assignments/unassigned/
```
Returns all trusted devices that don't have an area assignment.

**Response:**
```json
{
  "count": 2,
  "devices": [
    {
      "id": 5,
      "device_id": "abc-123",
      "device_name": "My Phone",
      "user_email": "user@example.com",
      "last_used_at": "2026-02-10T02:00:00Z",
      "created_at": "2026-02-01T10:00:00Z"
    }
  ]
}
```

## Usage Examples

### Organizing New Devices

When a user logs in from a new device and it becomes a trusted device:

1. The device is created but has no area assignment
2. An admin or automated process can call the sync endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/device-areas/areas/sync_unassigned/ \
     -H "Authorization: Bearer <token>"
   ```
3. The device is automatically assigned to the default area

### Bulk Organization

To organize multiple devices at once:

1. Get list of unassigned devices:
   ```bash
   curl http://localhost:8000/api/device-areas/assignments/unassigned/ \
     -H "Authorization: Bearer <token>"
   ```

2. Create or select an area for them:
   ```bash
   curl -X POST http://localhost:8000/api/device-areas/areas/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "Home Office", "description": "Work devices"}'
   ```

3. Assign devices to the area:
   ```bash
   curl -X POST http://localhost:8000/api/device-areas/areas/1/assign_devices/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"device_ids": [1, 2, 3], "area_id": 1}'
   ```

## Admin Interface

The feature includes Django admin interfaces for:

- Managing device areas
- Viewing and editing device area assignments
- Seeing device counts per area

Access at: `http://localhost:8000/admin/device_areas/`

## Permissions

- **Authenticated users**: Can view and manage their own device assignments
- **Staff users**: Can view and manage all device assignments and areas
- **Area creation**: Available to all authenticated users
- **Sync operation**: Available to all authenticated users

## Testing

Run tests with:
```bash
# All device_areas tests
python manage.py test mysite.device_areas --settings=mysite.test_settings

# Specific test files
python manage.py test mysite.device_areas.tests.test_models --settings=mysite.test_settings
python manage.py test mysite.device_areas.tests.test_api --settings=mysite.test_settings

# Or with pytest
pytest mysite/device_areas/tests/
```

## Integration with Home Assistant

This feature is designed to integrate with Home Assistant's area concept:

1. **Device Registration**: When a device is trusted in the system, it can be synced to Home Assistant
2. **Area Mapping**: Areas created here can map to Home Assistant areas/zones
3. **Automation**: Use the sync endpoint in automated scripts or webhooks
4. **Device Organization**: Keep device organization consistent between this system and Home Assistant

## Future Enhancements

Potential future improvements:

- [ ] Automatic area detection based on IP address or location
- [ ] Integration with Home Assistant API for two-way sync
- [ ] Area templates and presets
- [ ] Device movement history tracking
- [ ] Area-based device analytics
- [ ] Geofencing support for automatic area assignment
