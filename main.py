#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support CRM - Main Application Entry Point

This module initializes and runs the Support CRM desktop application.
It handles:
- Application initialization
- Configuration loading
- Database connection setup
- Logging configuration
- Stylesheet loading
- Main window creation
"""

import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

import config
from db.connection import DatabaseConnection
from db.schema_manager import SchemaManager
from ui.main_window import MainWindow
from ui.i18n import get_translation_manager


def setup_logging():
    """
    Configure application logging with file rotation.
    Logs are written to logs/app.log with rotation at 10MB.
    """
    # Ensure logs directory exists
    log_dir = config.LOGGING_CONFIG['log_file'].parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(config.LOGGING_CONFIG['log_level'])
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        config.LOGGING_CONFIG['log_file'],
        maxBytes=config.LOGGING_CONFIG['max_bytes'],
        backupCount=config.LOGGING_CONFIG['backup_count'],
        encoding='utf-8'
    )
    
    # Create console handler for errors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.ERROR)
    
    # Create formatter
    formatter = logging.Formatter(
        config.LOGGING_CONFIG['format'],
        datefmt=config.LOGGING_CONFIG['date_format']
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info("=" * 60)
    logging.info("Support CRM Application Starting")
    logging.info("=" * 60)


def load_stylesheet(app: QApplication) -> bool:
    """
    Load and apply QSS stylesheet to the application.
    
    Args:
        app: QApplication instance
        
    Returns:
        True if stylesheet loaded successfully, False otherwise
    """
    try:
        # Path to stylesheet
        qss_file = Path(__file__).parent / 'resources' / 'qss' / 'style.qss'
        
        if not qss_file.exists():
            logging.warning(f"Stylesheet file not found: {qss_file}")
            return False
        
        # Read stylesheet content
        with open(qss_file, 'r', encoding='utf-8') as f:
            stylesheet = f.read()
        
        # Apply stylesheet to application
        app.setStyleSheet(stylesheet)
        
        logging.info(f"Stylesheet loaded successfully from: {qss_file}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to load stylesheet: {e}")
        return False


def initialize_database() -> DatabaseConnection:
    """
    Initialize database connection and schema.
    
    Returns:
        DatabaseConnection instance
        
    Raises:
        Exception: If database connection or initialization fails
    """
    try:
        # Create database connection
        db_connection = DatabaseConnection(config.DATABASE_CONFIG)
        
        # Test connection
        if not db_connection.test_connection():
            raise Exception("Database connection test failed")
        
        logging.info("Database connection established successfully")
        
        # Initialize schema if needed
        schema_manager = SchemaManager(db_connection)
        if schema_manager.initialize_database():
            logging.info("Database schema initialized successfully")
        else:
            logging.warning("Database schema initialization had issues")
        
        # Run migrations automatically
        from db.migration_manager import MigrationManager
        migration_manager = MigrationManager(db_connection)
        if migration_manager.apply_all_pending():
            logging.info("Database migrations applied successfully")
        else:
            logging.warning("Some migrations may not have been applied")
        
        return db_connection
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise


def show_startup_error(title: str, message: str) -> bool:
    """
    Show error message dialog on startup failure.
    For database errors, opens configurator dialog directly.
    
    Args:
        title: Error dialog title
        message: Error message to display
        
    Returns:
        True if user configured database, False otherwise
    """
    # Create minimal QApplication if not exists
    if not QApplication.instance():
        app = QApplication(sys.argv)
    
    # For database connection errors, open configurator directly
    if "MariaDB Connection Error" in title or "Database Connection Error" in title:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("MariaDB Configuration Required")
        msg_box.setText(
            "Cannot connect to MariaDB database.\n\n"
            "Would you like to configure the database connection now?"
        )
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        result = msg_box.exec()
        
        if result == QMessageBox.Yes:
            # Open configurator dialog directly (embedded in main app)
            try:
                from configurator.db_configurator_window import DBConfiguratorWindow
                
                configurator = DBConfiguratorWindow()
                configurator.exec()  # Modal dialog
                
                # Return True to indicate user may have configured database
                return True
            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Error",
                    f"Failed to open configurator:\n\n{str(e)}"
                )
                return False
        else:
            return False
    else:
        QMessageBox.critical(None, title, message)
        return False


def main():
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Setup logging first
        setup_logging()
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Show splash screen
        from ui.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.show()
        splash.update_progress(10, "Αρχικοποίηση εφαρμογής...")
        app.processEvents()
        
        # Set application icon
        from utils.resource_loader import app_icon
        app.setWindowIcon(app_icon())
        
        # Set application metadata
        app.setApplicationName(config.APP_SETTINGS['app_name'])
        app.setOrganizationName(config.APP_SETTINGS['organization'])
        app.setApplicationVersion(config.APP_VERSION)
        
        splash.update_progress(20, "Ρύθμιση περιβάλλοντος...")
        app.processEvents()
        
        # Note: High DPI scaling is enabled by default in PySide6
        # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps (deprecated)
        
        logging.info(f"Application: {config.APP_SETTINGS['app_name']} v{config.APP_VERSION}")
        
        # Prevent Windows dark mode from overriding our styles
        # Use Fusion style for consistent cross-platform appearance
        from PySide6.QtGui import QPalette, QColor
        app.setStyle("Fusion")
        
        # Set custom light palette to prevent dark mode interference
        light_palette = QPalette()
        light_palette.setColor(QPalette.Window, QColor("#FAFAFA"))
        light_palette.setColor(QPalette.WindowText, QColor("#212121"))
        light_palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        light_palette.setColor(QPalette.AlternateBase, QColor("#F5F5F5"))
        light_palette.setColor(QPalette.Text, QColor("#212121"))
        light_palette.setColor(QPalette.Button, QColor("#FFFFFF"))
        light_palette.setColor(QPalette.ButtonText, QColor("#212121"))
        light_palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        light_palette.setColor(QPalette.Highlight, QColor("#2196F3"))
        light_palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        app.setPalette(light_palette)
        
        logging.info("Fusion style and custom palette applied to prevent dark mode override")
        
        splash.update_progress(30, "Φόρτωση στυλ...")
        app.processEvents()
        
        # Load and apply stylesheet
        stylesheet_loaded = load_stylesheet(app)
        if not stylesheet_loaded:
            logging.warning("Application will run without custom stylesheet")
        
        # Minimal spinbox/dateedit styling - no padding to preserve default arrows
        spinbox_style = """
