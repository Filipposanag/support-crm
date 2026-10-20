"""
Members repository for managing family member records.
Provides specialized queries for member data access.
"""

import logging
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class MembersRepository(BaseRepository):
    """
    Repository for members table operations.
    Extends BaseRepository with member-specific queries.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize MembersRepository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        super().__init__(db_connection, 'members')
        logger.debug("MembersRepository initialized")
    
    def get_by_family_id(self, family_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all active members of a specific family.
        
        Args:
            family_id: The ID of the family
            
        Returns:
            List of dictionaries representing family members
        """
        query = """
            SELECT * FROM members 
            WHERE family_id = %s AND is_active = 1
            ORDER BY inner_no, first_name
        """
        
        try:
            results = self.db.execute_query(query, (family_id,))
            logger.debug(f"Retrieved {len(results)} members for family_id={family_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving members for family_id={family_id}: {e}")
            raise
    
    def get_by_legacy_family_code(self, legacy_family_code: int, inner_no: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Find member(s) by legacy family code (from CSV import).
        Used during CSV import to match existing members.
        
        Args:
            legacy_family_code: The legacy CODE value from members.csv
            inner_no: Optional inner number (ANO) to identify specific member
            
        Returns:
            Dictionary representing the member record, or None if not found
            If inner_no is not provided, returns the first matching member
        """
        if inner_no is not None:
            query = """
                SELECT * FROM members 
                WHERE legacy_family_code = %s AND inner_no = %s
            """
            params = (legacy_family_code, inner_no)
        else:
            query = """
                SELECT * FROM members 
                WHERE legacy_family_code = %s 
                ORDER BY inner_no
                LIMIT 1
            """
            params = (legacy_family_code,)
        
        try:
            results = self.db.execute_query(query, params)
            if results:
                logger.debug(f"Found member with legacy_family_code={legacy_family_code}, inner_no={inner_no}")
                return results[0]
            else:
                logger.debug(f"No member found with legacy_family_code={legacy_family_code}, inner_no={inner_no}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving member by legacy_family_code={legacy_family_code}: {e}")
            raise
    
    def get_active_members_by_family(self, family_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve only active members of a specific family.
        
        Args:
            family_id: The ID of the family
            
        Returns:
            List of dictionaries representing active family members
        """
        query = """
            SELECT * FROM members 
            WHERE family_id = %s AND is_active = 1 
            ORDER BY inner_no, first_name
        """
        
        try:
            results = self.db.execute_query(query, (family_id,))
            logger.debug(f"Retrieved {len(results)} active members for family_id={family_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving active members for family_id={family_id}: {e}")
            raise
    
    def list_members_by_family(self, family_id: int, only_active: bool = True) -> List[Dict[str, Any]]:
        """
        List members of a specific family with optional active filter.
        
        Args:
            family_id: The ID of the family
            only_active: If True, only return active members (default: True)
            
        Returns:
            List of dictionaries representing family members
        """
        query = """
            SELECT * FROM members 
            WHERE family_id = %s 
                AND (%s = 0 OR is_active = 1)
            ORDER BY last_name, first_name
        """
        
        try:
            # Pass 0 if only_active is False, 1 if True
            results = self.db.execute_query(query, (family_id, 1 if only_active else 0))
            logger.debug(f"Retrieved {len(results)} members for family_id={family_id} (only_active={only_active})")
            return results
        except Exception as e:
            logger.error(f"Error listing members for family_id={family_id}: {e}")
            raise
    
    def count_members_by_family(self, family_id: int, active_only: bool = False) -> int:
        """
        Count the number of members in a family.
        
        Args:
            family_id: The ID of the family
            active_only: If True, only count active members
            
        Returns:
            Number of members in the family
        """
        if active_only:
            query = "SELECT COUNT(*) as count FROM members WHERE family_id = %s AND is_active = 1"
        else:
            query = "SELECT COUNT(*) as count FROM members WHERE family_id = %s"
        
        try:
            results = self.db.execute_query(query, (family_id,))
            count = results[0]['count'] if results else 0
            logger.debug(f"Member count for family_id={family_id}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting members for family_id={family_id}: {e}")
            raise
    
    def search_by_name(self, name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search members by first name or last name (partial match).
        
        Args:
            name: Search term to match against first_name or last_name
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing matching members
        """
        query = """
            SELECT m.*, f.last_name as family_last_name, f.first_name as family_first_name
            FROM members m
            JOIN families f ON m.family_id = f.id
            WHERE m.first_name LIKE %s OR m.last_name LIKE %s 
            ORDER BY m.last_name, m.first_name
            LIMIT %s OFFSET %s
        """
        
        search_pattern = f"%{name}%"
        
        try:
            results = self.db.execute_query(query, (search_pattern, search_pattern, limit, offset))
            logger.debug(f"Name search for '{name}' returned {len(results)} members")
            return results
        except Exception as e:
            logger.error(f"Error searching members by name '{name}': {e}")
            raise
    
    def search_by_national_id(self, national_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for a member by national ID (ADT).
        
        Args:
            national_id: National ID to search for
            
        Returns:
            Dictionary representing the member record, or None if not found
        """
        query = """
            SELECT m.*, f.last_name as family_last_name, f.first_name as family_first_name
            FROM members m
            JOIN families f ON m.family_id = f.id
            WHERE m.national_id = %s
        """
        
        try:
            results = self.db.execute_query(query, (national_id,))
            if results:
                logger.debug(f"Found member with national_id={national_id}")
                return results[0]
            else:
                logger.debug(f"No member found with national_id={national_id}")
                return None
        except Exception as e:
            logger.error(f"Error searching member by national_id={national_id}: {e}")
            raise
    
    def get_married_members_by_family(self, family_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve married members of a specific family.
        
        Args:
            family_id: The ID of the family
            
        Returns:
            List of dictionaries representing married family members
        """
        query = """
            SELECT * FROM members 
            WHERE family_id = %s AND married = 1 AND is_active = 1
            ORDER BY marriage_date DESC
        """
        
        try:
            results = self.db.execute_query(query, (family_id,))
            logger.debug(f"Retrieved {len(results)} married members for family_id={family_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving married members for family_id={family_id}: {e}")
            raise
    
    def delete_by_family_id(self, family_id: int) -> int:
        """
        Soft delete all members of a family.
        
        Args:
            family_id: The ID of the family
            
        Returns:
            Number of members deleted
        """
        query = "UPDATE members SET is_active = 0 WHERE family_id = %s"
        
        try:
            affected_rows = self.db.execute_update(query, (family_id,))
            self.db.commit()
            logger.info(f"Soft deleted {affected_rows} members for family_id={family_id}")
            return affected_rows
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting members for family_id={family_id}: {e}")
            raise
