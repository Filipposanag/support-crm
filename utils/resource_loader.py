# -*- coding: utf-8 -*-
"""
Resource Loader for Support CRM
Centralized loading of logos, icons, and other resources.
"""

import logging
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
from .resource_path import resource_path

logger = logging.getLogger(__name__)


class ResourceLoader:
    """Singleton class for loading application resources."""
    
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        logger.debug("ResourceLoader initialized with PyInstaller-compatible paths")
    
    def _get_path(self, relative: str) -> str:
        """Get full path to a resource file (PyInstaller compatible)."""
        path = resource_path(relative)
        if not path.exists():
            logger.warning(f"Resource file not found: {path}")
        return str(path)
    
    def app_icon(self) -> QIcon:
        """
        Get the application icon (favicon).
        
        Returns:
            QIcon for the application
        """
        cache_key = "app_icon"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        icon_path = self._get_path("Logo/favicon.ico")
        icon = QIcon(icon_path)
        self._cache[cache_key] = icon
        
        logger.debug(f"Loaded app icon from: {icon_path}")
        return icon
    
    def main_logo(self, width: int = None, height: int = None) -> QPixmap:
        """
        Get the main logo as a QPixmap.
        
        Args:
            width: Optional width to scale to (maintains aspect ratio)
            height: Optional height to scale to (maintains aspect ratio)
            
        Returns:
            QPixmap of the main logo
        """
        cache_key = f"main_logo_{width}_{height}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        logo_path = self._get_path("Logo/main_logo.png")
        pixmap = QPixmap(logo_path)
        
        if pixmap.isNull():
            logger.error(f"Failed to load main logo from: {logo_path}")
            return QPixmap()
        
        # Scale if dimensions provided
        if width and height:
            pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        elif width:
            pixmap = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
        elif height:
            pixmap = pixmap.scaledToHeight(height, Qt.SmoothTransformation)
        
        self._cache[cache_key] = pixmap
        logger.debug(f"Loaded main logo from: {logo_path} (size: {pixmap.width()}x{pixmap.height()})")
        return pixmap
    
    def logo_icon(self) -> QIcon:
        """
        Get the main logo as a QIcon.
        
        Returns:
            QIcon of the main logo
        """
        cache_key = "logo_icon"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        logo_path = self._get_path("Logo/main_logo.png")
        icon = QIcon(logo_path)
        self._cache[cache_key] = icon
        
        return icon
    
    def clear_cache(self):
        """Clear the resource cache."""
        self._cache.clear()
        logger.debug("Resource cache cleared")


# Singleton instance
_resource_loader = ResourceLoader()


def app_icon() -> QIcon:
    """
    Get the application icon (favicon).
    
    Returns:
        QIcon for the application
    """
    return _resource_loader.app_icon()


def main_logo(width: int = None, height: int = None) -> QPixmap:
    """
    Get the main logo as a QPixmap.
    
    Args:
        width: Optional width to scale to (maintains aspect ratio)
        height: Optional height to scale to (maintains aspect ratio)
        
    Returns:
        QPixmap of the main logo
    """
    return _resource_loader.main_logo(width, height)


def logo_icon() -> QIcon:
    """
    Get the main logo as a QIcon.
    
    Returns:
        QIcon of the main logo
    """
    return _resource_loader.logo_icon()
