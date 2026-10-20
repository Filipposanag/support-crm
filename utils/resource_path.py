# -*- coding: utf-8 -*-
"""
Resource Path Helper for PyInstaller
Handles resource paths for both development and frozen (PyInstaller) environments.
"""

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Relative path to resource (e.g., "Logo/main_logo.png")
        
    Returns:
        Absolute Path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Running in normal Python environment
        base_path = Path(__file__).resolve().parent.parent
    
    return base_path / relative_path


def get_app_data_dir() -> Path:
    """
    Get application data directory for storing license, backups, etc.
    
    Returns:
        Path to %PROGRAMDATA%\\SupportCRM
    """
    import os
    base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    folder = Path(base) / "SupportCRM"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