QSpinBox, QDoubleSpinBox {
    min-width: 80px;
    min-height: 28px;
}

QDateEdit {
    min-width: 110px;
    min-height: 28px;
}
"""
        app.setStyleSheet(app.styleSheet() + spinbox_style)
        logging.info("Minimal SpinBox and DateEdit styling applied")
        
        # Add global table styling for consistent layout (excluding calendar)
        table_style = """
QTableView {
    border: none;
    gridline-color: #d0d0d0;
    font-size: 13px;
    alternate-background-color: #fafafa;
}

QHeaderView::section {
    padding: 8px 10px;
    font-size: 13px;
}

QTableView::item {
    padding-left: 10px;
    padding-right: 10px;
    padding-top: 6px;
    padding-bottom: 6px;
}

/* Reset calendar table styling to prevent display issues */
QCalendarWidget QTableView {
    background-color: #FFFFFF;
    border: none;
    gridline-color: #E0E0E0;
    font-size: inherit;
    alternate-background-color: #FFFFFF;
}

QCalendarWidget QHeaderView::section {
    background-color: #F5F5F5;
    padding: 3px;
    font-size: inherit;
}

QCalendarWidget QTableView::item {
    padding: 2px;
    color: #212121;
}
"""
        app.setStyleSheet(app.styleSheet() + table_style)
        logging.info("Global table styling applied")
        
        splash.update_progress(40, "Φόρτωση γλώσσας...")
        app.processEvents()
        
        # Initialize translation manager with default language
        tr_manager = get_translation_manager()
        tr_manager.set_language(config.UI_SETTINGS['default_language'])
        logging.info(f"Default language set to: {config.UI_SETTINGS['default_language']}")
        
        splash.update_progress(50, "Σύνδεση με βάση δεδομένων...")
        app.processEvents()
        
        # Initialize database
        try:
            db_connection = initialize_database()
            splash.update_progress(70, "Βάση δεδομένων έτοιμη...")
        except Exception as e:
            # Convert exception to string safely (handle encoding issues)
            try:
                error_detail = str(e).encode('ascii', 'ignore').decode('ascii')
            except:
                try:
                    error_detail = str(e)
                except:
                    error_detail = "Database connection test failed"
            
            error_msg = f"Connection Details:\n"
            error_msg += f"Host: {config.DATABASE_CONFIG['host']}\n"
            error_msg += f"Port: {config.DATABASE_CONFIG['port']}\n"
            error_msg += f"Database: {config.DATABASE_CONFIG['database']}\n\n"
            error_msg += f"Error: {error_detail}\n\n"
            error_msg += "Please check:\n"
            error_msg += "• MariaDB service is running\n"
            error_msg += "• Database credentials are correct\n"
            error_msg += "• Database exists and is accessible"
            
            # Close splash before showing error
            splash.close()
            
            # Keep trying until user cancels or connection succeeds
            while True:
                # Show configurator dialog
                configured = show_startup_error("MariaDB Connection Error", error_msg)
                
                if not configured:
                    # User chose not to configure
                    logging.error(f"Application startup failed due to MariaDB connection error: {error_detail}")
                    return 1
                
                # User configured database, try again
                logging.info("User configured database, retrying connection...")
                try:
                    # Reload config
                    import importlib
                    importlib.reload(config)
                    db_connection = initialize_database()
                    logging.info("Database connection successful after configuration")
                    break  # Success! Exit the loop
                except Exception as e2:
                    # Still failed, update error message and loop again
                    try:
                        error_detail = str(e2).encode('ascii', 'ignore').decode('ascii')
                    except:
                        error_detail = "Database connection test failed"
                    
                    error_msg = f"Connection Details:\n"
                    error_msg += f"Host: {config.DATABASE_CONFIG['host']}\n"
                    error_msg += f"Port: {config.DATABASE_CONFIG['port']}\n"
                    error_msg += f"Database: {config.DATABASE_CONFIG['database']}\n\n"
                    error_msg += f"Error: {error_detail}\n\n"
                    error_msg += "Please check:\n"
                    error_msg += "• MariaDB service is running\n"
                    error_msg += "• Database credentials are correct\n"
                    error_msg += "• Database exists and is accessible"
                    
                    logging.error(f"Database connection still failed: {e2}")
                    # Loop will continue and show configurator again
        
        # Apply data fixes automatically
        try:
            from db.data_fixes import apply_all_data_fixes
            
            apply_all_data_fixes(db_connection)
        except Exception as e:
            logging.warning(f"Data fixes check failed: {e}")
        
        # Auto-load license from license.json if exists and not already in database
        try:
            import json
            from pathlib import Path
            
            license_file = Path("license.json")
            
            if license_file.exists():
                # Check if license already exists in database
                settings_service = SettingsService(db_connection)
                existing_license = settings_service.get_license_info()
                
                # Only load if no license in database or license is empty
                if not existing_license.get('key') or existing_license.get('status') == 'none':
                    logging.info("Found license.json - loading into database...")
                    
                    with open(license_file, 'r', encoding='utf-8') as f:
                        license_data = json.load(f)
                    
                    # Store license in database
                    success = settings_service.update_license_info(
                        license_key=license_data['license_key'],
                        owner_name=license_data['owner_name'],
                        start_date=license_data['start_date'],
                        end_date=license_data['end_date'],
                        status='active' if license_data.get('is_active', True) else 'inactive'
                    )
                    
                    if success:
                        logging.info(f"License loaded automatically: {license_data['license_key']}")
                    else:
                        logging.warning("Failed to load license from license.json")
                else:
                    logging.debug("License already exists in database - skipping auto-load")
            else:
                logging.debug("No license.json found - will use database license or DEMO mode")
                
        except Exception as e:
            logging.warning(f"Auto-load license failed: {e}")
        
        # STRICT LICENSE VALIDATION - Required for app startup
        from services.settings_service import SettingsService
        from services.license_service import LicenseService
        from services.license_validator import check_license_status, check_offline_grace_period
        from datetime import datetime
        
        settings_service = SettingsService(db_connection)
        
        # Close splash before license dialogs
        splash.close()
        
        # License validation loop - keep trying until valid license or user exits
        while True:
            license_info = settings_service.get_license_info()
            
            # Check 1: No license at all
            if not license_info.get('key') or license_info.get('status') == 'none':
                logging.warning("No license found - activation required")
                
                from ui.widgets.license_activation_dialog import LicenseActivationDialog
                activation_dialog = LicenseActivationDialog(settings_service)
                
                if activation_dialog.exec() != QDialog.Accepted:
                    # User cancelled - exit application
                    logging.info("User cancelled license activation - exiting")
                    return 0
                
                # License activated - reload and continue loop to validate
                license_info = settings_service.get_license_info()
                continue
            
            # Check 2: License expired
            end_date = license_info['end_date']
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            days_remaining = LicenseService.calculate_days_remaining(end_date)
            
            if days_remaining < 0:
                logging.warning(f"License expired {abs(days_remaining)} days ago")
                
                tr = get_translation_manager()
                QMessageBox.critical(
                    None,
                    tr.get('license_expired_title'),
                    tr.format('license_expired_message', days=abs(days_remaining))
                )
                
                from ui.widgets.license_activation_dialog import LicenseActivationDialog
                activation_dialog = LicenseActivationDialog(settings_service)
                
                if activation_dialog.exec() != QDialog.Accepted:
                    # User cancelled - exit application
                    logging.info("User cancelled license renewal - exiting")
                    return 0
                
                # New license activated - reload and continue loop
                license_info = settings_service.get_license_info()
                continue
            
            # Check 3: Online validation every 3 days OR if expiring soon
            # Calculate days since last online validation
            last_validation = license_info.get('last_online_validation')
            days_since_validation = 999  # Default: force check if never validated
            
            if last_validation:
                if isinstance(last_validation, str):
                    last_validation = datetime.strptime(last_validation, '%Y-%m-%d %H:%M:%S')
                days_since_validation = (datetime.now() - last_validation).days
            
            # Online check required if: 3+ days since last check OR expiring soon (<=3 days)
            need_online_check = days_since_validation >= 3 or days_remaining <= 3
            
            if need_online_check:
                reason = "periodic check (3 days)" if days_since_validation >= 3 else f"expiring soon ({days_remaining} days)"
                logging.info(f"Online validation required: {reason}")
                
                validation_result = check_license_status(
                    license_key=license_info['key'],
                    validation_url=config.LICENSE_VALIDATION_CONFIG['validation_url'],
                    timeout=config.LICENSE_VALIDATION_CONFIG['timeout'],
                    api_key=config.LICENSE_VALIDATION_CONFIG.get('api_key'),
                    basic_auth=config.LICENSE_VALIDATION_CONFIG.get('basic_auth')
                )
                
                if validation_result['online']:
                    # Online validation succeeded (server responded)
                    
                    # Check if license was not found on server
                    if validation_result.get('not_found'):
                        logging.error("License not found on server")
                        tr = get_translation_manager()
                        QMessageBox.critical(
                            None,
                            tr.get('license_not_found_title'),
                            tr.get('license_not_found_message')
                        )
                        
                        from ui.widgets.license_activation_dialog import LicenseActivationDialog
                        activation_dialog = LicenseActivationDialog(settings_service)
                        
                        if activation_dialog.exec() != QDialog.Accepted:
                            logging.info("User cancelled license activation - exiting")
                            return 0
                        
                        license_info = settings_service.get_license_info()
                        continue
                    
                    if validation_result['valid']:
                        # Update license data from server
                        server_start_date = validation_result['start_date']
                        server_end_date = validation_result['end_date']
                        server_owner = validation_result['owner_name']
                        
                        logging.info("Syncing license data from server to local database")
                        settings_service.set_license(
                            license_key=license_info['key'],
                            owner=server_owner,
                            start_date=server_start_date,
                            end_date=server_end_date,
                            status='active'
                        )
                        
                        # Recalculate days remaining with server end date
                        if isinstance(server_end_date, str):
                            server_end_date = datetime.strptime(server_end_date, '%Y-%m-%d').date()
                        days_remaining = LicenseService.calculate_days_remaining(server_end_date)
                        
                        settings_service.update_license_validation_tracking(online_success=True)
                        logging.info(f"License validated online: {days_remaining} days remaining")
                        
                        # Show warning if expiring soon
                        if days_remaining <= 7 and days_remaining >= 0:
                            tr = get_translation_manager()
                            QMessageBox.warning(
                                None,
                                tr.get('license_expiring_title'),
                                tr.format('license_expiring_message', days=days_remaining)
                            )
                        
                        break  # Valid license - proceed with app startup
                    else:
                        # License invalid/expired on server - LOCK
                        logging.error(f"License invalid on server: {validation_result.get('error')}")
                        
                        tr = get_translation_manager()
                        QMessageBox.critical(
                            None,
                            tr.get('license_problem_title'),
                            tr.get('license_problem_message')
                        )
                        
                        from ui.widgets.license_activation_dialog import LicenseActivationDialog
                        activation_dialog = LicenseActivationDialog(settings_service)
                        
                        if activation_dialog.exec() != QDialog.Accepted:
                            logging.info("User cancelled license activation - exiting")
                            return 0
                        
                        license_info = settings_service.get_license_info()
                        continue
                else:
                    # No internet - block if never validated, otherwise allow with warning
                    if days_since_validation >= 999:
                        # Never validated online - must have internet
                        logging.error("Never validated online - internet required")
                        tr = get_translation_manager()
                        QMessageBox.critical(
                            None,
                            tr.get('license_problem_title'),
                            tr.get('license_problem_message')
                        )
                        
                        # Show activation dialog
                        from ui.widgets.license_activation_dialog import LicenseActivationDialog
                        activation_dialog = LicenseActivationDialog(settings_service)
                        
                        if activation_dialog.exec() != QDialog.Accepted:
                            logging.info("User cancelled license activation - exiting")
                            return 0
                        
                        license_info = settings_service.get_license_info()
                        continue
                    else:
                        # Was validated before - allow with warning
                        logging.warning(f"No internet - last validated {days_since_validation} days ago")
                        tr = get_translation_manager()
                        QMessageBox.warning(
                            None,
                            tr.get('license_offline_warning_title'),
                            tr.format('license_offline_warning_message', days=days_since_validation)
                        )
                        break  # Allow app to start
            else:
                # No online check needed - recently validated
                logging.info(f"License valid, last checked {days_since_validation} days ago - skipping online check")
                break  # Valid license - proceed with app startup
        
        # License validated - continue with app startup
        logging.info("License validation successful - starting application")
        
        # === USER AUTHENTICATION ===
        splash.update_progress(80, "Σύνδεση χρήστη...")
        app.processEvents()
        
        from services.auth_service import AuthService
        from ui.dialogs import LoginDialog
        from ui.utils import set_auth_service
        
        # Initialize auth service
        auth_service = AuthService(db_connection)
        
        # Close splash for login dialog
        splash.close()
        
        # Show login dialog
        login_dialog = LoginDialog(auth_service)
        if login_dialog.exec() != QDialog.Accepted:
            logging.info("User cancelled login - exiting")
            return 0
        
        # Set global auth service for permission checks
        set_auth_service(auth_service)
        logging.info(f"User logged in: {auth_service.current_user.username}")
        
        # Re-show splash for remaining startup
        from ui.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.show()
        
        splash.update_progress(90, "Δημιουργία κύριου παραθύρου...")
        app.processEvents()
        
        # Create and show main window (pass auth_service)
        main_window = MainWindow(db_connection, auth_service)
        
        splash.update_progress(100, "Έτοιμο!")
        app.processEvents()
        
        # Close splash and show main window
        splash.finish(main_window)
        main_window.show()
        
        logging.info("Main window displayed - application ready")
        
        # Check for updates on startup if enabled
        try:
            settings = settings_service.load_settings()
            if settings and settings.auto_check_updates:
                # Use QTimer to check after UI is fully loaded
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, lambda: main_window.check_for_updates_on_startup())
                logging.info("Auto-check for updates scheduled")
        except Exception as e:
            logging.error(f"Failed to schedule auto-update check: {e}")
        
        # Run application event loop
        exit_code = app.exec()
        
        logging.info(f"Application exiting with code: {exit_code}")
        logging.info("=" * 60)
        
        return exit_code
        
    except Exception as e:
        logging.exception(f"Unexpected error during application startup: {e}")
        # Close splash if it exists
        try:
            if 'splash' in locals():
                splash.close()
        except:
            pass
        show_startup_error(
            "Application Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the log file for details."
        )
        return 1


if __name__ == '__main__':
    sys.exit(main())
