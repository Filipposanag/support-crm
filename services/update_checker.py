# -*- coding: utf-8 -*-
"""
Update Checker Service - Check for application updates.
"""

import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class UpdateInfo:
    """Container for update information."""
    
    def __init__(self, latest_version: str, download_url: str, changelog: str, mandatory: bool = False):
        self.latest_version = latest_version
        self.download_url = download_url
        self.changelog = changelog
        self.mandatory = mandatory


def fetch_update_info(url: str, timeout: int = 5) -> Optional[UpdateInfo]:
    """
    Fetch update information from remote server.
    
    Args:
        url: URL to update.json file
        timeout: Request timeout in seconds
        
    Returns:
        UpdateInfo object if successful, None otherwise
    """
    try:
        logger.info(f"Checking for updates from: {url}")
        
        # Make HTTP request
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Parse JSON
        data = response.json()
        
        # Validate required fields
        if 'latest_version' not in data or 'download_url' not in data:
            logger.error("Invalid update.json format: missing required fields")
            return None
        
        # Create UpdateInfo object
        update_info = UpdateInfo(
            latest_version=data['latest_version'],
            download_url=data['download_url'],
            changelog=data.get('changelog', ''),
            mandatory=data.get('mandatory', False)
        )
        
        logger.info(f"Update info fetched successfully: {update_info.latest_version}")
        return update_info
        
    except requests.exceptions.Timeout:
        logger.warning(f"Update check timed out after {timeout} seconds")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Update check failed: connection error")
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Update check failed: HTTP {e.response.status_code}")
        return None
    except ValueError as e:
        logger.error(f"Update check failed: invalid JSON - {e}")
        return None
    except Exception as e:
        logger.error(f"Update check failed: {e}", exc_info=True)
        return None


def is_newer_version(local: str, remote: str) -> bool:
    """
    Compare version strings to determine if remote is newer.
    
    Args:
        local: Local version string (e.g., "1.0.0")
        remote: Remote version string (e.g., "1.0.3")
        
    Returns:
        True if remote version is newer than local
    """
    try:
        # Split versions into parts
        local_parts = [int(x) for x in local.split('.')]
        remote_parts = [int(x) for x in remote.split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(local_parts), len(remote_parts))
        local_parts += [0] * (max_len - len(local_parts))
        remote_parts += [0] * (max_len - len(remote_parts))
        
        # Compare each part
        for local_part, remote_part in zip(local_parts, remote_parts):
            if remote_part > local_part:
                return True
            elif remote_part < local_part:
                return False
        
        # Versions are equal
        return False
        
    except (ValueError, AttributeError) as e:
        logger.error(f"Version comparison failed: {e}")
        return False


def check_for_updates(current_version: str, update_url: str, timeout: int = 5) -> Tuple[bool, Optional[UpdateInfo]]:
    """
    Check if a newer version is available.
    
    Args:
        current_version: Current application version
        update_url: URL to update.json file
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (has_update, update_info)
        - has_update: True if newer version available
        - update_info: UpdateInfo object if available, None otherwise
    """
    update_info = fetch_update_info(update_url, timeout)
    
    if not update_info:
        return False, None
    
    has_update = is_newer_version(current_version, update_info.latest_version)
    
    return has_update, update_info
