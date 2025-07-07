# Knowledge Base Permissions System - Implementation Documentation

## Overview

This document describes the comprehensive knowledge base permissions system that has been implemented in GiSaWeb. The system allows administrators to control which users and groups can access specific knowledge bases, replacing the previous system where all knowledge bases were accessible to all users.

## Features Implemented

### 1. Backend API Endpoints
- **GET** `/api/v1/knowledge/admin/permissions` - Get all knowledge base permissions (admin only)
- **GET** `/api/v1/knowledge/{id}/permissions` - Get permissions for a specific knowledge base (admin only)
- **POST** `/api/v1/knowledge/{id}/permissions` - Update permissions for a specific knowledge base (admin only)
- **POST** `/api/v1/knowledge/admin/permissions/bulk` - Bulk update permissions for multiple knowledge bases (admin only)

### 2. Admin Interface Components
- **Knowledge Management Page** - `/admin/knowledge` with comprehensive permissions management
- **Bulk Actions** - Select multiple knowledge bases and apply permissions in bulk
- **Individual Editing** - Modal interface for detailed permission configuration per knowledge base
- **Visual Access Indicators** - Clear display of read/write access for users and groups

### 3. Permission Model
The system uses the existing access control framework with:
- **Read Access**: Who can view and use the knowledge base
- **Write Access**: Who can modify the knowledge base content
- **Public vs Private**: Toggle between public access (all users) and restricted access
- **User-based Permissions**: Direct assignment to specific users
- **Group-based Permissions**: Assignment via user groups

## API Documentation

### Get All Knowledge Permissions
```http
GET /api/v1/knowledge/admin/permissions
Authorization: Bearer <admin_token>
```

**Response:**
```json
[
  {
    "id": "kb-id-123",
    "name": "Knowledge Base Name",
    "description": "Knowledge base description",
    "user_id": "owner-user-id",
    "access_control": {
      "read": {
        "user_ids": ["user1", "user2"],
        "group_ids": ["group1"]
      },
      "write": {
        "user_ids": ["user1"],
        "group_ids": ["admin-group"]
      }
    },
    "users_with_read_access": [
      {"id": "user1", "name": "John Doe", "email": "john@example.com"}
    ],
    "users_with_write_access": [
      {"id": "user1", "name": "John Doe", "email": "john@example.com"}
    ],
    "groups_with_read_access": [
      {"id": "group1", "name": "Viewers"}
    ],
    "groups_with_write_access": [
      {"id": "admin-group", "name": "Administrators"}
    ]
  }
]
```

### Update Knowledge Base Permissions
```http
POST /api/v1/knowledge/{id}/permissions
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "read": {
    "user_ids": ["user1", "user2"],
    "group_ids": ["group1"]
  },
  "write": {
    "user_ids": ["user1"],
    "group_ids": ["admin-group"]
  }
}
```

### Bulk Update Permissions
```http
POST /api/v1/knowledge/admin/permissions/bulk
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "knowledge_base_ids": ["kb1", "kb2", "kb3"],
  "access_control": {
    "read": {
      "user_ids": ["user1"],
      "group_ids": ["viewers"]
    },
    "write": {
      "user_ids": ["user1"],
      "group_ids": ["editors"]
    }
  }
}
```

**Response:**
```json
{
  "success_count": 2,
  "total_requested": 3,
  "failed_updates": [
    {
      "knowledge_base_id": "kb3",
      "error": "Knowledge base not found"
    }
  ]
}
```

## Frontend API Integration

### TypeScript Interfaces
```typescript
export interface KnowledgePermission {
  group_ids?: string[];
  user_ids?: string[];
}

export interface KnowledgePermissionsForm {
  read?: KnowledgePermission;
  write?: KnowledgePermission;
}

export interface KnowledgePermissionsResponse {
  id: string;
  name: string;
  description: string;
  user_id: string;
  access_control?: {
    read?: KnowledgePermission;
    write?: KnowledgePermission;
  };
  users_with_read_access: Array<{ id: string; name: string; email: string }>;
  users_with_write_access: Array<{ id: string; name: string; email: string }>;
  groups_with_read_access: Array<{ id: string; name: string }>;
  groups_with_write_access: Array<{ id: string; name: string }>;
}
```

### API Functions
```typescript
// Get all knowledge base permissions
const permissions = await getAllKnowledgePermissions(token);

// Get permissions for a specific knowledge base
const kbPermissions = await getKnowledgePermissions(token, knowledgeBaseId);

// Update permissions for a knowledge base
await updateKnowledgePermissions(token, knowledgeBaseId, {
  read: { user_ids: ['user1'], group_ids: ['group1'] },
  write: { user_ids: ['user1'], group_ids: ['admin'] }
});

// Bulk update permissions
await bulkUpdateKnowledgePermissions(token, {
  knowledge_base_ids: ['kb1', 'kb2'],
  access_control: {
    read: { user_ids: ['user1'] },
    write: { user_ids: ['admin1'] }
  }
});
```

## Administrator Guide

### Accessing Knowledge Permissions Management

