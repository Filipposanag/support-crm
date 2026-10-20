# -*- coding: utf-8 -*-
"""
Authentication and Authorization Service for Support CRM.
Handles user login, password management, and permission checking.
"""

import logging
from services.audit_context import set_current_user
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import bcrypt

from models.user import User, UserGroup, Permission, UserSession
from db.repositories.users_repo import UsersRepository
from db.repositories.groups_repo import UserGroupsRepository, PermissionsRepository
from db.repositories.security_repo import SecuritySettingsRepository

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for authentication and authorization operations.
    Manages user login, sessions, and permission checking.
    """
    
    # Default configuration (overridden by database settings)
    SESSION_DURATION_HOURS = 8
    MAX_FAILED_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 15
    BCRYPT_ROUNDS = 12
    BRUTE_FORCE_ENABLED = True
    
    def __init__(self, db_connection):
        """
        Initialize AuthService.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
        self.users_repo = UsersRepository(db_connection)
        self.groups_repo = UserGroupsRepository(db_connection)
        self.permissions_repo = PermissionsRepository(db_connection)
        self.security_repo = SecuritySettingsRepository(db_connection)
        
        # Current logged-in user (singleton pattern for desktop app)
        self._current_user: Optional[User] = None
        self._current_session: Optional[UserSession] = None
        
        # Load security settings from database
        self._load_security_settings()
        
        logger.info("AuthService initialized")
    
    def _load_security_settings(self):
        """Load security settings from database."""
        try:
            settings = self.security_repo.get_settings()
            self.SESSION_DURATION_HOURS = settings.get('session_duration_hours', 8)
            self.MAX_FAILED_ATTEMPTS = settings.get('max_failed_attempts', 5)
            self.LOCK_DURATION_MINUTES = settings.get('lockout_duration_minutes', 15)
            self.BCRYPT_ROUNDS = settings.get('bcrypt_rounds', 12)
            self.BRUTE_FORCE_ENABLED = settings.get('brute_force_enabled', True)
            self._password_policy = {
                'min_length': settings.get('password_min_length', 6),
                'require_uppercase': settings.get('password_require_uppercase', False),
                'require_lowercase': settings.get('password_require_lowercase', False),
                'require_number': settings.get('password_require_number', False),
                'require_special': settings.get('password_require_special', False)
            }
            logger.debug(f"Security settings loaded: brute_force={self.BRUTE_FORCE_ENABLED}, max_attempts={self.MAX_FAILED_ATTEMPTS}")
        except Exception as e:
            logger.warning(f"Could not load security settings, using defaults: {e}")
            self._password_policy = {
                'min_length': 6,
                'require_uppercase': False,
                'require_lowercase': False,
                'require_number': False,
                'require_special': False
            }
    
    def reload_security_settings(self):
        """Reload security settings from database."""
        self._load_security_settings()
        logger.info("Security settings reloaded")
    
    # =========================================================================
    # Password Management
    # =========================================================================
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hash string
        """
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        Validate password against policy.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        policy = self._password_policy
        
        if len(password) < policy['min_length']:
            return False, f"Ο κωδικός πρέπει να έχει τουλάχιστον {policy['min_length']} χαρακτήρες"
        
        if policy['require_uppercase'] and not any(c.isupper() for c in password):
            return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον ένα κεφαλαίο γράμμα"
        
        if policy['require_lowercase'] and not any(c.islower() for c in password):
            return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον ένα πεζό γράμμα"
        
        if policy['require_number'] and not any(c.isdigit() for c in password):
            return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον έναν αριθμό"
        
        if policy['require_special']:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον έναν ειδικό χαρακτήρα"
        
        return True, ""
    
    def get_password_policy(self) -> Dict[str, Any]:
        """Get current password policy settings."""
        return self._password_policy.copy()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored bcrypt hash
            
        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (success, message, user)
        """
        try:
            # Get user by username
            user_data = self.users_repo.get_by_username(username)
            
            if not user_data:
                logger.warning(f"Login failed: user '{username}' not found")
                return False, "Λάθος όνομα χρήστη ή κωδικός", None
            
            # Check if account is active
            if not user_data.get('is_active', False):
                logger.warning(f"Login failed: user '{username}' is inactive")
                return False, "Ο λογαριασμός είναι απενεργοποιημένος", None
            
            # Check if account is locked
            locked_until = user_data.get('locked_until')
            if locked_until and datetime.now() < locked_until:
                remaining = (locked_until - datetime.now()).seconds // 60
                logger.warning(f"Login failed: user '{username}' is locked")
                return False, f"Ο λογαριασμός είναι κλειδωμένος. Δοκιμάστε σε {remaining} λεπτά.", None
            
            # Verify password
            if not self.verify_password(password, user_data['password_hash']):
                # Brute-force protection (if enabled)
                if self.BRUTE_FORCE_ENABLED:
                    result = self.users_repo.increment_failed_attempts(
                        user_data['id'],
                        self.MAX_FAILED_ATTEMPTS,
                        self.LOCK_DURATION_MINUTES
                    )
                    
                    if result.get('locked'):
                        logger.warning(f"User '{username}' locked after {result['attempts']} failed attempts")
                        return False, f"Πολλές αποτυχημένες προσπάθειες. Ο λογαριασμός κλειδώθηκε για {result['lock_minutes']} λεπτά.", None
                    
                    remaining = self.MAX_FAILED_ATTEMPTS - result['attempts']
                    logger.warning(f"Login failed for '{username}': wrong password ({remaining} attempts remaining)")
                    return False, f"Λάθος κωδικός. Απομένουν {remaining} προσπάθειες.", None
                else:
                    logger.warning(f"Login failed for '{username}': wrong password (brute-force protection disabled)")
                    return False, "Λάθος κωδικός", None
            
            # Successful login - build user object
            user = self._build_user_from_data(user_data)
            
            # Update last login
            self.users_repo.update_last_login(user.id)
            
            # Create session
            self._current_user = user
            set_current_user(getattr(user, 'username', None))
            self._create_session(user)
            
            logger.info(f"User '{username}' logged in successfully")
            return True, "Επιτυχής σύνδεση", user
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"Σφάλμα σύνδεσης: {str(e)}", None
    
    def logout(self) -> bool:
        """
        Logout current user.
        
        Returns:
            True if logout successful
        """
        if self._current_user:
            logger.info(f"User '{self._current_user.username}' logged out")
            self._end_session()
            self._current_user = None
            set_current_user('system')
            self._current_session = None
            return True
        return False
    
    def _build_user_from_data(self, user_data: Dict[str, Any]) -> User:
        """Build User object from database data."""
        # Get group with permissions
        group_data = self.groups_repo.get_with_permissions(user_data['group_id'])
        
        # Build permissions list
        permissions = []
        if group_data and 'permissions' in group_data:
            for p in group_data['permissions']:
                permissions.append(Permission(
                    id=p['id'],
                    code=p['code'],
                    name=p['name'],
                    category=p['category'],
                    description=p.get('description', '')
                ))
        
        # Build group
        group = UserGroup(
            id=group_data['id'] if group_data else user_data['group_id'],
            name=group_data['name'] if group_data else user_data.get('group_name', ''),
            description=group_data.get('description', '') if group_data else '',
            is_system=group_data.get('is_system', False) if group_data else False,
            permissions=permissions
        )
        
        # Build user
        user = User(
            id=user_data['id'],
            username=user_data['username'],
            password_hash=user_data['password_hash'],
            email=user_data.get('email', ''),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            group_id=user_data['group_id'],
            group=group,
            is_active=user_data.get('is_active', True),
            is_system=user_data.get('is_system', False),
            last_login=user_data.get('last_login'),
            failed_attempts=user_data.get('failed_attempts', 0),
            locked_until=user_data.get('locked_until'),
            created_at=user_data.get('created_at'),
            updated_at=user_data.get('updated_at')
        )

        # Attach per-user permission overrides (grants/denials) on top of role
        try:
            overrides = self.users_repo.get_permission_overrides(user.id)
            user.extra_permission_codes = {
                o['code'] for o in overrides if o['effect'] == 'grant'
            }
            user.denied_permission_codes = {
                o['code'] for o in overrides if o['effect'] == 'deny'
            }
        except Exception as e:
            logger.warning(f"Could not load permission overrides for user {user.id}: {e}")

        return user
    
    def _create_session(self, user: User):
        """Create a new session for the user."""
        try:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=self.SESSION_DURATION_HOURS)
            
            query = """
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (%s, %s, %s)
            """
            self.db.execute_update(query, (user.id, token, expires_at))
            self.db.commit()
            
            self._current_session = UserSession(
                user_id=user.id,
                session_token=token,
                expires_at=expires_at,
                created_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error creating session: {e}")
    
    def _end_session(self):
        """End the current session."""
        if self._current_session:
            try:
                query = "UPDATE user_sessions SET ended_at = NOW() WHERE session_token = %s"
                self.db.execute_update(query, (self._current_session.session_token,))
                self.db.commit()
            except Exception as e:
                logger.error(f"Error ending session: {e}")
    
    # =========================================================================
    # Current User & Authorization
    # =========================================================================
    
    @property
    def current_user(self) -> Optional[User]:
        """Get the currently logged-in user."""
        return self._current_user
    
    @property
    def is_authenticated(self) -> bool:
        """Check if a user is currently logged in."""
        return self._current_user is not None
    
    def has_permission(self, permission_code: str) -> bool:
        """
        Check if current user has a specific permission.
        
        Args:
            permission_code: Permission code (e.g., 'families.create')
            
        Returns:
            True if user has permission
        """
        if not self._current_user:
            return False
        return self._current_user.has_permission(permission_code)
    
    def can(self, action: str, resource: str) -> bool:
        """
        Check if current user can perform an action on a resource.
        
        Args:
            action: Action name (view, create, edit, delete, export)
            resource: Resource name (families, payments, etc.)
            
        Returns:
            True if user has permission
        """
        if not self._current_user:
            return False
        return self._current_user.can(action, resource)
    
    def require_permission(self, permission_code: str) -> bool:
        """
        Check permission and raise exception if not authorized.
        
        Args:
            permission_code: Permission code to check
            
        Returns:
            True if authorized
            
        Raises:
            PermissionError: If not authorized
        """
        if not self.has_permission(permission_code):
            raise PermissionError(f"Δεν έχετε δικαίωμα: {permission_code}")
        return True
    
    def is_admin(self) -> bool:
        """Check if current user is an administrator."""
        if not self._current_user:
            return False
        return self._current_user.is_admin()
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    def create_user(self, username: str, password: str, email: str = '',
                    first_name: str = '', last_name: str = '',
                    group_id: int = 2) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new user.
        
        Args:
            username: Username (must be unique)
            password: Plain text password
            email: Email address
            first_name: First name
            last_name: Last name
            group_id: Group ID (default: 2 = Χρήστες)
            
        Returns:
            Tuple of (success, message, user_id)
        """
        try:
            # Check if username exists
            if self.users_repo.get_by_username(username):
                return False, "Το όνομα χρήστη υπάρχει ήδη", None
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            user_id = self.users_repo.create_user({
                'username': username,
                'password_hash': password_hash,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'group_id': group_id,
                'is_active': True
            })
            
            logger.info(f"Created user: {username}")
            return True, "Ο χρήστης δημιουργήθηκε επιτυχώς", user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Σφάλμα δημιουργίας χρήστη: {str(e)}", None
    
    def change_password(self, user_id: int, old_password: str, 
                        new_password: str) -> Tuple[bool, str]:
        """
        Change a user's password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        try:
            user_data = self.users_repo.get_by_id(user_id)
            if not user_data:
                return False, "Ο χρήστης δεν βρέθηκε"
            
            # Verify old password
            if not self.verify_password(old_password, user_data['password_hash']):
                return False, "Λάθος τρέχων κωδικός"
            
            # Hash and update new password
            new_hash = self.hash_password(new_password)
            self.users_repo.update_user(user_id, {'password_hash': new_hash})
            
            logger.info(f"Password changed for user ID: {user_id}")
            return True, "Ο κωδικός άλλαξε επιτυχώς"
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, f"Σφάλμα αλλαγής κωδικού: {str(e)}"
    
    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset a user's password (admin function).
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        try:
            new_hash = self.hash_password(new_password)
            success = self.users_repo.update_user(user_id, {
                'password_hash': new_hash,
                'failed_attempts': 0,
                'locked_until': None
            })
            
            if success:
                logger.info(f"Password reset for user ID: {user_id}")
                return True, "Ο κωδικός επαναφέρθηκε επιτυχώς"
            return False, "Ο χρήστης δεν βρέθηκε"
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, f"Σφάλμα επαναφοράς κωδικού: {str(e)}"
    
    # =========================================================================
    # Group & Permission Queries
    # =========================================================================
    
    def get_all_groups(self, include_permissions: bool = False) -> List[Dict[str, Any]]:
        """Get all user groups."""
        return self.groups_repo.list_groups(include_permissions)
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Get all available permissions."""
        return self.permissions_repo.list_all()
    
    def get_permissions_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get permissions grouped by category."""
        permissions = self.permissions_repo.list_all()
        result = {}
        for p in permissions:
            category = p['category']
            if category not in result:
                result[category] = []
            result[category].append(p)
        return result

    # =========================================================================
    # Per-User Permission Overrides
    # =========================================================================

    def get_user_permission_overrides(self, user_id: int) -> List[Dict[str, Any]]:
        """Get a user's per-user permission overrides (grant/deny)."""
        return self.users_repo.get_permission_overrides(user_id)

    def set_user_permissions(self, user_id: int, grant_ids: List[int],
                             deny_ids: List[int]) -> bool:
        """Set a user's per-user permission overrides (replaces existing).

        If the user currently being edited is the logged-in user, refresh
        the cached permission set so the UI reflects changes immediately.
        """
        ok = self.users_repo.set_permission_overrides(user_id, grant_ids, deny_ids)
        if ok and self._current_user and self._current_user.id == user_id:
            refreshed = self.users_repo.get_with_group(user_id)
            if refreshed:
                self._current_user = self._build_user_from_data(refreshed)
        return ok

    def count_active_admins(self) -> int:
        """Number of active administrators (group Διαχειριστές = id 1)."""
        return self.users_repo.count_active_admins(1)
