# -*- coding: utf-8 -*-
"""
Permission helper utilities for UI components.
Provides decorators and helpers for permission-based UI control.
"""

import logging
from functools import wraps
from typing import Optional, Callable, List
from PySide6.QtWidgets import QWidget, QPushButton, QMessageBox
from PySide6.QtGui import QAction

logger = logging.getLogger(__name__)

# Global auth service reference (set during app initialization)
_auth_service = None


def set_auth_service(auth_service):
    """Set the global auth service reference."""
    global _auth_service
    _auth_service = auth_service


def get_auth_service():
    """Get the global auth service reference."""
    return _auth_service


def has_permission(permission_code: str) -> bool:
    """Check if current user has a permission."""
    if _auth_service is None:
        return True  # No auth = allow all (for backwards compatibility)
    return _auth_service.has_permission(permission_code)


def can(action: str, resource: str) -> bool:
    """Check if current user can perform action on resource."""
    if _auth_service is None:
        return True
    return _auth_service.can(action, resource)


def is_admin() -> bool:
    """Check if current user is admin."""
    if _auth_service is None:
        return True
    return _auth_service.is_admin()


def require_permission(permission_code: str):
    """
    Decorator to require a permission for a method.
    Shows error message if permission denied.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_permission(permission_code):
                QMessageBox.warning(
                    None, "Πρόσβαση Απορρίφθηκε",
                    f"Δεν έχετε δικαίωμα για αυτή την ενέργεια.\n"
                    f"Απαιτείται: {permission_code}"
                )
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


def setup_widget_permissions(widget: QWidget, permissions_map: dict):
    """
    Setup widget visibility/enabled state based on permissions.
    
    Args:
        widget: Parent widget containing child widgets
        permissions_map: Dict mapping widget names to permission codes
            Example: {'delete_btn': 'families.delete', 'settings_action': 'settings.view'}
    """
    for widget_name, permission_code in permissions_map.items():
        child = widget.findChild(QWidget, widget_name)
        if child:
            allowed = has_permission(permission_code)
            if isinstance(child, (QPushButton, QAction)):
                child.setEnabled(allowed)
            else:
                child.setVisible(allowed)


def filter_actions_by_permission(actions: List[QAction], permissions_map: dict):
    """
    Enable/disable actions based on permissions.
    
    Args:
        actions: List of QAction objects
        permissions_map: Dict mapping action object names to permission codes
    """
    for action in actions:
        if action.objectName() in permissions_map:
            permission_code = permissions_map[action.objectName()]
            action.setEnabled(has_permission(permission_code))
