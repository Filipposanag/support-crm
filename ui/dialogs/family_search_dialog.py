# -*- coding: utf-8 -*-
"""
Family search dialog for selecting a family from a searchable list.
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class FamilySearchDialog(QDialog):
    """Dialog for searching and selecting a family."""
    
    family_selected = Signal(int, str)  # family_id, family_name
    
    def __init__(self, families_repo, parent=None):
        """
        Initialize the family search dialog.
        
        Args:
            families_repo: FamiliesRepository instance for loading families
            parent: Parent widget
        """
        super().__init__(parent)
        self.families_repo = families_repo
        self.selected_family_id = None
        self.selected_family_name = None
        
        self.setWindowTitle("Αναζήτηση Πελάτη")
        
        # Set app icon
        from utils.resource_loader import app_icon
        self.setWindowIcon(app_icon())
        
        # Set size
        self.setMinimumSize(700, 500)
        self.resize(700, 500)
        
        self._init_ui()
        self._load_families()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Επιλέξτε Πελάτη")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Search field
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        search_label = QLabel("🔍 Αναζήτηση:")
        search_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Πληκτρολογήστε όνομα πελάτη...")
        self.search_edit.textChanged.connect(self._filter_families)
        search_layout.addWidget(self.search_edit)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Επώνυμο", "Όνομα", "ΑΣΠΕ", "Κωδικός"])
        
        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Επώνυμο
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Όνομα
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # ΑΣΠΕ
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Κωδικός
        
        # Double-click to select
        self.table.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.info_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.select_button = QPushButton("Επιλογή")
        self.select_button.setMinimumWidth(100)
        self.select_button.clicked.connect(self._on_select)
        self.select_button.setEnabled(False)
        buttons_layout.addWidget(self.select_button)
        
        self.cancel_button = QPushButton("Ακύρωση")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # Enable select button when row is selected
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Focus on search field
        self.search_edit.setFocus()
    
    def _load_families(self, search_text: str = ""):
        """Load families into the table."""
        try:
            # Get active families
            families = self.families_repo.list_families(
                search=search_text,
                only_active=True,
                limit=10000,
                offset=0
            )
            
            self.table.setRowCount(0)
            
            for family in families:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Επώνυμο
                last_name_item = QTableWidgetItem(family.get('last_name', ''))
                last_name_item.setData(Qt.UserRole, family.get('id'))
                self.table.setItem(row, 0, last_name_item)
                
                # Όνομα
                first_name_item = QTableWidgetItem(family.get('first_name', ''))
                self.table.setItem(row, 1, first_name_item)
                
                # ΑΣΠΕ
                adt_item = QTableWidgetItem(family.get('national_id', ''))
                self.table.setItem(row, 2, adt_item)
                
                # Κωδικός (legacy_code)
                legacy_code = family.get('legacy_code')
                code_text = str(legacy_code) if legacy_code is not None else ''
                code_item = QTableWidgetItem(code_text)
                self.table.setItem(row, 3, code_item)
            
            # Update info label
            self.info_label.setText(f"Βρέθηκαν {len(families)} πελάτες")
            
            logger.debug(f"Loaded {len(families)} families into search dialog")
        except Exception as e:
            logger.error(f"Error loading families: {e}")
            self.info_label.setText(f"Σφάλμα φόρτωσης: {str(e)}")
    
    def _filter_families(self, text: str):
        """Filter families based on search text."""
        self._load_families(text)
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.table.selectedItems()) > 0
        self.select_button.setEnabled(has_selection)
    
    def _on_double_click(self):
        """Handle double-click on table row."""
        self._on_select()
    
    def _on_select(self):
        """Handle select button click."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Get family data
        family_id = self.table.item(row, 0).data(Qt.UserRole)
        last_name = self.table.item(row, 0).text()
        first_name = self.table.item(row, 1).text()
        family_name = f"{last_name} {first_name}".strip()
        
        self.selected_family_id = family_id
        self.selected_family_name = family_name
        
        # Emit signal
        self.family_selected.emit(family_id, family_name)
        
        logger.info(f"Family selected: {family_name} (ID: {family_id})")
        
        self.accept()
    
    def get_selected_family(self):
        """Get the selected family ID and name."""
        return self.selected_family_id, self.selected_family_name
