"""
Families repository for managing family records.
Provides specialized queries for family data access.
"""

import logging
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class FamiliesRepository(BaseRepository):
    """
    Repository for families table operations.
    Extends BaseRepository with family-specific queries.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize FamiliesRepository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        super().__init__(db_connection, 'families')
        self.reporting_service = None  # Will be set by dependency injection
        logger.debug("FamiliesRepository initialized")
    
    def get_by_legacy_code(self, legacy_code: int) -> Optional[Dict[str, Any]]:
        """
        Find a family by its legacy code (from CSV import).
        Used during CSV import to match existing families.
        
        Args:
            legacy_code: The legacy CODE value from client.csv
            
        Returns:
            Dictionary representing the family record, or None if not found
        """
        query = "SELECT * FROM families WHERE legacy_code = %s"
        
        try:
            results = self.db.execute_query(query, (legacy_code,))
            if results:
                logger.debug(f"Found family with legacy_code={legacy_code}")
                return results[0]
            else:
                logger.debug(f"No family found with legacy_code={legacy_code}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving family by legacy_code={legacy_code}: {e}")
            raise
    
    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Find a family by its code (legacy_code as string).
        Used for checking code uniqueness in the UI.
        
        Args:
            code: The code value (can be numeric or alphanumeric)
            
        Returns:
            Dictionary representing the family record, or None if not found
        """
        query = "SELECT * FROM families WHERE legacy_code = %s"
        
        try:
            results = self.db.execute_query(query, (code,))
            if results:
                logger.debug(f"Found family with code={code}")
                return results[0]
            else:
                logger.debug(f"No family found with code={code}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving family by code={code}: {e}")
            raise
    
    def get_next_code(self, settings_counter: int = None) -> int:
        """
        Get the next available code for a new family.
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
            # Return 1 as fallback
            return 1
    
    def search_by_name(self, name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search families by last name or first name (partial match).
        
        Args:
            name: Search term to match against last_name or first_name
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing matching families
        """
        query = """
            SELECT * FROM families 
            WHERE last_name LIKE %s OR first_name LIKE %s
               OR CONCAT(last_name, ' ', first_name) LIKE %s
               OR CONCAT(first_name, ' ', last_name) LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        
        search_pattern = f"%{name}%"
        
        try:
            results = self.db.execute_query(query, (search_pattern, search_pattern, search_pattern, search_pattern, limit, offset))
            logger.debug(f"Name search for '{name}' returned {len(results)} families")
            return results
        except Exception as e:
            logger.error(f"Error searching families by name '{name}': {e}")
            raise
    
    def search_by_national_id(self, national_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for a family by national ID (ADT).
        
        Args:
            national_id: National ID to search for
            
        Returns:
            Dictionary representing the family record, or None if not found
        """
        query = "SELECT * FROM families WHERE national_id = %s"
        
        try:
            results = self.db.execute_query(query, (national_id,))
            if results:
                logger.debug(f"Found family with national_id={national_id}")
                return results[0]
            else:
                logger.debug(f"No family found with national_id={national_id}")
                return None
        except Exception as e:
            logger.error(f"Error searching family by national_id={national_id}: {e}")
            raise
    
    def get_active_families(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve only active families (is_active = 1).
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing active families
        """
        query = """
            SELECT * FROM families 
            WHERE is_active = 1 
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} active families (limit={limit}, offset={offset})")
            return results
        except Exception as e:
            logger.error(f"Error retrieving active families: {e}")
            raise
    
    def search_families(
        self, 
        name: Optional[str] = None,
        national_id: Optional[str] = None,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple filter criteria.
        
        Args:
            name: Optional name to search (partial match on last_name or first_name)
            national_id: Optional national ID to search (exact match)
            active_only: If True, only return active families
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing matching families
        """
        where_clauses = []
        params = []
        
        if name:
            where_clauses.append(
                "(last_name LIKE %s OR first_name LIKE %s OR "
                "CONCAT(last_name, ' ', first_name) LIKE %s OR "
                "CONCAT(first_name, ' ', last_name) LIKE %s)"
            )
            search_pattern = f"%{name}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
        if national_id:
            where_clauses.append("national_id = %s")
            params.append(national_id)
        
        if active_only:
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
            logger.debug(f"Advanced search returned {len(results)} families")
            return results
        except Exception as e:
            logger.error(f"Error in advanced family search: {e}")
            raise
    
    def get_families_with_payment_info(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get families with additional payment information.
        Includes last payment year and outstanding amount.
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries with family and payment information
        """
        query = """
            SELECT 
                f.*,
                MAX(p.year) as last_payment_year,
                COALESCE(SUM(p.remaining_amount), 0) as outstanding_amount,
                COUNT(DISTINCT m.id) as actual_members_count
            FROM families f
            LEFT JOIN payments p ON f.id = p.family_id
            LEFT JOIN members m ON f.id = m.family_id AND m.is_active = 1
            GROUP BY f.id
            ORDER BY f.last_name, f.first_name
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} families with payment info")
            return results
        except Exception as e:
            logger.error(f"Error retrieving families with payment info: {e}")
            raise
    
    def count_active_families(self) -> int:
        """
        Count the number of active families.
        
        Returns:
            Number of active families
        """
        query = "SELECT COUNT(*) as count FROM families WHERE is_active = 1"
        
        try:
            results = self.db.execute_query(query)
            count = results[0]['count'] if results else 0
            logger.debug(f"Active families count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting active families: {e}")
            raise

    
    def list_families(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        limit: int = 100,
        offset: int = 0,
        search_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List families with optional filters.
        
        Args:
            search: Search term for family fields (partial match)
            only_active: If True, only return active families
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination
            search_fields: List of field names to search in (e.g., ["code", "last_name"]). If None, searches all fields.
            
        Returns:
            List of family records as dictionaries
        """
        where_clauses = []
        params = []
        
        if search:
            # Map field keys to database column names
            # Note: legacy_code is INT, so we need CAST for LIKE to work properly
            field_map = {
                "code": "CAST(legacy_code AS CHAR)",
                "last_name": "last_name",
                "first_name": "first_name",
                "father_name": "father_name",
                "spouse_name": "spouse_name",
                "spouse_maiden_name": "spouse_maiden_name",
                "adt": "national_id",
                "phone": "phone",
                "mobile": "mobile",
                "city": "city",
                "email": "email"
            }
            
            # If search_fields is provided and not empty, use only those fields
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
                # Default: search all fields including new fields
                # Note: CAST legacy_code to CHAR for LIKE to work with numeric codes
                where_clauses.append(
                    "(last_name LIKE %s OR first_name LIKE %s OR father_name LIKE %s OR "
                    "spouse_name LIKE %s OR spouse_maiden_name LIKE %s OR phone LIKE %s OR "
                    "mobile LIKE %s OR city LIKE %s OR national_id LIKE %s OR "
                    "email LIKE %s OR address LIKE %s OR postal_code LIKE %s OR "
                    "profession LIKE %s OR CAST(legacy_code AS CHAR) LIKE %s OR "
                    "CONCAT(last_name, ' ', first_name) LIKE %s OR "
                    "CONCAT(first_name, ' ', last_name) LIKE %s)"
                )
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern, search_pattern, 
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern,
                              search_pattern, search_pattern])
        
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
            logger.debug(f"list_families returned {len(results)} families")
            return results
        except Exception as e:
            logger.error(f"Error listing families: {e}")
            raise
    
    def count_families(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        search_fields: Optional[List[str]] = None
    ) -> int:
        """
        Count families matching the given filters.
        
        Args:
            search: Search term for family fields
            only_active: If True, only count active families
            search_fields: List of field names to search in (e.g., ["code", "last_name"]). If None, searches all fields.
            
        Returns:
            Total count of matching families
        """
        where_clauses = []
        params = []
        
        if search:
            # Map field keys to database column names
            # Note: legacy_code is INT, so we need CAST for LIKE to work properly
            field_map = {
                "code": "CAST(legacy_code AS CHAR)",
                "last_name": "last_name",
                "first_name": "first_name",
                "father_name": "father_name",
                "spouse_name": "spouse_name",
                "spouse_maiden_name": "spouse_maiden_name",
                "adt": "national_id",
                "phone": "phone",
                "mobile": "mobile",
                "city": "city",
                "email": "email"
            }
            
            # If search_fields is provided and not empty, use only those fields
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
                # Default: search all fields including new fields
                # Note: CAST legacy_code to CHAR for LIKE to work with numeric codes
                where_clauses.append(
                    "(last_name LIKE %s OR first_name LIKE %s OR father_name LIKE %s OR "
                    "spouse_name LIKE %s OR spouse_maiden_name LIKE %s OR phone LIKE %s OR "
                    "mobile LIKE %s OR city LIKE %s OR national_id LIKE %s OR "
                    "email LIKE %s OR address LIKE %s OR postal_code LIKE %s OR "
                    "profession LIKE %s OR CAST(legacy_code AS CHAR) LIKE %s OR "
                    "CONCAT(last_name, ' ', first_name) LIKE %s OR "
                    "CONCAT(first_name, ' ', last_name) LIKE %s)"
                )
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern, search_pattern, 
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern, search_pattern,
                              search_pattern, search_pattern,
                              search_pattern, search_pattern])
        
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
            logger.debug(f"count_families returned {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting families: {e}")
            raise
    
    def create_family(self, family_data: Dict[str, Any], auto_numbering_service=None) -> int:
        """
        Create a new family record.
        
        Args:
            family_data: Dictionary with family fields
            auto_numbering_service: Optional AutoNumberingService for generating legacy_code
            
        Returns:
            ID of the newly created family
        """
        # Auto-generate legacy_code if not provided or is 0
        if 'legacy_code' not in family_data or family_data.get('legacy_code', 0) == 0:
            if auto_numbering_service:
                # Use auto-numbering service
                next_code = auto_numbering_service.get_next_legacy_code()
            else:
                # Fallback: Get the next available legacy_code from database
                max_code_result = self.db.execute_query(
                    "SELECT COALESCE(MAX(legacy_code), 0) + 1 as next_code FROM families"
                )
                next_code = max_code_result[0]['next_code'] if max_code_result else 1
            
            family_data['legacy_code'] = next_code
            logger.debug(f"Auto-generated legacy_code: {next_code}")
        
        fields = [
            'legacy_code', 'last_name', 'first_name', 'father_name',
            'spouse_first_name', 'spouse_last_name', 'spouse_father_name',
            'spouse_name', 'spouse_maiden_name', 'is_divorced', 'spouse_deceased',
            'national_id', 'profession', 'address', 'city', 'postal_code',
            'phone', 'mobile', 'email', 'birth_date', 'members_count',
            'is_association_member', 'notes', 'is_active'
        ]
        
        # Filter only fields that exist in family_data
        insert_fields = [f for f in fields if f in family_data]
        values = [family_data[f] for f in insert_fields]
        
        fields_str = ', '.join(insert_fields)
        placeholders = ', '.join(['%s'] * len(insert_fields))
        
        query = f"INSERT INTO families ({fields_str}) VALUES ({placeholders})"
        
        try:
            family_id = self.db.execute_update(query, tuple(values))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Created family with id={family_id}, legacy_code={family_data['legacy_code']}")
            
            # Invalidate reporting cache
            if self.reporting_service:
                self.reporting_service.invalidate_cache()
            
            return family_id
        except Exception as e:
            logger.error(f"Error creating family: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def update_family(self, family_id: int, family_data: Dict[str, Any]) -> bool:
        """
        Update an existing family record.
        
        Args:
            family_id: ID of the family to update
            family_data: Dictionary with fields to update
            
        Returns:
            True if successful
        """
        # Remove id from update data if present
        family_data = {k: v for k, v in family_data.items() if k != 'id'}
        
        if not family_data:
            logger.warning("No fields to update")
            return False
        
        set_clauses = [f"{field} = %s" for field in family_data.keys()]
        values = list(family_data.values())
        values.append(family_id)
        
        query = f"UPDATE families SET {', '.join(set_clauses)} WHERE id = %s"
        
        try:
            rows_affected = self.db.execute_update(query, tuple(values))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Updated family id={family_id}, rows affected={rows_affected}")
            
            # Invalidate reporting cache (members_count might have changed)
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error updating family id={family_id}: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def soft_delete_family(self, family_id: int) -> bool:
        """
        Soft delete a family by setting is_active = 0.
        
        Args:
            family_id: ID of the family to soft delete
            
        Returns:
            True if successful
        """
        query = "UPDATE families SET is_active = 0 WHERE id = %s"
        
        try:
            rows_affected = self.db.execute_update(query, (family_id,))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Soft deleted family id={family_id}")
            
            # Invalidate reporting cache
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error soft deleting family id={family_id}: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise

    def get_family_by_id(self, family_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a family by its ID.
        Wrapper around get_by_id for clarity.
        
        Args:
            family_id: The family ID
            
        Returns:
            Dictionary representing the family record, or None if not found
        """
        return self.get_by_id(family_id)
