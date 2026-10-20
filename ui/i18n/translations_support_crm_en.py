# -*- coding: utf-8 -*-
"""
English translations for Support CRM
Αγγλικές μεταφράσεις για Support CRM
"""

SUPPORT_CRM_TRANSLATIONS_EN = {
    # Application
    'app_title': 'Support CRM',
    'app_name': 'Support CRM - Support Management System',
    'app_version': 'Version',
    'app_description': 'Client and remote support management system',
    
    # Navigation
    'nav_dashboard': 'Dashboard',
    'nav_clients': 'Clients',
    'nav_sessions': 'Sessions',
    'nav_subscriptions': 'Subscriptions',
    'nav_payments': 'Payments',
    'nav_packages': 'Packages',
    'nav_documents': 'Documents',
    'nav_reports': 'Reports',
    'nav_settings': 'Settings',
    
    # Clients
    'clients': 'Clients',
    'client': 'Client',
    'client_code': 'Client Code',
    'client_name': 'Client Name',
    'client_info': 'Client Information',
    'client_details': 'Client Details',
    'new_client': 'New Client',
    'edit_client': 'Edit Client',
    'delete_client': 'Delete Client',
    'active_clients': 'Active Clients',
    'inactive_clients': 'Inactive Clients',
    'total_clients': 'Total Clients',
    'company_name': 'Company Name',
    'contact_person': 'Contact Person',
    
    # Client Fields
    'first_name': 'First Name',
    'last_name': 'Last Name',
    'email': 'Email',
    'phone': 'Phone',
    'mobile': 'Mobile',
    'address': 'Address',
    'city': 'City',
    'postal_code': 'Postal Code',
    'tax_id': 'Tax ID',
    'notes': 'Notes',
    'support_notes': 'Support Notes',
    
    # RustDesk
    'rustdesk': 'RustDesk',
    'rustdesk_id': 'RustDesk ID',
    'rustdesk_password': 'RustDesk Password',
    'rustdesk_connect': 'RustDesk Connect',
    'rustdesk_connection': 'RustDesk Connection',
    'rustdesk_configured': 'RustDesk Configured',
    'rustdesk_not_configured': 'RustDesk Not Configured',
    'rustdesk_settings': 'RustDesk Settings',
    'rustdesk_server': 'RustDesk Server',
    'rustdesk_server_host': 'Server Address',
    'rustdesk_server_port': 'Server Port',
    'rustdesk_api_key': 'API Key',
    'rustdesk_relay_server': 'Relay Server',
    'connect_to_client': 'Connect to Client',
    'connecting': 'Connecting...',
    'connected': 'Connected',
    'disconnected': 'Disconnected',
    'connection_failed': 'Connection Failed',
    
    # Sessions
    'sessions': 'Sessions',
    'session': 'Session',
    'support_session': 'Support Session',
    'new_session': 'New Session',
    'active_session': 'Active Session',
    'active_sessions': 'Active Sessions',
    'completed_sessions': 'Completed Sessions',
    'session_history': 'Session History',
    'start_session': 'Start Session',
    'end_session': 'End Session',
    'cancel_session': 'Cancel Session',
    'session_duration': 'Session Duration',
    'session_type': 'Session Type',
    'session_status': 'Session Status',
    'session_details': 'Session Details',
    'session_description': 'Session Description',
    'session_notes': 'Session Notes',
    'issue_summary': 'Issue Summary',
    'start_time': 'Start Time',
    'end_time': 'End Time',
    'duration_minutes': 'Duration (minutes)',
    'technician': 'Technician',
    
    # Session Types
    'session_type_remote': 'Remote (RustDesk)',
    'session_type_onsite': 'On-site',
    'session_type_phone': 'Phone',
    'session_type_email': 'Email/Chat',
    
    # Session Status
    'status_active': 'Active',
    'status_completed': 'Completed',
    'status_cancelled': 'Cancelled',
    
    # Support Plans
    'support_plan': 'Support Plan',
    'support_plans': 'Support Plans',
    'plan_hourly': 'Hourly Rate',
    'plan_monthly': 'Monthly Subscription',
    'plan_yearly': 'Yearly Subscription',
    'plan_custom': 'Custom',
    'hourly_rate': 'Hourly Rate',
    'monthly_rate': 'Monthly Rate',
    'yearly_rate': 'Yearly Rate',
    'rate': 'Rate',
    'default_rate': 'Default Rate',
    
    # Billing
    'billing': 'Billing',
    'billed_amount': 'Billed Amount',
    'auto_billing': 'Auto Billing',
    'billing_enabled': 'Billing Enabled',
    'billing_disabled': 'Billing Disabled',
    'unbilled_sessions': 'Unbilled Sessions',
    'create_payment': 'Create Payment',
    'payment_created': 'Payment created',
    
    # Timer
    'timer': 'Timer',
    'timer_running': 'Timer Running',
    'timer_stopped': 'Timer Stopped',
    'elapsed_time': 'Elapsed Time',
    
    # Buttons
    'btn_connect': 'Connect',
    'btn_disconnect': 'Disconnect',
    'btn_start': 'Start',
    'btn_stop': 'Stop',
    'btn_pause': 'Pause',
    'btn_resume': 'Resume',
    'btn_save': 'Save',
    'btn_cancel': 'Cancel',
    'btn_close': 'Close',
    'btn_add': 'Add',
    'btn_edit': 'Edit',
    'btn_delete': 'Delete',
    'btn_search': 'Search',
    'btn_refresh': 'Refresh',
    'btn_export': 'Export',
    'btn_import': 'Import',
    'btn_print': 'Print',
    'btn_test_connection': 'Test Connection',
    'btn_configure': 'Configure',
    
    # Messages
    'msg_session_started': 'Session started',
    'msg_session_ended': 'Session completed',
    'msg_session_cancelled': 'Session cancelled',
    'msg_connection_success': 'Connection successful',
    'msg_connection_failed': 'Connection failed',
    'msg_rustdesk_not_found': 'RustDesk not found. Please install it.',
    'msg_client_saved': 'Client saved',
    'msg_client_deleted': 'Client deleted',
    'msg_confirm_delete': 'Are you sure you want to delete?',
    'msg_confirm_end_session': 'Are you sure you want to end the session?',
    'msg_no_active_session': 'No active session',
    'msg_rustdesk_id_required': 'RustDesk ID required',
    'msg_client_required': 'Please select a client',
    
    # Reports
    'reports': 'Reports',
    'report': 'Report',
    'session_report': 'Session Report',
    'billing_report': 'Billing Report',
    'client_report': 'Client Report',
    'revenue_report': 'Revenue Report',
    'statistics': 'Statistics',
    'total_sessions': 'Total Sessions',
    'total_hours': 'Total Hours',
    'total_revenue': 'Total Revenue',
    'average_duration': 'Average Duration',
    'date_range': 'Date Range',
    'from_date': 'From Date',
    'to_date': 'To Date',
    
    # Settings
    'settings': 'Settings',
    'general_settings': 'General Settings',
    'rustdesk_settings': 'RustDesk Settings',
    'billing_settings': 'Billing Settings',
    'session_settings': 'Session Settings',
    'rounding_minutes': 'Rounding (minutes)',
    'auto_billing_enabled': 'Auto Billing Enabled',
    
    # Common
    'yes': 'Yes',
    'no': 'No',
    'ok': 'OK',
    'apply': 'Apply',
    'reset': 'Reset',
    'clear': 'Clear',
    'all': 'All',
    'none': 'None',
    'active': 'Active',
    'inactive': 'Inactive',
    'enabled': 'Enabled',
    'disabled': 'Disabled',
    'required': 'Required',
    'optional': 'Optional',
    'loading': 'Loading...',
    'saving': 'Saving...',
    'processing': 'Processing...',
    'success': 'Success',
    'error': 'Error',
    'warning': 'Warning',
    'info': 'Information',
    
    # Tables
    'table_no_data': 'No data available',
    'table_loading': 'Loading data...',
    'table_rows_per_page': 'Rows per page',
    'table_page': 'Page',
    'table_of': 'of',
    'table_total': 'Total',
    
    # Filters
    'filter': 'Filter',
    'filters': 'Filters',
    'filter_by': 'Filter by',
    'search': 'Search',
    'search_placeholder': 'Search...',
    'show_all': 'Show All',
    'show_active': 'Show Active',
    'show_inactive': 'Show Inactive',
    
    # Dates
    'date': 'Date',
    'time': 'Time',
    'datetime': 'Date & Time',
    'today': 'Today',
    'yesterday': 'Yesterday',
    'this_week': 'This Week',
    'this_month': 'This Month',
    'this_year': 'This Year',
    'last_7_days': 'Last 7 Days',
    'last_30_days': 'Last 30 Days',
    'custom_range': 'Custom Range',
    
    # Units
    'minutes': 'minutes',
    'hours': 'hours',
    'days': 'days',
    'currency': '€',
    'per_hour': '/hour',
    'per_month': '/month',
    'per_year': '/year',
}

# Combine with existing translations
def get_all_translations_en():
    """Returns all English translations"""
    from ui.i18n.translations_en import TRANSLATIONS_EN
    combined = TRANSLATIONS_EN.copy()
    combined.update(SUPPORT_CRM_TRANSLATIONS_EN)
    return combined
