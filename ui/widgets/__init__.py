# -*- coding: utf-8 -*-
"""
UI Widgets Module
Contains all custom widgets for the Support CRM application.
"""

from ui.widgets.client_form import ClientForm
from ui.widgets.payments_view import PaymentsView
from ui.widgets.payments_table_model import PaymentsTableModel
from ui.widgets.payment_form import PaymentForm

# Support CRM - New widgets
from ui.widgets.clients_view import ClientsView
from ui.widgets.sessions_view import SessionsView
from ui.widgets.client_form import ClientForm
from ui.widgets.session_form import SessionForm

__all__ = [
    'ClientForm',
    'PaymentsView',
    'PaymentsTableModel',
    'PaymentForm',
    # Support CRM
    'ClientsView',
    'SessionsView',
    'ClientForm',
    'SessionForm',
]
