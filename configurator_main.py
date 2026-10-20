#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support CRM Configurator - Main Entry Point

Standalone configuration tool for:
- Database connection setup
- Schema initialization
- Default app_settings creation
"""

import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication

from configurator.db_configurator_window import DBConfiguratorWindow


def setup_logging():
    """Configure logging for configurator."""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = RotatingFileHandler(
        log_dir / 'configurator.log',
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info("=" * 60)
    logging.info("Support CRM Configurator Starting")
    logging.info("=" * 60)


def main():
    """Main entry point for configurator."""
    try:
        # Setup logging
        setup_logging()
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Support CRM Configurator")
        app.setOrganizationName("Support")
        
        # Create and show DB configurator window
        window = DBConfiguratorWindow()
        window.show()
        
        logging.info("DB Configurator window displayed")
        
        # Run application
        exit_code = app.exec()
        
        logging.info(f"Configurator exiting with code: {exit_code}")
        logging.info("=" * 60)
        
        return exit_code
        
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
