# -*- coding: utf-8 -*-
"""
Import Dialog
Modal dialog wrapper for CSV import functionality.
"""

import logging
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt

from services.import_service import ImportService
from ui.i18n import TranslationManager
from ui.widgets.import_view import ImportView

logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """
    Modal dialog for CSV data import.
    Wraps ImportView in a dialog for use as a tool rather than a main view.
    """
    
    def __init__(
        self,
        import_service: ImportService,
        tr_manager: TranslationManager,
        parent=None
    ):
        """
        Initialize ImportDialog.
        
        Args:
            import_service: ImportService instance
            tr_manager: TranslationManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.import_service = import_service
        self.tr_manager = tr_manager
        
        self._init_ui()
        
        logger.debug("ImportDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set dialog properties
        self.setWindowTitle(self.tr_manager.get('import_title'))
        
        # Set app icon
        from utils.resource_loader import app_icon
        self.setWindowIcon(app_icon())
        
        self.setMinimumSize(900, 550)
        self.resize(950, 600)
        
        # Set modal
        self.setModal(True)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add ImportView as central widget
        self.import_view = ImportView(
            self.import_service,
            self.tr_manager,
            self
        )
        layout.addWidget(self.import_view)
        
        logger.debug("ImportDialog UI initialized")
