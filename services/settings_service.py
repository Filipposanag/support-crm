# -*- coding: utf-8 -*-
"""
Settings Service for main CRM application.
Provides access to organization and PDF settings from app_settings table.
"""

import logging
import json
from typing import Optional
from dataclasses import dataclass, asdict, field
from db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """Application settings data class."""
    org_name: str = ''
    org_short_name: str = ''
    org_address: str = ''
    org_city: str = ''
    org_postal_code: str = ''
    org_phone: str = ''
    org_email: str = ''
    org_afm: str = ''  # ΑΦΜ - Αριθμός Φορολογικού Μητρώου
    # Invoicing / VAT
    vat_rate: float = 24.0  # Default VAT % for documents (0 = no VAT breakdown)
    invoice_counter: int = 1
    invoice_prefix: str = 'ΤΠΥ'
    pdf_title: str = 'Βεβαίωση Συνδρομής'  # Legacy - kept for backward compatibility
    pdf_footer: str = ''  # Legacy - kept for backward compatibility
    pdf_logo_path: str = ''
    
    # Separate PDF settings per document type
    pdf_payment_title: str = 'Απόδειξη Πληρωμής'
    pdf_payment_footer: str = ''
    pdf_subscription_title: str = 'Βεβαίωση Συνδρομής'
    pdf_subscription_footer: str = ''
    
    # Receipt/Invoice appearance (editable from Settings > «Ρυθμίσεις PDF»)
    pdf_accent_color: str = '#1565C0'
    pdf_show_qr: bool = True
    pdf_show_session: bool = True
    
    # PDF Template JSON data (visual editor)
    pdf_template_family: str = ''
    pdf_template_payment: str = ''
    pdf_template_subscription: str = ''
    
    # Column preferences
    families_visible_columns: Optional[list] = None
    families_columns_locked: bool = False
    payments_visible_columns: Optional[list] = None
    payments_columns_locked: bool = False
    subscriptions_visible_columns: Optional[list] = None
    subscriptions_columns_locked: bool = False
    reports_visible_columns: Optional[list] = None
    reports_columns_locked: bool = False
    
    # Search field preferences
    families_search_fields: Optional[list] = None
    payments_search_fields: Optional[list] = None
    subscriptions_search_fields: Optional[list] = None
    reports_search_fields: Optional[list] = None
    
    # SMTP Settings
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_from_email: str = ''
    smtp_from_name: str = ''
    
    # Subscription Notifications
    days_before_expiration: int = 30
    highlight_enabled: bool = True
    color_expiring: str = '#FFA500'
    color_expired: str = '#FF0000'
    
    # Email Receipt Template
    email_receipt_subject: str = 'Απόδειξη Πληρωμής'
    email_receipt_body: str = 'Αγαπητέ/ή {family_name},\n\nΣας αποστέλλουμε την απόδειξη πληρωμής σας.\n\nΗμερομηνία: {payment_date}\nΠοσό: {amount}€\nΑριθμός Απόδειξης: {receipt_no}\n\nΜε εκτίμηση,\n{org_name}'
    
    # Email Subscription Reminder Template
    email_subscription_subject: str = 'Υπενθύμιση Συνδρομής'
    email_subscription_body: str = 'Αγαπητέ/ή {family_name},\n\nΣας υπενθυμίζουμε ότι η συνδρομή σας λήγει στις {expiry_date}.\n\nΣυνολικό Ποσό: {total_amount}€\nΠληρωμένο: {paid_amount}€\nΥπόλοιπο: {remaining_amount}€\n\nΠαρακαλούμε προβείτε στην εξόφληση.\n\nΜε εκτίμηση,\n{org_name}'
    
    # Email Family Certificate Template
    email_certificate_subject: str = 'Βεβαίωση Εγγραφής'
    email_certificate_body: str = 'Αγαπητέ/ή {family_name},\n\nΣας αποστέλλουμε τη βεβαίωση εγγραφής σας στον σύλλογό μας.\n\nΑριθμός Μητρώου: {family_code}\nΑριθμός Μελών: {members_count}\n\nΜε εκτίμηση,\n{org_name}'
    
    # License Management
    license_key: str = ''
    license_owner: str = ''
    license_start_date: Optional[str] = None  # Will be converted to date
    license_end_date: Optional[str] = None    # Will be converted to date
    license_status: str = 'none'  # 'active', 'expired', 'none'
    
    # License Validation Tracking
    last_online_validation: Optional[str] = None  # Last successful online validation
    last_validation_attempt: Optional[str] = None  # Last validation attempt (success or fail)
    offline_since: Optional[str] = None  # When the app went offline
    
    # Auto-Numbering Settings
    receipt_counter: int = 1
    subscription_counter: int = 1
    family_counter: int = 1
    receipt_prefix: str = 'ΑΠ'
    subscription_prefix: str = 'ΣΥΝ'
    
    # Update Checker Settings
    auto_check_updates: bool = True
    
    # RustDesk Settings
    rustdesk_server_host: str = ''
    rustdesk_server_port: int = 21116
    rustdesk_api_key: str = ''
    rustdesk_relay_server: str = ''
    default_hourly_rate: float = 50.00
    
    # Default column definitions (Support CRM - Clients)
    # Note: family_code/family_name are database aliases for backward compatibility
    DEFAULT_FAMILIES_COLUMNS = ["code", "company_name", "last_name", "first_name", "phone", "mobile", "email", "city", "is_active"]
    DEFAULT_PAYMENTS_COLUMNS = ["date", "family_code", "family_name", "description", "subscription_start_date", "subscription_end_date", "total_amount", "paid_amount", "remaining_amount", "status", "receipt_no"]
    DEFAULT_SUBSCRIPTIONS_COLUMNS = ["code", "family_name", "year", "start_date", "end_date", "is_free", "total_amount", "paid_amount", "remaining_amount", "status", "subscription_code"]
    DEFAULT_REPORTS_COLUMNS = ["code", "family_name", "city", "date", "charged", "paid", "remaining"]
    
    def get_visible_columns(self, view_name: str) -> list:
        """
        Get visible columns for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", or "reports"
            
        Returns:
            List of column keys
        """
        if view_name == "families":
            return self.families_visible_columns if self.families_visible_columns else self.DEFAULT_FAMILIES_COLUMNS.copy()
        elif view_name == "payments":
            return self.payments_visible_columns if self.payments_visible_columns else self.DEFAULT_PAYMENTS_COLUMNS.copy()
        elif view_name == "subscriptions":
            return self.subscriptions_visible_columns if self.subscriptions_visible_columns else self.DEFAULT_SUBSCRIPTIONS_COLUMNS.copy()
        elif view_name == "reports":
            return self.reports_visible_columns if self.reports_visible_columns else self.DEFAULT_REPORTS_COLUMNS.copy()
        return []
    
    def set_visible_columns(self, view_name: str, columns: list) -> None:
        """
        Set visible columns for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", or "reports"
            columns: List of column keys
        """
        if view_name == "families":
            self.families_visible_columns = columns if columns else self.DEFAULT_FAMILIES_COLUMNS.copy()
        elif view_name == "payments":
            self.payments_visible_columns = columns if columns else self.DEFAULT_PAYMENTS_COLUMNS.copy()
        elif view_name == "subscriptions":
            self.subscriptions_visible_columns = columns if columns else self.DEFAULT_SUBSCRIPTIONS_COLUMNS.copy()
        elif view_name == "reports":
            self.reports_visible_columns = columns if columns else self.DEFAULT_REPORTS_COLUMNS.copy()
    
    def get_columns_locked(self, view_name: str) -> bool:
        """
        Get column lock status for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", or "reports"
            
        Returns:
            True if columns are locked
        """
        if view_name == "families":
            return self.families_columns_locked
        elif view_name == "payments":
            return self.payments_columns_locked
        elif view_name == "subscriptions":
            return self.subscriptions_columns_locked
        elif view_name == "reports":
            return self.reports_columns_locked
        return False
    
    def set_columns_locked(self, view_name: str, locked: bool) -> None:
        """
        Set column lock status for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", or "reports"
            locked: True to lock columns
        """
        if view_name == "families":
            self.families_columns_locked = locked
        elif view_name == "payments":
            self.payments_columns_locked = locked
        elif view_name == "subscriptions":
            self.subscriptions_columns_locked = locked
        elif view_name == "reports":
            self.reports_columns_locked = locked
    
    # Default search fields (Support CRM - Clients)
    DEFAULT_FAMILIES_SEARCH_FIELDS = ["code", "company_name", "last_name", "first_name", "email"]
    DEFAULT_PAYMENTS_SEARCH_FIELDS = ["code", "company_name", "last_name", "first_name"]
    DEFAULT_SUBSCRIPTIONS_SEARCH_FIELDS = ["code", "company_name", "last_name", "first_name", "phone"]
    DEFAULT_REPORTS_SEARCH_FIELDS = ["code", "company_name", "last_name", "first_name", "city"]
    
    def get_search_fields(self, view_name: str) -> list:
        """
        Get search fields for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", "reports"
            
        Returns:
            List of field keys to search in
        """
        if view_name == "families":
            return self.families_search_fields if self.families_search_fields else self.DEFAULT_FAMILIES_SEARCH_FIELDS.copy()
        elif view_name == "payments":
            return self.payments_search_fields if self.payments_search_fields else self.DEFAULT_PAYMENTS_SEARCH_FIELDS.copy()
        elif view_name == "subscriptions":
            return self.subscriptions_search_fields if self.subscriptions_search_fields else self.DEFAULT_SUBSCRIPTIONS_SEARCH_FIELDS.copy()
        elif view_name == "reports":
            return self.reports_search_fields if self.reports_search_fields else self.DEFAULT_REPORTS_SEARCH_FIELDS.copy()
        return []
    
    def set_search_fields(self, view_name: str, fields: list) -> None:
        """
        Set search fields for a view.
        
        Args:
            view_name: "families", "payments", "subscriptions", "reports"
            fields: List of field keys to search in
        """
        if view_name == "families":
            self.families_search_fields = fields if fields else self.DEFAULT_FAMILIES_SEARCH_FIELDS.copy()
        elif view_name == "payments":
            self.payments_search_fields = fields if fields else self.DEFAULT_PAYMENTS_SEARCH_FIELDS.copy()
        elif view_name == "subscriptions":
            self.subscriptions_search_fields = fields if fields else self.DEFAULT_SUBSCRIPTIONS_SEARCH_FIELDS.copy()
        elif view_name == "reports":
            self.reports_search_fields = fields if fields else self.DEFAULT_REPORTS_SEARCH_FIELDS.copy()
        
        logger.info(f"Search fields for {view_name} set to: {fields}")


