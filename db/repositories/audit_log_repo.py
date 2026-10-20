# -*- coding: utf-8 -*-
"""
Audit Log Repository - Database operations for audit_log table.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)


class AuditLogRepository:
    """Repository for audit_log table operations."""
    
    def __init__(self, db_connection):
        """
        Initialize repository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection

    def log(self, table_name, record_id, operation, old_values=None,
            new_values=None, changed_by="system"):
        """Write an audit entry. operation: INSERT | UPDATE | DELETE."""
        import json
        def _enc(v):
            if v is None:
                return None
            if isinstance(v, str):
                return v
            try:
                return json.dumps(v, ensure_ascii=False, default=str)
            except Exception:
                return str(v)
        try:
            self.db.execute_update(
                "INSERT INTO audit_log (table_name, record_id, operation, "
                "old_values, new_values, changed_by) VALUES (%s,%s,%s,%s,%s,%s)",
                (table_name, int(record_id or 0), operation,
                 _enc(old_values), _enc(new_values), changed_by or "system"))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return False
    
    def get_all_logs(self, limit: int = 1000, offset: int = 0) -> List[Dict]:
        """
        Get all audit logs with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of audit log dictionaries
        """
        query = """
            SELECT 
                id,
                table_name,
                record_id,
                operation,
                old_values,
                new_values,
                changed_by,
                changed_at,
                ip_address
            FROM audit_log
            ORDER BY changed_at DESC, id DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            results = self.db.execute_query(query, (limit, offset))
            logger.debug(f"Retrieved {len(results)} audit logs (limit={limit}, offset={offset})")
            return results
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []
    
    def get_logs_by_table(self, table_name: str, limit: int = 1000) -> List[Dict]:
        """
        Get audit logs for a specific table.
        
        Args:
            table_name: Name of the table to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of audit log dictionaries
        """
        query = """
            SELECT 
                id,
                table_name,
                record_id,
                operation,
                old_values,
                new_values,
                changed_by,
                changed_at,
                ip_address
            FROM audit_log
            WHERE table_name = %s
            ORDER BY changed_at DESC, id DESC
            LIMIT %s
        """
        
        try:
            results = self.db.execute_query(query, (table_name, limit))
            logger.debug(f"Retrieved {len(results)} audit logs for table '{table_name}'")
            return results
        except Exception as e:
            logger.error(f"Error fetching audit logs for table '{table_name}': {e}")
            return []
    
    def get_logs_by_record(self, table_name: str, record_id: int) -> List[Dict]:
        """
        Get audit logs for a specific record.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record
            
        Returns:
            List of audit log dictionaries
        """
        query = """
            SELECT 
                id,
                table_name,
                record_id,
                operation,
                old_values,
                new_values,
                changed_by,
                changed_at,
                ip_address
            FROM audit_log
            WHERE table_name = %s AND record_id = %s
            ORDER BY changed_at DESC, id DESC
        """
        
        try:
            results = self.db.execute_query(query, (table_name, record_id))
            logger.debug(f"Retrieved {len(results)} audit logs for {table_name}.{record_id}")
            return results
        except Exception as e:
            logger.error(f"Error fetching audit logs for {table_name}.{record_id}: {e}")
            return []
    
    def get_logs_by_date_range(self, start_date: date, end_date: date, limit: int = 1000) -> List[Dict]:
        """
        Get audit logs within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of audit log dictionaries
        """
        query = """
            SELECT 
                id,
                table_name,
                record_id,
                operation,
                old_values,
                new_values,
                changed_by,
                changed_at,
                ip_address
            FROM audit_log
            WHERE DATE(changed_at) BETWEEN %s AND %s
            ORDER BY changed_at DESC, id DESC
            LIMIT %s
        """
        
        try:
            results = self.db.execute_query(query, (start_date, end_date, limit))
            logger.debug(f"Retrieved {len(results)} audit logs between {start_date} and {end_date}")
            return results
        except Exception as e:
            logger.error(f"Error fetching audit logs by date range: {e}")
            return []
    
    def get_total_count(self) -> int:
        """
        Get total count of audit logs.
        
        Returns:
            Total number of audit log records
        """
        query = "SELECT COUNT(*) as count FROM audit_log"
        
        try:
            results = self.db.execute_query(query)
            count = results[0]['count'] if results else 0
            logger.debug(f"Total audit log count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting audit log count: {e}")
            return 0
    
    def delete_old_logs(self, days: int = 365) -> int:
        """
        Delete audit logs older than specified days.
        
        Args:
            days: Number of days to keep (default: 365)
            
        Returns:
            Number of deleted records
        """
        query = """
            DELETE FROM audit_log
            WHERE changed_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        try:
            affected_rows = self.db.execute_update(query, (days,))
            connection = self.db.get_connection()
            connection.commit()
            logger.info(f"Deleted {affected_rows} audit logs older than {days} days")
            return affected_rows
        except Exception as e:
            logger.error(f"Error deleting old audit logs: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return 0
    
    def clear_all(self) -> int:
        """
        Delete ALL audit logs from database.
        
        WARNING: This operation cannot be undone!
        
        Returns:
            Number of deleted records
        """
        query = "DELETE FROM audit_log"
        
        try:
            affected_rows = self.db.execute_update(query)
            connection = self.db.get_connection()
            connection.commit()
            logger.warning(f"CLEARED ALL audit logs: {affected_rows} records deleted")
            return affected_rows
        except Exception as e:
            logger.error(f"Error clearing all audit logs: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return 0
    
    def enforce_limit(self, max_records: int = 1000) -> int:
        """
        Enforce maximum number of audit log records.
        Deletes oldest records if limit is exceeded.
        
        Args:
            max_records: Maximum number of records to keep (default: 1000)
            
        Returns:
            Number of deleted records
        """
        try:
            # Get current count
            count = self.get_total_count()
            
            if count <= max_records:
                return 0
            
            # Calculate how many to delete
            to_delete = count - max_records
            
            # Delete oldest records
            query = """
                DELETE FROM audit_log
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id FROM audit_log
                        ORDER BY changed_at ASC, id ASC
                        LIMIT %s
                    ) AS old_logs
                )
            """
            
            affected_rows = self.db.execute_update(query, (to_delete,))
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Enforced audit log limit: deleted {affected_rows} oldest records (kept {max_records})")
            return affected_rows
            
        except Exception as e:
            logger.error(f"Error enforcing audit log limit: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return 0
