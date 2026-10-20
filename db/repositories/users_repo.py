# -*- coding: utf-8 -*-
"""
Users repository for managing user accounts and authentication.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class UsersRepository(BaseRepository):
    """Repository for users table operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection, 'users')
        logger.debug("UsersRepository initialized")
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        query = """
            SELECT u.*, g.name as group_name, g.description as group_description
            FROM users u
            JOIN user_groups g ON u.group_id = g.id
            WHERE u.username = %s
        """
        try:
            results = self.db.execute_query(query, (username,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            raise
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = %s"
        try:
            results = self.db.execute_query(query, (email,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            raise
    
    def get_with_group(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with group information."""
        query = """
            SELECT u.*, g.name as group_name, g.description as group_description
            FROM users u
            JOIN user_groups g ON u.group_id = g.id
            WHERE u.id = %s
        """
        try:
            results = self.db.execute_query(query, (user_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting user with group: {e}")
            raise
    
    def list_users(self, search: str = None, only_active: bool = False,
                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List users with optional filters."""
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append(
                "(u.username LIKE %s OR u.email LIKE %s OR "
                "u.first_name LIKE %s OR u.last_name LIKE %s)"
            )
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern, pattern])
        
        if only_active:
            where_clauses.append("u.is_active = 1")
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
            SELECT u.*, g.name as group_name
            FROM users u
            JOIN user_groups g ON u.group_id = g.id
            {where_clause}
            ORDER BY u.username
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        try:
            return self.db.execute_query(query, tuple(params))
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise
    
    def count_users(self, search: str = None, only_active: bool = False) -> int:
        """Count users with optional filters."""
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append(
                "(username LIKE %s OR email LIKE %s OR "
                "first_name LIKE %s OR last_name LIKE %s)"
            )
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern, pattern])
        
        if only_active:
            where_clauses.append("is_active = 1")
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"SELECT COUNT(*) as count FROM users {where_clause}"
        
        try:
            results = self.db.execute_query(query, tuple(params) if params else None)
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            raise
    
    def create_user(self, user_data: Dict[str, Any]) -> int:
        """Create a new user."""
        fields = ['username', 'password_hash', 'email', 'first_name', 
                  'last_name', 'group_id', 'is_active']
        
        insert_fields = [f for f in fields if f in user_data]
        values = [user_data[f] for f in insert_fields]
        
        placeholders = ', '.join(['%s'] * len(insert_fields))
        fields_str = ', '.join(insert_fields)
        
        query = f"INSERT INTO users ({fields_str}) VALUES ({placeholders})"
        
        try:
            user_id = self.db.execute_update(query, tuple(values))
            self.db.commit()
            logger.info(f"Created user: {user_data.get('username')}")
            return user_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Update user data."""
        user_data = {k: v for k, v in user_data.items() if k != 'id'}
        
        if not user_data:
            return False
        
        set_clauses = [f"{field} = %s" for field in user_data.keys()]
        values = list(user_data.values())
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s"
        
        try:
            rows = self.db.execute_update(query, tuple(values))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user: {e}")
            raise
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        query = "UPDATE users SET last_login = NOW(), failed_attempts = 0 WHERE id = %s"
        try:
            self.db.execute_update(query, (user_id,))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def increment_failed_attempts(self, user_id: int, lock_after: int = 5,
                                   lock_minutes: int = 15) -> Dict[str, Any]:
        """Increment failed login attempts and lock if threshold reached."""
        # Get current attempts
        query = "SELECT failed_attempts FROM users WHERE id = %s"
        try:
            results = self.db.execute_query(query, (user_id,))
            if not results:
                return {'locked': False, 'attempts': 0}
            
            current_attempts = results[0]['failed_attempts'] + 1
            
            if current_attempts >= lock_after:
                # Lock account
                query = """
                    UPDATE users 
                    SET failed_attempts = %s, 
                        locked_until = DATE_ADD(NOW(), INTERVAL %s MINUTE)
                    WHERE id = %s
                """
                self.db.execute_update(query, (current_attempts, lock_minutes, user_id))
                self.db.commit()
                return {'locked': True, 'attempts': current_attempts, 'lock_minutes': lock_minutes}
            else:
                # Just increment
                query = "UPDATE users SET failed_attempts = %s WHERE id = %s"
                self.db.execute_update(query, (current_attempts, user_id))
                self.db.commit()
                return {'locked': False, 'attempts': current_attempts}
        except Exception as e:
            logger.error(f"Error incrementing failed attempts: {e}")
            return {'locked': False, 'attempts': 0}
    
    def unlock_user(self, user_id: int) -> bool:
        """Unlock a user account."""
        query = "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s"
        try:
            self.db.execute_update(query, (user_id,))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error unlocking user: {e}")
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        query = "UPDATE users SET is_active = 0 WHERE id = %s AND is_system = 0"
        try:
            rows = self.db.execute_update(query, (user_id,))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating user: {e}")
            raise
    
    def get_permission_overrides(self, user_id: int) -> List[Dict[str, Any]]:
        """Get per-user permission overrides (grants/denials) with codes."""
        query = """
            SELECT p.id AS permission_id, p.code, up.effect
            FROM user_permissions up
            JOIN permissions p ON p.id = up.permission_id
            WHERE up.user_id = %s
        """
        try:
            return self.db.execute_query(query, (user_id,))
        except Exception as e:
            logger.error(f"Error getting permission overrides: {e}")
            return []

    def set_permission_overrides(self, user_id: int, grant_ids: List[int],
                                 deny_ids: List[int]) -> bool:
        """Replace a user's permission overrides in one transaction."""
        try:
            self.db.execute_update(
                "DELETE FROM user_permissions WHERE user_id = %s", (user_id,)
            )
            for pid in grant_ids:
                self.db.execute_update(
                    "INSERT INTO user_permissions (user_id, permission_id, effect) "
                    "VALUES (%s, %s, 'grant')", (user_id, pid)
                )
            for pid in deny_ids:
                self.db.execute_update(
                    "INSERT INTO user_permissions (user_id, permission_id, effect) "
                    "VALUES (%s, %s, 'deny')", (user_id, pid)
                )
            self.db.commit()
            logger.info(f"Updated permission overrides for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting permission overrides: {e}")
            raise

    def count_active_admins(self, admin_group_id: int = 1) -> int:
        """Count active users in the administrators group."""
        query = ("SELECT COUNT(*) AS count FROM users "
                 "WHERE group_id = %s AND is_active = 1")
        try:
            results = self.db.execute_query(query, (admin_group_id,))
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"Error counting active admins: {e}")
            return 0

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (only non-system users)."""
        query = "DELETE FROM users WHERE id = %s AND is_system = 0"
        try:
            rows = self.db.execute_update(query, (user_id,))
            self.db.commit()
            return rows > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user: {e}")
            raise
