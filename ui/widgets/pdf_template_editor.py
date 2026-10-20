# -*- coding: utf-8 -*-
"""
PDF Template Editor - Visual editor for PDF templates with grid, zoom, and draggable fields.
"""

import logging
import json
from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QPushButton, QComboBox, QLabel, QSpinBox, QToolBar,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QColorDialog,
    QGraphicsItem, QSlider, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QScrollArea,
    QStyledItemDelegate
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSizeF, QModelIndex
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPainter, QFont, QPixmap,
    QWheelEvent, QMouseEvent, QKeyEvent
)

from resources.icons import get_icon

logger = logging.getLogger(__name__)

# A4 dimensions in points (72 dpi)
A4_WIDTH = 595
A4_HEIGHT = 842

# Grid settings
GRID_SIZE = 20  # pixels


class AlignmentDelegate(QStyledItemDelegate):
    """Delegate for alignment column with dropdown selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = ["Αριστερά", "Κέντρο", "Δεξιά"]
    
    def createEditor(self, parent, option, index):
        """Create combo box editor."""
        combo = QComboBox(parent)
        combo.addItems(self.items)
        return combo
    
    def setEditorData(self, editor, index):
        """Set current value in combo box."""
        value = index.data(Qt.DisplayRole)
        idx = self.items.index(value) if value in self.items else 0
        editor.setCurrentIndex(idx)
    
    def setModelData(self, editor, model, index):
        """Save selected value to model."""
        model.setData(index, editor.currentText(), Qt.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        """Set editor geometry to cell bounds."""
        editor.setGeometry(option.rect)

# Available database fields for each template type
DATABASE_FIELDS = {
    'family': [
        ('{client_name}', 'Όνομα Πελάτη'),
        ('{first_name}', 'Όνομα'),
        ('{last_name}', 'Επώνυμο'),
        ('{aspe}', 'Αριθμός ΑΣΠΕ'),
        ('{phone}', 'Τηλέφωνο'),
        ('{email}', 'Email'),
        ('{address}', 'Διεύθυνση'),
        ('{city}', 'Πόλη'),
        ('{postal_code}', 'Τ.Κ.'),
        ('{members_count}', 'Αριθμός Μελών'),
        ('{family_code}', 'Κωδικός Πελάτη'),
        ('{registration_date}', 'Ημ/νία Εγγραφής'),
        # Πεδία Μελών (για πίνακες)
        ('{member_first_name}', 'Όνομα Μέλους'),
        ('{member_last_name}', 'Επώνυμο Μέλους'),
        ('{member_mother_name}', 'Όνομα Μητρός'),
        ('{member_national_id}', 'ΑΣΠΕ Μέλους'),
        ('{member_profession}', 'Επάγγελμα'),
        ('{member_birth_date}', 'Ημ/νία Γέννησης'),
        ('{member_is_married}', 'Παντρεμένος/η (Ναι/Όχι)'),
        ('{member_marriage_date}', 'Ημ/νία Γάμου'),
        ('{member_is_deceased}', 'Αποθανών/ούσα (Ναι/Όχι)'),
        ('{member_is_disabled}', 'ΑΜΕΑ (Ναι/Όχι)'),
    ],
    'payment': [
        ('{client_name}', 'Όνομα Πελάτη'),
        ('{first_name}', 'Όνομα'),
        ('{last_name}', 'Επώνυμο'),
        ('{receipt_no}', 'Αριθμός Απόδειξης'),
        ('{payment_date}', 'Ημερομηνία Πληρωμής'),
        ('{description}', 'Περιγραφή'),
        ('{amount}', 'Ποσό'),
        ('{total_amount}', 'Συνολικό Ποσό'),
        ('{paid_amount}', 'Πληρωμένο Ποσό'),
        ('{remaining}', 'Υπόλοιπο'),
        ('{remarks}', 'Παρατηρήσεις'),
        ('{subscription_code}', 'Κωδικός Συνδρομής'),
        ('{year}', 'Έτος'),
    ],
    'subscription': [
        ('{client_name}', 'Όνομα Πελάτη'),
        ('{year}', 'Έτος'),
        ('{start_date}', 'Ημ/νία Έναρξης'),
        ('{end_date}', 'Ημ/νία Λήξης'),
        ('{status}', 'Κατάσταση'),
        ('{subscription_code}', 'Κωδικός Συνδρομής'),
        ('{total_amount}', 'Συνολικό Ποσό'),
        ('{paid_amount}', 'Πληρωμένο'),
        ('{remaining}', 'Υπόλοιπο'),
    ],
    'member': [
        ('{member_first_name}', 'Όνομα Μέλους'),
        ('{member_last_name}', 'Επώνυμο Μέλους'),
        ('{member_mother_name}', 'Όνομα Μητρός'),
        ('{member_national_id}', 'ΑΣΠΕ Μέλους'),
        ('{member_profession}', 'Επάγγελμα'),
        ('{member_birth_date}', 'Ημ/νία Γέννησης'),
        ('{member_is_married}', 'Παντρεμένος/η (Ναι/Όχι)'),
        ('{member_marriage_date}', 'Ημ/νία Γάμου'),
        ('{member_is_deceased}', 'Αποθανών/ούσα (Ναι/Όχι)'),
        ('{member_is_disabled}', 'ΑΜΕΑ (Ναι/Όχι)'),
    ],
    'common': [
        ('{org_name}', 'Όνομα Οργανισμού'),
        ('{org_address}', 'Διεύθυνση Οργανισμού'),
        ('{org_phone}', 'Τηλέφωνο Οργανισμού'),
        ('{org_email}', 'Email Οργανισμού'),
        ('{org_afm}', 'ΑΦΜ Οργανισμού'),
        ('{date}', 'Σημερινή Ημερομηνία'),
        ('{time}', 'Τρέχουσα Ώρα'),
    ]
}


class DraggableField(QGraphicsRectItem):
    """A draggable field on the PDF canvas."""
    
    def __init__(self, field_type: str, x: float, y: float, width: float, height: float, 
                 content: str = "", field_id: str = "", extra_data: Dict = None, parent=None):
        super().__init__(0, 0, width, height, parent)
        self.setPos(x, y)
        
        self.field_type = field_type  # 'text', 'image', 'table', 'db_field', 'header', 'footer'
        self.field_id = field_id or f"{field_type}_{id(self)}"
        self.content = content
        self.extra_data = extra_data or {}  # For table columns, image path, font settings, etc.
        
        # Make it draggable and selectable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # Styling based on type
        self._setup_style()
        
        # Add text label
        self.text_item = QGraphicsTextItem(self)
        self._update_display()
        
        # Image preview (for image fields)
        self.image_item = None
        if field_type == 'image' and self.extra_data.get('image_path'):
            self._load_image_preview()
    
    def _setup_style(self):
        """Setup visual style based on field type."""
        colors = {
            'text': QColor(200, 220, 255, 180),
            'image': QColor(220, 255, 200, 180),
            'table': QColor(255, 220, 200, 180),
            'db_field': QColor(255, 255, 200, 180),
            'header': QColor(200, 200, 255, 180),
            'footer': QColor(255, 200, 255, 180),
        }
        
        border_colors = {
            'text': QColor(100, 150, 255),
            'image': QColor(100, 200, 100),
            'table': QColor(255, 150, 100),
            'db_field': QColor(200, 200, 100),
            'header': QColor(100, 100, 200),
            'footer': QColor(200, 100, 200),
        }
        
        color = colors.get(self.field_type, QColor(200, 200, 200, 180))
        border = border_colors.get(self.field_type, QColor(150, 150, 150))
        
        self.setBrush(QBrush(color))
        self.setPen(QPen(border, 2))
    
    def _update_display(self):
        """Update the text display."""
        if self.field_type == 'table':
            cols = self.extra_data.get('columns', [])
            display_text = f"[Πίνακας: {len(cols)} στήλες]"
        elif self.field_type == 'image':
            path = self.extra_data.get('image_path', '')
            if path:
                display_text = f"[Εικόνα: {path.split('/')[-1]}]"
            else:
                display_text = "[Εικόνα]"
        elif self.field_type == 'db_field':
            display_text = self.content or "[Πεδίο Βάσης]"
        else:
            display_text = self.content if self.content else f"[{self.field_type}]"
        
        if len(display_text) > 40:
            display_text = display_text[:37] + "..."
        
        self.text_item.setPlainText(display_text)
        
        # Apply font settings
        font = QFont()
        font.setPointSize(self.extra_data.get('font_size', 10))
        font.setBold(self.extra_data.get('font_bold', False))
        font.setItalic(self.extra_data.get('font_italic', False))
        self.text_item.setFont(font)
        
        # Center text in field
        text_rect = self.text_item.boundingRect()
        field_rect = self.rect()
        x = (field_rect.width() - text_rect.width()) / 2
        y = (field_rect.height() - text_rect.height()) / 2
        self.text_item.setPos(max(2, x), max(2, y))
    
    def _load_image_preview(self):
        """Load and display image preview."""
        path = self.extra_data.get('image_path', '')
        if path:
            try:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    # Scale to fit
                    scaled = pixmap.scaled(
                        int(self.rect().width() - 4),
                        int(self.rect().height() - 4),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    if self.image_item:
                        self.image_item.setPixmap(scaled)
                    else:
                        self.image_item = QGraphicsPixmapItem(scaled, self)
                        self.image_item.setPos(2, 2)
                    self.text_item.setVisible(False)
            except Exception as e:
                logger.error(f"Failed to load image: {e}")
    
    def itemChange(self, change, value):
        """Handle item changes for snap-to-grid."""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            x = round(new_pos.x() / GRID_SIZE) * GRID_SIZE
            y = round(new_pos.y() / GRID_SIZE) * GRID_SIZE
            return QPointF(x, y)
        return super().itemChange(change, value)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit field."""
        if self.scene() and hasattr(self.scene(), 'field_double_clicked'):
            self.scene().field_double_clicked.emit(self)
        super().mouseDoubleClickEvent(event)
    
    def to_dict(self) -> Dict:
        """Convert field to dictionary for saving."""
        return {
            'field_id': self.field_id,
            'field_type': self.field_type,
            'x': self.pos().x(),
            'y': self.pos().y(),
            'width': self.rect().width(),
            'height': self.rect().height(),
            'content': self.content,
            'extra_data': self.extra_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DraggableField':
        """Create field from dictionary."""
        field = cls(
            field_type=data.get('field_type', 'text'),
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 100),
            height=data.get('height', 30),
            content=data.get('content', ''),
            field_id=data.get('field_id', ''),
            extra_data=data.get('extra_data', {})
        )
        return field


