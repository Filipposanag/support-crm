"""
Export service for exporting reports to various formats.
Handles Excel, CSV, and other export formats.
"""

import logging
import os
from pathlib import Path
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from services.reporting_service import SubscriptionReportResult

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting reports to various formats."""
    
    @staticmethod
    def export_subscription_report_to_pdf(
        result: SubscriptionReportResult, 
        filepath: str, 
        filters_summary: str = ""
    ) -> None:
        """
        Δημιουργεί PDF με αναφορά συνδρομών.
        
        Args:
            result: SubscriptionReportResult με rows και summary
            filepath: Πλήρης διαδρομή αρχείου για αποθήκευση
            filters_summary: Προαιρετική περιγραφή φίλτρων
            
        Raises:
            Exception: Αν αποτύχει η εξαγωγή
        """
        try:
            logger.info(f"Exporting subscription report to PDF: {filepath}")
            
            # Register Unicode fonts for Greek support
            ExportService._register_greek_fonts()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Build PDF content
            story = []
            styles = ExportService._create_pdf_styles()
            
            # Title
            title = Paragraph("Αναφορά Συνδρομών", styles['ReportTitle'])
            story.append(title)
            story.append(Spacer(1, 0.5*cm))
            
            # Filters summary
            if filters_summary:
                filters_para = Paragraph(f"<b>Φίλτρα:</b> {filters_summary}", styles['ReportNormal'])
                story.append(filters_para)
                story.append(Spacer(1, 0.5*cm))
            
            # Data table
            table = ExportService._create_pdf_table(result)
            story.append(table)
            story.append(Spacer(1, 0.8*cm))
            
            # Summary
            summary_content = ExportService._create_pdf_summary(result, styles)
            story.extend(summary_content)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Successfully exported {len(result.rows)} rows to PDF")
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _register_greek_fonts():
        """Register Unicode fonts for Greek character support."""
        BASE_DIR = os.path.dirname(os.path.dirname(__file__))
        FONTS_DIR = os.path.join(BASE_DIR, "resources", "fonts")
        
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONTS_DIR, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")))
            logger.debug("Unicode fonts registered successfully")
        except Exception as e:
            logger.error(f"Failed to register fonts: {e}")
            raise Exception(f"Αποτυχία φόρτωσης γραμματοσειρών: {str(e)}")
    
    @staticmethod
    def _create_pdf_styles():
        """Create custom PDF styles with Greek font support."""
        styles = getSampleStyleSheet()
        
        # Custom title style
        styles.add(ParagraphStyle(
            name='ReportTitle',
            fontName='DejaVu-Bold',
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.HexColor('#4472C4')
        ))
        
        # Custom normal style
        styles.add(ParagraphStyle(
            name='ReportNormal',
            fontName='DejaVu',
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Custom summary style
        styles.add(ParagraphStyle(
            name='ReportSummary',
            fontName='DejaVu-Bold',
            fontSize=11,
            alignment=TA_LEFT,
            spaceAfter=4
        ))
        
        return styles
    
    @staticmethod
    def _create_pdf_table(result: SubscriptionReportResult) -> Table:
        """Create the data table for PDF."""
        # Headers
        headers = ["Κωδικός", "Πελάτης", "Πόλη", "Μέλη", "Χρεωθέν", "Πληρωμένο", "Υπόλοιπο"]
        
        # Build table data
        table_data = [headers]
        
        for row in result.rows:
            table_data.append([
                str(row.family_code),
                row.family_name,
                row.city,
                str(row.members_count),
                f"{float(row.total_amount):.2f} €",
                f"{float(row.paid_amount):.2f} €",
                f"{float(row.remaining_amount):.2f} €"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1.5*cm, 5*cm, 3*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        
        # Table style
        table_style = TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Data rows style
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Κωδικός
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Μέλη
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Ποσά
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        
        table.setStyle(table_style)
        
        return table
    
    @staticmethod
    def _create_pdf_summary(result: SubscriptionReportResult, styles) -> list:
        """Create summary section for PDF."""
        summary = result.summary
        summary_content = []
        
        # Summary title
        summary_title = Paragraph("<b>Σύνοψη</b>", styles['ReportSummary'])
        summary_content.append(summary_title)
        summary_content.append(Spacer(1, 0.3*cm))
        
        # Summary data
        summary_lines = [
            f"<b>Σύνολο οικογενειών:</b> {summary.total_families}",
            f"<b>Σύνολο μελών:</b> {summary.total_members}",
            f"<b>Σύνολο χρεωθέντων:</b> {float(summary.total_charged):.2f} €",
            f"<b>Σύνολο εισπράξεων:</b> <font color='green'>{float(summary.total_paid):.2f} €</font>",
            f"<b>Συνολική οφειλή:</b> <font color='red'>{float(summary.total_debt):.2f} €</font>",
        ]
        
        for line in summary_lines:
            para = Paragraph(line, styles['ReportNormal'])
            summary_content.append(para)
        
        return summary_content
    
    @staticmethod
    def export_subscription_report_to_excel(result: SubscriptionReportResult, filepath: str) -> None:
        """
        Εξάγει τα δεδομένα της αναφοράς συνδρομών σε αρχείο Excel (.xlsx).
        
        Args:
            result: SubscriptionReportResult με rows και summary
            filepath: Πλήρης διαδρομή αρχείου για αποθήκευση
            
        Raises:
            Exception: Αν αποτύχει η εξαγωγή
        """
        try:
            logger.info(f"Exporting subscription report to Excel: {filepath}")
            
            # Create workbook
            wb = Workbook()
            
            # Remove default sheet
            if 'Sheet' in wb.sheetnames:
                wb.remove(wb['Sheet'])
            
            # Create sheets
            ExportService._create_details_sheet(wb, result)
            ExportService._create_summary_sheet(wb, result)
            
            # Save workbook
            wb.save(filepath)
            
            logger.info(f"Successfully exported {len(result.rows)} rows to Excel")
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _create_details_sheet(wb: Workbook, result: SubscriptionReportResult) -> None:
        """Create the detailed data sheet."""
        ws = wb.create_sheet("Αναλυτικά", 0)
        
        # Define headers
        headers = ["Κωδικός", "Πελάτης", "Πόλη", "Μέλη", "Χρεωθέν", "Πληρωμένο", "Υπόλοιπο"]
        
        # Style for headers
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Write headers
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Write data rows
        for row_idx, row_data in enumerate(result.rows, start=2):
            # Κωδικός
            cell = ws.cell(row=row_idx, column=1, value=row_data.family_code)
            cell.border = border
            cell.alignment = Alignment(horizontal="center")
            
            # Πελάτης
            cell = ws.cell(row=row_idx, column=2, value=row_data.family_name)
            cell.border = border
            
            # Πόλη
            cell = ws.cell(row=row_idx, column=3, value=row_data.city)
            cell.border = border
            
            # Μέλη
            cell = ws.cell(row=row_idx, column=4, value=row_data.members_count)
            cell.border = border
            cell.alignment = Alignment(horizontal="center")
            
            # Χρεωθέν
            cell = ws.cell(row=row_idx, column=5, value=float(row_data.total_amount))
            cell.border = border
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal="right")
            
            # Πληρωμένο
            cell = ws.cell(row=row_idx, column=6, value=float(row_data.paid_amount))
            cell.border = border
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal="right")
            
            # Υπόλοιπο
            cell = ws.cell(row=row_idx, column=7, value=float(row_data.remaining_amount))
            cell.border = border
            cell.number_format = '#,##0.00'
            cell.alignment = Alignment(horizontal="right")
            
            # Color code remaining amount
            if row_data.remaining_amount > 0:
                cell.font = Font(color="C00000", bold=True)  # Red for debt
            elif row_data.remaining_amount < 0:
                cell.font = Font(color="0070C0")  # Blue for overpayment
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 12  # Κωδικός
        ws.column_dimensions['B'].width = 30  # Πελάτης
        ws.column_dimensions['C'].width = 20  # Πόλη
        ws.column_dimensions['D'].width = 10  # Μέλη
        ws.column_dimensions['E'].width = 14  # Χρεωθέν
        ws.column_dimensions['F'].width = 14  # Πληρωμένο
        ws.column_dimensions['G'].width = 14  # Υπόλοιπο
        
        # Freeze header row
        ws.freeze_panes = 'A2'
    
    @staticmethod
    def _create_summary_sheet(wb: Workbook, result: SubscriptionReportResult) -> None:
        """Create the summary sheet."""
        ws = wb.create_sheet("Σύνοψη", 1)
        
        summary = result.summary
        
        # Style for labels
        label_font = Font(bold=True, size=12)
        value_font = Font(size=12)
        
        # Title
        ws.cell(row=1, column=1, value="Σύνοψη Αναφοράς Συνδρομών")
        ws.cell(row=1, column=1).font = Font(bold=True, size=14, color="4472C4")
        ws.merge_cells('A1:B1')
        
        # Add empty row
        row = 3
        
        # Σύνολο οικογενειών
        ws.cell(row=row, column=1, value="Σύνολο οικογενειών:")
        ws.cell(row=row, column=1).font = label_font
        ws.cell(row=row, column=2, value=summary.total_families)
        ws.cell(row=row, column=2).font = value_font
        row += 1
        
        # Σύνολο μελών
        ws.cell(row=row, column=1, value="Σύνολο μελών:")
        ws.cell(row=row, column=1).font = label_font
        ws.cell(row=row, column=2, value=summary.total_members)
        ws.cell(row=row, column=2).font = value_font
        row += 2
        
        # Σύνολο χρεωθέντων
        ws.cell(row=row, column=1, value="Σύνολο χρεωθέντων:")
        ws.cell(row=row, column=1).font = label_font
        cell = ws.cell(row=row, column=2, value=float(summary.total_charged))
        cell.font = value_font
        cell.number_format = '#,##0.00 €'
        row += 1
        
        # Σύνολο εισπράξεων
        ws.cell(row=row, column=1, value="Σύνολο εισπράξεων:")
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="008000")  # Green
        cell = ws.cell(row=row, column=2, value=float(summary.total_paid))
        cell.font = Font(size=12, color="008000")
        cell.number_format = '#,##0.00 €'
        row += 1
        
        # Συνολική οφειλή
        ws.cell(row=row, column=1, value="Συνολική οφειλή:")
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="C00000")  # Red
        cell = ws.cell(row=row, column=2, value=float(summary.total_debt))
        cell.font = Font(size=12, color="C00000", bold=True)
        cell.number_format = '#,##0.00 €'
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20
