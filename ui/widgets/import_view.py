# -*- coding: utf-8 -*-
"""
Import View Widget
Provides interface for importing CSV data (client.csv, members.csv, report.csv).
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QProgressBar,
    QPlainTextEdit, QFileDialog, QMessageBox, QHeaderView, QFormLayout,
    QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from services.import_service import ImportService, ImportResult
from ui.i18n import TranslationManager
from resources.icons import get_icon

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    """
    Worker thread for CSV import operations.
    Runs import in background to keep UI responsive.
    """
    
    # Signals
    progress_updated = Signal(int, int)  # current, total
    import_completed = Signal(object)  # ImportResult
    import_failed = Signal(str)  # error message
    
    def __init__(
        self,
        import_service: ImportService,
        file_path: str,
        import_type: str,
        parent=None
    ):
        """
        Initialize import worker.
        
        Args:
            import_service: ImportService instance
            file_path: Path to CSV file
            import_type: Type of import ('client', 'members', 'report')
            parent: Parent object
        """
        super().__init__(parent)
        self.import_service = import_service
        self.file_path = file_path
        self.import_type = import_type
    
    def run(self):
        """Execute the import operation."""
        try:
            # Select appropriate import method
            if self.import_type == 'client':
                result = self.import_service.import_clients_csv(
                    self.file_path,
                    progress_callback=self._on_progress
                )
            elif self.import_type == 'members':
                result = self.import_service.import_members_csv(
                    self.file_path,
                    progress_callback=self._on_progress
                )
            elif self.import_type == 'report':
                result = self.import_service.import_reports_csv(
                    self.file_path,
                    progress_callback=self._on_progress
                )
            else:
                raise ValueError(f"Unknown import type: {self.import_type}")
            
            self.import_completed.emit(result)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.import_failed.emit(str(e))
    
    def _on_progress(self, current: int, total: int):
        """
        Progress callback from import service.
        
        Args:
            current: Current row number
            total: Total rows
        """
        self.progress_updated.emit(current, total)


class ImportSectionWidget(QWidget):
    """
    Widget for a single CSV import section.
    Contains file picker, preview, progress bar, and log area.
    """
    
    def __init__(
        self,
        title: str,
        import_type: str,
        import_service: ImportService,
        tr_manager: TranslationManager,
        parent=None
    ):
        """
        Initialize import section widget.
        
        Args:
            title: Section title
            import_type: Type of import ('client', 'members', 'report')
            import_service: ImportService instance
            tr_manager: TranslationManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.import_type = import_type
        self.import_service = import_service
        self.tr_manager = tr_manager
        self.file_path = ""
        self.import_worker: Optional[ImportWorker] = None
        
        self._init_ui(title)
        self._connect_signals()
        
        logger.debug(f"ImportSectionWidget initialized: {import_type}")
    
    def _init_ui(self, title: str):
        """Initialize the user interface."""
        # Create group box
        group_box = QGroupBox(title)
        group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)
        
        # Group box layout
        groupbox_layout = QVBoxLayout(group_box)
        groupbox_layout.setContentsMargins(12, 12, 12, 12)
        groupbox_layout.setSpacing(10)
        
        # Form layout for structured fields
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)
        
        # Row 1: Selected file
        self.file_path_label = QLabel(self.tr_manager.get('import_no_file'))
        self.file_path_label.setStyleSheet("color: #757575; font-style: italic;")
        self.file_path_label.setWordWrap(True)
        form_layout.addRow(self.tr_manager.get('import_selected_file') + ":", self.file_path_label)
        
        # Row 2: Preview (small text showing row count)
        self.preview_info_label = QLabel(self.tr_manager.get('import_no_preview'))
        self.preview_info_label.setStyleSheet("color: #757575; font-size: 11px;")
        form_layout.addRow(self.tr_manager.get('import_preview') + ":", self.preview_info_label)
        
        # Row 3: Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        form_layout.addRow(self.tr_manager.get('import_progress') + ":", self.progress_bar)
        
        # Row 4: Log file path
        self.log_path_label = QLabel(self.tr_manager.get('import_no_log'))
        self.log_path_label.setStyleSheet("color: #757575; font-size: 11px;")
        self.log_path_label.setWordWrap(True)
        form_layout.addRow(self.tr_manager.get('import_log_file') + ":", self.log_path_label)
        
        groupbox_layout.addLayout(form_layout)
        
        # Button row (right-aligned)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.select_file_btn = QPushButton(get_icon('search'), self.tr_manager.get('import_select_file'))
        self.select_file_btn.setMinimumWidth(140)
        button_layout.addWidget(self.select_file_btn)
        
        # Add "Select Folder" button for batch import
        self.select_folder_btn = QPushButton(get_icon('search'), "Επιλογή Φακέλου")
        self.select_folder_btn.setMinimumWidth(140)
        self.select_folder_btn.setToolTip("Επιλέξτε φάκελο με πολλά CSV αρχεία για μαζική εισαγωγή")
        button_layout.addWidget(self.select_folder_btn)
        
        groupbox_layout.addLayout(button_layout)
        
        # Import button (centered)
        import_button_layout = QHBoxLayout()
        import_button_layout.addStretch()
        
        self.import_btn = QPushButton(get_icon('import'), self.tr_manager.get('import_start'))
        self.import_btn.setMinimumWidth(180)
        self.import_btn.setEnabled(False)
        import_button_layout.addWidget(self.import_btn)
        
        import_button_layout.addStretch()
        groupbox_layout.addLayout(import_button_layout)
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        self.select_file_btn.clicked.connect(self._on_select_file)
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        self.import_btn.clicked.connect(self._on_import)
    
    def _on_select_file(self):
        """Handle file selection button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr_manager.get('import_select_file'),
            "",
            "CSV/Excel Files (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
        )
        
        if file_path:
            self.file_path = file_path
            # Show just the filename
            file_name = Path(file_path).name
            self.file_path_label.setText(file_name)
            self.file_path_label.setStyleSheet("color: #000000; font-weight: bold;")
            self.file_path_label.setToolTip(file_path)  # Full path in tooltip
            self.import_btn.setEnabled(True)
            
            # Load preview
            self._load_preview()
            
            logger.info(f"File selected: {file_path}")
    
    def _on_select_folder(self):
        """Handle folder selection button click for batch import."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Επιλέξτε φάκελο με CSV αρχεία",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            # Find matching CSV files in folder
            folder = Path(folder_path)
            
            # Search for files based on import type (CSV and Excel)
            matching_files = []
            if self.import_type == 'client':
                matching_files.extend(folder.glob("client*.csv"))
                matching_files.extend(folder.glob("client*.xlsx"))
            elif self.import_type == 'members':
                matching_files.extend(folder.glob("member*.csv"))
                matching_files.extend(folder.glob("member*.xlsx"))
            elif self.import_type == 'report':
                matching_files.extend(folder.glob("report*.csv"))
                matching_files.extend(folder.glob("report*.xlsx"))
            else:
                matching_files.extend(folder.glob("*.csv"))
                matching_files.extend(folder.glob("*.xlsx"))
            
            if not matching_files:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    f"Δεν βρέθηκαν αρχεία που να ταιριάζουν με το μοτίβο '{pattern}' στον φάκελο."
                )
                return
            
            if len(matching_files) > 1:
                # Multiple files found - ask user to select one
                from PySide6.QtWidgets import QInputDialog
                file_names = [f.name for f in matching_files]
                selected_name, ok = QInputDialog.getItem(
                    self,
                    "Επιλογή Αρχείου",
                    f"Βρέθηκαν {len(matching_files)} αρχεία. Επιλέξτε ένα:",
                    file_names,
                    0,
                    False
                )
                
                if ok and selected_name:
                    selected_file = folder / selected_name
                    self.file_path = str(selected_file)
                else:
                    return
            else:
                # Only one file found - use it
                self.file_path = str(matching_files[0])
            
            # Show the selected file
            file_name = Path(self.file_path).name
            self.file_path_label.setText(f"📁 {file_name}")
            self.file_path_label.setStyleSheet("color: #1976d2; font-weight: bold;")
            self.file_path_label.setToolTip(self.file_path)
            self.import_btn.setEnabled(True)
            
            # Load preview
            self._load_preview()
            
            logger.info(f"File selected from folder: {self.file_path}")
    
    def _load_preview(self):
        """Load and display CSV preview."""
        try:
            # Get preview data
            preview_data = self.import_service.preview_csv(self.file_path, rows=10)
            
            if not preview_data:
                self.preview_info_label.setText(self.tr_manager.get('info_no_records'))
                self.preview_info_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
                return
            
            # Get column names from first row
            if preview_data:
                columns = list(preview_data[0].keys())
                preview_text = f"{len(preview_data)} γραμμές, {len(columns)} στήλες"
                self.preview_info_label.setText(preview_text)
                self.preview_info_label.setStyleSheet("color: #2e7d32; font-size: 11px; font-weight: bold;")
            
            logger.debug(f"Preview loaded: {len(preview_data)} rows")
            
        except Exception as e:
            error_msg = f"{self.tr_manager.get('error_file_read')}: {str(e)}"
            self.preview_info_label.setText(error_msg)
            self.preview_info_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
            logger.error(f"Preview load failed: {e}")
            QMessageBox.critical(self, self.tr_manager.get('error_title'), error_msg)
    
    def _on_import(self):
        """Handle import button click."""
        if not self.file_path:
            QMessageBox.warning(
                self,
                self.tr_manager.get('warning_title'),
                self.tr_manager.get('import_no_file')
            )
            return
        
        # Disable import button during import
        self.import_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Εισαγωγή σε εξέλιξη...")
        
        # Update log path
        self.log_path_label.setText("Δημιουργία αρχείου καταγραφής...")
        self.log_path_label.setStyleSheet("color: #1976d2; font-size: 11px;")
        
        # Create and start worker thread
        self.import_worker = ImportWorker(
            self.import_service,
            self.file_path,
            self.import_type,
            self
        )
        
        # Connect worker signals
        self.import_worker.progress_updated.connect(self._on_progress_updated)
        self.import_worker.import_completed.connect(self._on_import_completed)
        self.import_worker.import_failed.connect(self._on_import_failed)
        
        # Start import
        self.import_worker.start()
        
        logger.info(f"Import started: {self.import_type} - {self.file_path}")
    
    def _on_progress_updated(self, current: int, total: int):
        """
        Handle progress update from worker.
        
        Args:
            current: Current row number
            total: Total rows
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} γραμμές ({percentage}%)")
            logger.debug(f"Import progress: {current}/{total} ({percentage}%)")
    
    def _on_import_completed(self, result: ImportResult):
        """
        Handle import completion.
        
        Args:
            result: ImportResult object
        """
        # Update progress bar to 100%
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat(f"Ολοκληρώθηκε - {result.success_count}/{result.total_rows} επιτυχείς")
        
        # Update log path if available
        if hasattr(result, 'log_file') and result.log_file:
            self.log_path_label.setText(str(result.log_file))
            self.log_path_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
            self.log_path_label.setToolTip(str(result.log_file))
        else:
            log_summary = f"✓ {result.success_count} επιτυχείς, ✗ {result.failed_count} αποτυχίες"
            self.log_path_label.setText(log_summary)
            self.log_path_label.setStyleSheet("color: #2e7d32; font-size: 11px; font-weight: bold;")
        
        # Re-enable buttons
        self.import_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        
        # Show success message
        error_details = ""
        if result.errors:
            error_sample = "\n".join(result.errors[:3])
            if len(result.errors) > 3:
                error_sample += f"\n... και {len(result.errors) - 3} ακόμα σφάλματα"
            error_details = f"\n\nΣφάλματα:\n{error_sample}"
        
        QMessageBox.information(
            self,
            self.tr_manager.get('success_title'),
            f"{self.tr_manager.get('import_completed')}\n\n"
            f"{self.tr_manager.get('import_success_rows')}: {result.success_count}\n"
            f"{self.tr_manager.get('import_failed_rows')}: {result.failed_count}\n"
            f"{self.tr_manager.get('import_duration')}: {result.duration_seconds:.2f}s"
            f"{error_details}"
        )
        
        logger.info(
            f"Import completed: {result.success_count} success, "
            f"{result.failed_count} failed, {result.duration_seconds:.2f}s"
        )
    
    def _on_import_failed(self, error_message: str):
        """
        Handle import failure.
        
        Args:
            error_message: Error message
        """
        # Update progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Αποτυχία εισαγωγής")
        
        # Update log path
        self.log_path_label.setText(f"Σφάλμα: {error_message}")
        self.log_path_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
        
        # Re-enable buttons
        self.import_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        
        # Show error message
        QMessageBox.critical(
            self,
            self.tr_manager.get('error_title'),
            f"{self.tr_manager.get('import_failed')}\n\n{error_message}"
        )
        
        logger.error(f"Import failed: {error_message}")
    
    def update_translations(self):
        """Update all UI text when language changes."""
        self.select_file_btn.setText(self.tr_manager.get('import_select_file'))
        self.import_btn.setText(self.tr_manager.get('import_start'))
        
        if not self.file_path:
            self.file_path_label.setText(self.tr_manager.get('import_no_file'))
            self.preview_info_label.setText(self.tr_manager.get('import_no_preview'))
            self.log_path_label.setText(self.tr_manager.get('import_no_log'))


class ImportView(QWidget):
    """
    Main import view widget.
    Provides interface for importing all three CSV types.
    """
    
    def __init__(
        self,
        import_service: ImportService,
        tr_manager: TranslationManager,
        parent=None
    ):
        """
        Initialize ImportView.
        
        Args:
            import_service: ImportService instance
            tr_manager: TranslationManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.import_service = import_service
        self.tr_manager = tr_manager
        
        self._init_ui()
        
        logger.debug("ImportView initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel(self.tr_manager.get('import_title'))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Add spacing after title
        layout.addSpacing(10)
        
        # Create three import sections
        self.clients_section = ImportSectionWidget(
            self.tr_manager.get('import_clients'),
            'client',
            self.import_service,
            self.tr_manager,
            self
        )
        layout.addWidget(self.clients_section)
        
        # Add spacing between sections
        layout.addSpacing(20)
        
        self.reports_section = ImportSectionWidget(
            self.tr_manager.get('import_reports'),
            'report',
            self.import_service,
            self.tr_manager,
            self
        )
        layout.addWidget(self.reports_section)
        
        # Add stretch to push sections to top
        layout.addStretch()
    
    def update_translations(self):
        """Update all UI text when language changes."""
        # Update section widgets
        self.clients_section.update_translations()
        self.reports_section.update_translations()
        
        logger.debug("ImportView translations updated")
    
    def refresh(self):
        """Refresh view (placeholder for consistency with other views)."""
        logger.debug("ImportView refresh called")
