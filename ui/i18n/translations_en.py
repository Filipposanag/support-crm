# -*- coding: utf-8 -*-
"""
English translations for Support CRM
"""

TRANSLATIONS_EN = {
    # Application
    'app_title': 'Support CRM',
    'app_version': 'Version',
    
    # Menu Bar
    'menu_file': 'File',
    'menu_edit': 'Edit',
    'menu_view': 'View',
    'menu_tools': 'Tools',
    'menu_help': 'Help',
    
    # Menu Items - File
    'menu_new': 'New',
    'menu_open': 'Open',
    'menu_save': 'Save',
    'menu_save_as': 'Save As',
    'menu_export': 'Export',
    'menu_import': 'Import',
    'menu_import_data': 'Import Data (CSV/Excel)...',
    'menu_print': 'Print',
    'menu_exit': 'Exit',
    
    # Menu Items - Edit
    'menu_undo': 'Undo',
    'menu_redo': 'Redo',
    'menu_cut': 'Cut',
    'menu_copy': 'Copy',
    'menu_paste': 'Paste',
    'menu_delete': 'Delete',
    'menu_select_all': 'Select All',
    'menu_preferences': 'Preferences',
    
    # Menu Items - View
    'menu_refresh': 'Refresh',
    'menu_zoom_in': 'Zoom In',
    'menu_zoom_out': 'Zoom Out',
    'menu_fullscreen': 'Full Screen',
    
    # Menu Items - Help
    'menu_about': 'About',
    'menu_documentation': 'Documentation',
    'menu_check_updates': 'Check for Updates',
    
    # Navigation
    'nav_dashboard': 'Dashboard',
    'nav_clients': 'Clients',
    'nav_sessions': 'Sessions',
    'nav_families': 'Families',  # Keep for backward compatibility
    'nav_payments': 'Payments',
    'nav_packages': 'Packages',
    'nav_documents': 'Documents',
    'nav_debts': 'Debts',
    'nav_subscriptions': 'Subscriptions',
    'nav_import': 'Import',
    'nav_reports': 'Reports',
    'nav_audit_log': 'Audit Log',
    'nav_settings': 'Settings',
    'nav_users': 'Users',
    
    # Common Buttons
    'btn_new': 'New',
    'btn_add': 'Add',
    'btn_edit': 'Edit',
    'btn_delete': 'Delete',
    'btn_save': 'Save',
    'btn_cancel': 'Cancel',
    'btn_close': 'Close',
    'btn_ok': 'OK',
    'btn_yes': 'Yes',
    'btn_no': 'No',
    'btn_apply': 'Apply',
    'btn_search': 'Search',
    'btn_filter': 'Filter',
    'btn_clear': 'Clear',
    'btn_refresh': 'Refresh',
    'btn_export': 'Export',
    'btn_import': 'Import',
    'btn_browse': 'Browse',
    'btn_select_file': 'Select File',
    'btn_generate': 'Generate',
    'btn_preview': 'Preview',
    'btn_back': 'Back',
    'btn_next': 'Next',
    'btn_finish': 'Finish',
    
    # Families View
    'families_title': 'Family Management',
    'families_search_placeholder': 'Search family (Name, Surname, ID, Phone, City)...',
    'families_filter_active': 'Active only',
    'families_view_members': 'View Members',
    'families_total': 'Total families',
    'families_active': 'Active',
    'families_inactive': 'Inactive',
    
    # Family Form
    'family_form_title_new': 'New Family',
    'family_form_title_edit': 'Edit Family',
    'family_tab_basic': 'Basic Information',
    'family_tab_members': 'Members',
    'family_tab_payments': 'Payments',
    'family_tab_notes': 'Notes',
    
    # Family Fields
    'family_code': 'Code',
    'family_last_name': 'Last Name',
    'family_first_name': 'First Name',
    'family_spouse_name': 'Spouse Name',
    'family_national_id': 'National ID',
    'family_profession': 'Profession',
    'family_address': 'Address',
    'family_city': 'City',
    'family_postal_code': 'Postal Code',
    'family_phone': 'Phone',
    'family_mobile': 'Mobile',
    'family_email': 'Email',
    'family_birth_date': 'Birth Date',
    'family_members_count': 'Members Count',
    'family_notes': 'Notes',
    'family_is_active': 'Active',
    'family_active': 'Active family',
    'family_inactive': 'Inactive family',
    'family_created_at': 'Created',
    'family_updated_at': 'Updated',
    
    # Members
    'members_title': 'Family Members',
    'member_add': 'Add Member',
    'member_edit': 'Edit Member',
    'member_remove': 'Remove Member',
    'member_form_title_new': 'New Member',
    'member_form_title_edit': 'Edit Member',
    
    # Member Fields
    'member_inner_no': 'No.',
    'member_first_name': 'First Name',
    'member_last_name': 'Last Name',
    'member_national_id': 'National ID',
    'member_birth_date': 'Birth Date',
    'member_profession': 'Profession',
    'member_married': 'Married',
    'member_marriage_date': 'Marriage Date',
    'member_reg_date': 'Registration Date',
    
    # Payments View
    'payments_title': 'Payment Management',
    'payments_filter_year': 'Year',
    'payments_filter_family': 'Family',
    'payments_filter_outstanding': 'Outstanding only',
    'payments_new': 'New Payment',
    'payments_summary': 'Payment Summary',
    'payments_total_families': 'Total Families',
    'payments_total_collected': 'Total Collected',
    'payments_total_outstanding': 'Total Outstanding',
    'payments_paid_count': 'Paid',
    'payments_partial_count': 'Partial',
    'payments_unpaid_count': 'Unpaid',
    
    # Payment Form
    'payment_form_title_new': 'New Payment',
    'payment_form_title_edit': 'Edit Payment',
    
    # Payment Fields
    'payment_family': 'Family',
    'payment_date': 'Date',
    'payment_time': 'Time',
    'payment_description': 'Description',
    'payment_receipt_no': 'Receipt No.',
    'payment_total_amount': 'Total Amount',
    'payment_paid_amount': 'Paid Amount',
    'payment_remaining_amount': 'Remaining',
    'payment_status': 'Status',
    'payment_year': 'Year',
    'payment_remarks': 'Remarks',
    
    # Payment Status
    'payment_status_paid': 'Paid',
    'payment_status_partial': 'Partial',
    'payment_status_unpaid': 'Unpaid',
    
    # Import View
    'import_title': 'Import Data (CSV/Excel)',
    'import_clients': 'Import Clients (client.csv)',
    'import_members': 'Import Members (members.csv)',
    'import_reports': 'Import Payments (report.csv)',
    'import_select_file': 'Select File',
    'import_file_path': 'File Path',
    'import_preview': 'Preview',
    'import_start': 'Start Import',
    'import_progress': 'Progress',
    'import_log': 'Log',
    'import_status': 'Status',
    
    # Import Messages
    'import_no_file': 'No file selected',
    'import_selected_file': 'Selected file',
    'import_no_preview': 'No preview available',
    'import_log_file': 'Log File',
    'import_no_log': 'No log file',
    'import_file_not_found': 'File not found',
    'import_invalid_format': 'Invalid file format',
    'import_in_progress': 'Import in progress...',
    'import_completed': 'Import completed',
    'import_failed': 'Import failed',
    'import_total_rows': 'Total rows',
    'import_success_rows': 'Successful',
    'import_failed_rows': 'Failed',
    'import_duration': 'Duration',
    
    # Reports View
    'reports_title': 'Reports',
    'reports_type': 'Report Type',
    'reports_unpaid_subscriptions': 'Unpaid Subscriptions',
    'reports_payment_summary': 'Payment Summary',
    'reports_family_list': 'Family List',
    'reports_member_statistics': 'Member Statistics',
    'reports_year': 'Year',
    'reports_generate': 'Generate Report',
    'reports_export_csv': 'Export to CSV',
    'reports_export_pdf': 'Export to PDF',
    'reports_no_data': 'No data available',
    
    # Report Columns
    'report_col_code': 'Code',
    'report_col_family_name': 'Family',
    'report_col_phone': 'Phone',
    'report_col_email': 'Email',
    'report_col_outstanding': 'Outstanding',
    'report_col_last_payment': 'Last Payment',
    'report_col_city': 'City',
    'report_col_members': 'Members',
    
    # Table Columns
    'col_id': 'ID',
    'col_code': 'Code',
    'col_last_name': 'Last Name',
    'col_first_name': 'First Name',
    'col_phone': 'Phone',
    'col_mobile': 'Mobile',
    'col_city': 'City',
    'col_members_count': 'Members',
    'col_active': 'Active',
    'col_last_payment_year': 'Last Subscription',
    'col_outstanding_amount': 'Outstanding',
    'col_family': 'Family',
    'col_date': 'Date',
    'col_description': 'Description',
    'col_total_amount': 'Total Amount',
    'col_paid_amount': 'Paid',
    'col_remaining': 'Remaining',
    'col_status': 'Status',
    'col_inner_no': 'No.',
    'col_birth_date': 'Birth Date',
    'col_profession': 'Profession',
    'col_married': 'Married',
    'col_actions': 'Actions',
    
    # Pagination
    'pagination_page': 'Page',
    'pagination_of': 'of',
    'pagination_rows_per_page': 'Rows per page',
    'pagination_first': 'First',
    'pagination_previous': 'Previous',
    'pagination_next': 'Next',
    'pagination_last': 'Last',
    'pagination_total_records': 'Total records',
    
    # Search and Filter
    'search_placeholder': 'Search...',
    'filter_all': 'All',
    'filter_active': 'Active',
    'filter_inactive': 'Inactive',
    'filter_apply': 'Apply Filters',
    'filter_clear': 'Clear Filters',
    'search_by_name': 'Search by name',
    'search_by_adt': 'Search by National ID',
    'search_by_phone': 'Search by phone',
    
    # Validation Messages
    'validation_required': 'This field is required',
    'validation_invalid_email': 'Invalid email address',
    'validation_invalid_phone': 'Invalid phone number',
    'validation_invalid_date': 'Invalid date',
    'validation_invalid_number': 'Invalid number',
    'validation_min_length': 'Minimum length: {0} characters',
    'validation_max_length': 'Maximum length: {0} characters',
    'validation_positive_number': 'Number must be positive',
    'validation_future_date': 'Date cannot be in the future',
    'validation_duplicate': 'Record already exists',
    
    # Error Messages
    'error_title': 'Error',
    'error_database_connection': 'Database connection failed',
    'error_database_query': 'Query execution error',
    'error_file_not_found': 'File not found',
    'error_file_read': 'File read error',
    'error_file_write': 'File write error',
    'error_permission_denied': 'Permission denied',
    'error_unknown': 'Unknown error',
    'error_save_failed': 'Save failed',
    'error_delete_failed': 'Delete failed',
    'error_load_failed': 'Load failed',
    'error_view_creation': 'Error creating view',
    'error_view_switch': 'Error switching view',
    
    # Success Messages
    'success_title': 'Success',
    'success_saved': 'Saved successfully',
    'success_deleted': 'Deleted successfully',
    'success_imported': 'Imported successfully',
    'success_exported': 'Exported successfully',
    'success_updated': 'Updated successfully',
    
    # Warning Messages
    'warning_title': 'Warning',
    'warning_unsaved_changes': 'There are unsaved changes. Do you want to continue?',
    'warning_delete_confirm': 'Are you sure you want to delete this record?',
    'warning_delete_family': 'Deleting the family will also delete all its members. Continue?',
    'warning_no_selection': 'No record selected',
    'warning_invalid_data': 'Invalid data',
    
    # Info Messages
    'info_title': 'Information',
    'info_no_records': 'No records found',
    'info_loading': 'Loading...',
    'info_processing': 'Processing...',
    'info_please_wait': 'Please wait...',
    
    # Confirmation Messages
    'confirm_title': 'Confirmation',
    'confirm_delete': 'Confirm Delete',
    'confirm_save': 'Confirm Save',
    'confirm_exit': 'Are you sure you want to exit the application?',
    
    # Status Bar
    'status_ready': 'Ready',
    'status_connected': 'Connected',
    'status_disconnected': 'Disconnected',
    'status_loading': 'Loading...',
    'status_saving': 'Saving...',
    'status_records': 'records',
    
    # Language
    'language': 'Language',
    'language_greek': 'Ελληνικά',
    'language_english': 'English',
    
    # Settings
    'settings_title': 'Settings',
    'settings_general': 'General',
    'settings_database': 'Database',
    'settings_appearance': 'Appearance',
    'settings_language': 'Language',
    'settings_theme': 'Theme',
    'settings_font_size': 'Font Size',
    
    # About
    'about_title': 'About Support CRM',
    'about_version': 'Version',
    'about_description': 'Customer management and remote support system',
    'about_copyright': 'Copyright',
    'about_license': 'License',
    
    # License Messages
    'license_problem_title': 'License Problem',
    'license_problem_message': 'There is a problem with the license.\n\nPlease contact PC Project.',
    'license_not_found_title': 'License Not Found',
    'license_not_found_message': 'The license was not found on the server.\n\nPossible causes:\n• The license has been deactivated\n• Wrong license key\n\nPlease contact PC Project.',
    'license_expired_title': 'License Expired',
    'license_expired_message': 'The license expired {days} days ago.\n\nPlease activate a new license to continue.',
    'license_invalid_title': 'Invalid License',
    'license_expiring_title': 'Expiration Warning',
    'license_expiring_message': 'The license expires in {days} days!\n\nPlease renew your license.',
    'license_offline_warning_title': 'Unable to Validate Online',
    'license_offline_warning_message': 'Unable to connect for license validation.\n\nLast validation: {days} days ago.\n\nPlease connect to the Internet soon.',
    'license_activation_title': 'License Activation',
    'license_activation_required': 'License Required',
    'license_activation_desc': 'No active license found.\n\nPlease enter your license key to continue.\nInternet connection required for validation.',
    'license_key_label': 'License Key:',
    'license_key_placeholder': 'Enter your license key',
    'license_btn_exit': 'Exit Application',
    'license_btn_activate': 'Activate',
    'license_btn_activating': 'Validating...',
    'license_empty_key': 'Please enter a license key.',
    'license_activation_success': 'Activation Successful',
    'license_activation_success_msg': 'License activated successfully!\n\nOwner: {owner}\nStart Date: {start_date}\nEnd Date: {end_date}\n\n{days} days remaining.',
    'license_save_failed': 'Failed to save license to database.',
    
    # Misc
    'required_field': 'Required field',
    'optional_field': 'Optional field',
    'select': 'Select',
    'select_all': 'Select All',
    'deselect_all': 'Deselect All',
    'loading': 'Loading...',
    'no_data': 'No data',
    'total': 'Total',
    'average': 'Average',
    'count': 'Count',
    'sum': 'Sum',
    'min': 'Minimum',
    'max': 'Maximum',
    'yes': 'Yes',
    'no': 'No',
    'all': 'All',
    'none': 'None',
    'other': 'Other',
    'unknown': 'Unknown',
    'not_applicable': 'N/A',
}


# Import Support CRM translations
from ui.i18n.translations_support_crm_en import SUPPORT_CRM_TRANSLATIONS_EN

# Merge Support CRM translations
TRANSLATIONS_EN.update(SUPPORT_CRM_TRANSLATIONS_EN)
