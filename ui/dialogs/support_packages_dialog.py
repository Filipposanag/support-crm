# -*- coding: utf-8 -*-
"""
Support Packages Management Dialog
Dialog for managing support packages with pricing
"""

import logging
from typing import Optional
from ui.utils.ui_helpers import gr_question
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QMessageBox, QHeaderView, QLineEdit, QTextEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QFormLayout, QDialogButtonBox,
    QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QStandardItemModel, QStandardItem

logger = logging.getLogger(__name__)


class SupportPackagesDialog(QDialog):
    """Dialog for managing support packages."""
    
    # Signal emitted when packages are modified
    packages_changed = Signal()
    
    def __init__(self, db_connection, parent=None):
        """
        Initialize SupportPackagesDialog.
        
        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db_connection
        
        self.setWindowTitle("Διαχείριση Πακέτων Υποστήριξης")
        self.resize(900, 600)
        
        self._init_ui()
        self._load_packages()
        
        logger.debug("SupportPackagesDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Πακέτα Υποστήριξης")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Info label
        info_label = QLabel(
            "Διαχειριστείτε τα διαθέσιμα πακέτα υποστήριξης. "
            "Τα πακέτα χρησιμοποιούνται στις πληρωμές για αυτόματη ενημέρωση των πελατών."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
        
        # Create model
        self.table_model = QStandardItemModel()
        self.table_view.setModel(self.table_model)
        
        # Set column headers
        self._setup_table_columns()
        
        layout.addWidget(self.table_view, stretch=1)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        from resources.icons import get_icon
        
        self.new_btn = QPushButton(get_icon('add'), "Νέο Πακέτο")
        self.new_btn.clicked.connect(self._on_new_package)
        self.new_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.new_btn)
        
        self.edit_btn = QPushButton(get_icon('edit'), "Επεξεργασία")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit_package)
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(get_icon('delete'), "Διαγραφή")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete_package)
        self.delete_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton(get_icon('close'), "Κλείσιμο")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        self.table_view.doubleClicked.connect(self._on_edit_package)
    
    def _setup_table_columns(self):
        """Setup table columns."""
        headers = [
            "Όνομα Πακέτου",
            "Τύπος",
            "Τιμή",
            "Διάρκεια",
            "Προπληρωμένες Ώρες",
            "Περιγραφή",
            "Ενεργό"
        ]
        self.table_model.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSection(0, 180)  # Name
        header.resizeSection(1, 100)  # Type
        header.resizeSection(2, 90)   # Price
        header.resizeSection(3, 90)   # Duration
        header.resizeSection(4, 140)  # Prepaid Hours
        header.resizeSection(5, 200)  # Description
        header.resizeSection(6, 70)   # Active
    
    def _load_packages(self):
        """Load packages from database."""
        try:
            query = """
                SELECT id, name, package_type, description, price, 
                       duration_months, prepaid_hours, is_active
                FROM support_packages
                ORDER BY package_type, name
            """
            
            packages = self.db.execute_query(query)
            self._populate_table(packages)
            
            logger.debug(f"Loaded {len(packages)} packages")
            
        except Exception as e:
            logger.error(f"Error loading packages: {e}")
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα φόρτωσης πακέτων:\n{str(e)}"
            )
    
    def _populate_table(self, packages: list):
        """Populate table with package data."""
        self.table_model.removeRows(0, self.table_model.rowCount())
        
        type_display = {
            'hourly': 'Ωριαία',
            'monthly': 'Μηνιαία',
            'yearly': 'Ετήσια',
            'custom': 'Προσαρμοσμένο'
        }
        
        for package in packages:
            row = []
            
            # Name
            row.append(QStandardItem(package.get('name', '')))
            
            # Type
            pkg_type = package.get('package_type', 'hourly')
            row.append(QStandardItem(type_display.get(pkg_type, pkg_type)))
            
            # Price
            price = float(package.get('price', 0))
            row.append(QStandardItem(f"{price:.2f} €"))
            
            # Duration
            duration = package.get('duration_months')
            if duration:
                duration_text = f"{duration} μήνες" if duration > 1 else "1 μήνας"
            else:
                duration_text = "-"
            row.append(QStandardItem(duration_text))
            
            # Prepaid Hours
            from ui.utils.ui_helpers import fmt_hours_min
            prepaid_hours = package.get('prepaid_hours')
            hours_text = fmt_hours_min(prepaid_hours) if (prepaid_hours and float(prepaid_hours) > 0) else "-"
            row.append(QStandardItem(hours_text))
            
            # Description
            desc = package.get('description', '')
            row.append(QStandardItem(desc[:50] + '...' if len(desc) > 50 else desc))
            
            # Active
            is_active = package.get('is_active', 1)
            row.append(QStandardItem('Ναι' if is_active else 'Όχι'))
            
            # Store package ID in first column
            row[0].setData(package.get('id'), Qt.UserRole)
            
            self.table_model.appendRow(row)
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = self.table_view.selectionModel().hasSelection()
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def _get_selected_package_id(self) -> Optional[int]:
        """Get the ID of the selected package."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return None
        
        index = selection[0]
        return self.table_model.item(index.row(), 0).data(Qt.UserRole)
    
    def _on_new_package(self):
        """Handle new package button click."""
        dialog = PackageFormDialog(self.db, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_packages()
            self.packages_changed.emit()
    
    def _on_edit_package(self):
        """Handle edit package button click."""
        package_id = self._get_selected_package_id()
        if not package_id:
            return
        
        dialog = PackageFormDialog(self.db, package_id=package_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_packages()
            self.packages_changed.emit()
    
    def _on_delete_package(self):
        """Handle delete package button click."""
        package_id = self._get_selected_package_id()
        if not package_id:
            return
        
        reply = gr_question(
            self,
            "Επιβεβαίωση Διαγραφής",
            "Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το πακέτο;\n\n"
            "Σημείωση: Οι υπάρχουσες πληρωμές με αυτό το πακέτο δεν θα επηρεαστούν.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM support_packages WHERE id = %s"
                self.db.execute_update(query, (package_id,))
                self.db.commit()
                
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    "Το πακέτο διαγράφηκε επιτυχώς"
                )
                
                self._load_packages()
                self.packages_changed.emit()
                
            except Exception as e:
                logger.error(f"Error deleting package: {e}")
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Σφάλμα διαγραφής πακέτου:\n{str(e)}"
                )


class PackageFormDialog(QDialog):
    """Dialog for creating/editing a support package."""
    
    def __init__(self, db_connection, package_id: Optional[int] = None, parent=None):
        """
        Initialize PackageFormDialog.
        
        Args:
            db_connection: Database connection
            package_id: Optional package ID for editing
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db_connection
        self.package_id = package_id
        
        self.setWindowTitle(
            "Επεξεργασία Πακέτου" if package_id else "Νέο Πακέτο"
        )
        self.resize(600, 500)
        
        self._init_ui()
        
        if self.package_id:
            self._load_package_data()
        
        logger.debug(f"PackageFormDialog initialized (package_id={package_id})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel(
            "Επεξεργασία Πακέτου" if self.package_id else "Νέο Πακέτο"
        )
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Form
        form = QFormLayout()
        form.setContentsMargins(0, 10, 0, 10)
        form.setHorizontalSpacing(15)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("π.χ. Βασικό Πακέτο")
        form.addRow("Όνομα Πακέτου *:", self.name_input)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItem("Ωριαία Χρέωση", "hourly")
        self.type_combo.addItem("Μηνιαία Συνδρομή", "monthly")
        self.type_combo.addItem("Ετήσια Συνδρομή", "yearly")
        self.type_combo.addItem("Πακέτο Ωρών", "custom")
        self.type_combo.setStyleSheet(
            "QComboBox{combobox-popup:0;}"
            "QComboBox QAbstractItemView::item{min-height:34px;padding:6px 10px;}"
        )
        self.type_combo.setMaxVisibleItems(10)
        for _i in range(self.type_combo.count()):
            self.type_combo.setItemData(_i, QSize(0, 34), Qt.SizeHintRole)
        form.addRow("Τύπος *:", self.type_combo)
        
        # Price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 99999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix(" €")
        self.price_input.setValue(0.00)
        form.addRow("Τιμή *:", self.price_input)
        
        # Prepaid hours the package grants
        self.hours_input = QDoubleSpinBox()
        self.hours_input.setRange(0, 9999)
        self.hours_input.setDecimals(1)
        self.hours_input.setSuffix(" ώρες")
        self.hours_input.setSpecialValueText("Χωρίς ώρες (χρονικό)")
        self.hours_input.setValue(0)
        self.hours_input.setToolTip("Πόσες ώρες υποστήριξης περιλαμβάνει το πακέτο")
        form.addRow("Ώρες Πακέτου:", self.hours_input)

        # Validity in months
        self.duration_input = QSpinBox()
        self.duration_input.setRange(0, 120)
        self.duration_input.setSuffix(" μήνες")
        self.duration_input.setSpecialValueText("Χωρίς λήξη")
        self.duration_input.setValue(0)
        self.duration_input.setToolTip("Για πόσους μήνες ισχύει το πακέτο")
        form.addRow("Διάρκεια ισχύος:", self.duration_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Περιγραφή πακέτου...")
        form.addRow("Περιγραφή:", self.description_input)

        # Active status (retire a package without deleting its history)
        self.active_check = QCheckBox("Διαθέσιμο για νέες αναθέσεις")
        self.active_check.setChecked(True)
        self.active_check.setToolTip(
            "Ξετικάρετε για να αποσύρετε το πακέτο: δεν θα εμφανίζεται σε νέες "
            "αναθέσεις, αλλά το ιστορικό των πελατών διατηρείται."
        )
        form.addRow("Κατάσταση:", self.active_check)

        layout.addLayout(form)
        
        # Required fields note
        note_label = QLabel("* Υποχρεωτικά πεδία")
        note_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        layout.addWidget(note_label)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Save).setText("Αποθήκευση")
        button_box.button(QDialogButtonBox.Cancel).setText("Ακύρωση")
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_package_data(self):
        """Load package data for editing."""
        try:
            query = """
                SELECT name, package_type, description, price, duration_months, prepaid_hours, is_active
                FROM support_packages
                WHERE id = %s
            """
            
            results = self.db.execute_query(query, (self.package_id,))
            if not results:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Το πακέτο δεν βρέθηκε"
                )
                self.reject()
                return
            
            package = results[0]
            
            # Populate fields
            self.name_input.setText(package.get('name', ''))
            
            pkg_type = package.get('package_type', 'hourly')
            index = self.type_combo.findData(pkg_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            self.price_input.setValue(float(package.get('price', 0)))
            _ph = package.get('prepaid_hours')
            self.hours_input.setValue(float(_ph) if _ph else 0)
            self.duration_input.setValue(int(package.get('duration_months') or 0))
            
            self.description_input.setPlainText(package.get('description', ''))
            self.active_check.setChecked(bool(package.get('is_active', 1)))
            
            logger.debug(f"Loaded package data for ID {self.package_id}")
            
        except Exception as e:
            logger.error(f"Error loading package data: {e}")
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα φόρτωσης δεδομένων:\n{str(e)}"
            )
            self.reject()
    
    def _validate_form(self) -> bool:
        """Validate form data."""
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το όνομα πακέτου είναι υποχρεωτικό"
            )
            self.name_input.setFocus()
            return False
        
        if self.price_input.value() < 0:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Η τιμή δεν μπορεί να είναι αρνητική"
            )
            self.price_input.setFocus()
            return False
        
        return True
    
    def _on_save(self):
        """Handle save button click."""
        if not self._validate_form():
            return
        
        try:
            _dur_months = self.duration_input.value() if self.duration_input.value() > 0 else None
            _prepaid_hours = self.hours_input.value() if self.hours_input.value() > 0 else None
            # Prepare data
            data = {
                'name': self.name_input.text().strip(),
                'package_type': self.type_combo.currentData(),
                'description': self.description_input.toPlainText().strip(),
                'price': self.price_input.value(),
                'duration_months': _dur_months,
                'prepaid_hours': _prepaid_hours,
                'is_active': 1 if self.active_check.isChecked() else 0
            }
            
            if self.package_id:
                # Update existing
                query = """
                    UPDATE support_packages
                    SET name = %s, package_type = %s, description = %s,
                        price = %s, duration_months = %s, prepaid_hours = %s,
                        is_active = %s, updated_at = NOW()
                    WHERE id = %s
                """
                self.db.execute_update(
                    query,
                    (data['name'], data['package_type'], data['description'],
                     data['price'], data['duration_months'], data['prepaid_hours'],
                     data['is_active'], self.package_id)
                )
            else:
                # Create new
                query = """
                    INSERT INTO support_packages
                    (name, package_type, description, price, duration_months, prepaid_hours, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.db.execute_update(
                    query,
                    (data['name'], data['package_type'], data['description'],
                     data['price'], data['duration_months'], data['prepaid_hours'],
                     data['is_active'])
                )
            
            self.db.commit()
            
            QMessageBox.information(
                self,
                "Επιτυχία",
                "Το πακέτο αποθηκεύτηκε επιτυχώς"
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving package: {e}")
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα αποθήκευσης:\n{str(e)}"
            )