class PDFCanvas(QGraphicsScene):
    """Graphics scene representing the PDF page with grid."""
    
    field_double_clicked = Signal(object)
    field_selected = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, A4_WIDTH, A4_HEIGHT)
        self.grid_visible = True
        self.fields: List[DraggableField] = []
        
        # Draw page background
        self._draw_page_background()
    
    def _draw_page_background(self):
        """Draw the white page background."""
        page_rect = QGraphicsRectItem(0, 0, A4_WIDTH, A4_HEIGHT)
        page_rect.setBrush(QBrush(Qt.white))
        page_rect.setPen(QPen(QColor(200, 200, 200), 1))
        page_rect.setZValue(-10)
        self.addItem(page_rect)
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw grid background."""
        super().drawBackground(painter, rect)
        
        if not self.grid_visible:
            return
        
        pen = QPen(QColor(230, 230, 230), 0.5)
        painter.setPen(pen)
        
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        for x in range(left, int(rect.right()), GRID_SIZE):
            if 0 <= x <= A4_WIDTH:
                painter.drawLine(x, max(0, int(rect.top())), x, min(A4_HEIGHT, int(rect.bottom())))
        
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        for y in range(top, int(rect.bottom()), GRID_SIZE):
            if 0 <= y <= A4_HEIGHT:
                painter.drawLine(max(0, int(rect.left())), y, min(A4_WIDTH, int(rect.right())), y)
    
    def add_field(self, field_type: str, x: float = 50, y: float = 50, 
                  width: float = 150, height: float = 40, content: str = "",
                  extra_data: Dict = None) -> DraggableField:
        """Add a new field to the canvas."""
        field = DraggableField(field_type, x, y, width, height, content, extra_data=extra_data)
        self.addItem(field)
        self.fields.append(field)
        return field
    
    def remove_selected_fields(self):
        """Remove all selected fields."""
        for item in self.selectedItems():
            if isinstance(item, DraggableField):
                self.fields.remove(item)
                self.removeItem(item)
    
    def get_template_data(self) -> Dict:
        """Get all fields as template data."""
        return {
            'page_width': A4_WIDTH,
            'page_height': A4_HEIGHT,
            'fields': [field.to_dict() for field in self.fields]
        }
    
    def load_template_data(self, data: Dict):
        """Load template from data."""
        for field in self.fields[:]:
            self.removeItem(field)
        self.fields.clear()
        
        for field_data in data.get('fields', []):
            field = DraggableField.from_dict(field_data)
            self.addItem(field)
            self.fields.append(field)


class PDFCanvasView(QGraphicsView):
    """Graphics view with zoom support."""
    
    def __init__(self, scene: PDFCanvas, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self.zoom_factor = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def zoom_in(self):
        if self.zoom_factor < self.max_zoom:
            self.zoom_factor *= 1.1
            self.setTransform(self.transform().scale(1.1, 1.1))
    
    def zoom_out(self):
        if self.zoom_factor > self.min_zoom:
            self.zoom_factor /= 1.1
            self.setTransform(self.transform().scale(1/1.1, 1/1.1))
    
    def zoom_reset(self):
        self.resetTransform()
        self.zoom_factor = 1.0
    
    def zoom_fit(self):
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        self.zoom_factor = self.transform().m11()
    
    def set_zoom(self, percent: int):
        factor = percent / 100.0
        self.resetTransform()
        self.scale(factor, factor)
        self.zoom_factor = factor


class FieldEditDialog(QDialog):
    """Dialog for editing field properties with tabs for different settings."""
    
    def __init__(self, field: DraggableField, template_type: str = 'family', parent=None):
        super().__init__(parent)
        self.field = field
        self.template_type = template_type
        self.setWindowTitle(f"Επεξεργασία: {field.field_type}")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        self.resize(700, 550)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for different settings
        tabs = QTabWidget()
        
        # Basic tab
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Βασικά")
        
        # Content tab (for text/db_field)
        if self.field.field_type in ['text', 'db_field', 'header', 'footer']:
            content_tab = self._create_content_tab()
            tabs.addTab(content_tab, "Περιεχόμενο")
        
        # Table tab (for table fields)
        if self.field.field_type == 'table':
            table_tab = self._create_table_tab()
            tabs.addTab(table_tab, "Στήλες Πίνακα")
        
        # Image tab (for image fields)
        if self.field.field_type == 'image':
            image_tab = self._create_image_tab()
            tabs.addTab(image_tab, "Εικόνα")
        
        # Font tab
        font_tab = self._create_font_tab()
        tabs.addTab(font_tab, "Γραμματοσειρά")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _create_basic_tab(self) -> QWidget:
        """Create basic settings tab."""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)
        
        # Field ID
        self.id_input = QLineEdit(self.field.field_id)
        form.addRow("ID Πεδίου:", self.id_input)
        
        # Position - X and Y on same row
        pos_layout = QHBoxLayout()
        pos_layout.setSpacing(15)
        
        x_label = QLabel("X:")
        x_label.setFixedWidth(20)
        pos_layout.addWidget(x_label)
        
        self.x_input = QSpinBox()
        self.x_input.setRange(0, A4_WIDTH)
        self.x_input.setValue(int(self.field.pos().x()))
        self.x_input.setMinimumWidth(80)
        pos_layout.addWidget(self.x_input)
        
        pos_layout.addSpacing(20)
        
        y_label = QLabel("Y:")
        y_label.setFixedWidth(20)
        pos_layout.addWidget(y_label)
        
        self.y_input = QSpinBox()
        self.y_input.setRange(0, A4_HEIGHT)
        self.y_input.setValue(int(self.field.pos().y()))
        self.y_input.setMinimumWidth(80)
        pos_layout.addWidget(self.y_input)
        
        pos_layout.addStretch()
        form.addRow("Θέση:", pos_layout)
        
        # Size - Width and Height on same row
        size_layout = QHBoxLayout()
        size_layout.setSpacing(15)
        
        width_label = QLabel("Πλάτος:")
        width_label.setFixedWidth(50)
        size_layout.addWidget(width_label)
        
        self.width_input = QSpinBox()
        self.width_input.setRange(20, A4_WIDTH)
        self.width_input.setValue(int(self.field.rect().width()))
        self.width_input.setMinimumWidth(80)
        size_layout.addWidget(self.width_input)
        
        size_layout.addSpacing(20)
        
        height_label = QLabel("Ύψος:")
        height_label.setFixedWidth(40)
        size_layout.addWidget(height_label)
        
        self.height_input = QSpinBox()
        self.height_input.setRange(20, A4_HEIGHT)
        self.height_input.setValue(int(self.field.rect().height()))
        self.height_input.setMinimumWidth(80)
        size_layout.addWidget(self.height_input)
        
        size_layout.addStretch()
        form.addRow("Μέγεθος:", size_layout)
        
        return tab
    
    def _create_content_tab(self) -> QWidget:
        """Create content editing tab with database fields."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Database fields section
        db_group = QGroupBox("Πεδία Βάσης Δεδομένων")
        db_layout = QVBoxLayout(db_group)
        
        db_label = QLabel("Κάντε κλικ για να προσθέσετε στο περιεχόμενο:")
        db_layout.addWidget(db_label)
        
        # Fields list
        self.db_fields_list = QListWidget()
        self.db_fields_list.setMaximumHeight(150)
        
        # Add common fields
        for field_code, field_name in DATABASE_FIELDS.get('common', []):
            item = QListWidgetItem(f"{field_name} → {field_code}")
            item.setData(Qt.UserRole, field_code)
            self.db_fields_list.addItem(item)
        
        # Add template-specific fields
        for field_code, field_name in DATABASE_FIELDS.get(self.template_type, []):
            item = QListWidgetItem(f"{field_name} → {field_code}")
            item.setData(Qt.UserRole, field_code)
            self.db_fields_list.addItem(item)
        
        self.db_fields_list.itemDoubleClicked.connect(self._insert_db_field)
        db_layout.addWidget(self.db_fields_list)
        
        layout.addWidget(db_group)
        
        # Content editor
        content_group = QGroupBox("Περιεχόμενο")
        content_layout = QVBoxLayout(content_group)
        
        self.content_input = QTextEdit()
        self.content_input.setPlainText(self.field.content)
        self.content_input.setMinimumHeight(100)
        content_layout.addWidget(self.content_input)
        
        layout.addWidget(content_group)
        
        return tab
    
    def _create_table_tab(self) -> QWidget:
        """Create table columns editing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table options row
        options_layout = QHBoxLayout()
        
        # Orientation option
        options_layout.addWidget(QLabel("Προσανατολισμός:"))
        self.table_orientation_combo = QComboBox()
        self.table_orientation_combo.addItems(["Οριζόντια (headers πάνω)", "Κάθετα (headers αριστερά)"])
        current_orientation = self.field.extra_data.get('orientation', 'horizontal')
        self.table_orientation_combo.setCurrentIndex(0 if current_orientation == 'horizontal' else 1)
        options_layout.addWidget(self.table_orientation_combo)
        
        options_layout.addSpacing(20)
        
        # Row height option
        options_layout.addWidget(QLabel("Ύψος γραμμής:"))
        self.row_height_input = QSpinBox()
        self.row_height_input.setRange(15, 100)
        self.row_height_input.setValue(self.field.extra_data.get('row_height', 22))
        self.row_height_input.setSuffix(" px")
        self.row_height_input.setFixedWidth(80)
        options_layout.addWidget(self.row_height_input)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        layout.addWidget(QLabel("Ορίστε τις στήλες του πίνακα:"))
        
        # Columns table
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(4)
        self.columns_table.setHorizontalHeaderLabels(["Τίτλος Στήλης", "Πεδίο Βάσης", "Πλάτος %", "Στοίχιση"])
        
        # Make table stretch to fill available space
        header = self.columns_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.columns_table.setColumnWidth(2, 80)
        self.columns_table.setColumnWidth(3, 100)
        
        # Set delegate for alignment column (column 3) - dropdown on click
        self.alignment_delegate = AlignmentDelegate(self.columns_table)
        self.columns_table.setItemDelegateForColumn(3, self.alignment_delegate)
        
        # Set minimum height for table
        self.columns_table.setMinimumHeight(150)
        
        # Load existing columns
        columns = self.field.extra_data.get('columns', [])
        row_count = len(columns) if columns else 2
        self.columns_table.setRowCount(row_count)
        
        # Alignment display map
        align_display = {'left': 'Αριστερά', 'center': 'Κέντρο', 'right': 'Δεξιά'}
        
        for i, col in enumerate(columns):
            self.columns_table.setItem(i, 0, QTableWidgetItem(col.get('title', '')))
            self.columns_table.setItem(i, 1, QTableWidgetItem(col.get('field', '')))
            self.columns_table.setItem(i, 2, QTableWidgetItem(str(col.get('width', 50))))
            # Alignment - will show dropdown on click
            align_value = col.get('align', 'left')
            self.columns_table.setItem(i, 3, QTableWidgetItem(align_display.get(align_value, 'Αριστερά')))
        
        # Add default values for empty rows
        for i in range(len(columns), row_count):
            self.columns_table.setItem(i, 0, QTableWidgetItem(''))
            self.columns_table.setItem(i, 1, QTableWidgetItem(''))
            self.columns_table.setItem(i, 2, QTableWidgetItem('50'))
            self.columns_table.setItem(i, 3, QTableWidgetItem('Αριστερά'))
        
        layout.addWidget(self.columns_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_col_btn = QPushButton("+ Προσθήκη Στήλης")
        add_col_btn.clicked.connect(self._add_table_column)
        btn_layout.addWidget(add_col_btn)
        
        remove_col_btn = QPushButton("- Αφαίρεση Στήλης")
        remove_col_btn.clicked.connect(lambda: self.columns_table.removeRow(self.columns_table.currentRow()))
        btn_layout.addWidget(remove_col_btn)
        
        layout.addLayout(btn_layout)
        
        # Available fields
        layout.addWidget(QLabel("Διαθέσιμα πεδία για στήλες:"))
        fields_text = ", ".join([f[0] for f in DATABASE_FIELDS.get(self.template_type, [])])
        fields_label = QLabel(fields_text)
        fields_label.setWordWrap(True)
        fields_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(fields_label)
        
        return tab
    
    def _add_table_column(self):
        """Add a new column to the table."""
        row = self.columns_table.rowCount()
        self.columns_table.setRowCount(row + 1)
        self.columns_table.setItem(row, 0, QTableWidgetItem(''))
        self.columns_table.setItem(row, 1, QTableWidgetItem(''))
        self.columns_table.setItem(row, 2, QTableWidgetItem('50'))
        self.columns_table.setItem(row, 3, QTableWidgetItem('Αριστερά'))
    
    def _create_image_tab(self) -> QWidget:
        """Create image selection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Current image
        self.image_path_label = QLabel(self.field.extra_data.get('image_path', 'Δεν έχει επιλεγεί εικόνα'))
        self.image_path_label.setWordWrap(True)
        layout.addWidget(self.image_path_label)
        
        # Preview
        self.image_preview = QLabel()
        self.image_preview.setMinimumHeight(150)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        
        path = self.field.extra_data.get('image_path', '')
        if path:
            self._load_image_preview(path)
        else:
            self.image_preview.setText("Προεπισκόπηση")
        
        layout.addWidget(self.image_preview)
        
        # Select button
        select_btn = QPushButton("Επιλογή Εικόνας...")
        select_btn.clicked.connect(self._select_image)
        layout.addWidget(select_btn)
        
        # Use logo checkbox
        self.use_logo_checkbox = QCheckBox("Χρήση Logo Συλλόγου")
        self.use_logo_checkbox.setChecked(self.field.extra_data.get('use_logo', False))
        layout.addWidget(self.use_logo_checkbox)
        
        layout.addStretch()
        
        return tab
    
    def _create_font_tab(self) -> QWidget:
        """Create font settings tab."""
        tab = QWidget()
        form = QFormLayout(tab)
        
        # Font size
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(6, 72)
        self.font_size_input.setValue(self.field.extra_data.get('font_size', 12))
        form.addRow("Μέγεθος:", self.font_size_input)
        
        # Bold
        self.font_bold_checkbox = QCheckBox("Έντονα")
        self.font_bold_checkbox.setChecked(self.field.extra_data.get('font_bold', False))
        form.addRow("", self.font_bold_checkbox)
        
        # Italic
        self.font_italic_checkbox = QCheckBox("Πλάγια")
        self.font_italic_checkbox.setChecked(self.field.extra_data.get('font_italic', False))
        form.addRow("", self.font_italic_checkbox)
        
        # Alignment
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Αριστερά", "Κέντρο", "Δεξιά"])
        align_map = {'left': 0, 'center': 1, 'right': 2}
        self.align_combo.setCurrentIndex(align_map.get(self.field.extra_data.get('align', 'left'), 0))
        form.addRow("Στοίχιση:", self.align_combo)
        
        return tab
    
    def _insert_db_field(self, item: QListWidgetItem):
        """Insert database field into content."""
        field_code = item.data(Qt.UserRole)
        if hasattr(self, 'content_input'):
            cursor = self.content_input.textCursor()
            cursor.insertText(field_code)
    
    def _select_image(self):
        """Select image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Επιλογή Εικόνας", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.image_path_label.setText(file_path)
            self._load_image_preview(file_path)
    
    def _load_image_preview(self, path: str):
        """Load image preview."""
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview.setPixmap(scaled)
        except Exception as e:
            logger.error(f"Failed to load image preview: {e}")
    
    def get_values(self) -> Dict:
        """Get all edited values."""
        values = {
            'field_id': self.id_input.text(),
            'x': self.x_input.value(),
            'y': self.y_input.value(),
            'width': self.width_input.value(),
            'height': self.height_input.value(),
            'extra_data': {
                'font_size': self.font_size_input.value(),
                'font_bold': self.font_bold_checkbox.isChecked(),
                'font_italic': self.font_italic_checkbox.isChecked(),
                'align': ['left', 'center', 'right'][self.align_combo.currentIndex()]
            }
        }
        
        # Content
        if hasattr(self, 'content_input'):
            values['content'] = self.content_input.toPlainText()
        else:
            values['content'] = self.field.content
        
        # Table columns
        if hasattr(self, 'columns_table'):
            columns = []
            # Map Greek text to alignment values
            align_text_map = {
                'αριστερά': 'left', 'αριστερα': 'left', 'left': 'left',
                'κέντρο': 'center', 'κεντρο': 'center', 'center': 'center',
                'δεξιά': 'right', 'δεξια': 'right', 'right': 'right'
            }
            
            for row in range(self.columns_table.rowCount()):
                title_item = self.columns_table.item(row, 0)
                field_item = self.columns_table.item(row, 1)
                width_item = self.columns_table.item(row, 2)
                align_item = self.columns_table.item(row, 3)
                
                if title_item and title_item.text():
                    # Get alignment from text
                    align_value = 'left'
                    if align_item and align_item.text():
                        align_text = align_item.text().lower().strip()
                        align_value = align_text_map.get(align_text, 'left')
                    
                    columns.append({
                        'title': title_item.text(),
                        'field': field_item.text() if field_item else '',
                        'width': int(width_item.text()) if width_item and width_item.text().isdigit() else 50,
                        'align': align_value
                    })
            values['extra_data']['columns'] = columns
            
            # Table orientation
            if hasattr(self, 'table_orientation_combo'):
                orientation = 'horizontal' if self.table_orientation_combo.currentIndex() == 0 else 'vertical'
                values['extra_data']['orientation'] = orientation
            
            if hasattr(self, 'row_height_input'):
                values['extra_data']['row_height'] = self.row_height_input.value()
        
        # Image
        if hasattr(self, 'image_path_label'):
            path = self.image_path_label.text()
            if path != 'Δεν έχει επιλεγεί εικόνα':
                values['extra_data']['image_path'] = path
            values['extra_data']['use_logo'] = self.use_logo_checkbox.isChecked()
        
        return values


class PDFTemplateEditor(QWidget):
    """Main PDF Template Editor widget."""
    
    template_saved = Signal(str, dict)
    
    def __init__(self, settings_service=None, template_type: str = 'family', parent=None):
        super().__init__(parent)
        self.settings_service = settings_service
        self.template_type = template_type
        self.current_template_name = ""
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Field types and DB fields
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Center - Canvas
        self.canvas = PDFCanvas()
        self.canvas_view = PDFCanvasView(self.canvas)
        splitter.addWidget(self.canvas_view)
        
        # Right panel - Properties
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([180, 500, 180])
        layout.addWidget(splitter)
        
        # Status bar
        self.status_label = QLabel("Έτοιμο - Διπλό κλικ σε πεδίο για επεξεργασία")
        layout.addWidget(self.status_label)
    
    def _create_toolbar(self) -> QToolBar:
        """Create the toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # Template selector
        toolbar.addWidget(QLabel("Template: "))
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "Απόδειξη Πληρωμής",
            "Βεβαίωση Εγγραφής",
            "Βεβαίωση Συνδρομής"
        ])
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        toolbar.addWidget(self.template_combo)
        
        toolbar.addSeparator()
        
        # Zoom controls
        toolbar.addWidget(QLabel(" Zoom: "))
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedWidth(30)
        self.zoom_out_btn.clicked.connect(lambda: self.canvas_view.zoom_out())
        toolbar.addWidget(self.zoom_out_btn)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(25, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(self.zoom_slider)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedWidth(30)
        self.zoom_in_btn.clicked.connect(lambda: self.canvas_view.zoom_in())
        toolbar.addWidget(self.zoom_in_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        toolbar.addWidget(self.zoom_label)
        
        self.zoom_fit_btn = QPushButton("Προσαρμογή")
        self.zoom_fit_btn.clicked.connect(self._on_zoom_fit)
        toolbar.addWidget(self.zoom_fit_btn)
        
        toolbar.addSeparator()
        
        # Grid toggle
        self.grid_checkbox = QCheckBox("Πλέγμα")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self._on_grid_toggled)
        toolbar.addWidget(self.grid_checkbox)
        
        toolbar.addSeparator()
        
        # Save/Load
        self.save_btn = QPushButton(get_icon('export'), "Αποθήκευση")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.save_btn.clicked.connect(self._on_save)
        toolbar.addWidget(self.save_btn)
        
        self.load_btn = QPushButton(get_icon('import'), "Φόρτωση")
        self.load_btn.clicked.connect(self._on_load)
        toolbar.addWidget(self.load_btn)
        
        return toolbar
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with field types and database fields."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMinimumWidth(170)
        layout = QVBoxLayout(panel)
        
        # Field types section
        layout.addWidget(QLabel("Προσθήκη Πεδίου:"))
        
        field_types = [
            ("Κείμενο", "text", "edit"),
            ("Εικόνα", "image", "export"),
            ("Πίνακας", "table", "reports"),
            ("Πεδίο Βάσης", "db_field", "search"),
            ("Κεφαλίδα", "header", "families"),
            ("Υποσέλιδο", "footer", "families"),
        ]
        
        for label, field_type, icon_name in field_types:
            btn = QPushButton(get_icon(icon_name), label)
            btn.clicked.connect(lambda checked, ft=field_type: self._add_field(ft))
            layout.addWidget(btn)
        
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Πεδία Βάσης:"))
        
        # Database fields list
        self.db_fields_list = QListWidget()
        self.db_fields_list.setMaximumHeight(200)
        self._populate_db_fields()
        self.db_fields_list.itemDoubleClicked.connect(self._add_db_field_from_list)
        layout.addWidget(self.db_fields_list)
        
        layout.addStretch()
        
        # Delete button
        self.delete_btn = QPushButton(get_icon('delete'), "Διαγραφή")
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.delete_btn.clicked.connect(self._delete_selected)
        layout.addWidget(self.delete_btn)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Create right panel with field list."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMinimumWidth(170)
        layout = QVBoxLayout(panel)
        
        layout.addWidget(QLabel("Πεδία Template:"))
        
        self.fields_list = QListWidget()
        self.fields_list.itemDoubleClicked.connect(self._on_field_list_double_clicked)
        layout.addWidget(self.fields_list)
        
        refresh_btn = QPushButton(get_icon('refresh'), "Ανανέωση")
        refresh_btn.clicked.connect(self._refresh_fields_list)
        layout.addWidget(refresh_btn)
        
        return panel
    
    def _populate_db_fields(self):
        """Populate database fields list."""
        self.db_fields_list.clear()
        
        # Common fields
        for field_code, field_name in DATABASE_FIELDS.get('common', []):
            item = QListWidgetItem(f"{field_name}")
            item.setData(Qt.UserRole, field_code)
            item.setToolTip(field_code)
            self.db_fields_list.addItem(item)
        
        # Template-specific fields
        for field_code, field_name in DATABASE_FIELDS.get(self.template_type, []):
            item = QListWidgetItem(f"{field_name}")
            item.setData(Qt.UserRole, field_code)
            item.setToolTip(field_code)
            self.db_fields_list.addItem(item)
    
    def _connect_signals(self):
        """Connect signals."""
        self.canvas.field_double_clicked.connect(self._on_field_double_clicked)
    
    def _add_field(self, field_type: str):
        """Add a new field to the canvas."""
        sizes = {
            'text': (200, 40),
            'image': (150, 100),
            'table': (A4_WIDTH - 100, 150),
            'db_field': (150, 30),
            'header': (A4_WIDTH - 100, 60),
            'footer': (A4_WIDTH - 100, 40),
        }
        width, height = sizes.get(field_type, (150, 40))
        
        y_positions = {
            'header': 20,
            'footer': A4_HEIGHT - 80,
        }
        y = y_positions.get(field_type, 100)
        
        extra_data = {'font_size': 12}
        if field_type == 'table':
            extra_data['columns'] = [
                {'title': 'Στήλη 1', 'field': '', 'width': 50},
                {'title': 'Στήλη 2', 'field': '', 'width': 50}
            ]
        
        field = self.canvas.add_field(field_type, 50, y, width, height, extra_data=extra_data)
        self._refresh_fields_list()
        self.status_label.setText(f"Προστέθηκε: {field_type} - Διπλό κλικ για επεξεργασία")
    
    def _add_db_field_from_list(self, item: QListWidgetItem):
        """Add database field from list."""
        field_code = item.data(Qt.UserRole)
        field_name = item.text()
        
        field = self.canvas.add_field('db_field', 50, 100, 180, 30, content=field_code)
        self._refresh_fields_list()
        self.status_label.setText(f"Προστέθηκε πεδίο: {field_name}")
    
    def _delete_selected(self):
        """Delete selected fields."""
        self.canvas.remove_selected_fields()
        self._refresh_fields_list()
        self.status_label.setText("Διαγράφηκαν τα επιλεγμένα πεδία")
    
    def _on_field_double_clicked(self, field: DraggableField):
        """Handle field double-click for editing."""
        dialog = FieldEditDialog(field, self.template_type, self)
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            field.field_id = values['field_id']
            field.content = values['content']
            field.setPos(values['x'], values['y'])
            field.setRect(0, 0, values['width'], values['height'])
            field.extra_data.update(values['extra_data'])
            field._update_display()
            if field.field_type == 'image':
                field._load_image_preview()
            self._refresh_fields_list()
            self.status_label.setText(f"Ενημερώθηκε: {field.field_id}")
    
    def _on_field_list_double_clicked(self, item: QListWidgetItem):
        """Handle field list double-click."""
        field_id = item.data(Qt.UserRole)
        for field in self.canvas.fields:
            if field.field_id == field_id:
                self._on_field_double_clicked(field)
                break
    
    def _refresh_fields_list(self):
        """Refresh the fields list."""
        self.fields_list.clear()
        for field in self.canvas.fields:
            display = f"{field.field_type}: {field.content[:20] if field.content else field.field_id}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, field.field_id)
            self.fields_list.addItem(item)
    
    def _on_zoom_changed(self, value: int):
        self.canvas_view.set_zoom(value)
        self.zoom_label.setText(f"{value}%")
    
    def _on_zoom_fit(self):
        self.canvas_view.zoom_fit()
        percent = int(self.canvas_view.zoom_factor * 100)
        self.zoom_slider.setValue(percent)
        self.zoom_label.setText(f"{percent}%")
    
    def _on_grid_toggled(self, checked: bool):
        self.canvas.grid_visible = checked
        self.canvas.update()
    
    def _on_template_changed(self, template_name: str):
        self.current_template_name = template_name
        # Update template type
        if "Απόδειξη" in template_name:
            self.template_type = 'payment'
        elif "Εγγραφής" in template_name:
            self.template_type = 'family'
        elif "Συνδρομής" in template_name:
            self.template_type = 'subscription'
        self._populate_db_fields()
        self._load_template(template_name)
    
    def _load_template(self, template_name: str):
        """Load a template."""
        if self.settings_service:
            try:
                settings = self.settings_service.load_settings()
                if settings:
                    template_key = f"pdf_template_{self.template_type}"
                    template_json = getattr(settings, template_key, None)
                    if template_json:
                        data = json.loads(template_json)
                        self.canvas.load_template_data(data)
                        self._refresh_fields_list()
                        self.status_label.setText(f"Φορτώθηκε: {template_name}")
                        return
            except Exception as e:
                logger.error(f"Error loading template: {e}")
        
        self._load_default_template(template_name)
    
    def _load_default_template(self, template_name: str):
        """Load default template."""
        for field in self.canvas.fields[:]:
            self.canvas.removeItem(field)
        self.canvas.fields.clear()
        
        if "Απόδειξη" in template_name:
            self.canvas.add_field('header', 50, 20, A4_WIDTH - 100, 60, "{org_name}", 
                                  extra_data={'font_size': 16, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('text', 50, 100, 300, 40, "ΑΠΟΔΕΙΞΗ ΠΛΗΡΩΜΗΣ",
                                  extra_data={'font_size': 18, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('db_field', 50, 160, 200, 30, "{receipt_no}")
            self.canvas.add_field('db_field', 50, 200, 200, 30, "{payment_date}")
            self.canvas.add_field('db_field', 50, 240, 300, 30, "{family_name}")
            self.canvas.add_field('db_field', 50, 280, 200, 40, "{amount}€",
                                  extra_data={'font_size': 16, 'font_bold': True})
            self.canvas.add_field('footer', 50, A4_HEIGHT - 80, A4_WIDTH - 100, 40, "{org_address}")
        
        elif "Εγγραφής" in template_name:
            self.canvas.add_field('image', 50, 20, 80, 80, extra_data={'use_logo': True})
            self.canvas.add_field('header', 150, 30, A4_WIDTH - 200, 50, "{org_name}",
                                  extra_data={'font_size': 16, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('text', 50, 120, 400, 40, "ΒΕΒΑΙΩΣΗ ΕΓΓΡΑΦΗΣ",
                                  extra_data={'font_size': 18, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('db_field', 50, 180, 400, 80, 
                                  "Βεβαιώνεται ότι ο πελάτης {family_name} είναι εγγεγραμμένος στον σύλλογό μας.")
            self.canvas.add_field('table', 50, 280, A4_WIDTH - 100, 200, extra_data={
                'columns': [
                    {'title': 'Ονοματεπώνυμο', 'field': '{member_name}', 'width': 40},
                    {'title': 'Σχέση', 'field': '{relation}', 'width': 30},
                    {'title': 'Ημ. Γέννησης', 'field': '{birth_date}', 'width': 30}
                ]
            })
            self.canvas.add_field('footer', 50, A4_HEIGHT - 80, A4_WIDTH - 100, 40, "{org_address} | {org_phone}")
        
        elif "Συνδρομής" in template_name:
            self.canvas.add_field('header', 50, 20, A4_WIDTH - 100, 60, "{org_name}",
                                  extra_data={'font_size': 16, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('text', 50, 100, 300, 40, "ΒΕΒΑΙΩΣΗ ΣΥΝΔΡΟΜΗΣ",
                                  extra_data={'font_size': 18, 'font_bold': True, 'align': 'center'})
            self.canvas.add_field('db_field', 50, 160, 300, 30, "Πελάτης: {family_name}")
            self.canvas.add_field('db_field', 50, 200, 200, 30, "Έτος: {year}")
            self.canvas.add_field('db_field', 50, 240, 250, 30, "Περίοδος: {start_date} - {end_date}")
            self.canvas.add_field('db_field', 50, 280, 200, 30, "Κατάσταση: {status}")
            self.canvas.add_field('footer', 50, A4_HEIGHT - 80, A4_WIDTH - 100, 40, "{org_address}")
        
        self._refresh_fields_list()
        self.status_label.setText(f"Φορτώθηκε προεπιλογή: {template_name}")
    
    def _on_save(self):
        """Save current template."""
        template_data = self.canvas.get_template_data()
        template_name = self.template_combo.currentText()
        
        self.template_saved.emit(template_name, template_data)
        
        QMessageBox.information(self, "Αποθήκευση", f"Το template '{template_name}' αποθηκεύτηκε!")
        self.status_label.setText(f"Αποθηκεύτηκε: {template_name}")
    
    def _on_load(self):
        """Load template from file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Φόρτωση Template", "", "JSON Files (*.json)")
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.canvas.load_template_data(data)
                self._refresh_fields_list()
                self.status_label.setText(f"Φορτώθηκε: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία φόρτωσης: {str(e)}")


class PDFTemplateEditorDialog(QDialog):
    """Dialog wrapper for the PDF Template Editor."""
    
    def __init__(self, template_type: str, template_name: str, 
                 db_connection=None, settings_service=None, parent=None):
        super().__init__(parent)
        self.template_type = template_type
        self.template_name = template_name
        self.db_connection = db_connection
        self.settings_service = settings_service
        
        self.setWindowTitle(f"Επεξεργασία PDF Template - {template_name}")
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)
        
        self._init_ui()
        self._load_template()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = PDFTemplateEditor(self.settings_service, self.template_type, self)
        self.editor.template_saved.connect(self._on_template_saved)
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 10, 10, 10)
        
        self.export_btn = QPushButton(get_icon('export'), "Εξαγωγή JSON")
        self.export_btn.clicked.connect(self._export_template)
        btn_layout.addWidget(self.export_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("Κλείσιμο")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_template(self):
        """Load the template for editing."""
        template_map = {
            'family': 'Βεβαίωση Εγγραφής',
            'payment': 'Απόδειξη Πληρωμής',
            'subscription': 'Βεβαίωση Συνδρομής'
        }
        
        combo_text = template_map.get(self.template_type, self.template_name)
        index = self.editor.template_combo.findText(combo_text)
        if index >= 0:
            # Block signals to prevent double loading
            self.editor.template_combo.blockSignals(True)
            self.editor.template_combo.setCurrentIndex(index)
            self.editor.template_combo.blockSignals(False)
        
        # Always load the template (even if combo didn't change)
        self.editor.template_type = self.template_type
        self.editor._populate_db_fields()
        self.editor._load_template(combo_text)
    
    def _on_template_saved(self, template_name: str, template_data: dict):
        """Handle template save."""
        if self.settings_service:
            try:
                template_json = json.dumps(template_data, ensure_ascii=False)
                logger.info(f"Saving template {template_name}, type={self.template_type}, json_length={len(template_json)}")
                
                settings = self.settings_service.load_settings()
                if settings:
                    template_key = f"pdf_template_{self.template_type}"
                    logger.info(f"Setting {template_key} on settings object")
                    setattr(settings, template_key, template_json)
                    
                    # Verify it was set
                    saved_value = getattr(settings, template_key, None)
                    logger.info(f"Value set: {bool(saved_value)}, length: {len(saved_value) if saved_value else 0}")
                    
                    result = self.settings_service.save_settings(settings)
                    logger.info(f"save_settings returned: {result}")
                    
                    if result:
                        # Verify by reloading
                        self.settings_service.reload_settings()
                        reloaded = self.settings_service.load_settings()
                        reloaded_value = getattr(reloaded, template_key, None)
                        logger.info(f"After reload, {template_key} has value: {bool(reloaded_value)}")
                    
                    logger.info(f"Template saved: {template_name}")
                else:
                    logger.error("No settings object returned from load_settings")
            except Exception as e:
                logger.error(f"Error saving template: {e}", exc_info=True)
                QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία αποθήκευσης:\n{str(e)}")
    
    def _export_template(self):
        """Export template to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Εξαγωγή Template", f"{self.template_type}_template.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                template_data = self.editor.canvas.get_template_data()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Εξαγωγή", f"Εξήχθη επιτυχώς:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία εξαγωγής:\n{str(e)}")
