# -*- coding: utf-8 -*-
"""
User groups repository for managing roles and permissions.
"""

import logging
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class UserGroupsRepository(BaseRepository):
    """Repository for user_groups table operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection, 'user_groups')
        logger.debug("UserGroupsRepository initialized")
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get group by name."""
        query = "SELECT * FROM user_groups WHERE name = %s"
        try:
            results = self.db.execute_query(query, (name,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting group by name: {e}")
            raise
    
    def get_with_permissions(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get group with all its permissions."""
        # Get group
        group = self.get_by_id(group_id)
        if not group:
            return None
        
        # Get permissions
        query = """
            SELECT p.*
            FROM permissions p
            JOIN group_permissions gp ON p.id = gp.permission_id
            WHERE gp.group_id = %s
            ORDER BY p.category, p.code
        """
        try:
            permissions = self.db.execute_query(query, (group_id,))
            group['permissions'] = permissions
            return group
        except Exception as e:
            logger.error(f"Error getting group permissions: {e}")
            raise
    
    def list_groups(self, include_permissions: bool = False) -> List[Dict[str, Any]]:
        """List all groups, optionally with permissions."""
        query = "SELECT * FROM user_groups ORDER BY id"
        try:
            groups = self.db.execute_query(query)
            
            if include_permissions:
                for group in groups:
                    perm_query = """
                        SELECT p.*
                        FROM permissions p
                        JOIN group_permissions gp ON p.id = gp.permission_id
                        WHERE gp.group_id = %s
                        ORDER BY p.category, p.code
                    """
                    group['permissions'] = self.db.execute_query(perm_query, (group['id'],))
            
            return groups
        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            raise
    
    def get_users_count(self, group_id: int) -> int:
        """Get count of users in a group."""
        query = "SELECT COUNT(*) as count FROM users WHERE group_id = %s"
        try:
            results = self.db.execute_query(query, (group_id,))
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"Error counting group users: {e}")
            return 0
    
    def create_group(self, name: str, description: str = '') -> int:
        """Create a new group."""
        query = "INSERT INTO user_groups (name, description) VALUES (%s, %s)"
        try:
            group_id = self.db.execute_update(query, (name, description))
            self.db.commit()
            logger.info(f"Created group: {name}")
            return group_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating group: {e}")
            raise
    
    def update_group(self, group_id: int, name: str = None, description: str = None) -> bool:
        """Update group details."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if not updates:
            return False
        
        params.append(group_id)
        query = f"UPDATE user_groups SET {', '.join(updates)} WHERE id = %s AND is_system = 0"
        
        try:
            rows = self.db.execute_update(query, tuple(params))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating group: {e}")
            raise
    
    def delete_group(self, group_id: int) -> bool:
        """Delete a group (only non-system groups with no users)."""
        # Check if group has users
        if self.get_users_count(group_id) > 0:
            raise ValueError("Cannot delete group with active users")
        
        query = "DELETE FROM user_groups WHERE id = %s AND is_system = 0"
        try:
            rows = self.db.execute_update(query, (group_id,))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting group: {e}")
            raise
    
    def set_permissions(self, group_id: int, permission_ids: List[int]) -> bool:
        """Set group permissions (replaces existing)."""
        try:
            # Remove existing permissions
            self.db.execute_update(
                "DELETE FROM group_permissions WHERE group_id = %s",
                (group_id,)
            )
            
            # Add new permissions
            if permission_ids:
                for perm_id in permission_ids:
                    self.db.execute_update(
                        "INSERT INTO group_permissions (group_id, permission_id) VALUES (%s, %s)",
                        (group_id, perm_id)
                    )
            
            self.db.commit()
            logger.info(f"Updated permissions for group {group_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting group permissions: {e}")
            raise
    
    def add_permission(self, group_id: int, permission_id: int) -> bool:
        """Add a single permission to a group."""
        query = "INSERT IGNORE INTO group_permissions (group_id, permission_id) VALUES (%s, %s)"
        try:
            self.db.execute_update(query, (group_id, permission_id))
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding permission: {e}")
            raise
    
    def remove_permission(self, group_id: int, permission_id: int) -> bool:
        """Remove a permission from a group."""
        query = "DELETE FROM group_permissions WHERE group_id = %s AND permission_id = %s"
        try:
            rows = self.db.execute_update(query, (group_id, permission_id))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing permission: {e}")
            raise


class PermissionsRepository(BaseRepository):
    """Repository for permissions table operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection, 'permissions')
        logger.debug("PermissionsRepository initialized")
    
    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get permission by code."""
        query = "SELECT * FROM permissions WHERE code = %s"
        try:
            results = self.db.execute_query(query, (code,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting permission by code: {e}")
            raise
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all permissions ordered by category."""
        query = "SELECT * FROM permissions ORDER BY category, code"
        try:
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error listing permissions: {e}")
            raise
    
    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        """List permissions for a specific category."""
        query = "SELECT * FROM permissions WHERE category = %s ORDER BY code"
        try:
            return self.db.execute_query(query, (category,))
        except Exception as e:
            logger.error(f"Error listing permissions by category: {e}")
            raise
    
    def get_categories(self) -> List[str]:
        """Get list of unique permission categories."""
        query = "SELECT DISTINCT category FROM permissions ORDER BY category"
        try:
            results = self.db.execute_query(query)
            return [r['category'] for r in results]
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise
    
    def get_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all permissions for a user through their group."""
        query = """
            SELECT DISTINCT p.*
            FROM permissions p
            JOIN group_permissions gp ON p.id = gp.permission_id
            JOIN users u ON u.group_id = gp.group_id
            WHERE u.id = %s
            ORDER BY p.category, p.code
        """
        try:
            return self.db.execute_query(query, (user_id,))
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            raise
    
    def user_has_permission(self, user_id: int, permission_code: str) -> bool:
        """Check if user has a specific permission."""
        query = """
            SELECT COUNT(*) as count
            FROM permissions p
            JOIN group_permissions gp ON p.id = gp.permission_id
            JOIN users u ON u.group_id = gp.group_id
            WHERE u.id = %s AND p.code = %s
        """
        try:
            results = self.db.execute_query(query, (user_id, permission_code))
            return results[0]['count'] > 0 if results else False
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False
