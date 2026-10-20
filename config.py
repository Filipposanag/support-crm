"""
Configuration module for Support CRM application.
Loads settings from environment variables and provides default values.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory (PyInstaller compatible)
def get_base_dir() -> Path:
    """Get base directory for bundled resources, works for both dev and PyInstaller builds."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return Path(sys._MEIPASS)
    except AttributeError:
        # Running in normal Python environment
        return Path(__file__).resolve().parent

def get_config_dir() -> Path:
    """Get directory for config files (writable location)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use install directory for config
        return Path(sys.executable).parent
    else:
        # Running in development mode
        return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
CONFIG_DIR = get_config_dir()

# Document output directories (invoices / receipts)
# Kept next to the app config (install dir when frozen, project root in dev).
INVOICES_DIR = CONFIG_DIR / 'Τιμολόγια'
RECEIPTS_DIR = CONFIG_DIR / 'Αποδείξεις'
# Automatic database backups are stored here
BACKUPS_DIR = CONFIG_DIR / 'Αντίγραφα Ασφαλείας'


def ensure_document_dirs():
    """Create the invoice/receipt output folders if missing.

    Returns (invoices_dir, receipts_dir) as Path objects.
    """
    try:
        INVOICES_DIR.mkdir(parents=True, exist_ok=True)
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return INVOICES_DIR, RECEIPTS_DIR


def ensure_backup_dir():
    """Create the automatic-backups folder if missing. Returns the Path."""
    try:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return BACKUPS_DIR

# Database Configuration
# Try to load from db_config.json first (created by configurator)
# Fall back to environment variables if not found
def _load_db_config():
    """Load database configuration from db_config.json or environment variables."""
    config_file = CONFIG_DIR / 'config' / 'db_config.json'
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    'host': config.get('host', 'localhost'),
                    'port': config.get('port', 3306),
                    'user': config.get('user', 'root'),
                    'password': config.get('password', ''),
                    'database': config.get('database', 'supportcrm'),
                    'charset': 'utf8mb4',
                    'autocommit': False,
                }
        except Exception:
            pass  # Fall back to environment variables
    
    # Use environment variables as fallback
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'supportcrm'),
        'charset': 'utf8mb4',
        'autocommit': False,
    }

DATABASE_CONFIG = _load_db_config()

# CSV Import Settings
CSV_SETTINGS = {
    'encoding': 'cp1253',
    'fallback_encodings': ['latin1', 'utf-8'],
    'delimiter': ';',
    'batch_size': 500,  # Records per commit
    'preview_rows': 10,  # Rows to show in preview
}

# UI Settings
UI_SETTINGS = {
    'default_language': os.getenv('DEFAULT_LANGUAGE', 'el'),  # 'el' or 'en'
    'window_title': 'Support CRM',
    'window_width': 1280,
    'window_height': 800,
    'page_size': 100,  # Records per page in tables
    'filter_debounce_ms': 500,  # Milliseconds to wait before applying filters
    'theme': 'modern',  # UI theme
}

# Logging Configuration
LOGGING_CONFIG = {
    'log_file': BASE_DIR / 'logs' / 'app.log',
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),  # DEBUG, INFO, WARNING, ERROR
    'max_bytes': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5,  # Keep 5 backup files
    'format': '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
}

# Application Settings
APP_VERSION = "3.0.0"  # Centralized version constant - Support CRM

APP_SETTINGS = {
    'version': APP_VERSION,
    'organization': 'Support CRM',
    'app_name': 'SupportCRM',
}

# Update Checker Settings
UPDATE_CHECKER_CONFIG = {
    'update_url': 'https://example.com/downloads/update.json',  # Update server URL
    'timeout': 5,  # seconds
}

# License Validation Settings
LICENSE_VALIDATION_CONFIG = {
    'validation_url': 'https://pcp.com.gr/licenses/{key}.json',  # {key} will be replaced with license key
    'timeout': 10,  # seconds - increased for slower connections
    'require_online': True,  # ALWAYS require online validation - no offline mode
    # Security - No API key needed for direct JSON access
    'api_key': None,
    'basic_auth': None,
}

# Resource Paths
RESOURCES_DIR = BASE_DIR / 'resources'
ICONS_DIR = RESOURCES_DIR / 'icons'
QSS_FILE = RESOURCES_DIR / 'qss' / 'style.qss'

# Performance Settings
PERFORMANCE_SETTINGS = {
    'query_timeout': 30,  # seconds
    'import_progress_interval': 100,  # Update progress every N records
    'max_search_results': 1000,  # Maximum results to return in searches
}
