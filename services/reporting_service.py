"""
Reporting service for generating reports and analytics.
Provides methods for creating various reports and exporting data.
"""

import logging
import csv
from typing import List, Dict, Any, Optional
from decimal import Decimal
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FamilySubscriptionRow:
    """Data for a single family in the subscription report."""
    family_id: int
    family_code: int
    family_name: str
    city: str
    members_count: int
    total_amount: Decimal      # σύνολο χρεωμένο ποσό
    paid_amount: Decimal       # σύνολο πληρωμένο ποσό
    remaining_amount: Decimal  # υπόλοιπο (οφειλή)
    last_payment_date: Any     # τελευταία ημερομηνία πληρωμής


@dataclass
class SubscriptionReportSummary:
    """Summary statistics for the subscription report."""
    total_families: int
    total_members: int
    total_charged: Decimal
    total_paid: Decimal
    total_debt: Decimal


@dataclass
class SubscriptionReportResult:
    """Complete subscription report with rows and summary."""
    rows: list[FamilySubscriptionRow]
    summary: SubscriptionReportSummary


class ReportingService:
    """
    Service for generating reports and analytics.
    Handles report generation, data aggregation, and CSV export.
    """
    
    def __init__(self, families_repo, payments_repo):
        """
        Initialize ReportingService with repository dependencies.
        
        Args:
            families_repo: FamiliesRepository instance
            payments_repo: PaymentsRepository instance
        """
        self.families_repo = families_repo
        self.payments_repo = payments_repo
        self._cache: dict[tuple, SubscriptionReportResult] = {}
        logger.info("ReportingService initialized")

    def get_unpaid_families(self, year: int) -> List[Dict[str, Any]]:
        """
        Get families with unpaid or partially paid subscriptions for a specified year.
        
        This method identifies families that either:
        1. Have no payment record for the specified year, OR
        2. Have payments with remaining_amount > 0 for the specified year
        
        Args:
            year: The year to check for unpaid subscriptions
            
        Returns:
            List of dictionaries containing family details and outstanding amounts.
            Each dictionary includes:
            - family_id: Family ID
            - legacy_code: Legacy code from CSV import
            - last_name: Family last name
            - first_name: Family first name
            - phone: Phone number
            - mobile: Mobile number
            - email: Email address
            - city: City
            - outstanding_amount: Total outstanding amount for the year
            - last_payment_date: Date of last payment (if any)
            - payment_count: Number of payments for the year
        """
        try:
            logger.info(f"Generating unpaid families report for year {year}")
            
            # Use the repository method to get unpaid families
            unpaid_families = self.payments_repo.get_unpaid_by_year(year)
            
            logger.info(f"Found {len(unpaid_families)} families with unpaid/partial subscriptions for year {year}")
            
            return unpaid_families
            
        except Exception as e:
            logger.error(f"Error generating unpaid families report for year {year}: {e}")
            raise

    def export_to_csv(self, data: List[Dict[str, Any]], file_path: str) -> bool:
        """
        Export report data to a CSV file with UTF-8 encoding for Greek characters.
        
        Args:
            data: List of dictionaries containing report data
            file_path: Path where the CSV file should be saved
            
        Returns:
            True if export was successful, False otherwise
            
        Raises:
            ValueError: If data is empty or file_path is invalid
            IOError: If file cannot be written
        """
        if not data:
            logger.warning("Cannot export empty data to CSV")
            raise ValueError("Cannot export empty data to CSV")
        
        if not file_path:
            logger.error("Invalid file path provided for CSV export")
            raise ValueError("File path cannot be empty")
        
        try:
            logger.info(f"Exporting {len(data)} records to CSV: {file_path}")
            
            # Ensure the directory exists
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Get column headers from the first record
            headers = list(data[0].keys())
            
            # Write to CSV with UTF-8 encoding for Greek characters
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                
                # Write header row
                writer.writeheader()
                
                # Write data rows
                for row in data:
                    # Convert Decimal values to strings for CSV export
                    processed_row = {}
                    for key, value in row.items():
                        if isinstance(value, Decimal):
                            processed_row[key] = str(value)
                        elif value is None:
                            processed_row[key] = ''
                        else:
                            processed_row[key] = value
                    
                    writer.writerow(processed_row)
            
            logger.info(f"Successfully exported {len(data)} records to {file_path}")
            return True
            
        except IOError as e:
            logger.error(f"IO error while exporting to CSV {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error exporting data to CSV {file_path}: {e}")
            raise

    def get_payment_summary(self, year: int) -> Dict[str, Any]:
        """
        Get payment summary statistics for a specified year.
        
        Calculates aggregate statistics including:
        - Total number of families with payments
        - Count of paid, partial, and unpaid payments
        - Total collected amount
        - Total outstanding amount
        
        Args:
            year: The year to summarize
            
        Returns:
            Dictionary containing summary statistics:
            - total_families: Number of unique families with payments
            - total_payments: Total number of payment records
            - paid_count: Number of fully paid payments
            - partial_count: Number of partially paid payments
            - unpaid_count: Number of unpaid payments
            - total_amount: Total amount due
            - total_collected: Total amount collected
            - total_outstanding: Total remaining amount
        """
        try:
            logger.info(f"Generating payment summary for year {year}")
            
            # Use the repository method to get payment summary
            summary = self.payments_repo.get_payment_summary_by_year(year)
            
            logger.info(f"Payment summary for year {year}: "
                       f"{summary['total_families']} families, "
                       f"{summary['total_collected']} collected, "
                       f"{summary['total_outstanding']} outstanding")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating payment summary for year {year}: {e}")
            raise
    
    def invalidate_cache(self):
        """
        Invalidate (clear) the subscription report cache.
        Should be called when payment or family data changes.
        """
        self._cache.clear()
        logger.info("[reporting] Cache invalidated")
    
    def get_subscription_report(
        self,
        year: Optional[int] = None,
        only_with_debt: bool = False,
        date_from: Optional[Any] = None,
        date_to: Optional[Any] = None,
        min_members: Optional[int] = None,
        max_members: Optional[int] = None,
        search_text: Optional[str] = None,
        search_fields: Optional[list] = None
    ) -> SubscriptionReportResult:
        """
        Επιστρέφει λίστα οικογενειών με στοιχεία πληρωμών + συνολική σύνοψη
        με βάση τα φίλτρα.
        
        Args:
            year: Έτος για φιλτράρισμα (None = όλα τα έτη)
            only_with_debt: Αν True, μόνο πελάτες με οφειλές
            date_from: Ημερομηνία από (προτεραιότητα έναντι year)
            date_to: Ημερομηνία έως (προτεραιότητα έναντι year)
            min_members: Ελάχιστος αριθμός μελών
            max_members: Μέγιστος αριθμός μελών
            search_text: Κείμενο αναζήτησης
            search_fields: Λίστα πεδίων για αναζήτηση
            
        Returns:
            SubscriptionReportResult με rows και summary
        """
        # Build cache key from filters
        cache_key = (
            year,
            only_with_debt,
            date_from.isoformat() if date_from else None,
            date_to.isoformat() if date_to else None,
            min_members,
            max_members,
            search_text,
            tuple(search_fields) if search_fields else None
        )
        
        # Check cache
        if cache_key in self._cache:
            logger.info("[reporting] Using cached result")
            return self._cache[cache_key]
        
        logger.info("[reporting] Cache MISS → Executing SQL")
        
        try:
            logger.info(
                f"Generating subscription report (year={year}, debt={only_with_debt}, "
                f"date_from={date_from}, date_to={date_to}, "
                f"min_members={min_members}, max_members={max_members})"
            )
            
            # Build SQL query
            query = """
                SELECT 
                    f.id as family_id,
                    f.legacy_code as family_code,
                    CONCAT(f.last_name, ' ', f.first_name) as family_name,
                    f.city,
                    f.members_count,
                    COALESCE(SUM(p.total_amount), 0) as total_amount,
                    COALESCE(SUM(p.paid_amount), 0) as paid_amount,
                    COALESCE(SUM(p.remaining_amount), 0) as remaining_amount,
                    MAX(p.payment_date) as last_payment_date
                FROM families f
                LEFT JOIN payments p ON f.id = p.family_id
            """
            
            # Add WHERE clauses
            where_clauses = []
            params = []
            
            # Date filter (priority over year) - ONLY show payments within date range
            if date_from is not None and date_to is not None:
                where_clauses.append("p.payment_date BETWEEN %s AND %s")
                params.extend([date_from, date_to])
            # Year filter (if no date range)
            elif year is not None:
                where_clauses.append("p.year = %s")
                params.append(year)
            
            # Filter by active families
            where_clauses.append("f.is_active = 1")
            
            # Search text filter
            if search_text:
                # Map field keys to database columns
                field_map = {
                    "code": "f.legacy_code",
                    "last_name": "f.last_name",
                    "first_name": "f.first_name",
                    "father_name": "f.father_name",
                    "spouse_name": "f.spouse_name",
                    "spouse_maiden_name": "f.spouse_maiden_name",
                    "city": "f.city"
                }
                
                # If search_fields is provided and not empty, use only those fields
                if search_fields:
                    search_conditions = []
                    for field_key in search_fields:
                        db_column = field_map.get(field_key)
                        if db_column:
                            search_conditions.append(f"{db_column} LIKE %s")
                            params.append(f"%{search_text}%")
                    
                    if search_conditions:
                        where_clauses.append(f"({' OR '.join(search_conditions)})")
                else:
                    # Default: search all fields
                    where_clauses.append("""(
                        f.legacy_code LIKE %s OR
                        f.last_name LIKE %s OR
                        f.first_name LIKE %s OR
                        f.father_name LIKE %s OR
                        f.spouse_name LIKE %s OR
                        f.spouse_maiden_name LIKE %s OR
                        f.city LIKE %s OR
                        CONCAT(f.last_name, ' ', f.first_name) LIKE %s OR
                        CONCAT(f.first_name, ' ', f.last_name) LIKE %s
                    )""")
                    search_pattern = f"%{search_text}%"
                    params.extend([search_pattern] * 9)
            
            # Members count filter
            if min_members is not None and max_members is not None:
                where_clauses.append("f.members_count BETWEEN %s AND %s")
                params.extend([min_members, max_members])
            elif min_members is not None:
                where_clauses.append("f.members_count >= %s")
                params.append(min_members)
            elif max_members is not None:
                where_clauses.append("f.members_count <= %s")
                params.append(max_members)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Group by family
            query += """
                GROUP BY f.id, f.legacy_code, f.last_name, f.first_name, f.city, f.members_count
            """
            
            # Filter by debt if requested (after grouping)
            if only_with_debt:
                query += " HAVING remaining_amount > 0"
            
            # Order by family name
            query += " ORDER BY f.last_name, f.first_name"
            
            # Execute query
            db_connection = self.families_repo.db
            results = db_connection.execute_query(query, tuple(params) if params else None)
            
            # Build FamilySubscriptionRow objects
            rows = []
            for result in results:
                row = FamilySubscriptionRow(
                    family_id=result['family_id'],
                    family_code=result['family_code'],
                    family_name=result['family_name'],
                    city=result['city'] or '',
                    members_count=result['members_count'] or 0,
                    total_amount=Decimal(str(result['total_amount'])),
                    paid_amount=Decimal(str(result['paid_amount'])),
                    remaining_amount=Decimal(str(result['remaining_amount'])),
                    last_payment_date=result.get('last_payment_date')
                )
                rows.append(row)
            
            # Calculate summary
            total_families = len(rows)
            total_members = sum(row.members_count for row in rows)
            total_charged = sum(row.total_amount for row in rows)
            total_paid = sum(row.paid_amount for row in rows)
            total_debt = sum(row.remaining_amount for row in rows)
            
            summary = SubscriptionReportSummary(
                total_families=total_families,
                total_members=total_members,
                total_charged=total_charged,
                total_paid=total_paid,
                total_debt=total_debt
            )
            
            logger.info(
                f"Subscription report generated: {total_families} families, "
                f"{total_members} members, {total_charged} charged, "
                f"{total_paid} paid, {total_debt} debt"
            )
            
            result = SubscriptionReportResult(rows=rows, summary=summary)
            
            # Store in cache
            self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating subscription report: {e}", exc_info=True)
            raise
    
    def get_subscriptions(
        self,
        year: Optional[int] = None,
        only_debtors: bool = False,
        valid_from: Optional[Any] = None,
        valid_to: Optional[Any] = None,
        subscription_status: Optional[str] = None,
        search_text: Optional[str] = None,
        search_fields: Optional[list] = None
    ) -> list[dict]:
        """
        Επιστρέφει λίστα συνδρομών με φίλτρα για το SubscriptionsView.
        
        Args:
            year: Έτος για φιλτράρισμα (None = όλα τα έτη)
            only_debtors: Αν True, μόνο συνδρομές με οφειλές
            valid_from: Ημερομηνία από (για subscription_start_date/end_date)
            valid_to: Ημερομηνία έως (για subscription_start_date/end_date)
            subscription_status: Φίλτρο κατάστασης ('active', 'expired', 'pending')
            search_text: Κείμενο αναζήτησης (κωδικός, επώνυμο, όνομα, ΑΣΠΕ, τηλέφωνο)
            search_fields: Λίστα πεδίων για αναζήτηση (None = όλα τα πεδία)
            
        Returns:
            Λίστα από dictionaries με στοιχεία συνδρομών
        """
        try:
            logger.info(
                f"Getting subscriptions (year={year}, debtors={only_debtors}, "
                f"valid_from={valid_from}, valid_to={valid_to}, "
                f"status={subscription_status}, search={search_text})"
            )
            
            # Build SQL query - reading from subscriptions table with proper JOIN to payment
            # Use INNER JOIN to ensure we only get subscriptions with valid payment records
            query = """
                SELECT 
                    s.id as subscription_id,
                    s.payment_id,
                    f.id as family_id,
                    f.legacy_code as family_code,
                    CONCAT(f.last_name, ' ', f.first_name) as family_name,
                    f.phone,
                    f.mobile,
                    s.year,
                    s.total_amount,
                    s.paid_amount,
                    s.remaining_amount,
                    s.start_date as subscription_start_date,
                    s.end_date as subscription_end_date,
                    p.payment_date,
                    p.receipt_no,
                    p.description,
                    COALESCE(s.subscription_code, p.subscription_code, '') as subscription_code,
                    CASE
                        WHEN s.status = 'CANCELLED' THEN 'cancelled'
                        WHEN s.remaining_amount > 0 THEN 'pending'
                        WHEN s.status = 'ACTIVE' AND CURDATE() BETWEEN s.start_date AND s.end_date THEN 'active'
                        WHEN s.status = 'EXPIRED' OR CURDATE() > s.end_date THEN 'expired'
                        ELSE 'unknown'
                    END as subscription_status
                FROM subscriptions s
                INNER JOIN families f ON s.family_id = f.id
                INNER JOIN payments p ON s.payment_id = p.id
                WHERE f.is_active = 1
            """
            
            params = []
            
            # Year filter
            if year is not None:
                query += " AND s.year = %s"
                params.append(year)
            
            # Date range filter (for subscription validity)
            if valid_from is not None and valid_to is not None:
                query += " AND (s.start_date <= %s AND s.end_date >= %s)"
                params.extend([valid_to, valid_from])
            
            # Search text filter
            if search_text:
                # Map field keys to database columns
                # Note: legacy_code is INT, so we need CAST for LIKE to work properly
                field_map = {
                    "code": "CAST(f.legacy_code AS CHAR)",
                    "last_name": "f.last_name",
                    "first_name": "f.first_name",
                    "father_name": "f.father_name",
                    "spouse_name": "f.spouse_name",
                    "spouse_maiden_name": "f.spouse_maiden_name",
                    "adt": "f.national_id",
                    "phone": "f.phone",
                    "city": "f.city"
                }
                
                # If search_fields is provided and not empty, use only those fields
                if search_fields:
                    search_conditions = []
                    for field_key in search_fields:
                        db_column = field_map.get(field_key)
                        if db_column:
                            search_conditions.append(f"{db_column} LIKE %s")
                            params.append(f"%{search_text}%")
                    
                    if search_conditions:
                        query += f" AND ({' OR '.join(search_conditions)})"
                else:
                    # Default: search all fields
                    # Note: CAST legacy_code to CHAR for LIKE to work with numeric codes
                    query += """ AND (
                        CAST(f.legacy_code AS CHAR) LIKE %s OR
                        f.last_name LIKE %s OR
                        f.first_name LIKE %s OR
                        f.father_name LIKE %s OR
                        f.spouse_name LIKE %s OR
                        f.spouse_maiden_name LIKE %s OR
                        f.national_id LIKE %s OR
                        f.phone LIKE %s OR
                        f.mobile LIKE %s OR
                        CONCAT(f.last_name, ' ', f.first_name) LIKE %s OR
                        CONCAT(f.first_name, ' ', f.last_name) LIKE %s
                    )"""
                    search_pattern = f"%{search_text}%"
                    params.extend([search_pattern] * 11)
            
            # Only debtors filter
            if only_debtors:
                query += " AND s.remaining_amount > 0"
            
            # Order by subscription start date DESC (most recent first), then family name
            query += " ORDER BY s.start_date DESC, f.last_name, f.first_name"
            
            # Execute query
            db_connection = self.families_repo.db
            results = db_connection.execute_query(query, tuple(params) if params else None)
            
            # Filter by subscription status if specified (post-query filter)
            if subscription_status:
                results = [r for r in results if r.get('subscription_status') == subscription_status]
            
            logger.info(f"Found {len(results)} subscriptions")
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}", exc_info=True)
            raise
