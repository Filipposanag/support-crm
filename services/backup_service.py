# -*- coding: utf-8 -*-
"""
Backup Service - MariaDB/MySQL database backup and restore functionality.
"""

import logging
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BackupService:
    """Service for creating and restoring MariaDB/MySQL database backups."""
    
    def __init__(self, db_config: dict):
        """
        Initialize BackupService.
        
        Args:
            db_config: Database configuration dictionary with keys:
                - host: Database host
                - port: Database port
                - user: Database user
                - password: Database password
                - database: Database name
        """
        self.db_config = db_config
        self.host = db_config.get('host', 'localhost')
        self.port = db_config.get('port', 3306)
        self.user = db_config.get('user', 'root')
        self.password = db_config.get('password', '')
        self.database = db_config.get('database', 'supportcrm')
        
        logger.info(f"BackupService initialized for database: {self.database}")
    
    def _find_tool(self, *exe_names) -> str:
        """Locate a MariaDB/MySQL client tool.

        Tries each candidate name in PATH, then globs common Windows install
        roots for ANY installed version (MariaDB 10.x/11.x incl. mariadb-dump,
        MySQL Server 5.x-8.x, XAMPP, WAMP, Laragon). Falls back to the first
        bare name so the OS PATH still gets a chance at exec time.
        """
        import shutil
        import glob as _glob
        # 1) PATH
        for name in exe_names:
            found = shutil.which(name)
            if found:
                logger.info(f"Found {name} in PATH: {found}")
                return found
        # 2) Glob common install roots (any version)
        roots = [
            r"C:\Program Files\MariaDB*\bin",
            r"C:\Program Files (x86)\MariaDB*\bin",
            r"C:\Program Files\MySQL\MySQL Server*\bin",
            r"C:\Program Files (x86)\MySQL\MySQL Server*\bin",
            r"C:\xampp\mysql\bin",
            r"C:\wamp64\bin\mariadb\mariadb*\bin",
            r"C:\wamp64\bin\mysql\mysql*\bin",
            r"C:\laragon\bin\mysql\*\bin",
        ]
        for root in roots:
            for d in _glob.glob(root):
                for name in exe_names:
                    cand = Path(d) / f"{name}.exe"
                    if cand.exists():
                        logger.info(f"Found {name} at: {cand}")
                        return str(cand)
        logger.warning(f"Tool {exe_names} not found in PATH or common dirs; using '{exe_names[0]}'")
        return exe_names[0]

    def _find_mysqldump(self) -> str:
        """Find mysqldump / mariadb-dump."""
        return self._find_tool('mysqldump', 'mariadb-dump')

    def _find_mysql(self) -> str:
        """Find mysql / mariadb client."""
        return self._find_tool('mysql', 'mariadb')

    def _pymysql_connect(self, with_db: bool = True):
        """Open a direct pymysql connection (tuple cursor) using the app's driver."""
        import pymysql
        params = dict(
            host=self.host,
            port=int(self.port),
            user=self.user,
            password=self.password,
            charset='utf8mb4',
            autocommit=False,
        )
        if with_db:
            params['database'] = self.database
        return pymysql.connect(**params)

    def create_backup(self, dst_path: str) -> bool:
        """Create a full .sql backup using pure Python (pymysql) — no external tools.

        Avoids Windows application-control policies (WinError 4551) that block
        mysqldump.exe. Writes DROP+CREATE+INSERT for every base table (+ views).
        """
        try:
            dst = Path(dst_path)
            dst.parent.mkdir(parents=True, exist_ok=True)

            conn = self._pymysql_connect(with_db=True)
            try:
                with conn.cursor() as cur:
                    cur.execute("SHOW FULL TABLES")
                    rows = cur.fetchall()
                    base_tables = [r[0] for r in rows if (len(r) < 2 or r[1] == 'BASE TABLE')]
                    views = [r[0] for r in rows if len(r) >= 2 and r[1] == 'VIEW']

                    with open(dst, 'w', encoding='utf-8') as f:
                        f.write("-- Support CRM backup\n")
                        f.write(f"-- Database: {self.database}\n")
                        f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("SET NAMES utf8mb4;\n")
                        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

                        for t in base_tables:
                            cur.execute(f"SHOW CREATE TABLE `{t}`")
                            create_sql = cur.fetchone()[1]
                            f.write(f"DROP TABLE IF EXISTS `{t}`;\n")
                            f.write(create_sql + ";\n\n")

                            # Exclude generated/computed columns (cannot be INSERTed — error 1906)
                            cur.execute(
                                "SELECT COLUMN_NAME, EXTRA FROM information_schema.COLUMNS "
                                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
                                "ORDER BY ORDINAL_POSITION",
                                (self.database, t))
                            colinfo = cur.fetchall()
                            insert_cols = [r[0] for r in colinfo
                                           if 'GENERATED' not in (str(r[1] or '')).upper()]
                            if insert_cols:
                                cols_sql = ", ".join(f"`{c}`" for c in insert_cols)
                                select_sql = ", ".join(f"`{c}`" for c in insert_cols)
                                cur.execute(f"SELECT {select_sql} FROM `{t}`")
                                data = cur.fetchall()
                                if data:
                                    for drow in data:
                                        vals = ", ".join(conn.escape(v) for v in drow)
                                        f.write(f"INSERT INTO `{t}` ({cols_sql}) VALUES ({vals});\n")
                                    f.write("\n")

                        for v in views:
                            try:
                                cur.execute(f"SHOW CREATE VIEW `{v}`")
                                create_view = cur.fetchone()[1]
                                f.write(f"DROP VIEW IF EXISTS `{v}`;\n")
                                f.write(create_view + ";\n\n")
                            except Exception as _ve:
                                logger.warning(f"Skipping view {v}: {_ve}")

                        f.write("SET FOREIGN_KEY_CHECKS=1;\n")
                logger.info(f"Backup created successfully (python): {dst}")
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to create backup: {e}", exc_info=True)
            return False

    def restore_backup(self, src_path: str, db_connection=None) -> bool:
        """Restore a .sql backup using pure Python (pymysql) — no external tools.

        Creates the database if missing, then executes the script statement by
        statement. Works with backups produced by create_backup and with plain
        mysqldump .sql files.
        """
        try:
            src = Path(src_path)
            if not src.exists():
                logger.error(f"Backup file not found: {src}")
                return False

            # Close the app's live connection first (avoid locks during DDL)
            if db_connection:
                try:
                    db_connection.close()
                    logger.info("Database connection closed before restore")
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

            # Ensure the target database exists (covers "everything was deleted")
            try:
                root = self._pymysql_connect(with_db=False)
                with root.cursor() as c:
                    c.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
                    )
                root.commit()
                root.close()
            except Exception as ce:
                logger.warning(f"Could not pre-create database before restore: {ce}")

            with open(src, 'r', encoding='utf-8') as f:
                script = f.read()

            # Split into individual statements (backups use ';\n' as terminator)
            raw_statements = script.split(";\n")
            conn = self._pymysql_connect(with_db=True)
            try:
                with conn.cursor() as cur:
                    for raw in raw_statements:
                        # drop comment-only lines, keep the SQL
                        lines = [ln for ln in raw.splitlines()
                                 if not ln.strip().startswith('--')]
                        stmt = "\n".join(lines).strip()
                        if not stmt:
                            continue
                        cur.execute(stmt)
                conn.commit()
                logger.info(f"Database restored (python) from: {src}")
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return False

    def auto_backup(self, max_keep: int = 30):
        """Create a timestamped backup in the app backups folder; prune old ones.

        Returns the backup file path on success, else None. Never raises.
        """
        try:
            from config import ensure_backup_dir
            backup_dir = ensure_backup_dir()
        except Exception as e:
            logger.error(f"Backup folder unavailable: {e}")
            return None
        ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        dst = Path(backup_dir) / f"{self.database}_{ts}.sql"
        try:
            if self.create_backup(str(dst)):
                self._prune_backups(backup_dir, max_keep)
                logger.info(f"Automatic backup created: {dst}")
                return str(dst)
        except Exception as e:
            logger.error(f"Automatic backup failed: {e}", exc_info=True)
        return None

    def _prune_backups(self, backup_dir, max_keep: int = 30):
        """Keep only the newest `max_keep` automatic backups for this database."""
        try:
            files = sorted(
                Path(backup_dir).glob(f"{self.database}_*.sql"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in files[max_keep:]:
                try:
                    old.unlink()
                    logger.info(f"Pruned old backup: {old.name}")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Backup prune failed: {e}")

    def has_backup_today(self) -> bool:
        """True if an automatic backup already exists for today (this database)."""
        try:
            from config import BACKUPS_DIR
            today = datetime.now().strftime('%Y-%m-%d')
            return any(Path(BACKUPS_DIR).glob(f"{self.database}_{today}_*.sql"))
        except Exception:
            return False

    def get_suggested_backup_name(self) -> str:
        """
        Get a suggested backup filename with timestamp.
        
        Returns:
            Suggested backup filename
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.database}_backup_{timestamp}.sql"
