# -*- coding: utf-8 -*-
"""
Email Service - Handles email sending functionality using SMTP settings.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional, List

from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails using configured SMTP settings.
    """
    
    def __init__(self, settings_service: SettingsService):
        """
        Initialize EmailService.
        
        Args:
            settings_service: Settings service instance for SMTP configuration
        """
        self.settings_service = settings_service
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        html: bool = False
    ) -> bool:
        """
        Send an email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            attachments: List of file paths to attach (optional)
            html: If True, body is treated as HTML (default: False)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get SMTP configuration
            smtp_config = self.settings_service.get_smtp_config()
            
            # Validate SMTP configuration
            if not smtp_config.get('host'):
                logger.error("SMTP host not configured")
                return False
            
            # Create message
            msg = MIMEMultipart()
            
            # Set from address
            from_name = smtp_config.get('from_name', '')
            from_email = smtp_config.get('from_email', '')
            
            if from_name and from_email:
                msg['From'] = f"{from_name} <{from_email}>"
            elif from_email:
                msg['From'] = from_email
            else:
                logger.error("From email not configured")
                return False
            
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            body_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, body_type, 'utf-8'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if not Path(file_path).exists():
                        logger.warning(f"Attachment not found: {file_path}")
                        continue
                    
                    try:
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                            file_name = Path(file_path).name
                            
                            # Determine MIME type based on extension
                            if file_path.lower().endswith('.pdf'):
                                attachment = MIMEApplication(file_data, _subtype='pdf')
                            else:
                                attachment = MIMEApplication(file_data)
                            
                            attachment.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=file_name
                            )
                            msg.attach(attachment)
                            logger.debug(f"Attached file: {file_name}")
                    except Exception as e:
                        logger.error(f"Failed to attach file {file_path}: {e}")
            
            # Connect to SMTP server and send
            host = smtp_config.get('host')
            port = smtp_config.get('port', 587)
            use_tls = smtp_config.get('use_tls', True)
            username = smtp_config.get('username', '')
            password = smtp_config.get('password', '')
            
            if use_tls:
                server = smtplib.SMTP(host, port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(host, port, timeout=30)
            
            # Login if credentials provided
            if username and password:
                server.login(username, password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    def send_receipt_email(
        self,
        to_email: str,
        payment_data: dict,
        pdf_path: Optional[str] = None,
        custom_subject: Optional[str] = None,
        custom_body: Optional[str] = None
    ) -> bool:
        """
        Send a payment receipt email with optional PDF attachment.
        
        Args:
            to_email: Recipient email address
            payment_data: Dictionary with payment info (family_name, payment_date, amount, receipt_no)
            pdf_path: Path to PDF receipt file (optional)
            custom_subject: Custom subject (uses template if None)
            custom_body: Custom body (uses template if None)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get email receipt configuration
            receipt_config = self.settings_service.get_email_receipt_config()
            org_name = self.settings_service.get_org_name()
            
            # Use custom or template subject/body
            subject = custom_subject or receipt_config.get('subject', 'Απόδειξη Πληρωμής')
            body = custom_body or receipt_config.get('body', 'Σας αποστέλλουμε την απόδειξη πληρωμής σας.')
            
            # Replace placeholders
            body = body.format(
                family_name=payment_data.get('family_name', ''),
                client_name=payment_data.get('family_name', ''),
                payment_date=payment_data.get('payment_date', ''),
                amount=payment_data.get('amount', ''),
                receipt_no=payment_data.get('receipt_no', ''),
                org_name=org_name
            )
            subject = subject.format(
                family_name=payment_data.get('family_name', ''),
                client_name=payment_data.get('family_name', ''),
                payment_date=payment_data.get('payment_date', ''),
                amount=payment_data.get('amount', ''),
                receipt_no=payment_data.get('receipt_no', ''),
                org_name=org_name
            )
            
            # Send email with optional PDF attachment
            return self.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                attachments=[pdf_path] if pdf_path else None
            )
            
        except Exception as e:
            logger.error(f"Failed to send receipt email: {e}", exc_info=True)
            return False
    
    def send_subscription_reminder_email(
        self,
        to_email: str,
        subscription_data: dict,
        custom_subject: Optional[str] = None,
        custom_body: Optional[str] = None,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Send a subscription reminder email.
        
        Args:
            to_email: Recipient email address
            subscription_data: Dictionary with subscription info (family_name, expiry_date, total_amount, paid_amount, remaining_amount)
            custom_subject: Custom subject (uses template if None)
            custom_body: Custom body (uses template if None)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get email subscription configuration
            subscription_config = self.settings_service.get_email_subscription_config()
            org_name = self.settings_service.get_org_name()
            
            # Use custom or template subject/body
            subject = custom_subject or subscription_config.get('subject', 'Υπενθύμιση Συνδρομής')
            body = custom_body or subscription_config.get('body', 'Σας υπενθυμίζουμε ότι η συνδρομή σας λήγει.')
            
            # Replace placeholders
            body = body.format(
                family_name=subscription_data.get('family_name', ''),
                client_name=subscription_data.get('family_name', ''),
                expiry_date=subscription_data.get('expiry_date', ''),
                total_amount=subscription_data.get('total_amount', ''),
                paid_amount=subscription_data.get('paid_amount', ''),
                remaining_amount=subscription_data.get('remaining_amount', ''),
                org_name=org_name
            )
            subject = subject.format(
                family_name=subscription_data.get('family_name', ''),
                client_name=subscription_data.get('family_name', ''),
                expiry_date=subscription_data.get('expiry_date', ''),
                total_amount=subscription_data.get('total_amount', ''),
                paid_amount=subscription_data.get('paid_amount', ''),
                remaining_amount=subscription_data.get('remaining_amount', ''),
                org_name=org_name
            )
            
            # Send email (with optional attachment, e.g. the purchase receipt)
            return self.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                attachments=[attachment_path] if attachment_path else None
            )
            
        except Exception as e:
            logger.error(f"Failed to send subscription reminder email: {e}", exc_info=True)
            return False
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test SMTP connection with current settings.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            smtp_config = self.settings_service.get_smtp_config()
            
            if not smtp_config.get('host'):
                return False, "SMTP host δεν έχει ρυθμιστεί"
            
            host = smtp_config.get('host')
            port = smtp_config.get('port', 587)
            use_tls = smtp_config.get('use_tls', True)
            username = smtp_config.get('username', '')
            password = smtp_config.get('password', '')
            
            # Connect to SMTP server
            if use_tls:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(host, port, timeout=10)
            
            # Try to login if credentials provided
            if username and password:
                server.login(username, password)
            
            server.quit()
            
            return True, "Η σύνδεση με τον SMTP server ήταν επιτυχής!"
            
        except smtplib.SMTPAuthenticationError:
            return False, "Αποτυχία ταυτοποίησης. Ελέγξτε το username και password."
        except smtplib.SMTPException as e:
            return False, f"Σφάλμα SMTP: {str(e)}"
        except Exception as e:
            return False, f"Αποτυχία σύνδεσης: {str(e)}"
    
    def is_configured(self) -> bool:
        """
        Check if SMTP is properly configured.
        
        Returns:
            True if SMTP settings are configured, False otherwise
        """
        smtp_config = self.settings_service.get_smtp_config()
        return bool(
            smtp_config.get('host') and
            smtp_config.get('from_email')
        )
