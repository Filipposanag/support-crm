"""
Database schema initialization and management module.
Handles database and table creation on first run.
"""

import logging
from pathlib import Path
from typing import List
import pymysql

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages database schema initialization and verification.
    Ensures database and tables exist before application starts.
    """
    
    def __init__(self, db_connection):
        """
        Initialize schema manager.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
        self.schema_file = Path(__file__).parent / 'schema_consolidated.sql'
        
        # Required tables for the application
        self.required_tables = [
            'families',
            'members',
            'payments',
            'subscriptions',
            'import_logs',
            'app_settings'
        ]
    
    def initialize_database(self) -> bool:
        """
        Initialize database and schema if needed.
        This is the main entry point for schema setup.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Step 1: Check if database exists, create if not
            database_name = self.db.config['database']
            
            if not self.db.database_exists(database_name):
                logger.info(f"Database '{database_name}' does not exist, creating...")
                if not self.db.create_database(database_name):
                    logger.error(f"Failed to create database '{database_name}'")
                    return False
            else:
                logger.info(f"Database '{database_name}' already exists")
            
            # Step 2: Check if tables exist
            if not self.check_tables_exist():
                logger.info("Required tables missing, initializing schema...")
                if not self.execute_schema_file():
                    logger.error("Failed to initialize schema")
                    return False
            else:
                logger.info("All required tables exist")
            
            # Step 3: Verify schema integrity
            if not self.verify_schema():
                logger.warning("Schema verification found issues, but continuing...")
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def check_tables_exist(self) -> bool:
        """
        Check if all required tables exist in the database.
        
        Returns:
            True if all required tables exist, False otherwise
        """
        try:
            missing_tables = []
            
            for table_name in self.required_tables:
                if not self.db.table_exists(table_name):
                    missing_tables.append(table_name)
            
            if missing_tables:
                logger.info(f"Missing tables: {', '.join(missing_tables)}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking tables: {e}")
            return False
    
    def execute_schema_file(self) -> bool:
        """
        Execute the schema.sql file to create tables.
        
        Returns:
            True if schema execution successful, False otherwise
        """
        try:
            # Check if schema file exists
            if not self.schema_file.exists():
                logger.error(f"Schema file not found: {self.schema_file}")
                return False
            
            # Read schema file
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Split into individual statements (separated by semicolons)
            statements = self._split_sql_statements(schema_sql)
            
            # Execute each statement
            connection = self.db.get_connection()
            executed_count = 0
            
            for statement in statements:
                statement = statement.strip()
                if not statement:
                    continue
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(statement)
                    executed_count += 1
                except pymysql.Error as e:
                    logger.error(f"Error executing statement: {e}")
                    logger.error(f"Statement: {statement[:100]}...")
                    # Continue with other statements
            
            connection.commit()
            logger.info(f"Schema file executed successfully ({executed_count} statements)")
            return True
            
        except Exception as e:
            logger.error(f"Error executing schema file: {e}")
            return False
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """
        Split SQL file into individual statements.
        Handles comments and multi-line statements.
        
        Args:
            sql: SQL file content
            
        Returns:
            List of SQL statements
        """
        statements = []
        current_statement = []
        in_comment = False
        
        for line in sql.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Handle multi-line comments
            if line.startswith('/*'):
                in_comment = True
            if '*/' in line:
                in_comment = False
                continue
            if in_comment:
                continue
            
            # Skip single-line comments
            if line.startswith('--'):
                continue
            
            # Add line to current statement
            current_statement.append(line)
            
            # Check if statement is complete (ends with semicolon)
            if line.endswith(';'):
                statement = ' '.join(current_statement)
                statements.append(statement)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statement = ' '.join(current_statement)
            if statement.strip():
                statements.append(statement)
        
        return statements
    
    def verify_schema(self) -> bool:
        """
        Verify that all required tables exist and have expected structure.
        
        Returns:
            True if schema is valid, False otherwise
        """
        try:
            all_valid = True
            
            for table_name in self.required_tables:
                if not self.db.table_exists(table_name):
                    logger.error(f"Required table '{table_name}' does not exist")
                    all_valid = False
                else:
                    logger.debug(f"Table '{table_name}' verified")
            
            return all_valid
            
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[dict]:
        """
        Get column information for a table.
        Useful for debugging and verification.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries with column information
        """
        try:
            query = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    COLUMN_DEFAULT,
                    EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """
            
            results = self.db.execute_query(
                query,
                (self.db.config['database'], table_name)
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return []
    
    def drop_all_tables(self) -> bool:
        """
        Drop all tables in the database.
        WARNING: This will delete all data!
        Use only for testing or reset purposes.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning("Dropping all tables - THIS WILL DELETE ALL DATA!")
            
            connection = self.db.get_connection()
            
            # Disable foreign key checks temporarily
            with connection.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Drop tables in reverse order to handle dependencies
            for table_name in reversed(self.required_tables):
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                    logger.info(f"Dropped table '{table_name}'")
                except pymysql.Error as e:
                    logger.error(f"Error dropping table '{table_name}': {e}")
            
            # Re-enable foreign key checks
            with connection.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            connection.commit()
            logger.info("All tables dropped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            return False
    
    def reset_database(self) -> bool:
        """
        Reset the database by dropping and recreating all tables.
        WARNING: This will delete all data!
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning("Resetting database - THIS WILL DELETE ALL DATA!")
            
            # Drop all tables
            if not self.drop_all_tables():
                return False
            
            # Recreate tables
            if not self.execute_schema_file():
                return False
            
            logger.info("Database reset completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False


def initialize_database(db_connection) -> bool:
    """
    Convenience function to initialize database schema.
    
    Args:
        db_connection: DatabaseConnection instance
        
    Returns:
        True if initialization successful, False otherwise
    """
    schema_manager = SchemaManager(db_connection)
    return schema_manager.initialize_database()
