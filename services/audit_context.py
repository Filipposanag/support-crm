# -*- coding: utf-8 -*-
"""
Audit context: tracks the currently logged-in user and provides a
best-effort helper to write audit_log entries from anywhere.
"""

import logging

logger = logging.getLogger(__name__)

_state = {"username": "system"}


def set_current_user(username):
    """Remember who is acting (called on login/logout)."""
    _state["username"] = username or "system"


def get_current_user():
    return _state.get("username") or "system"


def log_audit(db, table_name, record_id, operation, old=None, new=None):
    """Best-effort audit entry. Never raises (audit must not break real ops)."""
    try:
        from db.repositories.audit_log_repo import AuditLogRepository
        AuditLogRepository(db).log(table_name, record_id, operation,
                                   old_values=old, new_values=new,
                                   changed_by=get_current_user())
    except Exception as e:
        logger.debug(f"audit log skipped: {e}")
