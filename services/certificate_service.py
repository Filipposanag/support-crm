# -*- coding: utf-8 -*-
"""
Certificate Service - Handles generation of registration certificates for families.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from db.repositories.families_repo import FamiliesRepository
from db.repositories.members_repo import MembersRepository
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# A4 dimensions
A4_WIDTH = 595
A4_HEIGHT = 842


class CertificateService:
    """
    Service for generating registration certificates (βεβαιώσεις εγγραφής) for families.
    """
    
    def __init__(
        self,
        families_repo: FamiliesRepository,
        members_repo: MembersRepository,
        settings_service: SettingsService
    ):
        """
        Initialize CertificateService.
        
        Args:
            families_repo: Families repository instance
            members_repo: Members repository instance
            settings_service: Settings service instance
        """
        self.families_repo = families_repo
        self.members_repo = members_repo
        self.settings_service = settings_service
        
        # Register Greek fonts if available
        self._register_fonts()
    
    def _register_fonts(self):
        """Register Greek-compatible fonts for PDF generation."""
        try:
            # Try to register DejaVu fonts (supports Greek)
            # These fonts should be included in the resources folder
            from config import RESOURCES_DIR
            fonts_dir = RESOURCES_DIR / 'fonts'
            
            if fonts_dir.exists():
                dejavu_path = fonts_dir / 'DejaVuSans.ttf'
                dejavu_bold_path = fonts_dir / 'DejaVuSans-Bold.ttf'
                
                if dejavu_path.exists():
                    pdfmetrics.registerFont(TTFont('DejaVu', str(dejavu_path)))
                    logger.debug("Registered DejaVu font")
                
                if dejavu_bold_path.exists():
                    pdfmetrics.registerFont(TTFont('DejaVu-Bold', str(dejavu_bold_path)))
                    logger.debug("Registered DejaVu-Bold font")
        except Exception as e:
            logger.warning(f"Could not register custom fonts: {e}")
    
    def generate_certificate(
        self,
        family_id: int,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a registration certificate PDF for a family.
        
        Args:
            family_id: ID of the family
            output_path: Optional custom output path (if None, uses temp directory)
            
        Returns:
            Path to generated PDF file, or None if failed
        """
        try:
            # Get family data
            family = self.families_repo.get_by_id(family_id)
            if not family:
                logger.error(f"Family not found: id={family_id}")
                return None
            
            # Get family members
            members = self.members_repo.get_by_family_id(family_id)
            
            # Get organization settings
            org_name = self.settings_service.get_org_name()
            
            # Determine output path
            if not output_path:
                from config import BASE_DIR
                output_dir = BASE_DIR / 'temp'
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"certificate_{family_id}_{timestamp}.pdf"
                output_path = str(output_dir / filename)
            
            # Get template positions from settings
            template_data = self._get_template_data('family')
            
            # Create PDF
            self._create_certificate_pdf(family, members, org_name, output_path, template_data)
            
            logger.info(f"Certificate generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}", exc_info=True)
            return None
    
    def _get_template_data(self, template_type: str) -> Optional[Dict]:
        """Get template data from settings."""
        try:
            settings = self.settings_service.load_settings()
            if settings:
                template_key = f"pdf_template_{template_type}"
                template_json = getattr(settings, template_key, None)
                if template_json:
                    import json
                    return json.loads(template_json)
        except Exception as e:
            logger.warning(f"Failed to load template: {e}")
        return None
    
    def _create_certificate_pdf(
        self,
        family: Dict[str, Any],
        members: list,
        org_name: str,
        output_path: str,
        template_data: Optional[Dict] = None
    ):
        """
        Create the actual PDF certificate document.
        
        Args:
            family: Family data dictionary
            members: List of family members
            org_name: Organization name
            output_path: Path to save PDF
            template_data: Optional visual template data
        """
        # Check if we have visual template
        if template_data and template_data.get('fields'):
            self._create_certificate_with_visual_template(family, members, org_name, output_path, template_data)
            return
        
        # Fallback to legacy platypus rendering
        self._create_certificate_legacy(family, members, org_name, output_path)
    
    def _create_certificate_with_visual_template(
        self,
        family: Dict[str, Any],
        members: list,
        org_name: str,
        output_path: str,
        template_data: Dict
    ):
        """Create certificate using visual template positions."""
        self._register_fonts()
        
        c = canvas.Canvas(output_path, pagesize=A4)
        settings = self.settings_service.load_settings()
        
        # Build data dict for placeholder replacement
        data = {
            'family_name': f"{family.get('last_name', '')} {family.get('first_name', '')}",
            'first_name': family.get('first_name', ''),
            'last_name': family.get('last_name', ''),
            'father_name': family.get('father_name', ''),
            'spouse_name': family.get('spouse_name', ''),
            'spouse_maiden_name': family.get('spouse_maiden_name', ''),
            'is_divorced': 'Ναι' if family.get('is_divorced') else 'Όχι',
            'is_widowed': 'Ναι' if family.get('spouse_deceased') else 'Όχι',
            'family_code': family.get('legacy_code', ''),
            'aspe': family.get('national_id', ''),
            'national_id': family.get('national_id', ''),
            'address': family.get('address', ''),
            'city': family.get('city', ''),
            'postal_code': family.get('postal_code', ''),
            'phone': family.get('phone', ''),
            'email': family.get('email', ''),
            'members_count': str(len(members)),
            'registration_date': family.get('created_at', ''),
            'org_name': org_name,
            'org_address': settings.org_address if settings else '',
            'org_phone': settings.org_phone if settings else '',
            'org_email': settings.org_email if settings else '',
            'org_afm': settings.org_afm if settings else '',
            'date': datetime.now().strftime('%d/%m/%Y'),
            'time': datetime.now().strftime('%H:%M'),
        }
        
        # Get all fields and sort by Y position
        fields = template_data.get('fields', [])
        fields_sorted = sorted(fields, key=lambda f: f.get('y', 0))
        
        logger.info(f"Drawing certificate with {len(fields)} fields from visual template")
        
        for field in fields_sorted:
            field_type = field.get('field_type', '')
            content = field.get('content', '')
            extra_data = field.get('extra_data', {})
            
            # Replace placeholders
            if content:
                for key, value in data.items():
                    content = content.replace(f'{{{key}}}', str(value))
            
            pos = {
                'x': field.get('x', 50),
                'y': field.get('y', 50),
                'width': field.get('width', 200),
                'height': field.get('height', 30),
                'font_size': extra_data.get('font_size', 12),
                'font_bold': extra_data.get('font_bold', False),
                'text_align': extra_data.get('align', 'left'),
            }
            
            if field_type == 'image':
                image_path = extra_data.get('image_path', '')
                use_logo = extra_data.get('use_logo', False)
                if use_logo and settings and settings.pdf_logo_path:
                    image_path = settings.pdf_logo_path
                if image_path and os.path.exists(image_path):
                    self._draw_logo_canvas(c, image_path, pos)
            
            elif field_type == 'header':
                text = content or org_name
                if text:
                    self._draw_text_canvas(c, text, pos)
            
            elif field_type == 'footer':
                text = content or (settings.pdf_footer if settings else '')
                if text:
                    self._draw_text_canvas(c, text, pos, colors.grey)
            
            elif field_type == 'text':
                if content:
                    if 'ΒΕΒΑΙΩΣΗ' in content.upper():
                        self._draw_text_canvas(c, content, pos, colors.HexColor('#1a5490'))
                    else:
                        self._draw_text_canvas(c, content, pos)
            
            elif field_type == 'db_field':
                if content:
                    self._draw_text_canvas(c, content, pos)
            
            elif field_type == 'table':
                # Draw members table
                self._draw_members_table_canvas(c, members, pos, extra_data)
        
        # Timestamp
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        c.setFont('DejaVu', 9)
        c.setFillColor(colors.grey)
        c.drawString(50, 30, f"Εκδόθηκε: {timestamp}")
        
        c.save()
    
    def _draw_text_canvas(self, c: canvas.Canvas, text: str, pos: Dict, color=colors.black):
        """Draw text on canvas at position."""
        if not text:
            return
        
        x = pos.get('x', 50)
        y = A4_HEIGHT - pos.get('y', 50) - pos.get('height', 20)
        font_size = pos.get('font_size', 12)
        font_bold = pos.get('font_bold', False)
        text_align = pos.get('text_align', 'left')
        width = pos.get('width', 200)
        
        font_name = 'DejaVu-Bold' if font_bold else 'DejaVu'
        try:
            c.setFont(font_name, font_size)
        except:
            c.setFont('Helvetica', font_size)
        c.setFillColor(color)
        
        text_width = c.stringWidth(text, font_name, font_size)
        
        if text_align == 'center':
            x = x + (width - text_width) / 2
        elif text_align == 'right':
            x = x + width - text_width
        
        c.drawString(x, y, text)
    
    def _draw_logo_canvas(self, c: canvas.Canvas, logo_path: str, pos: Dict):
        """Draw logo on canvas."""
        if not os.path.exists(logo_path):
            return
        
        try:
            x = pos.get('x', 50)
            y = A4_HEIGHT - pos.get('y', 50) - pos.get('height', 80)
            width = pos.get('width', 80)
            height = pos.get('height', 80)
            
            c.drawImage(logo_path, x, y, width=width, height=height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.error(f"Failed to draw logo: {e}")
    
    def _draw_members_table_canvas(self, c: canvas.Canvas, members: list, pos: Dict, extra_data: Dict):
        """Draw members table on canvas with grid lines like Excel."""
        columns = extra_data.get('columns', [
            {'title': 'Ονοματεπώνυμο', 'field': '{member_name}', 'width': 40},
            {'title': 'Σχέση', 'field': '{relation}', 'width': 30},
            {'title': 'Ημ. Γέννησης', 'field': '{birth_date}', 'width': 30}
        ])
        
        x = pos.get('x', 50)
        y = A4_HEIGHT - pos.get('y', 200)
        width = pos.get('width', 400)
        row_height = 22
        header_height = 28
        line_color = colors.HexColor('#1a5490')
        
        num_rows = min(len(members), 10)
        table_height = header_height + (num_rows * row_height)
        
        # Draw header background
        c.setFillColor(colors.HexColor('#e8f4f8'))
        c.rect(x, y - header_height, width, header_height, fill=1, stroke=0)
        
        # Draw header text
        c.setFillColor(line_color)
        c.setFont('DejaVu-Bold', 10)
        col_x = x
        for col in columns:
            col_width = width * col.get('width', 33) / 100
            c.drawString(col_x + 8, y - 18, col.get('title', ''))
            col_x += col_width
        
        # Draw rows
        c.setFont('DejaVu', 10)
        c.setFillColor(colors.black)
        current_y = y - header_height
        for member in members[:10]:
            current_y -= row_height
            col_x = x
            
            # Build member data dict for placeholder replacement
            member_data = {
                'member_name': f"{member.get('last_name', '')} {member.get('first_name', '')}",
                'member_first_name': member.get('first_name', ''),
                'member_last_name': member.get('last_name', ''),
                'member_mother_name': member.get('mother_name', ''),
                'member_national_id': member.get('national_id', ''),
                'member_profession': member.get('profession', ''),
                'member_is_married': 'Ναι' if member.get('married') else 'Όχι',
                'member_is_deceased': 'Ναι' if member.get('is_deceased') else 'Όχι',
                'member_is_disabled': 'Ναι' if member.get('is_disabled') else 'Όχι',
                'relation': member.get('relation', ''),
            }
            
            # Handle dates
            birth_date = member.get('birth_date', '')
            if birth_date and not isinstance(birth_date, str):
                birth_date = birth_date.strftime('%d/%m/%Y')
            member_data['birth_date'] = str(birth_date)
            member_data['member_birth_date'] = str(birth_date)
            
            marriage_date = member.get('marriage_date', '')
            if marriage_date and not isinstance(marriage_date, str):
                marriage_date = marriage_date.strftime('%d/%m/%Y')
            member_data['member_marriage_date'] = str(marriage_date) if marriage_date else ''
            
            for i, col in enumerate(columns):
                col_width = width * col.get('width', 33) / 100
                field_placeholder = col.get('field', '')
                
                # Replace placeholder with actual value
                value = field_placeholder
                for key, val in member_data.items():
                    value = value.replace(f'{{{key}}}', str(val))
                
                # Draw the value
                c.drawString(col_x + 8, current_y + 6, value[:30] if value else '')
                col_x += col_width
        
        # Draw grid lines
        c.setStrokeColor(line_color)
        c.setLineWidth(1)
        
        # Outer border
        c.rect(x, y - table_height, width, table_height, fill=0, stroke=1)
        
        # Horizontal lines (between rows)
        c.setLineWidth(0.5)
        for i in range(num_rows + 1):
            line_y = y - header_height - (i * row_height)
            c.line(x, line_y, x + width, line_y)
        
        # Header bottom line (thicker)
        c.setLineWidth(1)
        c.line(x, y - header_height, x + width, y - header_height)
        
        # Vertical lines (between columns) - draw for ALL columns including last
        c.setLineWidth(0.5)
        col_x = x
        for col in columns:
            col_width = width * col.get('width', 33) / 100
            col_x += col_width
            # Draw vertical line at the end of each column
            c.line(col_x, y, col_x, y - table_height)
    
    def _create_certificate_legacy(
        self,
        family: Dict[str, Any],
        members: list,
        org_name: str,
        output_path: str
    ):
        """Legacy certificate creation using platypus."""
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Container for PDF elements
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Try to use Greek font if available
        try:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName='DejaVu-Bold',
                fontSize=18,
                textColor=colors.HexColor('#1a5490'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName='DejaVu-Bold',
                fontSize=14,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=12
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName='DejaVu',
                fontSize=11,
                leading=16
            )
            
            small_style = ParagraphStyle(
                'CustomSmall',
                parent=styles['Normal'],
                fontName='DejaVu',
                fontSize=9,
                textColor=colors.grey
            )
        except:
            # Fallback to default fonts
            title_style = styles['Heading1']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']
            small_style = styles['Normal']
        
        # Header - Organization name
        story.append(Paragraph(org_name, title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Certificate title - use family certificate title (pdf_title field)
        settings = self.settings_service.get_all_settings()
        cert_title = "ΒΕΒΑΙΩΣΗ ΕΓΓΡΑΦΗΣ"
        if settings and settings.pdf_title:
            cert_title = settings.pdf_title
        story.append(Paragraph(cert_title, heading_style))
        story.append(Spacer(1, 1*cm))
        
        # Certificate body
        issue_date = datetime.now().strftime('%d/%m/%Y')
        
        body_text = f"""
        Βεβαιώνεται ότι ο πελάτης με τα παρακάτω στοιχεία είναι εγγεγραμμένος 
        στο μητρώο του {org_name}:
        """
        story.append(Paragraph(body_text, normal_style))
        story.append(Spacer(1, 0.8*cm))
        
        # Family details table
        family_data = [
            ['Κωδικός Πελάτη:', str(family.get('legacy_code', ''))],
            ['Επώνυμο:', family.get('last_name', '')],
            ['Όνομα:', family.get('first_name', '')],
            ['Α.Δ.Τ.:', family.get('national_id', '')],
            ['Διεύθυνση:', family.get('address', '')],
            ['Πόλη:', family.get('city', '')],
            ['Τηλέφωνο:', family.get('phone', '') or family.get('mobile', '')],
            ['Email:', family.get('email', '')],
        ]
        
        # Filter out empty rows
        family_data = [row for row in family_data if row[1]]
        
        family_table = Table(family_data, colWidths=[5*cm, 10*cm])
        family_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'DejaVu-Bold' if 'DejaVu-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'DejaVu' if 'DejaVu' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(family_table)
        story.append(Spacer(1, 1*cm))
        
        # Members section
        if members and len(members) > 0:
            members_title = f"Μέλη Πελάτη ({len(members)}):"
            story.append(Paragraph(members_title, heading_style))
            story.append(Spacer(1, 0.3*cm))
            
            members_data = [['Α/Α', 'Επώνυμο', 'Όνομα', 'Ημ. Γέννησης']]
            
            for idx, member in enumerate(members, 1):
                birth_date = ''
                if member.get('birth_date'):
                    try:
                        birth_date = member['birth_date'].strftime('%d/%m/%Y')
                    except:
                        birth_date = str(member['birth_date'])
                
                members_data.append([
                    str(idx),
                    member.get('last_name', ''),
                    member.get('first_name', ''),
                    birth_date
                ])
            
            members_table = Table(members_data, colWidths=[1.5*cm, 5*cm, 5*cm, 3.5*cm])
            members_table.setStyle(TableStyle([
                # Fonts
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold' if 'DejaVu-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'DejaVu' if 'DejaVu' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4f8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                # Alignment
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Grid lines - outer border (thick)
                ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#1a5490')),
                # Inner grid lines - horizontal and vertical separators
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a5490')),
                ('LINEAFTER', (0, 0), (-2, -1), 0.5, colors.HexColor('#1a5490')),
                # Header bottom line (thicker)
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1a5490')),
                # Padding
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(members_table)
            story.append(Spacer(1, 1.5*cm))
        
        # Footer - Issue date and signature
        footer_text = f"""
        <para align=right>
        Ημερομηνία Έκδοσης: {issue_date}<br/>
        <br/>
        <br/>
        _______________________<br/>
        Υπογραφή & Σφραγίδα
        </para>
        """
        story.append(Paragraph(footer_text, normal_style))
        
        # Add custom footer from settings if available (uses pdf_footer for family certificates)
        if settings and settings.pdf_footer:
            custom_footer = settings.pdf_footer
            if custom_footer:
                story.append(Spacer(1, 0.5*cm))
                footer_style = ParagraphStyle(
                    'CustomFooter',
                    fontName='DejaVu' if 'DejaVu' in pdfmetrics.getRegisteredFontNames() else 'Helvetica',
                    fontSize=9,
                    textColor=colors.grey,
                    alignment=TA_CENTER
                )
                story.append(Paragraph(custom_footer, footer_style))
        
        # Build PDF
        doc.build(story)
        logger.debug(f"PDF certificate created: {output_path}")

