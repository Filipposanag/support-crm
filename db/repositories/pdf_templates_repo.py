# -*- coding: utf-8 -*-
"""
PDF Templates Repository - Database operations for PDF template configurations.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PDFTemplateElement:
    """Represents a PDF template element."""
    id: int
    template_id: int
    element_type: str
    element_name: str
    pos_x: float
    pos_y: float
    width: float
    height: float
    font_size: int
    font_bold: bool
    font_italic: bool
    text_align: str
    visible: bool
    z_order: int
    custom_text: Optional[str] = None


@dataclass
class PDFTemplate:
    """Represents a PDF template configuration."""
    id: int
    template_type: str
    template_name: str
    page_width: float
    page_height: float
    margin_top: float
    margin_bottom: float
    margin_left: float
    margin_right: float
    elements: List[PDFTemplateElement] = None
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []


class PDFTemplatesRepository:
    """Repository for PDF template database operations."""
    
    def __init__(self, db_connection):
        """Initialize repository with database connection."""
        self.db_connection = db_connection
    
    def get_template(self, template_type: str) -> Optional[PDFTemplate]:
        """Get a PDF template by type with all its elements."""
        try:
            cursor = self.db_connection.cursor()
            
            # Get template
            cursor.execute("""
                SELECT id, template_type, template_name, page_width, page_height,
                       margin_top, margin_bottom, margin_left, margin_right
                FROM pdf_templates
                WHERE template_type = ?
            """, (template_type,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            template = PDFTemplate(
                id=row[0],
                template_type=row[1],
                template_name=row[2],
                page_width=row[3] or 595.0,
                page_height=row[4] or 842.0,
                margin_top=row[5] or 50.0,
                margin_bottom=row[6] or 50.0,
                margin_left=row[7] or 50.0,
                margin_right=row[8] or 50.0
            )
            
            # Get elements
            cursor.execute("""
                SELECT id, template_id, element_type, element_name, pos_x, pos_y,
                       width, height, font_size, font_bold, font_italic, text_align,
                       visible, z_order, custom_text
                FROM pdf_template_elements
                WHERE template_id = ?
                ORDER BY z_order
            """, (template.id,))
            
            for row in cursor.fetchall():
                element = PDFTemplateElement(
                    id=row[0],
                    template_id=row[1],
                    element_type=row[2],
                    element_name=row[3],
                    pos_x=row[4],
                    pos_y=row[5],
                    width=row[6],
                    height=row[7],
                    font_size=row[8],
                    font_bold=bool(row[9]),
                    font_italic=bool(row[10]) if row[10] is not None else False,
                    text_align=row[11],
                    visible=bool(row[12]),
                    z_order=row[13],
                    custom_text=row[14]
                )
                template.elements.append(element)
            
            return template
            
        except Exception as e:
            logger.error(f"Failed to get template {template_type}: {e}")
            return None
    
    def get_element_position(self, template_type: str, element_type: str) -> Optional[Dict[str, Any]]:
        """Get position and properties for a specific element."""
        try:
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT e.pos_x, e.pos_y, e.width, e.height, e.font_size, 
                       e.font_bold, e.text_align, e.visible
                FROM pdf_template_elements e
                JOIN pdf_templates t ON e.template_id = t.id
                WHERE t.template_type = ? AND e.element_type = ?
            """, (template_type, element_type))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'x': row[0],
                'y': row[1],
                'width': row[2],
                'height': row[3],
                'font_size': row[4],
                'font_bold': bool(row[5]),
                'text_align': row[6],
                'visible': bool(row[7])
            }
            
        except Exception as e:
            logger.error(f"Failed to get element position: {e}")
            return None
    
    def get_all_element_positions(self, template_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all element positions for a template type."""
        result = {}
        template = self.get_template(template_type)
        
        if template:
            for element in template.elements:
                result[element.element_type] = {
                    'x': element.pos_x,
                    'y': element.pos_y,
                    'width': element.width,
                    'height': element.height,
                    'font_size': element.font_size,
                    'font_bold': element.font_bold,
                    'text_align': element.text_align,
                    'visible': element.visible
                }
        
        return result
    
    def template_exists(self, template_type: str) -> bool:
        """Check if a template exists."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT 1 FROM pdf_templates WHERE template_type = ?",
                (template_type,)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check template existence: {e}")
            return False
