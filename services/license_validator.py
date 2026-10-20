# -*- coding: utf-8 -*-
"""
License Validator - Online license validation via JSON.
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class LicenseInfo:
    """Container for license information from server."""
    
    def __init__(self, data: dict):
        self.license_key = data.get('license_key', '')
        self.owner_name = data.get('owner_name', '')
        self.start_date = self._parse_date(data.get('start_date'))
        self.end_date = self._parse_date(data.get('end_date'))
        self.is_active = data.get('is_active', False)
        self.max_users = data.get('max_users', 1)
        self.features = data.get('features', [])
        self.notes = data.get('notes', '')
    
    def _parse_date(self, date_str: str):
        """Parse date string to datetime.date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None
    
    def is_valid(self) -> bool:
        """Check if license is valid and not expired."""
        if not self.is_active:
            return False
        
        if not self.end_date:
            return False
        
        today = datetime.now().date()
        return today <= self.end_date
    
    def days_remaining(self) -> int:
        """Calculate days remaining until expiration."""
        if not self.end_date:
            return -999
        
        today = datetime.now().date()
        delta = self.end_date - today
        return delta.days


def validate_license_online(license_key: str, validation_url: str, timeout: int = 5, 
                           api_key: str = None, basic_auth: tuple = None) -> Optional[LicenseInfo]:
    """
    Validate license key against online JSON endpoint.
    
    Args:
        license_key: License key to validate
        validation_url: URL to license validation JSON (e.g., https://example.com/licenses/{key}.json)
        timeout: Request timeout in seconds
        api_key: Optional API key for authentication (sent as X-API-KEY header)
        basic_auth: Optional tuple of (username, password) for HTTP Basic Auth
        
    Returns:
        LicenseInfo object if valid, None otherwise
    """
    try:
        # Clean up the key
        key = license_key.strip().upper()
        
        if not key:
            logger.warning("Empty license key provided")
            return None
        
        # Replace {key} placeholder in URL
        url = validation_url.replace('{key}', key)
        
        logger.info(f"Validating license online: {url}")
        
        # Prepare request parameters
        headers = {}
        auth = None
        
        # Add API key to headers if provided
        if api_key:
            headers['X-API-KEY'] = api_key
            logger.debug("Using API key authentication")
        
        # Add basic auth if provided
        if basic_auth and isinstance(basic_auth, tuple) and len(basic_auth) == 2:
            auth = basic_auth
            logger.debug("Using HTTP Basic authentication")
        
        # Make HTTP request
        response = requests.get(url, timeout=timeout, headers=headers, auth=auth)
        response.raise_for_status()
        
        # Parse JSON
        data = response.json()
        
        # Validate required fields
        if 'license_key' not in data:
            logger.error("Invalid license JSON: missing license_key field")
            return None
        
        # Check if the returned key matches
        if data['license_key'].upper() != key:
            logger.error("License key mismatch in response")
            return None
        
        # Create LicenseInfo object
        license_info = LicenseInfo(data)
        
        logger.info(f"License validated: {license_info.owner_name}, valid={license_info.is_valid()}")
        return license_info
        
    except requests.exceptions.Timeout:
        logger.warning(f"License validation timed out after {timeout} seconds")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("License validation failed: connection error")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"License key not found on server: {key}")
            # Return special marker for "not found" vs "connection error"
            return "NOT_FOUND"
        else:
            logger.warning(f"License validation failed: HTTP {e.response.status_code}")
        return None
    except ValueError as e:
        logger.error(f"License validation failed: invalid JSON - {e}")
        return None
    except Exception as e:
        logger.error(f"License validation failed: {e}", exc_info=True)
        return None


def check_license_status(license_key: str, validation_url: str, timeout: int = 5,
                        api_key: str = None, basic_auth: tuple = None) -> Dict[str, any]:
    """
    Check license status and return detailed information.
    
    Args:
        license_key: License key to check
        validation_url: URL to license validation JSON
        timeout: Request timeout in seconds
        api_key: Optional API key for authentication
        basic_auth: Optional tuple of (username, password) for HTTP Basic Auth
        
    Returns:
        Dictionary with license status information
    """
    license_info = validate_license_online(license_key, validation_url, timeout, api_key, basic_auth)
    
    # Check if license was not found on server (404)
    if license_info == "NOT_FOUND":
        return {
            'valid': False,
            'online': True,  # Server responded - we ARE online
            'not_found': True,
            'error': 'Η άδεια δεν βρέθηκε στον server.\n\nΠαρακαλώ επικοινωνήστε με την υποστήριξη.',
            'owner_name': '',
            'start_date': None,
            'end_date': None,
            'days_remaining': -999
        }
    
    if not license_info:
        return {
            'valid': False,
            'online': False,
            'error': 'Αδυναμία σύνδεσης με τον server επικύρωσης.\n\nΕλέγξτε τη σύνδεσή σας στο Internet.',
            'owner_name': '',
            'start_date': None,
            'end_date': None,
            'days_remaining': -999
        }
    
    if not license_info.is_valid():
        days = license_info.days_remaining()
        if days < 0:
            error = f'Η άδεια έληξε πριν {abs(days)} ημέρες.'
        else:
            error = 'Η άδεια δεν είναι ενεργή.'
        
        return {
            'valid': False,
            'online': True,
            'error': error,
            'owner_name': license_info.owner_name,
            'start_date': license_info.start_date,
            'end_date': license_info.end_date,
            'days_remaining': days
        }
    
    return {
        'valid': True,
        'online': True,
        'error': '',
        'owner_name': license_info.owner_name,
        'start_date': license_info.start_date,
        'end_date': license_info.end_date,
        'days_remaining': license_info.days_remaining(),
        'max_users': license_info.max_users,
        'features': license_info.features,
        'notes': license_info.notes
    }


def check_offline_grace_period(last_online_validation, offline_since, grace_days: int = 3) -> Dict[str, any]:
    """
    Check if offline grace period has expired.
    
    Args:
        last_online_validation: Last successful online validation datetime
        offline_since: When app went offline (first failed validation)
        grace_days: Number of days to allow offline usage
        
    Returns:
        Dictionary with grace period status
    """
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # If never validated online, no grace period
    if not last_online_validation:
        return {
            'allowed': False,
            'days_remaining': 0,
            'expired': True,
            'message': 'Απαιτείται online επικύρωση άδειας.'
        }
    
    # Convert string to datetime if needed
    if isinstance(last_online_validation, str):
        last_online_validation = datetime.strptime(last_online_validation, '%Y-%m-%d %H:%M:%S')
    
    # If offline_since is not set, we're not offline yet
    if not offline_since:
        return {
            'allowed': True,
            'days_remaining': grace_days,
            'expired': False,
            'message': 'Online - Δεν χρειάζεται grace period'
        }
    
    # Convert string to datetime if needed
    if isinstance(offline_since, str):
        offline_since = datetime.strptime(offline_since, '%Y-%m-%d %H:%M:%S')
    
    # Calculate days offline
    days_offline = (now - offline_since).days
    days_remaining = grace_days - days_offline
    
    if days_remaining <= 0:
        return {
            'allowed': False,
            'days_remaining': 0,
            'expired': True,
            'message': f'Το grace period των {grace_days} ημερών έληξε. Απαιτείται σύνδεση στο Internet.'
        }
    
    return {
        'allowed': True,
        'days_remaining': days_remaining,
        'expired': False,
        'message': f'Offline mode: Απομένουν {days_remaining} ημέρες'
    }