1. **Navigate to Admin Panel**: Go to `/admin` (admin users only)
2. **Select Knowledge Tab**: Click on the "Knowledge" tab in the admin navigation
3. **View Permissions**: See all knowledge bases with their current access settings

### Managing Individual Knowledge Base Permissions

1. **Edit Button**: Click the edit (pencil) icon next to any knowledge base
2. **Public vs Private**: 
   - Check "Public Access" to make the knowledge base available to all users
   - Uncheck to set up restricted access with specific users/groups
3. **Read Access**: 
   - Add users who can view and search the knowledge base
   - Add groups whose members can view and search the knowledge base
4. **Write Access**:
   - Add users who can modify the knowledge base content
   - Add groups whose members can modify the knowledge base content
5. **Save Changes**: Click "Save Changes" to apply the new permissions

### Bulk Permission Management

1. **Select Knowledge Bases**: Use checkboxes to select multiple knowledge bases
2. **Bulk Actions Panel**: The bulk actions panel appears when items are selected
3. **Set Permissions**: Configure read and write access for users and groups
4. **Apply**: Click "Apply to Selected" to update all selected knowledge bases

### Permission Inheritance Rules

- **Owner Access**: Knowledge base owners always have full read and write access
- **Write Includes Read**: Users with write access automatically have read access
- **Group Membership**: Users inherit permissions from all groups they belong to
- **Most Permissive**: If a user has access through multiple paths, the most permissive access is applied

## Security Considerations

### Authentication & Authorization
- All permission management endpoints require admin authentication
- Individual knowledge base access is checked on every request
- Permissions are validated server-side using existing access control framework

### Data Protection
- Unauthorized users cannot see knowledge bases they don't have access to
- Search results are filtered based on user permissions
- API responses only include accessible knowledge bases

### Audit Trail
- Permission changes are logged through the existing audit system
- Failed permission checks are logged for security monitoring

## Migration & Backward Compatibility

### Existing Knowledge Bases
- Knowledge bases created before this implementation have no access control (public by default)
- Existing functionality continues to work without changes
- Gradual migration to permission-based access can be done through the admin interface

### API Compatibility
- Existing knowledge base endpoints continue to work
- New permission fields are optional in API responses
- Client applications need updates only to use new permission features

## Troubleshooting

### Common Issues

**Users can't see knowledge bases they should have access to:**
- Check if the user is in the correct groups
- Verify group permissions are properly set
- Ensure the knowledge base isn't set to owner-only access

**Bulk updates partially failing:**
- Check the API response for specific error details
- Verify all selected knowledge bases exist
- Ensure proper admin permissions

**Permission changes not taking effect:**
- Refresh the page to reload current permissions
- Check if there are conflicting permission settings
- Verify the user's group memberships

### API Error Codes
- `401 Unauthorized`: Invalid or missing admin token
- `403 Forbidden`: User doesn't have admin permissions
- `404 Not Found`: Knowledge base doesn't exist
- `400 Bad Request`: Invalid permission format

## Implementation Files

### Backend Files
- `backend/open_webui/routers/knowledge.py` - API endpoints
- `backend/open_webui/utils/access_control.py` - Permission utilities
- `backend/open_webui/utils/auth.py` - Authentication functions

### Frontend Files
- `src/lib/apis/knowledge/index.ts` - API client functions
- `src/lib/components/admin/Knowledge.svelte` - Main admin component
- `src/lib/components/admin/Knowledge/KnowledgePermissions.svelte` - Permissions table
- `src/lib/components/admin/Knowledge/EditPermissionsModal.svelte` - Edit modal
- `src/routes/(app)/admin/knowledge/+page.svelte` - Admin route

### Navigation Updates
- `src/routes/(app)/admin/+layout.svelte` - Added Knowledge tab to admin navigation

## Testing

### Manual Testing Checklist

**Admin Interface:**
- [ ] Can access `/admin/knowledge` as admin user
- [ ] Can view all knowledge bases with permission status
- [ ] Can edit individual knowledge base permissions
- [ ] Can toggle between public and private access
- [ ] Can add/remove users and groups for read access
- [ ] Can add/remove users and groups for write access
- [ ] Can select multiple knowledge bases for bulk operations
- [ ] Can apply bulk permission changes
- [ ] Search functionality works correctly

**API Endpoints:**
- [ ] GET `/api/v1/knowledge/admin/permissions` returns all knowledge bases
- [ ] GET `/api/v1/knowledge/{id}/permissions` returns specific knowledge base permissions
- [ ] POST `/api/v1/knowledge/{id}/permissions` updates permissions correctly
- [ ] POST `/api/v1/knowledge/admin/permissions/bulk` bulk updates work
- [ ] Non-admin users cannot access admin endpoints
- [ ] Regular users only see knowledge bases they have access to

**Permission Enforcement:**
- [ ] Users can only see knowledge bases they have read access to
- [ ] Users can only modify knowledge bases they have write access to
- [ ] Group permissions work correctly
- [ ] Owner always has full access
- [ ] Public knowledge bases are visible to all users

This comprehensive permissions system provides fine-grained control over knowledge base access while maintaining security and usability for administrators and end users. 