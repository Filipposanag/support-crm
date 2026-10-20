# -*- coding: utf-8 -*-
"""
Database migration manager.
Automatically applies pending migrations on application startup.
"""

import logging
from pathlib import Path
from typing import List, Dict
import sys

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database migrations.
    Automatically detects and applies pending migrations.
    """
    
    def __init__(self, db_connection):
        """
        Initialize migration manager.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
        
        # Determine migrations directory based on whether we're frozen or not
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.migrations_dir = Path(sys._MEIPASS) / 'db' / 'migrations'
        else:
            # Running as script
            self.migrations_dir = Path(__file__).parent / 'migrations'
    
    def ensure_migrations_table(self) -> bool:
        """
        Ensure the schema_migrations table exists.
        
        Returns:
            True if table exists or was created successfully
        """
        try:
            # Check if table exists
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'schema_migrations'
                """)
                result = cursor.fetchone()
                
                if result and result['count'] > 0:
                    logger.debug("schema_migrations table already exists")
                    return True
            
            logger.info("Creating schema_migrations table...")
            
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INT PRIMARY KEY COMMENT 'Migration version number',
                    description VARCHAR(255) NOT NULL COMMENT 'Migration description',
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When migration was applied',
                    INDEX idx_schema_migrations_applied (applied_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Database migration tracking'
            """
            
            with connection.cursor() as cursor:
                cursor.execute(create_table_sql)
            connection.commit()
            
            logger.info("schema_migrations table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating schema_migrations table: {e}")
            return False
    
    def get_applied_migrations(self) -> List[int]:
        """
        Get list of already applied migration versions.
        
        Returns:
            List of migration version numbers
        """
        try:
            query = "SELECT version FROM schema_migrations ORDER BY version"
            results = self.db.execute_query(query)
            return [row['version'] for row in results]
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Dict]:
        """
        Get list of pending migrations that need to be applied.
        
        Returns:
            List of dictionaries with migration info (version, file_path, description)
        """
        try:
            # Get applied migrations
            applied = set(self.get_applied_migrations())
            logger.debug(f"Applied migrations: {sorted(applied)}")
            
            # Get all migration files
            if not self.migrations_dir.exists():
                logger.warning(f"Migrations directory not found: {self.migrations_dir}")
                return []
            
            pending = []
            
            for file_path in sorted(self.migrations_dir.glob('*.sql')):
                # Extract version number from filename (e.g., 012_fix_subscription_amounts.sql)
                filename = file_path.stem
                try:
                    version = int(filename.split('_')[0])
                except (ValueError, IndexError):
                    logger.warning(f"Invalid migration filename format: {filename}")
                    continue
                
                # Check if already applied
                if version in applied:
                    logger.debug(f"Skipping already applied migration {version}")
                    continue
                
                # Extract description from filename
                description = '_'.join(filename.split('_')[1:]).replace('_', ' ').title()
                
                pending.append({
                    'version': version,
                    'file_path': file_path,
                    'description': description
                })
            
            # Sort by version
            pending.sort(key=lambda x: x['version'])
            
            logger.debug(f"Pending migrations: {[m['version'] for m in pending]}")
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending migrations: {e}")
            return []

    def apply_migration(self, migration: Dict) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration: Dictionary with migration info (version, file_path, description)
            
        Returns:
            True if migration applied successfully
        """
        version = migration['version']
        file_path = migration['file_path']
        description = migration['description']
        
        try:
            logger.info(f"Applying migration {version}: {description}")
            
            # Read migration file
            with open(file_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # Split into statements
            statements = self._split_sql_statements(migration_sql)
            
            # Execute each statement
            connection = self.db.get_connection()
            
            # Increase timeouts for long-running ALTER TABLE statements
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION wait_timeout = 300")  # 5 minutes
                cursor.execute("SET SESSION interactive_timeout = 300")
                cursor.execute("SET SESSION lock_wait_timeout = 120")  # 2 minutes for locks
            
            for statement in statements:
                statement = statement.strip()
                if not statement:
                    continue
                
                # Skip the INSERT INTO schema_migrations statement if present
                # (we'll add it ourselves)
                if 'INSERT INTO schema_migrations' in statement.upper():
                    continue
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(statement)
                except Exception as e:
                    error_str = str(e)
                    # Handle MariaDB/MySQL "Duplicate column" errors gracefully
                    # Error code 1060 = Duplicate column name
                    if '1060' in error_str or 'Duplicate column' in error_str:
                        logger.warning(f"Column already exists, skipping: {statement[:80]}...")
                        continue
                    # Handle "Column already exists" for ADD COLUMN
                    if 'ADD COLUMN' in statement.upper() and ('already exists' in error_str.lower() or '1060' in error_str):
                        logger.warning(f"Column already exists, skipping: {statement[:80]}...")
                        continue
                    logger.error(f"Error executing migration statement: {e}")
                    logger.error(f"Statement: {statement[:200]}...")
                    raise
            
            # Record migration as applied (use INSERT IGNORE to avoid duplicates)
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT IGNORE INTO schema_migrations (version, description) VALUES (%s, %s)",
                    (version, description)
                )
            
            connection.commit()
            
            logger.info(f"Migration {version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migration {version}: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return False
    
    def apply_all_pending(self) -> bool:
        """
        Apply all pending migrations.
        
        Returns:
            True if all migrations applied successfully
        """
        try:
            # Ensure migrations table exists
            if not self.ensure_migrations_table():
                return False
            
            # Get pending migrations
            pending = self.get_pending_migrations()
            
            if not pending:
                logger.info("No pending migrations")
                return True
            
            logger.info(f"Found {len(pending)} pending migration(s)")
            
            # Apply each migration
            for migration in pending:
                if not self.apply_migration(migration):
                    logger.error(f"Failed to apply migration {migration['version']}, stopping")
                    return False
            
            logger.info(f"Successfully applied {len(pending)} migration(s)")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """
        Split SQL file into individual statements.
        Handles comments, multi-line statements, and DELIMITER changes.
        
        Args:
            sql: SQL file content
            
        Returns:
            List of SQL statements
        """
        statements = []
        current_statement = []
        in_comment = False
        delimiter = ';'
        
        lines = sql.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            # Skip empty lines
            if not line:
                continue
            
            # Handle DELIMITER changes
            if line.upper().startswith('DELIMITER'):
                parts = line.split()
                if len(parts) >= 2:
                    delimiter = parts[1]
                continue
            
            # Handle multi-line comments
            if line.startswith('/*'):
                in_comment = True
            if in_comment:
                if line.endswith('*/'):
                    in_comment = False
                continue
            
            # Skip single-line comments
            if line.startswith('--') or line.startswith('#'):
                continue
            
            # Add line to current statement
            current_statement.append(line)
            
            # Check if statement is complete (ends with current delimiter)
            # For custom delimiters like $, check if line ends with it
            if delimiter != ';':
                # Check if line ends with the delimiter
                if line.endswith(delimiter):
                    statement = ' '.join(current_statement)
                    # Remove the delimiter from the end
                    statement = statement[:-len(delimiter)].strip()
                    if statement:
                        statements.append(statement)
                    current_statement = []
            else:
                # Standard semicolon delimiter
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
