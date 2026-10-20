# -*- coding: utf-8 -*-
"""
Receipt Service for generating PDF receipts.
Uses template positions from database for customizable layouts.
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

from db.repositories.payments_repo import PaymentsRepository
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# A4 dimensions in points
A4_WIDTH = 595
A4_HEIGHT = 842


class ReceiptService:
    """Service for generating PDF receipts for payments."""
    
    def __init__(self, payments_repo: PaymentsRepository, settings_service: SettingsService):
        """Initialize ReceiptService."""
        self.payments_repo = payments_repo
        self.settings_service = settings_service
        self._fonts_registered = False
        logger.debug("ReceiptService initialized")
    
    def _register_fonts(self):
        """Register Unicode fonts for Greek support."""
        if self._fonts_registered:
            return
        
        BASE_DIR = os.path.dirname(os.path.dirname(__file__))
        FONTS_DIR = os.path.join(BASE_DIR, "resources", "fonts")
        
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONTS_DIR, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")))
            self._fonts_registered = True
            logger.debug("Unicode fonts registered successfully")
        except Exception as e:
            logger.error(f"Failed to register fonts: {e}")
            raise Exception(f"Αποτυχία φόρτωσης γραμματοσειρών: {str(e)}")
    
    
    
    
    def _draw_text(self, c: canvas.Canvas, text: str, pos: Dict[str, Any], color=colors.black):
        """Draw text at specified position with alignment."""
        if not pos or not pos.get('visible', True) or not text:
            return
        
        # Check if position has required keys
        if 'x' not in pos or 'y' not in pos:
            return
        
        x = pos['x']
        y = A4_HEIGHT - pos['y'] - pos.get('height', 20)  # Convert from top-left to bottom-left origin
        width = pos.get('width', 200)
        font_size = pos.get('font_size', 12)
        font_bold = pos.get('font_bold', False)
        text_align = pos.get('text_align', 'left')
        
        font_name = 'DejaVu-Bold' if font_bold else 'DejaVu'
        c.setFont(font_name, font_size)
        c.setFillColor(color)
        
        # Calculate text width for alignment
        text_width = c.stringWidth(text, font_name, font_size)
        
        if text_align == 'center':
            x = x + (width - text_width) / 2
        elif text_align == 'right':
            x = x + width - text_width
        
        c.drawString(x, y, text)
    
    def _draw_multiline_text(self, c: canvas.Canvas, text: str, pos: Dict[str, Any], color=colors.black):
        """Draw multiline text at specified position."""
        if not pos or not pos.get('visible', True) or not text:
            return
        
        # Check if position has required keys
        if 'x' not in pos or 'y' not in pos:
            return
        
        x = pos['x']
        y = A4_HEIGHT - pos['y']  # Convert from top-left to bottom-left origin
        font_size = pos.get('font_size', 12)
        font_bold = pos.get('font_bold', False)
        line_height = font_size * 1.3
        
        font_name = 'DejaVu-Bold' if font_bold else 'DejaVu'
        c.setFont(font_name, font_size)
        c.setFillColor(color)
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            c.drawString(x, y - (i * line_height), line)
    
    def _draw_table(self, c: canvas.Canvas, field: Dict, payment_data: dict, settings):
        """Draw a table at specified position with data, borders and alignment."""
        extra_data = field.get('extra_data', {})
        columns = extra_data.get('columns', [])
        orientation = extra_data.get('orientation', 'horizontal')
        row_height = extra_data.get('row_height', 22)
        
        if not columns:
            return
        
        x = field.get('x', 50)
        y = A4_HEIGHT - field.get('y', 200)
        width = field.get('width', 400)
        height = field.get('height', 150)
        font_size = extra_data.get('font_size', 10)
        
        if orientation == 'vertical':
            self._draw_table_vertical(c, x, y, width, height, columns, font_size, row_height, payment_data, settings)
        else:
            self._draw_table_horizontal(c, x, y, width, height, columns, font_size, row_height, payment_data, settings)
    
    def _draw_table_horizontal(self, c: canvas.Canvas, x: float, y: float, width: float, 
                                height: float, columns: list, font_size: int, row_height: int,
                                payment_data: dict, settings):
        """Draw table with headers on top (horizontal orientation)."""
        header_height = 25
        
        # Calculate column widths
        col_widths = []
        for col in columns:
            col_widths.append(width * col.get('width', 100 // len(columns)) / 100)
        
        # Draw outer table border
        c.setStrokeColor(colors.HexColor('#333333'))
        c.setLineWidth(1)
        c.rect(x, y - height, width, height)
        
        # Draw header row background
        c.setFillColor(colors.HexColor('#e8e8e8'))
        c.rect(x, y - header_height, width, header_height, fill=1, stroke=0)
        
        # Draw header border
        c.setStrokeColor(colors.HexColor('#333333'))
        c.setLineWidth(1)
        c.rect(x, y - header_height, width, header_height)
        
        # Draw column headers with vertical lines
        c.setFillColor(colors.black)
        c.setFont('DejaVu-Bold', font_size)
        col_x = x
        for i, col in enumerate(columns):
            col_width = col_widths[i]
            text = col.get('title', '')
            text_width = c.stringWidth(text, 'DejaVu-Bold', font_size)
            text_x = col_x + (col_width - text_width) / 2
            c.drawString(text_x, y - 17, text)
            
            if i < len(columns) - 1:
                c.line(col_x + col_width, y, col_x + col_width, y - height)
            col_x += col_width
        
        # Draw data row
        c.setFont('DejaVu', font_size)
        row_y = y - header_height - row_height
        
        col_x = x
        for i, col in enumerate(columns):
            col_width = col_widths[i]
            field_placeholder = col.get('field', '')
            value = self._replace_placeholders(field_placeholder, payment_data, settings)
            if value is None:
                value = ''
            value = str(value)
            
            align = col.get('align', 'left')
            text_width = c.stringWidth(value, 'DejaVu', font_size)
            if align == 'center':
                text_x = col_x + (col_width - text_width) / 2
            elif align == 'right':
                text_x = col_x + col_width - text_width - 5
            else:
                text_x = col_x + 5
            
            c.drawString(text_x, row_y + 5, value)
            col_x += col_width
        
        c.line(x, row_y, x + width, row_y)
    
    def _draw_table_vertical(self, c: canvas.Canvas, x: float, y: float, width: float, 
                              height: float, columns: list, font_size: int, row_height: int,
                              payment_data: dict, settings):
        """Draw table with headers on left (vertical orientation)."""
        # Use passed row_height parameter
        header_width = width * 0.35  # 35% for headers
        value_width = width - header_width
        
        # Calculate actual table height based on rows
        actual_height = row_height * len(columns)
        
        # Draw outer table border
        c.setStrokeColor(colors.HexColor('#333333'))
        c.setLineWidth(1)
        c.rect(x, y - actual_height, width, actual_height)
        
        # Draw header column background
        c.setFillColor(colors.HexColor('#e8e8e8'))
        c.rect(x, y - actual_height, header_width, actual_height, fill=1, stroke=0)
        
        # Draw vertical line between headers and values
        c.setStrokeColor(colors.HexColor('#333333'))
        c.line(x + header_width, y, x + header_width, y - actual_height)
        
        # Draw each row
        for i, col in enumerate(columns):
            row_y = y - (i * row_height)
            
            # Draw horizontal line (except for first row)
            if i > 0:
                c.line(x, row_y, x + width, row_y)
            
            # Draw header text (bold, left aligned)
            c.setFont('DejaVu-Bold', font_size)
            c.setFillColor(colors.black)
            header_text = col.get('title', '')
            c.drawString(x + 5, row_y - row_height / 2 - font_size / 3, header_text)
            
            # Draw value text
            c.setFont('DejaVu', font_size)
            field_placeholder = col.get('field', '')
            value = self._replace_placeholders(field_placeholder, payment_data, settings)
            if value is None:
                value = ''
            value = str(value)
            
            align = col.get('align', 'left')
            text_width = c.stringWidth(value, 'DejaVu', font_size)
            if align == 'center':
                text_x = x + header_width + (value_width - text_width) / 2
            elif align == 'right':
                text_x = x + width - text_width - 5
            else:
                text_x = x + header_width + 5
            
            c.drawString(text_x, row_y - row_height / 2 - font_size / 3, value)
    
    def _draw_logo(self, c: canvas.Canvas, logo_path: str, pos: Dict[str, Any]):
        """Draw logo at specified position."""
        if not pos or not pos.get('visible', True) or not logo_path:
            return
        
        # Check if position has required keys
        if 'x' not in pos or 'y' not in pos:
            return
        
        # Check if file exists
        if not os.path.exists(logo_path):
            logger.warning(f"Logo file not found: {logo_path}")
            return
        
        try:
            x = pos['x']
            y = A4_HEIGHT - pos['y'] - pos.get('height', 80)
            width = pos.get('width', 80)
            height = pos.get('height', 80)
            
            # Use mask='auto' for PNG transparency support
            c.drawImage(
                logo_path, x, y, 
                width=width, height=height, 
                preserveAspectRatio=True,
                mask='auto'
            )
            logger.debug(f"Logo drawn at ({x}, {y}) size ({width}x{height})")
        except Exception as e:
            logger.error(f"Could not draw logo '{logo_path}': {e}")
    
    def _replace_placeholders(self, text: str, payment_data: dict, settings) -> str:
        """Replace placeholders in text with actual values."""
        if not text:
            return text
        
        # Build replacement dict
        replacements = {
            'family_name': payment_data.get('family_name', ''),
            'client_name': payment_data.get('family_name', ''),
            'first_name': payment_data.get('first_name', ''),
            'last_name': payment_data.get('last_name', ''),
            'father_name': payment_data.get('father_name', ''),
            'spouse_name': payment_data.get('spouse_name', ''),
            'spouse_maiden_name': payment_data.get('spouse_maiden_name', ''),
            'is_divorced': 'Ναι' if payment_data.get('is_divorced') else 'Όχι',
            'is_widowed': 'Ναι' if payment_data.get('spouse_deceased') else 'Όχι',
            'family_code': payment_data.get('family_code', ''),
            'national_id': payment_data.get('national_id', ''),
            'afm': payment_data.get('afm', ''),
            'doy': payment_data.get('doy', ''),
            'company_name': payment_data.get('company_name', ''),
            'profession': payment_data.get('profession', ''),
            'document_title': ('ΤΙΜΟΛΟΓΙΟ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ' if payment_data.get('document_type')=='invoice' else 'ΑΠΟΔΕΙΞΗ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ'),
            'aspe': payment_data.get('national_id', ''),  # Alias
            'address': payment_data.get('address', ''),
            'city': payment_data.get('city', ''),
            'postal_code': payment_data.get('postal_code', ''),
            'phone': payment_data.get('phone', ''),
            'email': payment_data.get('email', ''),
            'description': payment_data.get('description', ''),
            'receipt_no': payment_data.get('receipt_no', ''),
            'subscription_code': payment_data.get('subscription_code', ''),
            'year': payment_data.get('year', ''),
            'status': payment_data.get('status', ''),
            'members_count': str(payment_data.get('members_count', '')),
            'notes': payment_data.get('notes', ''),
            'payment_method': payment_data.get('payment_method', ''),
            'remarks': payment_data.get('remarks', ''),
        }
        
        # Handle dates
        payment_date = payment_data.get('payment_date')
        if payment_date:
            if isinstance(payment_date, str):
                replacements['payment_date'] = payment_date
            else:
                replacements['payment_date'] = payment_date.strftime('%d/%m/%Y')
        else:
            replacements['payment_date'] = ''
        
        start_date = payment_data.get('subscription_start_date')
        if start_date:
            if isinstance(start_date, str):
                replacements['subscription_start_date'] = start_date
            else:
                replacements['subscription_start_date'] = start_date.strftime('%d/%m/%Y')
        else:
            replacements['subscription_start_date'] = ''
        
        end_date = payment_data.get('subscription_end_date')
        if end_date:
            if isinstance(end_date, str):
                replacements['subscription_end_date'] = end_date
            else:
                replacements['subscription_end_date'] = end_date.strftime('%d/%m/%Y')
        else:
            replacements['subscription_end_date'] = ''
        
        # Handle amounts
        total_amount = payment_data.get('total_amount', Decimal('0.00'))
        paid_amount = payment_data.get('paid_amount', Decimal('0.00'))
        remaining_amount = payment_data.get('remaining_amount', Decimal('0.00'))
        
        if isinstance(total_amount, Decimal):
            total_amount = float(total_amount)
        if isinstance(paid_amount, Decimal):
            paid_amount = float(paid_amount)
        if isinstance(remaining_amount, Decimal):
            remaining_amount = float(remaining_amount)
        
        replacements['total_amount'] = f"{total_amount:.2f} €"
        replacements['paid_amount'] = f"{paid_amount:.2f} €"
        replacements['remaining_amount'] = f"{remaining_amount:.2f} €"
        replacements['amount'] = f"{paid_amount:.2f} €"  # Alias for paid_amount
        replacements['remaining'] = f"{remaining_amount:.2f} €"  # Alias
        
        # Organization settings
        if settings:
            replacements['org_name'] = settings.org_name or ''
            replacements['org_address'] = settings.org_address or ''
            replacements['org_phone'] = settings.org_phone or ''
            replacements['org_email'] = settings.org_email or ''
            replacements['org_afm'] = settings.org_afm or ''
        
        # Current date and time
        from datetime import datetime
        now = datetime.now()
        replacements['current_date'] = now.strftime('%d/%m/%Y')
        replacements['date'] = now.strftime('%d/%m/%Y')  # Alias
        replacements['time'] = now.strftime('%H:%M')
        
        # Start/end date aliases
        replacements['start_date'] = replacements.get('subscription_start_date', '')
        replacements['end_date'] = replacements.get('subscription_end_date', '')
        
        # Replace placeholders
        result = text
        for key, value in replacements.items():
            result = result.replace(f'{{{key}}}', str(value))
        
        return result
    
    def _draw_custom_elements(self, c: canvas.Canvas, positions: Dict, payment_data: dict, settings):
        """Draw all custom elements from visual editor and legacy custom_text/custom_field."""
        # Draw legacy custom elements
        for key, pos in positions.items():
            if key == '_custom_fields':
                continue
            elem_type = pos.get('element_type', '')
            if elem_type not in ('custom_text', 'custom_field'):
                continue
            
            if not pos.get('visible', True):
                continue
            
            custom_text = pos.get('custom_text', '')
            if not custom_text:
                continue
            
            # Replace placeholders
            text = self._replace_placeholders(custom_text, payment_data, settings)
            self._draw_text(c, text, pos)
        
        # Draw custom fields from visual editor
        custom_fields = positions.get('_custom_fields', [])
        for field_pos in custom_fields:
            if not field_pos.get('visible', True):
                continue
            
            content = field_pos.get('content', '')
            if not content:
                continue
            
            # Replace placeholders
            text = self._replace_placeholders(content, payment_data, settings)
            self._draw_text(c, text, field_pos)

    
    
    
    
    
    
    
    def _draw_legacy_subscription(self, c: canvas.Canvas, positions: Dict, payment_data: dict, settings):
        """Legacy subscription rendering for backward compatibility."""
        # Draw logo
        if settings and settings.pdf_logo_path:
            logo_pos = positions.get('logo', {'x': 50, 'y': 30, 'width': 80, 'height': 80, 'visible': True})
            self._draw_logo(c, settings.pdf_logo_path, logo_pos)
        
        # Draw organization name
        if settings and settings.org_name:
            self._draw_text(c, settings.org_name, positions.get('org_name', {}))
        
        # Draw title
        pdf_title = settings.pdf_subscription_title if settings else "Βεβαίωση Συνδρομής"
        self._draw_text(c, pdf_title, positions.get('title', {}), colors.HexColor('#4CAF50'))
        
        # Draw content
        content_pos = positions.get('content', {})
        if content_pos.get('visible', True):
            content_lines = []
            if payment_data.get('subscription_code'):
                content_lines.append(f"Κωδικός Συνδρομής: {payment_data['subscription_code']}")
            if payment_data.get('family_name'):
                content_lines.append(f"Πελάτης: {payment_data['family_name']}")
            if payment_data.get('national_id'):
                content_lines.append(f"ΑΣΠΕ: {payment_data['national_id']}")
            self._draw_multiline_text(c, '\n'.join(content_lines), content_pos)
        
        # Draw amount
        amount_pos = positions.get('amount', {})
        if amount_pos.get('visible', True) and 'x' in amount_pos:
            total_amount = float(payment_data.get('total_amount', 0))
            paid_amount = float(payment_data.get('paid_amount', 0))
            amount_text = f"Ποσό: {paid_amount:.2f} € / {total_amount:.2f} €"
            self._draw_text(c, amount_text, amount_pos, colors.HexColor('#4CAF50'))
        
        # Draw footer
        footer_pos = positions.get('footer', {})
        if footer_pos.get('visible', True) and 'x' in footer_pos:
            footer_text = settings.pdf_subscription_footer if settings else ''
            if footer_text:
                self._draw_text(c, footer_text, footer_pos, colors.grey)

    def generate_document_pdf(self, payment_id: int, output_path: str, document_type: str = 'receipt') -> None:
        """
        Generate a clean, professional PDF for a Receipt (Απόδειξη) or Invoice
        (Τιμολόγιο). Self-contained (no visual-template dependency). The paid
        amount is treated as gross (VAT-inclusive) and split into net + VAT.
        """
        import os as _os
        self._register_fonts()

        data = self.payments_repo.get_payment_with_family(payment_id)
        if not data:
            raise ValueError(f"Δεν βρέθηκε η πληρωμή με id={payment_id}")

        settings = self.settings_service.get_all_settings()
        if not settings:
            settings = self.settings_service.load_settings()

        is_invoice = (document_type == 'invoice')
        # Title is editable from Settings > «Ρυθμίσεις PDF» (invoice -> pdf_subscription_title,
        # receipt -> pdf_payment_title). Falls back to the standard heading if left blank.
        _default_title = "ΤΙΜΟΛΟΓΙΟ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ" if is_invoice else "ΑΠΟΔΕΙΞΗ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ"
        _title_key = 'pdf_subscription_title' if is_invoice else 'pdf_payment_title'
        title = (getattr(settings, _title_key, '') or '').strip() or _default_title

        # Appearance options (editable from Settings > «Ρυθμίσεις PDF»); defaults keep the current look
        _accent_hex = (getattr(settings, 'pdf_accent_color', '') or '#1565C0').strip()
        try:
            ACCENT = colors.HexColor(_accent_hex)
        except Exception:
            ACCENT = colors.HexColor('#1565C0')
        show_qr = bool(getattr(settings, 'pdf_show_qr', 1))
        show_session = bool(getattr(settings, 'pdf_show_session', 1))
        LIGHT = colors.HexColor('#EAF2FB')
        GREY = colors.HexColor('#6B7785')
        LINE = colors.HexColor('#D8DEE6')

        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        gross = _f(data.get('total_amount')) or _f(data.get('paid_amount'))  # document shows the full charge; partial payments are tracked as debt on the client card, not re-issued
        vat_rate = _f(data.get('vat_rate'))
        if vat_rate > 0:
            net = gross / (1 + vat_rate / 100.0)
            vat_amount = gross - net
        else:
            net = gross
            vat_amount = 0.0

        client_name = data.get('company_name') or data.get('family_name') or ''
        number = data.get('receipt_no') or '—'
        pdate = data.get('payment_date')
        if pdate and not isinstance(pdate, str):
            pdate = pdate.strftime('%d/%m/%Y')
        pdate = pdate or datetime.now().strftime('%d/%m/%Y')
        description = data.get('description') or 'Υπηρεσίες τεχνικής υποστήριξης'

        # linked session (for a fuller body)
        detail_lines = []
        # The per-session detail line makes sense ONLY for a single per-session
        # (hourly/ad-hoc) charge. For subscription/package documents (support_package
        # set) the amount is a flat fee covering many sessions, so printing one
        # session underneath would look like it was charged for that session.
        _is_flat_fee = bool(data.get("support_package"))
        try:
            _sr = self.payments_repo.db.execute_query(
                "SELECT id, session_type, start_time, end_time, duration_minutes, "
                "duration_seconds, technician, issue_summary "
                "FROM support_sessions WHERE payment_id=%s ORDER BY id LIMIT 1",
                (payment_id,)) if (show_session and not _is_flat_fee) else None
        except Exception:
            _sr = None
        if _sr:
            _s = _sr[0]
            _tmap = {'remote': 'Απομακρυσμένη', 'onsite': 'Επιτόπου', 'phone': 'Τηλεφωνική'}
            _ttype = _tmap.get(_s.get('session_type') or '', _s.get('session_type') or '')
            def _dt(v):
                if not v:
                    return ''
                if isinstance(v, str):
                    return v
                try:
                    return v.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    return str(v)
            _mins = int(_s.get('duration_minutes') or 0)
            _h, _mm = _mins // 60, _mins % 60
            if _h and _mm:
                _dur = f"{_h} {'ώρα' if _h==1 else 'ώρες'} {_mm} {'λεπτό' if _mm==1 else 'λεπτά'}"
            elif _h:
                _dur = f"{_h} {'ώρα' if _h==1 else 'ώρες'}"
            else:
                _dur = f"{_mins} {'λεπτό' if _mins==1 else 'λεπτά'}"
            _head = f"Συνεδρία #{_s.get('id')}"
            if _ttype:
                _head += f" · {_ttype} υποστήριξη"
            detail_lines.append(_head)
            _st, _en = _dt(_s.get('start_time')), _dt(_s.get('end_time'))
            if _st:
                _period = f"Από {_st}" + (f" έως {_en}" if _en else "")
                _period += f" · Διάρκεια: {_dur}"
                detail_lines.append(_period)
            # Υπέρβαση πακέτου: δείξε ξεκάθαρα ΜΟΝΟ τον χρεώσιμο χρόνο εκτός πακέτου
            _rem = str(data.get('remarks') or '')
            if str(description).startswith('Υπέρβαση πακέτου') and 'billed_minutes=' in _rem:
                try:
                    _bm = int(_rem.split('billed_minutes=')[1].split()[0].strip())
                except Exception:
                    _bm = 0
                if _bm > 0:
                    detail_lines.append(
                        f"Χρεώσιμος χρόνος εκτός πακέτου: {_bm} {'λεπτό' if _bm==1 else 'λεπτά'}")
            if _s.get('technician'):
                detail_lines.append(f"Τεχνικός: {_s.get('technician')}")
            if _s.get('issue_summary'):
                detail_lines.append(f"Θέμα: {str(_s.get('issue_summary'))[:80]}")
            if str(description).startswith('Χρέωση συνεδρίας'):
                description = 'Υπηρεσίες τεχνικής υποστήριξης'

        # resolve a logo (settings first, then bundled Logo/main_logo.png)
        logo_path = getattr(settings, 'pdf_logo_path', '') or ''
        if not logo_path or not _os.path.exists(logo_path):
            fb = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'Logo', 'main_logo.png')
            logo_path = fb if _os.path.exists(fb) else ''

        W, H, M = A4_WIDTH, A4_HEIGHT, 45
        c = canvas.Canvas(output_path, pagesize=A4)
        top = H - M

        # ---- Header: logo / issuer (left) ----
        drew_logo = False
        if logo_path:
            try:
                c.drawImage(ImageReader(logo_path), M, top - 58, width=170, height=58,
                            preserveAspectRatio=True, anchor='nw', mask='auto')
                drew_logo = True
            except Exception:
                drew_logo = False

        iy = top - (66 if drew_logo else 0)
        c.setFillColor(colors.black)
        c.setFont('DejaVu-Bold', 11 if drew_logo else 14)
        c.drawString(M, iy, (getattr(settings, 'org_name', '') or 'Support CRM'))
        iy -= 13
        c.setFont('DejaVu', 8.5)
        c.setFillColor(GREY)
        issuer = []
        addr = ' '.join([p for p in [getattr(settings, 'org_address', '') or '',
                                     getattr(settings, 'org_city', '') or ''] if p]).strip()
        if addr:
            issuer.append(addr)
        if getattr(settings, 'org_afm', ''):
            issuer.append(f"ΑΦΜ: {settings.org_afm}")
        contact = '  ·  '.join([p for p in [
            (f"Τηλ: {settings.org_phone}" if getattr(settings, 'org_phone', '') else ''),
            (str(settings.org_email) if getattr(settings, 'org_email', '') else '')] if p])
        if contact:
            issuer.append(contact)
        for ln in issuer:
            c.drawString(M, iy, ln)
            iy -= 11

        # ---- Header: document title + meta (right) ----
        c.setFillColor(ACCENT)
        c.setFont('DejaVu-Bold', 15)
        c.drawRightString(W - M, top - 6, title)
        c.setFillColor(colors.black)
        c.setFont('DejaVu', 10)
        c.drawRightString(W - M, top - 26, f"Αρ.: {number}")
        c.setFillColor(GREY)
        c.drawRightString(W - M, top - 40, f"Ημ/νία: {pdate}")

        # ---- Accent divider ----
        yb = min(iy, top - 58) - 8
        c.setStrokeColor(ACCENT)
        c.setLineWidth(2)
        c.line(M, yb, W - M, yb)
        c.setLineWidth(1)

        # ---- Client block ----
        yb -= 26
        c.setFont('DejaVu-Bold', 8.5)
        c.setFillColor(GREY)
        c.drawString(M, yb, "ΣΤΟΙΧΕΙΑ ΠΕΛΑΤΗ")
        yb -= 16
        c.setFillColor(colors.black)
        c.setFont('DejaVu-Bold', 11)
        c.drawString(M, yb, str(client_name))
        yb -= 14
        c.setFont('DejaVu', 9.5)
        if data.get('afm'):
            c.drawString(M, yb, f"ΑΦΜ: {data.get('afm')}")
            yb -= 12
        if is_invoice:
            if data.get('profession'):
                c.drawString(M, yb, f"Επάγγελμα: {data.get('profession')}")
                yb -= 12
            addr2 = ' '.join([p for p in [data.get('address') or '',
                                          data.get('city') or ''] if p]).strip()
            if addr2:
                c.drawString(M, yb, f"Διεύθυνση: {addr2}")
                yb -= 12

        # ---- Items table ----
        yb -= 20
        band_h = 22
        c.setFillColor(ACCENT)
        c.rect(M, yb - band_h + 15, W - 2 * M, band_h, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('DejaVu-Bold', 9.5)
        c.drawString(M + 10, yb, "Περιγραφή")
        c.drawRightString(W - M - 10, yb, "Ποσό")
        yb -= band_h
        c.setFillColor(colors.black)
        c.setFont('DejaVu', 10)
        c.drawString(M + 10, yb, str(description)[:72])
        c.drawRightString(W - M - 10, yb, f"{gross:.2f} €")
        if detail_lines:
            c.setFont('DejaVu', 8.5)
            c.setFillColor(GREY)
            for _dl in detail_lines:
                yb -= 12
                c.drawString(M + 16, yb, str(_dl)[:92])
            c.setFillColor(colors.black)
        yb -= 12
        c.setStrokeColor(LINE)
        c.line(M, yb, W - M, yb)

        # ---- Totals ----
        yb -= 24
        lx = W - M - 210
        vx = W - M - 10
        if vat_amount > 0:
            c.setFont('DejaVu', 10)
            c.setFillColor(colors.black)
            c.drawString(lx, yb, "Καθαρή αξία:")
            c.drawRightString(vx, yb, f"{net:.2f} €")
            yb -= 15
            c.drawString(lx, yb, f"ΦΠΑ {vat_rate:.0f}%:")
            c.drawRightString(vx, yb, f"{vat_amount:.2f} €")
            yb -= 20
        else:
            yb -= 2
        # total box
        box_x = W - M - 220
        c.setFillColor(ACCENT)
        c.roundRect(box_x, yb - 20, 220, 30, 5, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('DejaVu-Bold', 12)
        c.drawString(box_x + 12, yb - 5, "Σύνολο")
        c.drawRightString(box_x + 220 - 12, yb - 5, f"{gross:.2f} €")

        # ---- Optional technician comments about the work (printed for the client) ----
        # Captured at issue time in the document-type dialog (payments.document_notes).
        _doc_notes = str(data.get('document_notes') or '').strip()
        if _doc_notes:
            from reportlab.lib.utils import simpleSplit
            ny = (yb - 20) - 30  # start below the total box, with a gap
            c.setFont('DejaVu-Bold', 8.5)
            c.setFillColor(GREY)
            c.drawString(M, ny, "ΠΑΡΑΤΗΡΗΣΕΙΣ")
            ny -= 15
            c.setFont('DejaVu', 9.5)
            c.setFillColor(colors.black)
            _lines = simpleSplit(_doc_notes, 'DejaVu', 9.5, W - 2 * M)
            for _nl in _lines:
                if ny < 92:  # keep clear of the footer / QR area
                    break
                c.drawString(M, ny, _nl)
                ny -= 12
            c.setFillColor(colors.black)

        # ---- Footer ----
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(M, 72, W - M, 72)
        foot = ' · '.join([p for p in [
            (getattr(settings, 'org_name', '') or ''),
            (getattr(settings, 'org_phone', '') or ''),
            (getattr(settings, 'org_email', '') or '')] if p])
        if foot:
            c.setFont('DejaVu', 8)
            c.setFillColor(GREY)
            c.drawCentredString(W / 2, 58, foot[:110])
        # optional custom footer note (editable from settings)
        _note_key = 'pdf_subscription_footer' if is_invoice else 'pdf_payment_footer'
        _note = (getattr(settings, _note_key, '') or '').strip()
        if _note:
            c.setFont('DejaVu', 8)
            c.setFillColor(GREY)
            c.drawCentredString(W / 2, 48, _note[:120])
        c.setFont('DejaVu', 7.5)
        c.setFillColor(GREY)
        c.drawString(M, 40, f"Εκδόθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # QR code (decorative electronic marking) — optional, toggled from settings
        if show_qr:
            try:
                from reportlab.graphics.barcode.qr import QrCodeWidget
                from reportlab.graphics.shapes import Drawing
                from reportlab.graphics import renderPDF
                _qr = QrCodeWidget("SUPPORT-CRM|E-DOC|VERIFY")
                _bd = _qr.getBounds()
                _bw = (_bd[2] - _bd[0]) or 1
                _bh = (_bd[3] - _bd[1]) or 1
                _sz = 66
                _d = Drawing(_sz, _sz, transform=[_sz / _bw, 0, 0, _sz / _bh, 0, 0])
                _d.add(_qr)
                _qx = W - M - _sz
                _qy = 84
                renderPDF.draw(_d, c, _qx, _qy)
                c.setFont('DejaVu', 6.5)
                c.setFillColor(GREY)
                c.drawCentredString(_qx + _sz / 2, _qy - 8, "Ηλεκτρονική σήμανση")
                c.setFillColor(colors.black)
            except Exception as _qe:
                logger.warning(f"QR draw skipped: {_qe}")

        c.save()
        logger.info(f"Document PDF ({document_type}) generated: {output_path}")
