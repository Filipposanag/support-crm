# -*- coding: utf-8 -*-
"""
User and authentication models for Support CRM.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Permission:
    """Permission data model."""
    id: Optional[int] = None
    code: str = ''  # e.g., 'families.create'
    name: str = ''  # e.g., 'Δημιουργία Πελάτη'
    category: str = ''  # e.g., 'families'
    description: str = ''
    
    def __hash__(self):
        return hash(self.code)
    
    def __eq__(self, other):
        if isinstance(other, Permission):
            return self.code == other.code
        return False


@dataclass
class UserGroup:
    """User group/role data model."""
    id: Optional[int] = None
    name: str = ''
    description: str = ''
    is_system: bool = False
    permissions: List[Permission] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def has_permission(self, permission_code: str) -> bool:
        """Check if group has a specific permission."""
        return any(p.code == permission_code for p in self.permissions)
    
    def get_permissions_by_category(self, category: str) -> List[Permission]:
        """Get all permissions for a specific category."""
        return [p for p in self.permissions if p.category == category]


@dataclass
class User:
    """User account data model."""
    id: Optional[int] = None
    username: str = ''
    password_hash: str = ''
    email: str = ''
    first_name: str = ''
    last_name: str = ''
    group_id: int = 0
    group: Optional[UserGroup] = None
    is_active: bool = True
    is_system: bool = False
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Per-user overrides on top of the group (role) baseline
    extra_permission_codes: set = field(default_factory=set)   # explicit grants
    denied_permission_codes: set = field(default_factory=set)  # explicit denials
    
    def get_full_name(self) -> str:
        """Get user's full name."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username
    
    def get_display_name(self) -> str:
        """Get display name (full name or username)."""
        full_name = self.get_full_name()
        return full_name if full_name != self.username else self.username
    
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until
    
    def is_admin_group(self) -> bool:
        """True if the user's role is the Administrators group."""
        return self.group is not None and self.group.name == 'Διαχειριστές'

    def has_permission(self, permission_code: str) -> bool:
        """Check effective permission: role baseline +/- per-user overrides.

        Administrators always have full access. Otherwise:
        effective = (group permissions ∪ user grants) − user denials.
        """
        # Administrators bypass all checks (never lock the admin out).
        if self.is_admin_group():
            return True
        # Explicit per-user denial wins over the role baseline.
        if permission_code in self.denied_permission_codes:
            return False
        # Granted by the role baseline...
        if self.group is not None and self.group.has_permission(permission_code):
            return True
        # ...or by an explicit per-user grant.
        return permission_code in self.extra_permission_codes
    
    def can(self, action: str, resource: str) -> bool:
        """
        Check if user can perform an action on a resource.
        
        Args:
            action: Action name (view, create, edit, delete, export)
            resource: Resource name (families, payments, etc.)
            
        Returns:
            True if user has permission
        """
        permission_code = f"{resource}.{action}"
        return self.has_permission(permission_code)
    
    def is_admin(self) -> bool:
        """Check if user is an administrator."""
        if self.group is None:
            return False
        return self.group.name == 'Διαχειριστές' or self.has_permission('groups.manage')


@dataclass
class UserSession:
    """User session data model for tracking logins."""
    id: Optional[int] = None
    user_id: int = 0
    session_token: str = ''
    ip_address: str = ''
    user_agent: str = ''
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return True
        return datetime.now() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is still active."""
        return not self.is_expired() and self.ended_at is None
