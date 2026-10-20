# -*- coding: utf-8 -*-
"""
Sessions repository for managing support session records.
Provides specialized queries for session data access.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class SessionsRepository(BaseRepository):
    """
    Repository for support_sessions table operations.
    Extends BaseRepository with session-specific queries.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize SessionsRepository.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        super().__init__(db_connection, 'support_sessions')
        logger.debug("SessionsRepository initialized")
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all currently active sessions.
        
        Returns:
            List of active session records
        """
        query = """
            SELECT s.*, c.last_name, c.first_name
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE s.status = 'active'
            ORDER BY s.start_time DESC
        """
        
        try:
            results = self.db.execute_query(query)
            logger.debug(f"Retrieved {len(results)} active sessions")
            return results
        except Exception as e:
            logger.error(f"Error retrieving active sessions: {e}")
            raise
    
    def get_client_sessions(
        self,
        client_id: int,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for a specific client.
        
        Args:
            client_id: Client ID
            limit: Maximum number of sessions to return
            status: Filter by status (active, completed, cancelled) or None for all
            
        Returns:
            List of session records
        """
        query = """
            SELECT * FROM support_sessions
            WHERE client_id = %s
        """
        params = [client_id]
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"Retrieved {len(results)} sessions for client {client_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving client sessions: {e}")
            raise
    
    def get_sessions_by_date_range(
        self,
        start_date: date,
        end_date: date,
        client_id: Optional[int] = None,
        technician: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sessions within a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            client_id: Optional client ID filter
            technician: Optional technician name filter
            
        Returns:
            List of session records
        """
        query = """
            SELECT s.*, c.last_name, c.first_name
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE DATE(s.start_time) >= %s AND DATE(s.start_time) <= %s
        """
        params = [start_date, end_date]
        
        if client_id:
            query += " AND s.client_id = %s"
            params.append(client_id)
        
        if technician:
            query += " AND s.technician = %s"
            params.append(technician)
        
        query += " ORDER BY s.start_time DESC"
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"Retrieved {len(results)} sessions for date range")
            return results
        except Exception as e:
            logger.error(f"Error retrieving sessions by date range: {e}")
            raise
    
    def get_sessions_by_technician(
        self,
        technician: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get sessions by technician.
        
        Args:
            technician: Technician name
            limit: Maximum number of sessions to return
            
        Returns:
            List of session records
        """
        query = """
            SELECT s.*, c.last_name, c.first_name
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE s.technician = %s
            ORDER BY s.start_time DESC
            LIMIT %s
        """
        
        try:
            results = self.db.execute_query(query, (technician, limit))
            logger.debug(f"Retrieved {len(results)} sessions for technician {technician}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving sessions by technician: {e}")
            raise
    
    def get_unbilled_sessions(self) -> List[Dict[str, Any]]:
        """
        Get completed sessions that haven't been billed yet.
        
        Returns:
            List of unbilled session records
        """
        query = """
            SELECT s.*, c.last_name, c.first_name
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE s.status = 'completed' 
            AND s.payment_id IS NULL
            AND s.billed_amount > 0
            ORDER BY s.end_time DESC
        """
        
        try:
            results = self.db.execute_query(query)
            logger.debug(f"Retrieved {len(results)} unbilled sessions")
            return results
        except Exception as e:
            logger.error(f"Error retrieving unbilled sessions: {e}")
            raise
    
    def get_session_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get session statistics for reporting.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            client_id: Optional client ID filter
            
        Returns:
            Dictionary with statistics
        """
        where_clauses = ["status = 'completed'"]
        params = []
        
        if start_date:
            where_clauses.append("DATE(start_time) >= %s")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("DATE(start_time) <= %s")
            params.append(end_date)
        
        if client_id:
            where_clauses.append("client_id = %s")
            params.append(client_id)
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration_minutes) as total_minutes,
                AVG(duration_minutes) as avg_minutes,
                SUM(billed_amount) as total_billed,
                COUNT(DISTINCT client_id) as unique_clients,
                COUNT(DISTINCT technician) as unique_technicians
            FROM support_sessions
            WHERE {where_clause}
        """
        
        try:
            results = self.db.execute_query(query, tuple(params) if params else None)
            if results:
                stats = results[0]
                logger.debug(f"Session statistics: {stats}")
                return stats
            return {}
        except Exception as e:
            logger.error(f"Error retrieving session statistics: {e}")
            raise
    
    def list_sessions(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filters.
        
        Args:
            search: Search term for client name or description
            status: Filter by status
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination
            
        Returns:
            List of session records
        """
        query = """
            SELECT s.*, c.last_name, c.first_name
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE 1=1
        """
        params = []
        
        if search:
            query += """ AND (
                c.last_name LIKE %s OR 
                c.first_name LIKE %s OR
                s.description LIKE %s OR
                s.technician LIKE %s OR
                CONCAT(c.last_name, ' ', c.first_name) LIKE %s OR
                CONCAT(c.first_name, ' ', c.last_name) LIKE %s
            )"""
            search_pattern = f"%{search}%"
            params.extend([search_pattern] * 6)
        
        if status:
            query += " AND s.status = %s"
            params.append(status)
        
        query += " ORDER BY s.start_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"list_sessions returned {len(results)} sessions")
            return results
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise
    
    def count_sessions(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count sessions matching the given filters.
        
        Args:
            search: Search term for client name or description
            status: Filter by status
            
        Returns:
            Total count of matching sessions
        """
        query = """
            SELECT COUNT(*) as count
            FROM support_sessions s
            LEFT JOIN families c ON s.client_id = c.id
            WHERE 1=1
        """
        params = []
        
        if search:
            query += """ AND (
                c.last_name LIKE %s OR 
                c.first_name LIKE %s OR
                s.description LIKE %s OR
                s.technician LIKE %s OR
                CONCAT(c.last_name, ' ', c.first_name) LIKE %s OR
                CONCAT(c.first_name, ' ', c.last_name) LIKE %s
            )"""
            search_pattern = f"%{search}%"
            params.extend([search_pattern] * 6)
        
        if status:
            query += " AND s.status = %s"
            params.append(status)
        
        try:
            results = self.db.execute_query(query, tuple(params) if params else None)
            count = results[0]['count'] if results else 0
            logger.debug(f"count_sessions returned {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting sessions: {e}")
            raise
