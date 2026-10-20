"""
Imports repository for managing import log records.
Tracks CSV import operations and their results.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class ImportsRepository(BaseRepository):
    """
    Repository for import_logs table operations.
    Extends BaseRepository with import logging functionality.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize ImportsRepository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        super().__init__(db_connection, 'import_logs')
        logger.debug("ImportsRepository initialized")
    
    def log_import(
        self,
        file_name: str,
        file_type: str,
        rows_total: int,
        rows_success: int,
        rows_failed: int,
        error_log: Optional[str] = None
    ) -> int:
        """
        Log an import operation to the database.
        
        Args:
            file_name: Name of the imported file
            file_type: Type of import ('client', 'members', 'report')
            rows_total: Total number of rows in the file
            rows_success: Number of successfully imported rows
            rows_failed: Number of failed rows
            error_log: Optional detailed error log (JSON or text)
            
        Returns:
            ID of the created import log record
        """
        data = {
            'file_name': file_name,
            'file_type': file_type,
            'rows_total': rows_total,
            'rows_success': rows_success,
            'rows_failed': rows_failed,
            'error_log': error_log
        }
        
        try:
            log_id = self.create(data)
            logger.info(
                f"Import logged: {file_type} - {file_name} "
                f"(Total: {rows_total}, Success: {rows_success}, Failed: {rows_failed})"
            )
            return log_id
        except Exception as e:
            logger.error(f"Error logging import for {file_name}: {e}")
            raise
    
    def get_by_file_type(self, file_type: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve import logs by file type.
        
        Args:
            file_type: Type of import ('client', 'members', 'report')
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing import logs
        """
        query = """
            SELECT * FROM import_logs 
            WHERE file_type = %s 
            ORDER BY imported_at DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (file_type, limit, offset))
            logger.debug(f"Retrieved {len(results)} import logs for file_type={file_type}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving import logs for file_type={file_type}: {e}")
            raise
    
    def get_recent_imports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent import operations.
        
        Args:
            limit: Maximum number of records to return (default: 10)
            
        Returns:
            List of dictionaries representing recent import logs
        """
        query = """
            SELECT * FROM import_logs 
            ORDER BY imported_at DESC
            LIMIT %s
        """
        
        try:
            results = self.db.execute_query(query, (limit,))
            logger.debug(f"Retrieved {len(results)} recent import logs")
            return results
        except Exception as e:
            logger.error(f"Error retrieving recent import logs: {e}")
            raise
    
    def get_imports_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve import logs within a date range.
        
        Args:
            start_date: Start of the date range
            end_date: End of the date range
            file_type: Optional file type filter
            
        Returns:
            List of dictionaries representing import logs
        """
        if file_type:
            query = """
                SELECT * FROM import_logs 
                WHERE imported_at BETWEEN %s AND %s AND file_type = %s
                ORDER BY imported_at DESC
            """
            params = (start_date, end_date, file_type)
        else:
            query = """
                SELECT * FROM import_logs 
                WHERE imported_at BETWEEN %s AND %s
                ORDER BY imported_at DESC
            """
            params = (start_date, end_date)
        
        try:
            results = self.db.execute_query(query, params)
            logger.debug(f"Retrieved {len(results)} import logs between {start_date} and {end_date}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving import logs by date range: {e}")
            raise
    
    def get_failed_imports(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve import operations that had failures.
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries representing import logs with failures
        """
        query = """
            SELECT * FROM import_logs 
            WHERE rows_failed > 0 
            ORDER BY imported_at DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} failed import logs")
            return results
        except Exception as e:
            logger.error(f"Error retrieving failed import logs: {e}")
            raise
    
    def get_import_statistics(self, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about import operations.
        
        Args:
            file_type: Optional file type filter
            
        Returns:
            Dictionary with import statistics
        """
        if file_type:
            query = """
                SELECT 
                    COUNT(*) as total_imports,
                    SUM(rows_total) as total_rows,
                    SUM(rows_success) as total_success,
                    SUM(rows_failed) as total_failed,
                    AVG(rows_success * 100.0 / NULLIF(rows_total, 0)) as avg_success_rate,
                    MIN(imported_at) as first_import,
                    MAX(imported_at) as last_import
                FROM import_logs
                WHERE file_type = %s
            """
            params = (file_type,)
        else:
            query = """
                SELECT 
                    COUNT(*) as total_imports,
                    SUM(rows_total) as total_rows,
                    SUM(rows_success) as total_success,
                    SUM(rows_failed) as total_failed,
                    AVG(rows_success * 100.0 / NULLIF(rows_total, 0)) as avg_success_rate,
                    MIN(imported_at) as first_import,
                    MAX(imported_at) as last_import
                FROM import_logs
            """
            params = ()
        
        try:
            results = self.db.execute_query(query, params)
            if results:
                stats = results[0]
                logger.debug(f"Import statistics: {stats}")
                return stats
            else:
                return {
                    'total_imports': 0,
                    'total_rows': 0,
                    'total_success': 0,
                    'total_failed': 0,
                    'avg_success_rate': 0.0,
                    'first_import': None,
                    'last_import': None
                }
        except Exception as e:
            logger.error(f"Error getting import statistics: {e}")
            raise
    
    def get_last_import_by_type(self, file_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent import for a specific file type.
        
        Args:
            file_type: Type of import ('client', 'members', 'report')
            
        Returns:
            Dictionary representing the last import log, or None if no imports exist
        """
        query = """
            SELECT * FROM import_logs 
            WHERE file_type = %s 
            ORDER BY imported_at DESC
            LIMIT 1
        """
        
        try:
            results = self.db.execute_query(query, (file_type,))
            if results:
                logger.debug(f"Found last import for file_type={file_type}")
                return results[0]
            else:
                logger.debug(f"No imports found for file_type={file_type}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving last import for file_type={file_type}: {e}")
            raise
    
    def count_imports_by_type(self) -> Dict[str, int]:
        """
        Count imports grouped by file type.
        
        Returns:
            Dictionary mapping file types to import counts
        """
        query = """
            SELECT file_type, COUNT(*) as count
            FROM import_logs
            GROUP BY file_type
        """
        
        try:
            results = self.db.execute_query(query)
            counts = {row['file_type']: row['count'] for row in results}
            logger.debug(f"Import counts by type: {counts}")
            return counts
        except Exception as e:
            logger.error(f"Error counting imports by type: {e}")
            raise
