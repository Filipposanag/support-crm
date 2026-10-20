"""
Import service for CSV data import operations.

This module handles importing legacy data from CSV files (client.csv, members.csv, report.csv)
with encoding detection, validation, and batch processing.
"""

import csv
import logging
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
import time as time_module

try:
    import openpyxl
    XLSX_SUPPORT = True
except ImportError:
    XLSX_SUPPORT = False
    logger = logging.getLogger(__name__)
    logger.warning("openpyxl not installed - XLSX import not supported")

from db.repositories.families_repo import FamiliesRepository
from db.repositories.members_repo import MembersRepository
from db.repositories.payments_repo import PaymentsRepository
from db.repositories.imports_repo import ImportsRepository
from models.family import Family
from models.member import Member
from models.payment import Payment

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """
    Result of a CSV import operation.
    
    Attributes:
        total_rows: Total number of rows in the CSV file
        success_count: Number of successfully imported rows
        failed_count: Number of failed rows
        errors: List of error messages
        duration_seconds: Time taken for the import operation
    """
    total_rows: int
    success_count: int
    failed_count: int
    errors: List[str]
    duration_seconds: float


class ImportService:
    """
    Service for importing CSV data into the database.
    
    Handles encoding detection, validation, batch processing, and error logging.
    """
    
    def __init__(
        self,
        families_repo: FamiliesRepository,
        members_repo: MembersRepository,
        payments_repo: PaymentsRepository,
        imports_repo: ImportsRepository
    ):
        """
        Initialize ImportService with repository dependencies.
        
        Args:
            families_repo: Repository for family operations
            members_repo: Repository for member operations
            payments_repo: Repository for payment operations
            imports_repo: Repository for import logging
        """
        self.families_repo = families_repo
        self.members_repo = members_repo
        self.payments_repo = payments_repo
        self.imports_repo = imports_repo
        
        logger.info("ImportService initialized")

    def import_clients_csv(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ImportResult:
        """
        Import client.csv or client.xlsx file into families table.
        
        CSV Format:
        - Encoding: cp1253 (with fallback to latin1, utf-8)
        - Delimiter: semicolon (;)
        - Columns: CODE, LNAME, FNAME, PNAME/SNAME/SPNAME/SLNAME, ADT, PROF, ADDR1, CITY, TK, TEL1, MOBILE1, EMAIL, BIRTH, MEMBERS
        
        Excel Format:
        - Same columns as CSV
        
        Args:
            file_path: Path to the client.csv or client.xlsx file
            progress_callback: Optional callback function(current, total) for progress updates
            
        Returns:
            ImportResult with statistics and errors
        """
        start_time = time_module.time()
        errors = []
        success_count = 0
        failed_count = 0
        total_rows = 0
        
        file_name = Path(file_path).name
        logger.info(f"Starting import of clients file: {file_name}")
        
        # Load rows from file (Excel or CSV)
        file_ext = Path(file_path).suffix.lower()
        rows = []
        
        if file_ext in ['.xlsx', '.xls']:
            # Excel file
            if not XLSX_SUPPORT:
                error_msg = "Η υποστήριξη Excel δεν είναι διαθέσιμη. Παρακαλώ εγκαταστήστε το openpyxl: pip install openpyxl"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
            
            try:
                rows = self._load_clients_xlsx(file_path)
                total_rows = len(rows)
                logger.info(f"Loaded {total_rows} rows from Excel file")
            except Exception as e:
                error_msg = f"Αποτυχία φόρτωσης Excel: {e}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
        else:
            # CSV file
            # Try different encodings
            encodings = ['cp1253', 'latin1', 'utf-8', 'utf-8-sig']
            file_content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                        file_content = f.read()
                        # Check for NUL bytes
                        if '\x00' in file_content:
                            error_msg = (
                                "Το αρχείο περιέχει binary δεδομένα. "
                                "Πιθανώς είναι Excel αρχείο. Παρακαλώ αποθηκεύστε το ως CSV."
                            )
                            logger.error(error_msg)
                            return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
                        used_encoding = encoding
                        logger.info(f"Successfully opened file with encoding: {encoding}")
                        break
                except UnicodeDecodeError as e:
                    logger.debug(f"Failed to open with encoding {encoding}: {e}")
                    continue
            
            if file_content is None:
                error_msg = f"Αδυναμία ανάγνωσης αρχείου με τις υποστηριζόμενες κωδικοποιήσεις: {encodings}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
            
            # Parse CSV
            try:
                csv_reader = csv.DictReader(file_content.splitlines(), delimiter=';')
                rows = list(csv_reader)
                total_rows = len(rows)
                logger.info(f"Parsed {total_rows} rows from CSV")
            except Exception as e:
                error_msg = f"Αποτυχία ανάλυσης CSV: {e}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
        
        # Process in batches
        batch_size = 500
        batch_data = []
        
        for row_num, row in enumerate(rows, start=1):
            try:
                # Map CSV columns to Family model
                family_data = self._map_client_row_to_family(row)
                
                # Check if family already exists by legacy_code
                existing_family = self.families_repo.get_by_legacy_code(family_data['legacy_code'])
                
                if existing_family:
                    # Update existing family
                    self.families_repo.update(existing_family['id'], family_data)
                else:
                    # Add to batch for insert
                    batch_data.append(family_data)
                
                success_count += 1
                
                # Progress callback every 100 records
                if progress_callback and row_num % 100 == 0:
                    progress_callback(row_num, total_rows)
                
                # Commit batch
                if len(batch_data) >= batch_size:
                    self._insert_family_batch(batch_data)
                    batch_data = []
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Row {row_num}: {str(e)} - Data: {row}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Insert remaining batch
        if batch_data:
            try:
                self._insert_family_batch(batch_data)
            except Exception as e:
                error_msg = f"Failed to insert final batch: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        duration = time_module.time() - start_time
        
        # Log import to database
        try:
            error_log = '\n'.join(errors[:100]) if errors else None  # Limit error log size
            self.imports_repo.log_import(
                file_name=file_name,
                file_type='client',
                rows_total=total_rows,
                rows_success=success_count,
                rows_failed=failed_count,
                error_log=error_log
            )
        except Exception as e:
            logger.error(f"Failed to log import: {e}")
        
        logger.info(
            f"Client import completed: {success_count} success, {failed_count} failed, "
            f"{duration:.2f}s"
        )
        
        return ImportResult(total_rows, success_count, failed_count, errors, duration)
    
    def _map_client_row_to_family(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Map a CSV row from client.csv to family data dictionary.
        
        Args:
            row: Dictionary representing a CSV row
            
        Returns:
            Dictionary with family data ready for database insertion
        """
        # Helper function to get value or None
        def get_value(key: str, default=None):
            value = row.get(key, '').strip()
            return value if value else default
        
        # Parse legacy code
        legacy_code = int(get_value('CODE', 0))
        
        # Combine spouse name fields (try different column names)
        spouse_name = (
            get_value('SPNAME') or 
            get_value('SLNAME') or 
            get_value('PNAME') or 
            get_value('SNAME')
        )
        
        # Parse birth date
        birth_date = None
        birth_str = get_value('BIRTH')
        if birth_str:
            birth_date = self._parse_date(birth_str)
        
        # Parse members count
        members_count = 0
        members_str = get_value('MEMBERS')
        if members_str:
            try:
                members_count = int(members_str)
            except ValueError:
                members_count = 0
        
        return {
            'legacy_code': legacy_code,
            'last_name': get_value('LNAME', ''),
            'first_name': get_value('FNAME', ''),
            'spouse_name': spouse_name,
            'national_id': get_value('ADT'),
            'profession': get_value('PROF'),
            'address': get_value('ADDR1'),
            'city': get_value('CITY'),
            'postal_code': get_value('TK'),
            'phone': get_value('TEL1'),
            'mobile': get_value('MOBILE1'),
            'email': get_value('EMAIL'),
            'birth_date': birth_date,
            'members_count': members_count,
            'is_active': True
        }
    
    def _insert_family_batch(self, batch_data: List[Dict[str, Any]]):
        """
        Insert a batch of family records.
        
        Args:
            batch_data: List of family data dictionaries
        """
        for family_data in batch_data:
            try:
                self.families_repo.create(family_data)
            except Exception as e:
                # Handle duplicate legacy_code errors
                if 'Duplicate entry' in str(e) or 'unique constraint' in str(e).lower():
                    logger.debug(f"Duplicate legacy_code {family_data['legacy_code']}, skipping")
                else:
                    raise

    def import_members_csv(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ImportResult:
        """
        Import members.csv or members.xlsx file into members table.
        
        CSV Format:
        - Encoding: cp1253 (with fallback to latin1, utf-8)
        - Delimiter: semicolon (;)
        - Columns: CODE, ANO, DATE, FNAME, LNAME, ADT, BDATE, PROF, MARRIED, MDATE
        
        Excel Format:
        - Same columns as CSV
        
        Args:
            file_path: Path to the members.csv or members.xlsx file
            progress_callback: Optional callback function(current, total) for progress updates
            
        Returns:
            ImportResult with statistics and errors
        """
        start_time = time_module.time()
        errors = []
        success_count = 0
        failed_count = 0
        total_rows = 0
        
        file_name = Path(file_path).name
        logger.info(f"Starting import of members file: {file_name}")
        
        # Check if file is Excel format - now supported!
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.xlsx', '.xls']:
            if not XLSX_SUPPORT:
                error_msg = "Η υποστήριξη Excel δεν είναι διαθέσιμη. Παρακαλώ εγκαταστήστε το openpyxl: pip install openpyxl"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
            
            try:
                rows = self._load_members_xlsx(file_path)
                total_rows = len(rows)
                logger.info(f"Loaded {total_rows} rows from Excel file")
            except Exception as e:
                error_msg = f"Αποτυχία φόρτωσης Excel: {e}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
        else:
            # CSV file handling
            # Try different encodings
            encodings = ['cp1253', 'latin1', 'utf-8', 'utf-8-sig']
            file_content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                        file_content = f.read()
                        # Check for NUL bytes
                        if '\x00' in file_content:
                            error_msg = (
                                "Το αρχείο περιέχει binary δεδομένα. "
                                "Πιθανώς είναι Excel αρχείο. Παρακαλώ αποθηκεύστε το ως CSV."
                            )
                            logger.error(error_msg)
                            return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
                        used_encoding = encoding
                        logger.info(f"Successfully opened file with encoding: {encoding}")
                        break
                except UnicodeDecodeError as e:
                    logger.debug(f"Failed to open with encoding {encoding}: {e}")
                    continue
            
            if file_content is None:
                error_msg = f"Αδυναμία ανάγνωσης αρχείου με τις υποστηριζόμενες κωδικοποιήσεις: {encodings}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
            
            # Parse CSV
            try:
                csv_reader = csv.DictReader(file_content.splitlines(), delimiter=';')
                rows = list(csv_reader)
                total_rows = len(rows)
                logger.info(f"Parsed {total_rows} rows from CSV")
            except Exception as e:
                error_msg = f"Αποτυχία ανάλυσης CSV: {e}"
                logger.error(error_msg)
                return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
        
        # Process in batches
        batch_size = 500
        batch_data = []
        
        for row_num, row in enumerate(rows, start=1):
            try:
                # Get legacy family code
                legacy_family_code = int(row.get('CODE', '0').strip())
                
                # Find matching family
                family = self.families_repo.get_by_legacy_code(legacy_family_code)
                
                if not family:
                    failed_count += 1
                    error_msg = f"Row {row_num}: Family not found for legacy_code={legacy_family_code}"
                    errors.append(error_msg)
                    logger.debug(error_msg)
                    continue
                
                # Map CSV columns to Member model
                member_data = self._map_member_row_to_member(row, family['id'])
                
                # Add to batch
                batch_data.append(member_data)
                success_count += 1
                
                # Progress callback every 100 records
                if progress_callback and row_num % 100 == 0:
                    progress_callback(row_num, total_rows)
                
                # Commit batch
                if len(batch_data) >= batch_size:
                    self._insert_member_batch(batch_data)
                    batch_data = []
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Row {row_num}: {str(e)} - Data: {row}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Insert remaining batch
        if batch_data:
            try:
                self._insert_member_batch(batch_data)
            except Exception as e:
                error_msg = f"Failed to insert final batch: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        duration = time_module.time() - start_time
        
        # Log import to database
        try:
            error_log = '\n'.join(errors[:100]) if errors else None
            self.imports_repo.log_import(
                file_name=file_name,
                file_type='members',
                rows_total=total_rows,
                rows_success=success_count,
                rows_failed=failed_count,
                error_log=error_log
            )
        except Exception as e:
            logger.error(f"Failed to log import: {e}")
        
        logger.info(
            f"Members import completed: {success_count} success, {failed_count} failed, "
            f"{duration:.2f}s"
        )
        
        return ImportResult(total_rows, success_count, failed_count, errors, duration)
    
    def _map_member_row_to_member(self, row: Dict[str, str], family_id: int) -> Dict[str, Any]:
        """
        Map a CSV row from members.csv to member data dictionary.
        
        Args:
            row: Dictionary representing a CSV row
            family_id: ID of the family this member belongs to
            
        Returns:
            Dictionary with member data ready for database insertion
        """
        # Helper function to get value or None
        def get_value(key: str, default=None):
            value = row.get(key, '').strip()
            return value if value else default
        
        # Parse legacy family code and inner number
        legacy_family_code = int(get_value('CODE', 0))
        inner_no = int(get_value('ANO', 0))
        
        # Parse registration date
        reg_date = None
        date_str = get_value('DATE')
        if date_str:
            reg_date = self._parse_date(date_str)
        
        # Parse birth date
        birth_date = None
        bdate_str = get_value('BDATE')
        if bdate_str:
            birth_date = self._parse_date(bdate_str)
        
        # Parse married status
        married = False
        married_str = get_value('MARRIED', '').upper()
        if married_str in ('1', 'TRUE', 'YES', 'Y', 'T'):
            married = True
        
        # Parse marriage date
        marriage_date = None
        mdate_str = get_value('MDATE')
        if mdate_str:
            marriage_date = self._parse_date(mdate_str)
        
        return {
            'family_id': family_id,
            'legacy_family_code': legacy_family_code,
            'inner_no': inner_no,
            'reg_date': reg_date,
            'first_name': get_value('FNAME', ''),
            'last_name': get_value('LNAME'),
            'national_id': get_value('ADT'),
            'birth_date': birth_date,
            'profession': get_value('PROF'),
            'married': married,
            'marriage_date': marriage_date,
            'is_active': True
        }
    
    def _insert_member_batch(self, batch_data: List[Dict[str, Any]]):
        """
        Insert a batch of member records.
        
        Args:
            batch_data: List of member data dictionaries
        """
        for member_data in batch_data:
            self.members_repo.create(member_data)

    def import_reports_csv(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ImportResult:
        """
        Import report.csv or report.xlsx file into payments table.
        
        File Format (CSV/XLSX):
        - CSV Encoding: cp1253 (with fallback to latin1, utf-8)
        - CSV Delimiter: semicolon (;)
        - Required Columns: CODE, PCODE, DATE, TIME, DESCR, ADT, REMARKS, COST, DEPOSIT, RESTP
        
        Column Mapping:
        - CODE      → payments.legacy_code
        - PCODE     → payments.legacy_pcode (used to find family_id)
        - DATE      → payments.payment_date
        - TIME      → payments.payment_time
        - DESCR     → payments.description
        - ADT       → payments.receipt_no
        - REMARKS   → payments.remarks
        - COST      → payments.total_amount
        - DEPOSIT   → payments.paid_amount
        - RESTP     → payments.remaining_amount
        
        Args:
            file_path: Path to the report.csv or report.xlsx file
            progress_callback: Optional callback function(current, total) for progress updates
            
        Returns:
            ImportResult with statistics and errors
        """
        start_time = time_module.time()
        errors = []
        success_count = 0
        failed_count = 0
        total_rows = 0
        
        file_name = Path(file_path).name
        logger.info(f"Starting import of payments file: {file_name}")
        
        # Load file (CSV or XLSX)
        try:
            rows = self._load_payments_file(file_path)
            total_rows = len(rows)
            logger.info(f"Loaded {total_rows} rows from file")
        except Exception as e:
            error_msg = f"Failed to load file: {e}"
            logger.error(error_msg)
            return ImportResult(0, 0, 0, [error_msg], time_module.time() - start_time)
        
        # Process in batches
        batch_size = 500
        batch_data = []
        
        for row_num, row in enumerate(rows, start=1):
            try:
                # Get legacy code (family code) - try CODE first, then PCODE
                legacy_code_str = row.get('CODE', '').strip()
                if not legacy_code_str:
                    legacy_code_str = row.get('PCODE', '').strip()
                
                if not legacy_code_str or legacy_code_str == '0':
                    failed_count += 1
                    error_msg = f"Row {row_num}: Missing or invalid CODE/PCODE"
                    errors.append(error_msg)
                    logger.debug(error_msg)
                    continue
                
                legacy_code = int(legacy_code_str)
                
                # Find matching family by legacy_code
                family = self.families_repo.get_by_legacy_code(legacy_code)
                
                if not family:
                    failed_count += 1
                    error_msg = f"Row {row_num}: Family not found for legacy_code={legacy_code}"
                    errors.append(error_msg)
                    logger.debug(error_msg)
                    continue
                
                # Map CSV columns to Payment model
                payment_data = self._map_report_row_to_payment(row, family['id'])
                
                # Add to batch
                batch_data.append(payment_data)
                success_count += 1
                
                # Progress callback every 100 records
                if progress_callback and row_num % 100 == 0:
                    progress_callback(row_num, total_rows)
                
                # Commit batch
                if len(batch_data) >= batch_size:
                    self._insert_payment_batch(batch_data)
                    batch_data = []
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Row {row_num}: {str(e)} - Data: {row}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Insert remaining batch
        if batch_data:
            try:
                self._insert_payment_batch(batch_data)
            except Exception as e:
                error_msg = f"Failed to insert final batch: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        duration = time_module.time() - start_time
        
        # Log import to database
        try:
            error_log = '\n'.join(errors[:100]) if errors else None
            self.imports_repo.log_import(
                file_name=file_name,
                file_type='report',
                rows_total=total_rows,
                rows_success=success_count,
                rows_failed=failed_count,
                error_log=error_log
            )
        except Exception as e:
            logger.error(f"Failed to log import: {e}")
        
        logger.info(
            f"Report import completed: {success_count} success, {failed_count} failed, "
            f"{duration:.2f}s"
        )
        
        return ImportResult(total_rows, success_count, failed_count, errors, duration)
    
    def _map_report_row_to_payment(self, row: Dict[str, str], family_id: int) -> Dict[str, Any]:
        """
        Map a CSV/XLSX row from report file to payment data dictionary.
        
        Column Mapping:
        - CODE      → payments.legacy_code
        - PCODE     → payments.legacy_pcode
        - DATE      → payments.payment_date
        - TIME      → payments.payment_time
        - DESCR     → payments.description
        - ADT       → payments.receipt_no
        - REMARKS   → payments.remarks
        - COST      → payments.total_amount
        - DEPOSIT   → payments.paid_amount
        - RESTP     → payments.remaining_amount
        
        Args:
            row: Dictionary representing a file row
            family_id: ID of the family this payment belongs to
            
        Returns:
            Dictionary with payment data ready for database insertion
        """
        # Helper function to get value or None
        def get_value(key: str, default=None):
            value = row.get(key, '').strip()
            return value if value else default
        
        # Parse legacy codes
        # CODE → legacy_code
        legacy_code = None
        code_str = get_value('CODE')
        if code_str and code_str != '0':
            try:
                legacy_code = int(code_str)
            except ValueError:
                pass
        
        # PCODE → legacy_pcode
        legacy_pcode = None
        pcode_str = get_value('PCODE')
        if pcode_str and pcode_str != '0':
            try:
                legacy_pcode = int(pcode_str)
            except ValueError:
                pass
        
        # DATE → payment_date
        payment_date = None
        date_str = get_value('DATE')
        if date_str:
            payment_date = self._parse_date(date_str)
        
        # TIME → payment_time
        payment_time = None
        time_str = get_value('TIME')
        if time_str:
            payment_time = self._parse_time(time_str)
        
        # COST → total_amount
        total_amount = Decimal('0.00')
        cost_str = get_value('COST')
        if cost_str:
            try:
                # Handle both comma and dot as decimal separator
                cost_str = cost_str.replace(',', '.')
                total_amount = Decimal(cost_str)
            except Exception as e:
                logger.debug(f"Failed to parse COST '{cost_str}': {e}")
                total_amount = Decimal('0.00')
        
        # DEPOSIT → paid_amount
        paid_amount = Decimal('0.00')
        deposit_str = get_value('DEPOSIT')
        if deposit_str:
            try:
                deposit_str = deposit_str.replace(',', '.')
                paid_amount = Decimal(deposit_str)
            except Exception as e:
                logger.debug(f"Failed to parse DEPOSIT '{deposit_str}': {e}")
                paid_amount = Decimal('0.00')
        
        # RESTP → remaining_amount
        remaining_amount = Decimal('0.00')
        restp_str = get_value('RESTP')
        if restp_str:
            try:
                restp_str = restp_str.replace(',', '.')
                remaining_amount = Decimal(restp_str)
            except Exception as e:
                logger.debug(f"Failed to parse RESTP '{restp_str}': {e}")
                # Calculate if parsing failed
                remaining_amount = total_amount - paid_amount
        else:
            # Calculate if not provided
            remaining_amount = total_amount - paid_amount
        
        # Ensure remaining_amount is not negative
        if remaining_amount < 0:
            remaining_amount = Decimal('0.00')
        
        # Calculate status based on amounts
        # - If paid_amount = 0 and remaining_amount > 0 → "unpaid"
        # - If paid_amount > 0 and remaining_amount > 0 → "partial"
        # - If remaining_amount = 0 → "paid"
        status = self._calculate_payment_status(paid_amount, remaining_amount)
        
        # Extract year from payment_date
        year = payment_date.year if payment_date else None
        
        return {
            'family_id': family_id,
            'legacy_code': legacy_code,
            'legacy_pcode': legacy_pcode,
            'payment_date': payment_date,
            'payment_time': payment_time,
            'description': get_value('DESCR'),  # DESCR → description
            'receipt_no': get_value('ADT'),     # ADT → receipt_no
            'remarks': get_value('REMARKS'),    # REMARKS → remarks
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'status': status,
            'year': year
        }
    
    def _load_payments_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Load payments data from CSV or XLSX file.
        
        Required columns: CODE, PCODE, DATE, TIME, DESCR, ADT, REMARKS, COST, DEPOSIT, RESTP
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dictionaries with payment data
            
        Raises:
            Exception: If file cannot be loaded or required columns are missing
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        # Validate file extension
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            raise Exception(
                "Μη υποστηριζόμενος τύπος αρχείου. "
                "Παρακαλώ επιλέξτε αρχείο CSV ή Excel (.csv ή .xlsx)."
            )
        
        # Required columns
        required_columns = ['CODE', 'PCODE', 'DATE', 'TIME', 'DESCR', 'ADT', 'REMARKS', 'COST', 'DEPOSIT', 'RESTP']
        
        if file_ext in ['.xlsx', '.xls']:
            return self._load_payments_xlsx(file_path, required_columns)
        else:
            return self._load_payments_csv(file_path, required_columns)
    
    def _load_payments_csv(self, file_path: str, required_columns: List[str]) -> List[Dict[str, str]]:
        """
        Load payments data from CSV file.
        
        Args:
            file_path: Path to CSV file
            required_columns: List of required column names
            
        Returns:
            List of dictionaries with payment data
            
        Raises:
            Exception: If file cannot be loaded or required columns are missing
        """
        # Try different encodings
        encodings = ['cp1253', 'latin1', 'utf-8', 'utf-8-sig']
        file_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    file_content = f.read()
                    # Check for NUL bytes
                    if '\x00' in file_content:
                        raise Exception(
                            "Το αρχείο περιέχει binary δεδομένα. "
                            "Πιθανώς είναι Excel αρχείο (.xlsx). "
                            "Για αρχεία Excel, χρησιμοποιήστε επέκταση .xlsx στο όνομα αρχείου."
                        )
                    used_encoding = encoding
                    logger.info(f"Successfully opened CSV with encoding: {encoding}")
                    break
            except UnicodeDecodeError as e:
                logger.debug(f"Failed to open with encoding {encoding}: {e}")
                continue
        
        if file_content is None:
            raise Exception(f"Αδυναμία ανάγνωσης αρχείου με τις υποστηριζόμενες κωδικοποιήσεις: {encodings}")
        
        # Parse CSV
        csv_reader = csv.DictReader(file_content.splitlines(), delimiter=';')
        rows = list(csv_reader)
        
        if not rows:
            raise Exception("Το αρχείο είναι κενό ή δεν έχει δεδομένα")
        
        # Validate required columns
        actual_columns = set(rows[0].keys())
        missing_columns = [col for col in required_columns if col not in actual_columns]
        
        if missing_columns:
            raise Exception(
                f"Λείπουν απαιτούμενες στήλες: {', '.join(missing_columns)}. "
                f"Απαιτούμενες στήλες: {', '.join(required_columns)}"
            )
        
        logger.info(f"CSV validation passed - all required columns present")
        return rows
    
    def _load_payments_xlsx(self, file_path: str, required_columns: List[str]) -> List[Dict[str, str]]:
        """
        Load payments data from XLSX file.
        
        Args:
            file_path: Path to XLSX file
            required_columns: List of required column names
            
        Returns:
            List of dictionaries with payment data
            
        Raises:
            Exception: If file cannot be loaded or required columns are missing
        """
        if not XLSX_SUPPORT:
            raise Exception("XLSX support not available. Please install openpyxl: pip install openpyxl")
        
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active
            
            # Get header row
            headers = []
            for cell in sheet[1]:
                headers.append(str(cell.value).strip() if cell.value else '')
            
            # Validate required columns
            actual_columns = set(headers)
            missing_columns = [col for col in required_columns if col not in actual_columns]
            
            if missing_columns:
                raise Exception(
                    f"Missing required columns: {', '.join(missing_columns)}. "
                    f"Required columns are: {', '.join(required_columns)}"
                )
            
            # Read data rows
            rows = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                row_dict = {}
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row):
                        value = row[col_idx]
                        # Convert to string, handle None
                        row_dict[header] = str(value).strip() if value is not None else ''
                    else:
                        row_dict[header] = ''
                
                # Skip empty rows
                if any(row_dict.values()):
                    rows.append(row_dict)
            
            workbook.close()
            
            if not rows:
                raise Exception("File is empty or has no data rows")
            
            logger.info(f"XLSX validation passed - all required columns present")
            return rows
            
        except Exception as e:
            if "openpyxl" in str(e):
                raise
            raise Exception(f"Failed to load XLSX file: {e}")
    
    def _insert_payment_batch(self, batch_data: List[Dict[str, Any]]):
        """
        Insert or update a batch of payment records.
        If a payment with the same legacy_pcode and family_id exists, update it.
        Otherwise, create a new payment.
        
        Args:
            batch_data: List of payment data dictionaries
        """
        for payment_data in batch_data:
            # Validate payment_date (required field)
            if not payment_data.get('payment_date'):
                logger.warning(f"Skipping payment with missing payment_date: {payment_data}")
                continue
            
            # Check if payment already exists (by legacy_pcode and family_id)
            legacy_pcode = payment_data.get('legacy_pcode')
            family_id = payment_data.get('family_id')
            
            if legacy_pcode and family_id:
                existing = self.payments_repo.get_by_legacy_pcode_and_family(legacy_pcode, family_id)
                if existing:
                    # Update existing payment
                    self.payments_repo.update(existing['id'], payment_data)
                    logger.debug(f"Updated payment id={existing['id']} (legacy_pcode={legacy_pcode})")
                    continue
            
            # Create new payment
            self.payments_repo.create(payment_data)
    
    def _calculate_payment_status(
        self,
        paid_amount: Decimal,
        remaining_amount: Decimal
    ) -> str:
        """
        Calculate payment status based on amounts.
        
        Logic:
        - If paid_amount = 0 and remaining_amount > 0 → "unpaid"
        - If paid_amount > 0 and remaining_amount > 0 → "partial"
        - If remaining_amount = 0 → "paid"
        
        Args:
            paid_amount: Amount paid
            remaining_amount: Remaining amount
            
        Returns:
            Payment status: 'paid', 'partial', or 'unpaid'
        """
        if remaining_amount <= 0:
            return "paid"
        elif paid_amount > 0 and remaining_amount > 0:
            return "partial"
        else:
            return "unpaid"

    def preview_csv(self, file_path: str, rows: int = 10) -> List[Dict[str, Any]]:
        """
        Preview the first N rows of a CSV or XLSX file.
        
        Handles encoding detection for CSV and openpyxl for XLSX.
        
        Args:
            file_path: Path to the CSV or XLSX file
            rows: Number of rows to preview (default: 10)
            
        Returns:
            List of dictionaries representing the first N rows
            
        Raises:
            Exception: If file cannot be opened or parsed
        """
        logger.info(f"Previewing file: {file_path} (first {rows} rows)")
        
        file_ext = Path(file_path).suffix.lower()
        
        # Handle XLSX files
        if file_ext in ['.xlsx', '.xls']:
            return self._preview_xlsx(file_path, rows)
        
        # Handle CSV files
        # Try different encodings
        encodings = ['cp1253', 'latin1', 'utf-8', 'utf-8-sig']
        file_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    file_content = f.read()
                    # Check for NUL bytes which indicate binary file
                    if '\x00' in file_content:
                        raise Exception(
                            "Το αρχείο περιέχει binary δεδομένα (NUL bytes). "
                            "Πιθανώς είναι Excel αρχείο. "
                            "Παρακαλώ χρησιμοποιήστε επέκταση .xlsx για αρχεία Excel."
                        )
                    used_encoding = encoding
                    logger.info(f"Successfully opened file with encoding: {encoding}")
                    break
            except UnicodeDecodeError as e:
                logger.debug(f"Failed to open with encoding {encoding}: {e}")
                continue
            except Exception as e:
                # Re-raise non-encoding errors
                raise
        
        if file_content is None:
            error_msg = (
                f"Αδυναμία ανάγνωσης αρχείου με τις υποστηριζόμενες κωδικοποιήσεις: {encodings}. "
                "Παρακαλώ βεβαιωθείτε ότι το αρχείο είναι σε μορφή CSV."
            )
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Parse CSV
        try:
            csv_reader = csv.DictReader(file_content.splitlines(), delimiter=';')
            preview_data = []
            
            for i, row in enumerate(csv_reader):
                if i >= rows:
                    break
                preview_data.append(row)
            
            logger.info(f"Preview loaded {len(preview_data)} rows")
            return preview_data
            
        except Exception as e:
            error_msg = f"Αποτυχία ανάλυσης CSV: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _preview_xlsx(self, file_path: str, rows: int = 10) -> List[Dict[str, Any]]:
        """
        Preview the first N rows of an XLSX file.
        
        Args:
            file_path: Path to the XLSX file
            rows: Number of rows to preview
            
        Returns:
            List of dictionaries representing the first N rows
            
        Raises:
            Exception: If file cannot be opened or parsed
        """
        if not XLSX_SUPPORT:
            raise Exception(
                "Η υποστήριξη XLSX δεν είναι διαθέσιμη. "
                "Παρακαλώ εγκαταστήστε το openpyxl: pip install openpyxl"
            )
        
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active
            
            # Get header row
            headers = []
            for cell in sheet[1]:
                headers.append(str(cell.value).strip() if cell.value else '')
            
            # Read preview rows
            preview_data = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if len(preview_data) >= rows:
                    break
                
                row_dict = {}
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row):
                        value = row[col_idx]
                        row_dict[header] = str(value).strip() if value is not None else ''
                    else:
                        row_dict[header] = ''
                
                # Skip empty rows
                if any(row_dict.values()):
                    preview_data.append(row_dict)
            
            workbook.close()
            
            logger.info(f"XLSX preview loaded {len(preview_data)} rows")
            return preview_data
            
        except Exception as e:
            error_msg = f"Αποτυχία ανάγνωσης XLSX: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string in various formats.
        
        Tries multiple date formats:
        - YYYYMMDD (20250115)
        - DD/MM/YYYY (15/01/2025)
        - YYYY-MM-DD (2025-01-15)
        
        Args:
            date_str: Date string to parse
            
        Returns:
            date object or None if parsing fails
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            try:
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return date(year, month, day)
            except ValueError:
                pass
        
        # Try DD/MM/YYYY format
        if '/' in date_str:
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    day = int(parts[0])
                    month = int(parts[1])
                    year = int(parts[2])
                    return date(year, month, day)
            except ValueError:
                pass
        
        # Try YYYY-MM-DD format
        if '-' in date_str:
            try:
                parts = date_str.split('-')
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    return date(year, month, day)
            except ValueError:
                pass
        
        logger.debug(f"Failed to parse date: {date_str}")
        return None
    
    def _parse_time(self, time_str: str) -> Optional[time]:
        """
        Parse time string in various formats.
        
        Tries multiple time formats:
        - HHMM (1430)
        - HH:MM (14:30)
        - HH:MM:SS (14:30:00)
        
        Args:
            time_str: Time string to parse
            
        Returns:
            time object or None if parsing fails
        """
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        # Try HHMM format
        if len(time_str) == 4 and time_str.isdigit():
            try:
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                return time(hour, minute)
            except ValueError:
                pass
        
        # Try HH:MM or HH:MM:SS format
        if ':' in time_str:
            try:
                parts = time_str.split(':')
                if len(parts) == 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    return time(hour, minute)
                elif len(parts) == 3:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    second = int(parts[2])
                    return time(hour, minute, second)
            except ValueError:
                pass
        
        logger.debug(f"Failed to parse time: {time_str}")
        return None
    
    def _load_clients_xlsx(self, file_path: str) -> List[Dict[str, str]]:
        """
        Load clients data from XLSX file.
        
        Args:
            file_path: Path to XLSX file
            
        Returns:
            List of dictionaries with client data
            
        Raises:
            Exception: If file cannot be loaded
        """
        if not XLSX_SUPPORT:
            raise Exception("XLSX support not available. Please install openpyxl: pip install openpyxl")
        
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active
            
            # Get header row
            headers = []
            for cell in sheet[1]:
                headers.append(str(cell.value).strip() if cell.value else '')
            
            # Read data rows
            rows = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                row_dict = {}
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row):
                        value = row[col_idx]
                        # Convert to string, handle None
                        row_dict[header] = str(value).strip() if value is not None else ''
                    else:
                        row_dict[header] = ''
                
                # Skip empty rows
                if any(row_dict.values()):
                    rows.append(row_dict)
            
            workbook.close()
            
            if not rows:
                raise Exception("File is empty or has no data rows")
            
            logger.info(f"XLSX clients loaded: {len(rows)} rows")
            return rows
            
        except Exception as e:
            if "openpyxl" in str(e):
                raise
            raise Exception(f"Failed to load XLSX file: {e}")
    
    def _load_members_xlsx(self, file_path: str) -> List[Dict[str, str]]:
        """
        Load members data from XLSX file.
        
        Args:
            file_path: Path to XLSX file
            
        Returns:
            List of dictionaries with member data
            
        Raises:
            Exception: If file cannot be loaded
        """
        if not XLSX_SUPPORT:
            raise Exception("XLSX support not available. Please install openpyxl: pip install openpyxl")
        
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = workbook.active
            
            # Get header row
            headers = []
            for cell in sheet[1]:
                headers.append(str(cell.value).strip() if cell.value else '')
            
            # Read data rows
            rows = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                row_dict = {}
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row):
                        value = row[col_idx]
                        # Convert to string, handle None
                        row_dict[header] = str(value).strip() if value is not None else ''
                    else:
                        row_dict[header] = ''
                
                # Skip empty rows
                if any(row_dict.values()):
                    rows.append(row_dict)
            
            workbook.close()
            
            if not rows:
                raise Exception("File is empty or has no data rows")
            
            logger.info(f"XLSX members loaded: {len(rows)} rows")
            return rows
            
        except Exception as e:
            if "openpyxl" in str(e):
                raise
            raise Exception(f"Failed to load XLSX file: {e}")
