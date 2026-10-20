# -*- coding: utf-8 -*-
"""
Internationalization package for Support CRM.

This module provides the TranslationManager class for managing UI translations
between Greek and English languages.
"""

import json
import os
from pathlib import Path
from typing import Optional

from .translations_el import TRANSLATIONS_EL
from .translations_en import TRANSLATIONS_EN


class TranslationManager:
    """
    Manages application translations and language switching.
    
    Supports Greek (el) and English (en) languages with persistent
    language preference storage.
    """
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'el': 'Ελληνικά',
        'en': 'English'
    }
    
    # Default language
    DEFAULT_LANGUAGE = 'el'
    
    # Preference file path
    PREFERENCE_FILE = Path.home() / '.support_crm' / 'preferences.json'
    
    def __init__(self):
        """Initialize the TranslationManager with default language."""
        self.translations = {
            'el': TRANSLATIONS_EL,
            'en': TRANSLATIONS_EN
        }
        
        # Load saved language preference or use default
        self.current_language = self._load_language_preference()
        
    def set_language(self, lang_code: str) -> bool:
        """
        Set the current language.
        
        Args:
            lang_code: Language code ('el' or 'en')
            
        Returns:
            bool: True if language was set successfully, False otherwise
        """
        if lang_code not in self.SUPPORTED_LANGUAGES:
            return False
            
        self.current_language = lang_code
        self._save_language_preference(lang_code)
        return True
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translated string for the current language.
        
        Args:
            key: Translation key
            default: Default value if key not found (optional)
            
        Returns:
            str: Translated string or key if not found
        """
        translations = self.translations.get(self.current_language, {})
        
        if key in translations:
            return translations[key]
        
        # Fallback to default language if key not found
        if self.current_language != self.DEFAULT_LANGUAGE:
            fallback_translations = self.translations.get(self.DEFAULT_LANGUAGE, {})
            if key in fallback_translations:
                return fallback_translations[key]
        
        # Return default or key itself
        return default if default is not None else key
    
    def get_current_language(self) -> str:
        """
        Get the current language code.
        
        Returns:
            str: Current language code ('el' or 'en')
        """
        return self.current_language
    
    def get_language_name(self, lang_code: Optional[str] = None) -> str:
        """
        Get the display name of a language.
        
        Args:
            lang_code: Language code (optional, uses current if not provided)
            
        Returns:
            str: Language display name
        """
        code = lang_code if lang_code else self.current_language
        return self.SUPPORTED_LANGUAGES.get(code, code)
    
    def get_supported_languages(self) -> dict:
        """
        Get dictionary of supported languages.
        
        Returns:
            dict: Dictionary mapping language codes to display names
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    def format(self, key: str, *args, **kwargs) -> str:
        """
        Get translated string and format it with arguments.
        
        Args:
            key: Translation key
            *args: Positional arguments for string formatting
            **kwargs: Keyword arguments for string formatting
            
        Returns:
            str: Formatted translated string
        """
        template = self.get(key)
        try:
            if args:
                return template.format(*args)
            elif kwargs:
                return template.format(**kwargs)
            return template
        except (KeyError, IndexError) as e:
            # Return unformatted string if formatting fails
            return template
    
    def _load_language_preference(self) -> str:
        """
        Load saved language preference from file.
        
        Returns:
            str: Saved language code or default language
        """
        try:
            if self.PREFERENCE_FILE.exists():
                with open(self.PREFERENCE_FILE, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
                    lang = preferences.get('language', self.DEFAULT_LANGUAGE)
                    
                    # Validate language code
                    if lang in self.SUPPORTED_LANGUAGES:
                        return lang
        except (json.JSONDecodeError, IOError, OSError):
            # If any error occurs, use default language
            pass
        
        return self.DEFAULT_LANGUAGE
    
    def _save_language_preference(self, lang_code: str) -> None:
        """
        Save language preference to file.
        
        Args:
            lang_code: Language code to save
        """
        try:
            # Create directory if it doesn't exist
            self.PREFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing preferences or create new
            preferences = {}
            if self.PREFERENCE_FILE.exists():
                try:
                    with open(self.PREFERENCE_FILE, 'r', encoding='utf-8') as f:
                        preferences = json.load(f)
                except (json.JSONDecodeError, IOError):
                    preferences = {}
            
            # Update language preference
            preferences['language'] = lang_code
            
            # Save to file
            with open(self.PREFERENCE_FILE, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, ensure_ascii=False, indent=2)
                
        except (IOError, OSError):
            # Silently fail if we can't save preferences
            pass


# Global instance for easy access
_translation_manager = None


def get_translation_manager() -> TranslationManager:
    """
    Get the global TranslationManager instance.
    
    Returns:
        TranslationManager: Global translation manager instance
    """
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


# Convenience function for quick translations
def tr(key: str, default: Optional[str] = None) -> str:
    """
    Quick translation function.
    
    Args:
        key: Translation key
        default: Default value if key not found
        
    Returns:
        str: Translated string
    """
    return get_translation_manager().get(key, default)


__all__ = [
    'TranslationManager',
    'get_translation_manager',
    'tr',
    'TRANSLATIONS_EL',
    'TRANSLATIONS_EN'
]