class SettingsService:
    """
    Service for accessing application settings.
    Reads organization info and PDF configuration from database.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize SettingsService.
        
        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection
        self._settings_cache: Optional[AppSettings] = None
    
    def load_settings(self) -> Optional[AppSettings]:
        """
        Load settings from database.
        
        Returns:
            AppSettings instance or None if not found
        """
        try:
            results = self.db_connection.execute_query(
                "SELECT * FROM app_settings WHERE id = 1"
            )
            
            if results:
                result = results[0]
                # Remove id and updated_at fields
                result.pop('id', None)
                result.pop('updated_at', None)
                
                # Parse JSON fields for column preferences and search fields
                json_list_fields = [
                    'families_visible_columns', 'payments_visible_columns',
                    'subscriptions_visible_columns', 'reports_visible_columns',
                    'families_search_fields', 'payments_search_fields',
                    'subscriptions_search_fields', 'reports_search_fields'
                ]
                for field_name in json_list_fields:
                    if field_name in result and result[field_name]:
                        try:
                            result[field_name] = json.loads(result[field_name])
                        except (json.JSONDecodeError, TypeError):
                            result[field_name] = None
                
                # Get valid field names from AppSettings dataclass
                import dataclasses
                valid_fields = {f.name for f in dataclasses.fields(AppSettings)}
                
                # Filter out unknown fields from database (e.g., old columns that no longer exist in code)
                unknown_fields = set(result.keys()) - valid_fields
                if unknown_fields:
                    logger.debug(f"Ignoring unknown DB fields: {unknown_fields}")
                
                filtered_result = {k: v for k, v in result.items() if k in valid_fields}
                
                settings = AppSettings(**filtered_result)
                self._settings_cache = settings
                logger.debug("Settings loaded from database")
                return settings
            else:
                logger.warning("No settings found in app_settings table")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return None
    
    def save_settings(self, settings: AppSettings) -> bool:
        """
        Save settings to database (INSERT or UPDATE id=1).
        
        Args:
            settings: AppSettings instance to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert dataclass to dict
            settings_dict = asdict(settings)
            
            # Remove class attributes that shouldn't be saved
            settings_dict.pop('DEFAULT_FAMILIES_COLUMNS', None)
            settings_dict.pop('DEFAULT_PAYMENTS_COLUMNS', None)
            settings_dict.pop('DEFAULT_SUBSCRIPTIONS_COLUMNS', None)
            settings_dict.pop('DEFAULT_REPORTS_COLUMNS', None)
            settings_dict.pop('DEFAULT_FAMILIES_SEARCH_FIELDS', None)
            settings_dict.pop('DEFAULT_PAYMENTS_SEARCH_FIELDS', None)
            settings_dict.pop('DEFAULT_SUBSCRIPTIONS_SEARCH_FIELDS', None)
            settings_dict.pop('DEFAULT_REPORTS_SEARCH_FIELDS', None)
            
            # Convert list fields to JSON strings (column preferences and search fields)
            json_list_fields = [
                'families_visible_columns', 'payments_visible_columns', 
                'subscriptions_visible_columns', 'reports_visible_columns',
                'families_search_fields', 'payments_search_fields', 
                'subscriptions_search_fields', 'reports_search_fields'
            ]
            for field_name in json_list_fields:
                if field_name in settings_dict and settings_dict[field_name] is not None:
                    settings_dict[field_name] = json.dumps(settings_dict[field_name])
            
            # Build UPDATE query (simpler and more reliable)
            fields = list(settings_dict.keys())
            values = [settings_dict[field] for field in fields]
            
            # Build SET clause for UPDATE
            set_parts = [f"{field} = %s" for field in fields]
            set_str = ', '.join(set_parts)
            
            query = f"""
                UPDATE app_settings 
                SET {set_str}
                WHERE id = 1
            """
            
            logger.info(f"Executing save query with {len(values)} values")
            logger.info(f"SMTP values: host={settings_dict.get('smtp_host')}, port={settings_dict.get('smtp_port')}, user={settings_dict.get('smtp_username')}")
            rows_affected = self.db_connection.execute_update(query, tuple(values))
            logger.info(f"Query executed, rows affected: {rows_affected}")
            
            self.db_connection.commit()
            logger.info("Transaction committed")
            
            # Update cache
            self._settings_cache = settings
            
            logger.info("Settings saved to database successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.db_connection.rollback()
            return False
    
    def reload_settings(self):
        """Force reload settings from database."""
        self._settings_cache = None
        self.load_settings()
    
    def get_org_name(self) -> str:
        """
        Get organization full name.
        
        Returns:
            Organization name or empty string
        """
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_name if self._settings_cache else ''
    
    def get_org_short_name(self) -> str:
        """Get organization short name/abbreviation."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_short_name if self._settings_cache else ''
    
    def get_org_address(self) -> str:
        """Get organization address."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_address if self._settings_cache else ''
    
    def get_org_city(self) -> str:
        """Get organization city."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_city if self._settings_cache else ''
    
    def get_org_postal_code(self) -> str:
        """Get organization postal code."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_postal_code if self._settings_cache else ''
    
    def get_org_phone(self) -> str:
        """Get organization phone number."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_phone if self._settings_cache else ''
    
    def get_org_email(self) -> str:
        """Get organization email address."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.org_email if self._settings_cache else ''
    
    def get_org_full_address(self) -> str:
        """Get formatted full organization address."""
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return ''
        
        parts = []
        if self._settings_cache.org_address:
            parts.append(self._settings_cache.org_address)
        
        city_postal = []
        if self._settings_cache.org_postal_code:
            city_postal.append(self._settings_cache.org_postal_code)
        if self._settings_cache.org_city:
            city_postal.append(self._settings_cache.org_city)
        
        if city_postal:
            parts.append(' '.join(city_postal))
        
        return ', '.join(parts)
    
    def get_pdf_title(self) -> str:
        """Get default PDF document title (legacy)."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.pdf_title if self._settings_cache else 'Βεβαίωση'
    
    def get_pdf_footer(self) -> str:
        """Get PDF footer text (legacy)."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.pdf_footer if self._settings_cache else ''
    
    def get_pdf_payment_title(self) -> str:
        """Get PDF title for payment receipts."""
        if self._settings_cache is None:
            self.load_settings()
        if self._settings_cache and self._settings_cache.pdf_payment_title:
            return self._settings_cache.pdf_payment_title
        return 'Απόδειξη Πληρωμής'
    
    def get_pdf_payment_footer(self) -> str:
        """Get PDF footer for payment receipts."""
        if self._settings_cache is None:
            self.load_settings()
        if self._settings_cache:
            # Use payment-specific footer, fallback to general footer
            return self._settings_cache.pdf_payment_footer or self._settings_cache.pdf_footer or ''
        return ''
    
    def get_pdf_subscription_title(self) -> str:
        """Get PDF title for subscription certificates."""
        if self._settings_cache is None:
            self.load_settings()
        if self._settings_cache and self._settings_cache.pdf_subscription_title:
            return self._settings_cache.pdf_subscription_title
        return 'Βεβαίωση Συνδρομής'
    
    def get_pdf_subscription_footer(self) -> str:
        """Get PDF footer for subscription certificates."""
        if self._settings_cache is None:
            self.load_settings()
        if self._settings_cache:
            # Use subscription-specific footer, fallback to general footer
            return self._settings_cache.pdf_subscription_footer or self._settings_cache.pdf_footer or ''
        return ''
    
    def get_logo_path(self) -> str:
        """Get path to organization logo image file."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache.pdf_logo_path if self._settings_cache else ''
    
    def has_logo(self) -> bool:
        """Check if organization logo is configured."""
        logo_path = self.get_logo_path()
        return bool(logo_path and logo_path.strip())
    
    def get_all_settings(self) -> Optional[AppSettings]:
        """Get all settings as AppSettings instance."""
        if self._settings_cache is None:
            self.load_settings()
        return self._settings_cache
    
    # SMTP Settings getters
    def get_smtp_config(self) -> dict:
        """Get SMTP configuration as dictionary."""
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return {}
        
        return {
            'host': self._settings_cache.smtp_host,
            'port': self._settings_cache.smtp_port,
            'use_tls': self._settings_cache.smtp_use_tls,
            'username': self._settings_cache.smtp_username,
            'password': self._settings_cache.smtp_password,
            'from_email': self._settings_cache.smtp_from_email,
            'from_name': self._settings_cache.smtp_from_name
        }
    
    def get_subscription_notification_config(self) -> dict:
        """Get subscription notification configuration."""
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return {
                'days_before_expiration': 30,
                'highlight_enabled': True,
                'color_expiring': '#FFA500',
                'color_expired': '#FF0000'
            }
        
        return {
            'days_before_expiration': self._settings_cache.days_before_expiration,
            'highlight_enabled': self._settings_cache.highlight_enabled,
            'color_expiring': self._settings_cache.color_expiring,
            'color_expired': self._settings_cache.color_expired
        }
    
    def get_email_receipt_config(self) -> dict:
        """Get email receipt configuration."""
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return {
                'subject': 'Απόδειξη Πληρωμής',
                'body': '''Αγαπητέ/ή {family_name},

Σας αποστέλλουμε την απόδειξη πληρωμής σας.

Ημερομηνία: {payment_date}
Ποσό: {amount}€
Αριθμός Απόδειξης: {receipt_no}

Με εκτίμηση,
{org_name}'''
            }
        
        return {
            'subject': self._settings_cache.email_receipt_subject,
            'body': self._settings_cache.email_receipt_body
        }
    
    def get_email_subscription_config(self) -> dict:
        """Get email subscription reminder configuration."""
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return {
                'subject': 'Υπενθύμιση Συνδρομής',
                'body': '''Αγαπητέ/ή {family_name},

Σας υπενθυμίζουμε ότι η συνδρομή σας λήγει στις {expiry_date}.

Συνολικό Ποσό: {total_amount}€
Πληρωμένο: {paid_amount}€
Υπόλοιπο: {remaining_amount}€

Παρακαλούμε προβείτε στην εξόφληση.

Με εκτίμηση,
{org_name}'''
            }
        
        return {
            'subject': self._settings_cache.email_subscription_subject,
            'body': self._settings_cache.email_subscription_body
        }
    
    # License Management methods
    def get_license_info(self) -> dict:
        """
        Get license information.
        
        Returns:
            Dictionary with license info
        """
        if self._settings_cache is None:
            self.load_settings()
        
        if not self._settings_cache:
            return {
                'key': '',
                'owner': '',
                'start_date': None,
                'end_date': None,
                'status': 'none'
            }
        
        return {
            'key': self._settings_cache.license_key,
            'owner': self._settings_cache.license_owner,
            'start_date': self._settings_cache.license_start_date,
            'end_date': self._settings_cache.license_end_date,
            'status': self._settings_cache.license_status
        }
    
    def set_license(self, license_key: str, owner: str, start_date, end_date, status: str) -> bool:
        """
        Set license information.
        
        Args:
            license_key: License key
            owner: License owner name
            start_date: License start date
            end_date: License end date
            status: License status ('active', 'expired', 'none')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current settings
            settings = self.load_settings()
            if not settings:
                settings = AppSettings()
            
            # Update license fields
            settings.license_key = license_key
            settings.license_owner = owner
            settings.license_start_date = start_date
            settings.license_end_date = end_date
            settings.license_status = status
            
            # Save settings
            return self.save_settings(settings)
            
        except Exception as e:
            logger.error(f"Failed to set license: {e}")
            return False

    def update_license_validation_tracking(self, online_success: bool) -> bool:
        """
        Update license validation tracking timestamps.
        
        Args:
            online_success: True if online validation succeeded, False if failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from datetime import datetime
            
            now = datetime.now()
            
            # Update in database directly
            if online_success:
                # Successful online validation
                sql = """
                    UPDATE app_settings 
                    SET last_online_validation = %s,
                        last_validation_attempt = %s,
                        offline_since = NULL
                    WHERE id = 1
                """
                self.db_connection.execute_update(sql, (now, now))
            else:
                # Failed validation - check if this is first failure
                sql = """
                    UPDATE app_settings 
                    SET last_validation_attempt = %s,
                        offline_since = COALESCE(offline_since, %s)
                    WHERE id = 1
                """
                self.db_connection.execute_update(sql, (now, now))
            
            self.db_connection.commit()
            
            # Reload cache
            self.reload_settings()
            
            logger.info(f"License validation tracking updated: online_success={online_success}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update license validation tracking: {e}")
            self.db_connection.rollback()
            return False
    
    def get_license_validation_info(self) -> dict:
        """
        Get license validation tracking information.
        
        Returns:
            Dictionary with validation tracking info
        """
        try:
            sql = """
                SELECT last_online_validation, last_validation_attempt, offline_since
                FROM app_settings
                WHERE id = 1
            """
            result = self.db_connection.execute_query(sql)
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    'last_online_validation': row[0],
                    'last_validation_attempt': row[1],
                    'offline_since': row[2]
                }
            
            return {
                'last_online_validation': None,
                'last_validation_attempt': None,
                'offline_since': None
            }
            
        except Exception as e:
            logger.error(f"Failed to get license validation info: {e}")
            return {
                'last_online_validation': None,
                'last_validation_attempt': None,
                'offline_since': None
            }
