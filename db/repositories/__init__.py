"""
Repository layer for database operations.
Implements the Repository pattern for clean separation of data access logic.
"""

# Import BaseRepository from separate module to avoid circular imports
from db.repositories.base_repository import BaseRepository

# Import all repositories for easy access
from db.repositories.clients_repo import ClientsRepository
from db.repositories.sessions_repo import SessionsRepository
from db.repositories.families_repo import FamiliesRepository  # Keep for backward compatibility during migration
from db.repositories.members_repo import MembersRepository
from db.repositories.payments_repo import PaymentsRepository
from db.repositories.subscriptions_repo import SubscriptionsRepository
from db.repositories.imports_repo import ImportsRepository
from db.repositories.audit_log_repo import AuditLogRepository
from db.repositories.pdf_templates_repo import PDFTemplatesRepository
from db.repositories.users_repo import UsersRepository
from db.repositories.security_repo import SecuritySettingsRepository

__all__ = [
    'BaseRepository',
    'ClientsRepository',
    'SessionsRepository',
    'FamiliesRepository',
    'MembersRepository',
    'PaymentsRepository',
    'SubscriptionsRepository',
    'ImportsRepository',
    'AuditLogRepository',
    'PDFTemplatesRepository',
    'UsersRepository',
    'SecuritySettingsRepository',
]
