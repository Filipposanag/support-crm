# -*- coding: utf-8 -*-
"""
Clients repository for managing client records in Support CRM.
Provides specialized queries for client data access.
"""

import logging
from services.audit_context import log_audit
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ClientsRepository(BaseRepository):
    """
    Repository for clients table operations.
    Extends BaseRepository with client-specific queries.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize ClientsRepository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        super().__init__(db_connection, 'families')  # Table is named 'families' in database
        self.reporting_service = None  # Will be set by dependency injection
        logger.debug("ClientsRepository initialized")
    
    def get_by_legacy_code(self, legacy_code: int) -> Optional[Dict[str, Any]]:
        """
        Find a client by its legacy code.
        
        Args:
            legacy_code: The legacy CODE value
            
        Returns:
            Dictionary representing the client record, or None if not found
        """
        query = "SELECT * FROM families WHERE legacy_code = %s"
        
        try:
            results = self.db.execute_query(query, (legacy_code,))
            if results:
                logger.debug(f"Found client with legacy_code={legacy_code}")
                return results[0]
            else:
                logger.debug(f"No client found with legacy_code={legacy_code}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving client by legacy_code={legacy_code}: {e}")
            raise
    
    def get_by_rustdesk_id(self, rustdesk_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a client by RustDesk ID.
        
        Args:
            rustdesk_id: The RustDesk client ID
            
        Returns:
            Dictionary representing the client record, or None if not found
        """
        query = "SELECT * FROM families WHERE rustdesk_id = %s"
        
        try:
            results = self.db.execute_query(query, (rustdesk_id,))
            if results:
                logger.debug(f"Found client with rustdesk_id={rustdesk_id}")
                return results[0]
            else:
                logger.debug(f"No client found with rustdesk_id={rustdesk_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving client by rustdesk_id={rustdesk_id}: {e}")
            raise
    
    def get_next_code(self, settings_counter: int = None) -> int:
        """
        Get the next available code for a new client.
        Uses the family_counter from settings if provided, otherwise finds max + 1.
        
        Args:
            settings_counter: Optional counter value from app_settings
        
        Returns:
            Next available code number
        """
        query = """
            SELECT MAX(CAST(legacy_code AS UNSIGNED)) as max_code 
            FROM families 
            WHERE legacy_code REGEXP '^[0-9]+$'
        """
        
        try:
            results = self.db.execute_query(query)
            db_max_code = 0
            if results and results[0]['max_code'] is not None:
                db_max_code = int(results[0]['max_code'])
            
            # Use the higher of: settings_counter or db_max_code + 1
            if settings_counter is not None and settings_counter > 0:
                next_code = max(settings_counter, db_max_code + 1)
            else:
                next_code = db_max_code + 1
            
            # Ensure we don't return 0
            if next_code <= 0:
                next_code = 1
            
            logger.debug(f"Next available code: {next_code} (db_max={db_max_code}, settings={settings_counter})")
            return next_code
        except Exception as e:
            logger.error(f"Error getting next code: {e}")
            return 1
    
    def search_by_name(self, name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search clients by last name, first name, or company name (partial match).
        
        Args:
            name: Search term to match
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing matching clients
        """
        query = """
            SELECT * FROM families 
            WHERE last_name LIKE %s OR first_name LIKE %s OR company_name LIKE %s
               OR CONCAT(last_name, ' ', first_name) LIKE %s
               OR CONCAT(first_name, ' ', last_name) LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        
        search_pattern = f"%{name}%"
        
        try:
            results = self.db.execute_query(query, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, limit, offset))
            logger.debug(f"Name search for '{name}' returned {len(results)} clients")
            return results
        except Exception as e:
            logger.error(f"Error searching clients by name '{name}': {e}")
            raise
    
    def get_active_clients(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve only active clients (is_active = 1).
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing active clients
        """
        query = """
            SELECT * FROM families 
            WHERE is_active = 1 
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} active clients (limit={limit}, offset={offset})")
            return results
        except Exception as e:
            logger.error(f"Error retrieving active clients: {e}")
            raise
    
    def get_clients_with_rustdesk(self) -> List[Dict[str, Any]]:
        """
        Get all clients that have RustDesk configured.
        
        Returns:
            List of clients with RustDesk ID
        """
        query = """
            SELECT * FROM families 
            WHERE rustdesk_id IS NOT NULL AND rustdesk_id != ''
            ORDER BY last_name, first_name
        """
        
        try:
            results = self.db.execute_query(query)
            logger.debug(f"Retrieved {len(results)} clients with RustDesk")
            return results
        except Exception as e:
            logger.error(f"Error retrieving clients with RustDesk: {e}")
            raise
    
    def get_clients_by_support_plan(self, support_plan: str) -> List[Dict[str, Any]]:
        """
        Get clients by support plan type.
        
        Args:
            support_plan: Support plan type (hourly, monthly, yearly, custom)
            
        Returns:
            List of clients with specified support plan
        """
        query = """
            SELECT * FROM families 
            WHERE support_plan = %s AND is_active = 1
            ORDER BY last_name, first_name
        """
        
        try:
            results = self.db.execute_query(query, (support_plan,))
            logger.debug(f"Retrieved {len(results)} clients with {support_plan} plan")
            return results
        except Exception as e:
            logger.error(f"Error retrieving clients by support plan: {e}")
            raise
    
    def get_active_package_names(self) -> dict:
        """Map client_id -> active package name (μη ληγμένο, is_active, με υπόλοιπο ώρες).
        Χρησιμοποιείται ώστε η στήλη «Πλάνο Υποστήριξης» να δείχνει το πακέτο αντί για «Ωριαία».
        Ένας πελάτης χωρίς ενεργό πακέτο (ή με ληγμένο/εξαντλημένο) δεν μπαίνει στο map."""
        query = """
            SELECT cph.client_id AS cid, sp.name AS pname
            FROM client_package_hours cph
            JOIN support_packages sp ON sp.id = cph.package_id
            WHERE cph.is_active = 1
              AND (cph.expiry_date IS NULL OR cph.expiry_date >= CURDATE())
              AND (cph.total_hours - cph.used_hours) > 0.01
            ORDER BY (cph.expiry_date IS NULL) DESC, cph.expiry_date DESC
        """
        result = {}
        try:
            for r in (self.db.execute_query(query) or []):
                cid = r.get('cid')
                if cid is not None and cid not in result:
                    result[cid] = r.get('pname')
        except Exception:
            pass
        return result

    def list_clients(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        limit: int = 100,
        offset: int = 0,
        search_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List clients with optional filters.
        
        Args:
            search: Search term for client fields (partial match)
            only_active: If True, only return active clients
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination
            search_fields: List of field names to search in
            
        Returns:
            List of client records as dictionaries
        """
        where_clauses = []
        params = []
        
        if search:
            field_map = {
                "code": "CAST(legacy_code AS CHAR)",
                "last_name": "last_name",
                "first_name": "first_name",
                "company_name": "company_name",
                "rustdesk_id": "rustdesk_id",
                "phone": "phone",
                "mobile": "mobile",
                "city": "city",
                "email": "email",
                "national_id": "national_id"
            }
            
            if search_fields:
                search_conditions = []
                for field_key in search_fields:
                    db_column = field_map.get(field_key)
                    if db_column:
                        search_conditions.append(f"{db_column} LIKE %s")
                        params.append(f"%{search}%")
                
                # Also match the full name in both orders so "Επώνυμο Όνομα" works
                search_conditions.append("CONCAT(last_name, ' ', first_name) LIKE %s")
                params.append(f"%{search}%")
                search_conditions.append("CONCAT(first_name, ' ', last_name) LIKE %s")
                params.append(f"%{search}%")
                if search_conditions:
                    where_clauses.append(f"({' OR '.join(search_conditions)})")
            else:
                # Default: search all fields
                where_clauses.append(
                    "(last_name LIKE %s OR first_name LIKE %s OR company_name LIKE %s OR "
                    "phone LIKE %s OR mobile LIKE %s OR city LIKE %s OR "
                    "email LIKE %s OR rustdesk_id LIKE %s OR national_id LIKE %s OR "
                    "CAST(legacy_code AS CHAR) LIKE %s OR "
                    "CONCAT(last_name, ' ', first_name) LIKE %s OR "
                    "CONCAT(first_name, ' ', last_name) LIKE %s)"
                )
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 12)
        
        if only_active:
            where_clauses.append("is_active = 1")
        
        if where_clauses:
            where_clause = " AND ".join(where_clauses)
            query = f"""
                SELECT * FROM families 
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """
        else:
            query = """
                SELECT * FROM families 
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """
        
        params.extend([limit, offset])
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"list_clients returned {len(results)} clients")
            return results
        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            raise
    
    def count_clients(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        search_fields: Optional[List[str]] = None
    ) -> int:
        """
        Count clients matching the given filters.
        
        Args:
            search: Search term for client fields
            only_active: If True, only count active clients
            search_fields: List of field names to search in
            
        Returns:
            Total count of matching clients
        """
        where_clauses = []
        params = []
        
        if search:
            field_map = {
                "code": "CAST(legacy_code AS CHAR)",
                "last_name": "last_name",
                "first_name": "first_name",
                "company_name": "company_name",
                "rustdesk_id": "rustdesk_id",
                "phone": "phone",
                "mobile": "mobile",
                "city": "city",
                "email": "email",
                "national_id": "national_id"
            }
            
            if search_fields:
                search_conditions = []
                for field_key in search_fields:
                    db_column = field_map.get(field_key)
                    if db_column:
                        search_conditions.append(f"{db_column} LIKE %s")
                        params.append(f"%{search}%")
                
                search_conditions.append("CONCAT(last_name, ' ', first_name) LIKE %s")
                params.append(f"%{search}%")
                search_conditions.append("CONCAT(first_name, ' ', last_name) LIKE %s")
                params.append(f"%{search}%")
                if search_conditions:
                    where_clauses.append(f"({' OR '.join(search_conditions)})")
            else:
                # Default: search all fields
                where_clauses.append(
                    "(last_name LIKE %s OR first_name LIKE %s OR company_name LIKE %s OR "
                    "phone LIKE %s OR mobile LIKE %s OR city LIKE %s OR "
                    "email LIKE %s OR rustdesk_id LIKE %s OR national_id LIKE %s OR "
                    "CAST(legacy_code AS CHAR) LIKE %s OR "
                    "CONCAT(last_name, ' ', first_name) LIKE %s OR "
                    "CONCAT(first_name, ' ', last_name) LIKE %s)"
                )
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 12)
        
        if only_active:
            where_clauses.append("is_active = 1")
        
        if where_clauses:
            where_clause = " AND ".join(where_clauses)
            query = f"SELECT COUNT(*) as count FROM families WHERE {where_clause}"
        else:
            query = "SELECT COUNT(*) as count FROM families"
        
        try:
            results = self.db.execute_query(query, tuple(params) if params else None)
            count = results[0]['count'] if results else 0
            logger.debug(f"count_clients returned {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting clients: {e}")
            raise
    
    def create_client(self, client_data: Dict[str, Any], auto_numbering_service=None) -> int:
        """
        Create a new client record.
        
        Args:
            client_data: Dictionary with client fields
            auto_numbering_service: Optional AutoNumberingService for generating legacy_code
            
        Returns:
            ID of the newly created client
        """
        # Auto-generate legacy_code if not provided or is 0
        if 'legacy_code' not in client_data or client_data.get('legacy_code', 0) == 0:
            if auto_numbering_service:
                next_code = auto_numbering_service.get_next_legacy_code()
            else:
                max_code_result = self.db.execute_query(
                    "SELECT COALESCE(MAX(legacy_code), 0) + 1 as next_code FROM families"
                )
                next_code = max_code_result[0]['next_code'] if max_code_result else 1
            
            client_data['legacy_code'] = next_code
            logger.debug(f"Auto-generated legacy_code: {next_code}")
        
        fields = [
            'legacy_code', 'last_name', 'first_name', 'company_name',
            'national_id', 'afm', 'doy', 'profession', 'address', 'city', 'postal_code',
            'phone', 'mobile', 'email', 'notes', 'notes_support', 'is_active',
            'rustdesk_id', 'rustdesk_password', 'support_plan',
            'hourly_rate', 'monthly_rate'
        ]
        
        # Filter only fields that exist in client_data
        insert_fields = [f for f in fields if f in client_data]
        values = [client_data[f] for f in insert_fields]
        
        fields_str = ', '.join(insert_fields)
        placeholders = ', '.join(['%s'] * len(insert_fields))
        
        query = f"INSERT INTO families ({fields_str}) VALUES ({placeholders})"
        
        try:
            client_id = self.db.execute_update(query, tuple(values))
            
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Created client with id={client_id}, legacy_code={client_data['legacy_code']}")
            
            if self.reporting_service:
                self.reporting_service.invalidate_cache()
            
            log_audit(self.db, 'families', client_id, 'INSERT', None, client_data)
            return client_id
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def update_client(self, client_id: int, client_data: Dict[str, Any]) -> bool:
        """
        Update an existing client record.
        
        Args:
            client_id: ID of the client to update
            client_data: Dictionary with fields to update
            
        Returns:
            True if successful
        """
        client_data = {k: v for k, v in client_data.items() if k != 'id'}
        
        if not client_data:
            logger.warning("No fields to update")
            return False
        
        set_clauses = [f"{field} = %s" for field in client_data.keys()]
        values = list(client_data.values())
        values.append(client_id)
        
        query = f"UPDATE families SET {', '.join(set_clauses)} WHERE id = %s"
        
        try:
            _old_client = self.get_client_by_id(client_id)
            rows_affected = self.db.execute_update(query, tuple(values))
            
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Updated client id={client_id}, rows affected={rows_affected}")
            log_audit(self.db, 'families', client_id, 'UPDATE', _old_client, client_data)
            
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error updating client id={client_id}: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def soft_delete_client(self, client_id: int) -> bool:
        """
        Soft delete a client by setting is_active = 0.
        
        Args:
            client_id: ID of the client to soft delete
            
        Returns:
            True if successful
        """
        query = "UPDATE families SET is_active = 0 WHERE id = %s"
        
        try:
            rows_affected = self.db.execute_update(query, (client_id,))
            
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Soft deleted client id={client_id}")
            log_audit(self.db, 'families', client_id, 'UPDATE', None, {'is_active': 0})
            
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error soft deleting client id={client_id}: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def delete_client(self, client_id: int) -> bool:
        """
        Permanently delete a client and all related data (CASCADE).
        
        WARNING: This will delete:
        - Client record
        - All payments
        - All subscriptions
        - All sessions
        - All members
        - All package hours
        
        Args:
            client_id: ID of the client to delete
            
        Returns:
            True if successful
        """
        query = "DELETE FROM families WHERE id = %s"
        _old_client = self.get_client_by_id(client_id)
        
        try:
            rows_affected = self.db.execute_update(query, (client_id,))
            
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Permanently deleted client id={client_id} and all related data")
            log_audit(self.db, 'families', client_id, 'DELETE', _old_client, None)
            
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error deleting client id={client_id}: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def deactivate_clients_with_expired_subscriptions(self) -> int:
        """
        Automatically deactivate clients whose subscriptions have expired.
        
        Returns:
            Number of clients deactivated
        """
        try:
            from datetime import date
            today = date.today()
            
            # Find active clients with expired subscriptions
            query = """
                UPDATE families f
                INNER JOIN (
                    SELECT s.family_id
                    FROM subscriptions s
                    INNER JOIN (
                        SELECT family_id, MAX(end_date) as latest_end_date
                        FROM subscriptions
                        GROUP BY family_id
                    ) latest ON s.family_id = latest.family_id AND s.end_date = latest.latest_end_date
                    WHERE s.end_date < %s
                    AND s.status = 'ACTIVE'
                ) expired ON f.id = expired.family_id
                SET f.is_active = 0
                WHERE f.is_active = 1
            """
            
            rows_affected = self.db.execute_update(query, (today,))
            
            connection = self.db.get_connection()
            connection.commit()
            
            if rows_affected > 0:
                logger.info(f"Auto-deactivated {rows_affected} clients with expired subscriptions")
                
                if self.reporting_service:
                    self.reporting_service.invalidate_cache()
            
            return rows_affected
            
        except Exception as e:
            logger.error(f"Error deactivating clients with expired subscriptions: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return 0
    
    def get_client_by_id(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a client by its ID.
        
        Args:
            client_id: The client ID
            
        Returns:
            Dictionary representing the client record, or None if not found
        """
        return self.get_by_id(client_id)
