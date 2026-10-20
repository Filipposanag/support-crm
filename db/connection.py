"""
Database connection management module.
Handles MariaDB connections with error handling and query execution.
"""

import logging
from typing import List, Optional, Tuple, Any
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Manages MariaDB database connections and provides query execution methods.
    Uses a single connection per application session with proper error handling.
    """
    
    def __init__(self, config: dict):
        """
        Initialize database connection manager.
        
        Args:
            config: Dictionary containing database connection parameters:
                - host: Database host
                - port: Database port
                - user: Database user
                - password: Database password
                - database: Database name
                - charset: Character set (default: utf8mb4)
                - autocommit: Autocommit mode (default: False)
        """
        self.config = config
        self._connection: Optional[pymysql.Connection] = None
        logger.info(f"DatabaseConnection initialized for {config.get('database')} at {config.get('host')}")
    
    def get_connection(self) -> pymysql.Connection:
        """
        Get or create a database connection.
        
        Returns:
            Active database connection
            
        Raises:
            pymysql.Error: If connection fails
        """
        if self._connection is None or not self._is_connection_alive():
            try:
                # Connection parameters
                conn_params = {
                    'host': self.config['host'],
                    'port': self.config['port'],
                    'user': self.config['user'],
                    'password': self.config['password'],
                    'database': self.config['database'],
                    'charset': self.config.get('charset', 'utf8mb4'),
                    'use_unicode': True,
                    'autocommit': self.config.get('autocommit', False),
                    'cursorclass': DictCursor
                }
                
                # Add auth_plugin for MariaDB compatibility
                # This fixes the "auth_gssapi_client not configured" error
                if 'auth_plugin' not in self.config:
                    conn_params['client_flag'] = pymysql.constants.CLIENT.MULTI_STATEMENTS
                
                self._connection = pymysql.connect(**conn_params)
                logger.info("Database connection established successfully")
            except pymysql.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        
        return self._connection
    
    def _is_connection_alive(self) -> bool:
        """
        Check if the current connection is alive.
        
        Returns:
            True if connection is alive, False otherwise
        """
        if self._connection is None:
            return False
        
        try:
            self._connection.ping(reconnect=False)
            return True
        except pymysql.Error:
            return False
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[dict]:
        """
        Execute a SELECT query and return results as list of dictionaries.
        
        Args:
            query: SQL SELECT query with placeholders (%s)
            params: Tuple of parameters for the query
            
        Returns:
            List of dictionaries representing rows
            
        Raises:
            pymysql.Error: If query execution fails
        """
        connection = self.get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                logger.debug(f"Query executed successfully, returned {len(results)} rows")
                return results
        except pymysql.Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query with placeholders (%s)
            params: Tuple of parameters for the query
            
        Returns:
            Number of affected rows or last insert ID for INSERT queries
            
        Raises:
            pymysql.Error: If query execution fails
        """
        connection = self.get_connection()
        
        try:
            with connection.cursor() as cursor:
                affected_rows = cursor.execute(query, params or ())
                
                # For INSERT queries, return the last insert ID
                if query.strip().upper().startswith('INSERT'):
                    last_id = cursor.lastrowid
                    logger.debug(f"INSERT executed successfully, last_id: {last_id}")
                    return last_id
                else:
                    logger.debug(f"UPDATE/DELETE executed successfully, affected rows: {affected_rows}")
                    return affected_rows
        except pymysql.Error as e:
            # Check if it's a duplicate column/key error (expected during migrations)
            error_code = e.args[0] if e.args else 0
            if error_code in (1060, 1061):  # Duplicate column/key
                logger.debug(f"Duplicate column/key (expected): {e}")
            else:
                logger.error(f"Update execution failed: {e}")
                logger.error(f"Query: {query}")
            raise
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        Execute a batch operation (multiple INSERT/UPDATE statements).
        Useful for bulk imports with better performance.
        
        Args:
            query: SQL query with placeholders (%s)
            params_list: List of tuples, each containing parameters for one execution
            
        Returns:
            Total number of affected rows
            
        Raises:
            pymysql.Error: If batch execution fails
        """
        if not params_list:
            logger.warning("execute_many called with empty params_list")
            return 0
        
        connection = self.get_connection()
        
        try:
            with connection.cursor() as cursor:
                affected_rows = cursor.executemany(query, params_list)
                logger.debug(f"Batch execution successful, affected rows: {affected_rows}")
                return affected_rows
        except pymysql.Error as e:
            logger.error(f"Batch execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Batch size: {len(params_list)}")
            raise
    
    def commit(self):
        """
        Commit the current transaction.
        
        Raises:
            pymysql.Error: If commit fails
        """
        if self._connection:
            try:
                self._connection.commit()
                logger.debug("Transaction committed successfully")
            except pymysql.Error as e:
                logger.error(f"Commit failed: {e}")
                raise
    
    def rollback(self):
        """
        Rollback the current transaction.
        
        Raises:
            pymysql.Error: If rollback fails
        """
        if self._connection:
            try:
                self._connection.rollback()
                logger.debug("Transaction rolled back successfully")
            except pymysql.Error as e:
                logger.error(f"Rollback failed: {e}")
                raise
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        Automatically commits on success or rolls back on error.
        
        Usage:
            with db.transaction():
                db.execute_update(query1, params1)
                db.execute_update(query2, params2)
        """
        try:
            yield self
            self.commit()
        except Exception as e:
            self.rollback()
            logger.error(f"Transaction failed and rolled back: {e}")
            raise
    
    def close(self):
        """
        Close the database connection.
        Should be called when the application exits.
        """
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Database connection closed")
            except pymysql.Error as e:
                logger.error(f"Error closing connection: {e}")
    
    def test_connection(self) -> bool:
        """
        Test if database connection can be established.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except pymysql.Error as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def database_exists(self, database_name: str) -> bool:
        """
        Check if a database exists.
        
        Args:
            database_name: Name of the database to check
            
        Returns:
            True if database exists, False otherwise
        """
        try:
            # Connect without specifying a database
            temp_config = self.config.copy()
            temp_config.pop('database', None)
            
            temp_conn = pymysql.connect(
                host=temp_config['host'],
                port=temp_config['port'],
                user=temp_config['user'],
                password=temp_config['password'],
                charset=temp_config.get('charset', 'utf8mb4'),
                use_unicode=True
            )
            
            with temp_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                    (database_name,)
                )
                result = cursor.fetchone()
            
            temp_conn.close()
            return result is not None
            
        except pymysql.Error as e:
            logger.error(f"Error checking database existence: {e}")
            return False
    
    def create_database(self, database_name: str) -> bool:
        """
        Create a new database if it doesn't exist.
        
        Args:
            database_name: Name of the database to create
            
        Returns:
            True if database was created or already exists, False on error
        """
        try:
            # Connect without specifying a database
            temp_config = self.config.copy()
            temp_config.pop('database', None)
            
            temp_conn = pymysql.connect(
                host=temp_config['host'],
                port=temp_config['port'],
                user=temp_config['user'],
                password=temp_config['password'],
                charset=temp_config.get('charset', 'utf8mb4'),
                use_unicode=True
            )
            
            with temp_conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            
            temp_conn.commit()
            temp_conn.close()
            logger.info(f"Database '{database_name}' created or already exists")
            return True
            
        except pymysql.Error as e:
            logger.error(f"Error creating database: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the current database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                    (self.config['database'], table_name)
                )
                result = cursor.fetchone()
                return result is not None
        except pymysql.Error as e:
            logger.error(f"Error checking table existence: {e}")
            return False
