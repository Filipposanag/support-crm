# -*- coding: utf-8 -*-
"""
Configuration Service for managing database connection settings.
Handles reading/writing db_config.json file.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_app_root() -> Path:
    """Get application root directory, works for both dev and PyInstaller builds."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        # For config files, we want to write to the actual install directory, not _MEIPASS
        return Path(sys.executable).parent
    else:
        # Running in development mode
        return Path(__file__).resolve().parent.parent


class ConfigService:
    """Service for managing database configuration file."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize ConfigService.
        
        Args:
            config_path: Path to config file (default: config/db_config.json)
        """
        if config_path is None:
            base_dir = get_app_root()
            config_path = base_dir / 'config' / 'db_config.json'
        
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, any]:
        """
        Load database configuration from file.
        
        Returns:
            Dictionary with database configuration
        """
        default_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '',
            'database': 'supportcrm'
        }
        
        if not self.config_path.exists():
            logger.info(f"Config file not found, using defaults: {self.config_path}")
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default_config
    
    def save_config(self, config: Dict[str, any]) -> bool:
        """
        Save database configuration to file.
        
        Args:
            config: Dictionary with database configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
