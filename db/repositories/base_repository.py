"""
Base repository class for database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base repository class providing common CRUD operations.
    All specific repositories should extend this class.
    """
    
    def __init__(self, db_connection: DatabaseConnection, table_name: str):
        """
        Initialize base repository.
        
        Args:
            db_connection: DatabaseConnection instance
            table_name: Name of the database table this repository manages
        """
        self.db = db_connection
        self.table_name = table_name
        logger.debug(f"BaseRepository initialized for table: {table_name}")
    
    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single record by its ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Dictionary representing the record, or None if not found
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = %s"
        
        try:
            results = self.db.execute_query(query, (id,))
            if results:
                logger.debug(f"Found record with id={id} in {self.table_name}")
                return results[0]
            else:
                logger.debug(f"No record found with id={id} in {self.table_name}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving record by id={id} from {self.table_name}: {e}")
            raise
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve paginated records from the table.
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing records
        """
        query = f"SELECT * FROM {self.table_name} LIMIT %s OFFSET %s"
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} records from {self.table_name} (limit={limit}, offset={offset})")
            return results
        except Exception as e:
            logger.error(f"Error retrieving records from {self.table_name}: {e}")
            raise
    
    def search(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search records with filters and pagination.
        
        Args:
            filters: Dictionary of column names and values to filter by
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing matching records
        """
        if not filters:
            return self.get_all(limit, offset)
        
        # Build WHERE clause
        where_clauses = []
        params = []
        
        for column, value in filters.items():
            if value is not None:
                where_clauses.append(f"{column} = %s")
                params.append(value)
        
        if not where_clauses:
            return self.get_all(limit, offset)
        
        where_clause = " AND ".join(where_clauses)
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"Search returned {len(results)} records from {self.table_name}")
            return results
        except Exception as e:
            logger.error(f"Error searching records in {self.table_name}: {e}")
            raise
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Create a new record in the table.
        
        Args:
            data: Dictionary of column names and values
            
        Returns:
            ID of the newly created record
        """
        if not data:
            raise ValueError("Cannot create record with empty data")
        
        # Build INSERT query
        columns = list(data.keys())
        placeholders = ["%s"] * len(columns)
        values = [data[col] for col in columns]
        
        query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        try:
            last_id = self.db.execute_update(query, tuple(values))
            self.db.commit()
            logger.info(f"Created new record in {self.table_name} with id={last_id}")
            return last_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating record in {self.table_name}: {e}")
            raise
    
    def update(self, id: int, data: Dict[str, Any]) -> bool:
        """
        Update an existing record.
        
        Args:
            id: Primary key value of the record to update
            data: Dictionary of column names and new values
            
        Returns:
            True if record was updated, False if not found
        """
        if not data:
            raise ValueError("Cannot update record with empty data")
        
        # Build UPDATE query
        set_clauses = []
        params = []
        
        for column, value in data.items():
            set_clauses.append(f"{column} = %s")
            params.append(value)
        
        params.append(id)
        set_clause = ", ".join(set_clauses)
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = %s"
        
        try:
            affected_rows = self.db.execute_update(query, tuple(params))
            self.db.commit()
            
            if affected_rows > 0:
                logger.info(f"Updated record id={id} in {self.table_name}")
                return True
            else:
                logger.warning(f"No record found with id={id} in {self.table_name} to update")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating record id={id} in {self.table_name}: {e}")
            raise
    
    def delete(self, id: int) -> bool:
        """
        Soft delete a record by setting is_active to 0.
        If the table doesn't have an is_active column, performs hard delete.
        
        Args:
            id: Primary key value of the record to delete
            
        Returns:
            True if record was deleted, False if not found
        """
        # Check if table has is_active column
        check_query = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s 
            AND COLUMN_NAME = 'is_active'
        """
        
        try:
            result = self.db.execute_query(check_query, (self.table_name,))
            
            if result:
                # Soft delete
                query = f"UPDATE {self.table_name} SET is_active = 0 WHERE id = %s"
                affected_rows = self.db.execute_update(query, (id,))
                self.db.commit()
                
                if affected_rows > 0:
                    logger.info(f"Soft deleted record id={id} in {self.table_name}")
                    return True
                else:
                    logger.warning(f"No record found with id={id} in {self.table_name} to delete")
                    return False
            else:
                # Hard delete
                query = f"DELETE FROM {self.table_name} WHERE id = %s"
                affected_rows = self.db.execute_update(query, (id,))
                self.db.commit()
                
                if affected_rows > 0:
                    logger.info(f"Hard deleted record id={id} in {self.table_name}")
                    return True
                else:
                    logger.warning(f"No record found with id={id} in {self.table_name} to delete")
                    return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting record id={id} from {self.table_name}: {e}")
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in the table, optionally with filters.
        
        Args:
            filters: Optional dictionary of column names and values to filter by
            
        Returns:
            Number of matching records
        """
        if not filters:
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            params = ()
        else:
            where_clauses = []
            params = []
            
            for column, value in filters.items():
                if value is not None:
                    where_clauses.append(f"{column} = %s")
                    params.append(value)
            
            if not where_clauses:
                query = f"SELECT COUNT(*) as count FROM {self.table_name}"
                params = ()
            else:
                where_clause = " AND ".join(where_clauses)
                query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_clause}"
                params = tuple(params)
        
        try:
            results = self.db.execute_query(query, params)
            count = results[0]['count'] if results else 0
            logger.debug(f"Count query returned {count} for {self.table_name}")
            return count
        except Exception as e:
            logger.error(f"Error counting records in {self.table_name}: {e}")
            raise
