"""
Icon loader utility for SupportCRM application.
Provides easy access to Material Design style icons.
"""
import os
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize


class IconLoader:
    """Utility class to load application icons."""
    
    _instance = None
    _icons_cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.icons_dir = os.path.join(os.path.dirname(__file__))
    
    def get_icon(self, icon_name: str, size: int = 24) -> QIcon:
        """
        Load an icon by name.
        
        Args:
            icon_name: Name of the icon (without .svg extension)
            size: Size of the icon in pixels (default: 24)
            
        Returns:
            QIcon object
        """
        cache_key = f"{icon_name}_{size}"
        
        if cache_key in self._icons_cache:
            return self._icons_cache[cache_key]
        
        icon_path = os.path.join(self.icons_dir, f"{icon_name}.svg")
        
        if not os.path.exists(icon_path):
            # Return empty icon if file doesn't exist
            return QIcon()
        
        icon = QIcon(icon_path)
        self._icons_cache[cache_key] = icon
        
        return icon
    
    def get_pixmap(self, icon_name: str, size: int = 24) -> QPixmap:
        """
        Load an icon as a QPixmap.
        
        Args:
            icon_name: Name of the icon (without .svg extension)
            size: Size of the icon in pixels (default: 24)
            
        Returns:
            QPixmap object
        """
        icon = self.get_icon(icon_name, size)
        return icon.pixmap(QSize(size, size))


# Singleton instance
icon_loader = IconLoader()


def get_icon(icon_name: str, size: int = 24) -> QIcon:
    """
    Convenience function to get an icon.
    
    Args:
        icon_name: Name of the icon (without .svg extension)
        size: Size of the icon in pixels (default: 24)
        
    Returns:
        QIcon object
    """
    return icon_loader.get_icon(icon_name, size)


def get_pixmap(icon_name: str, size: int = 24) -> QPixmap:
    """
    Convenience function to get an icon as a pixmap.
    
    Args:
        icon_name: Name of the icon (without .svg extension)
        size: Size of the icon in pixels (default: 24)
        
    Returns:
        QPixmap object
    """
    return icon_loader.get_pixmap(icon_name, size)
