#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version Update Script for Support CRM
Automatically updates version across all project files.

Usage:
    python update_version.py 3.0.1
    python update_version.py 3.1.0
"""

import sys
import re
from pathlib import Path
from datetime import datetime


def print_header():
    """Print script header."""
    print("=" * 60)
    print("Support CRM - Version Update Script")
    print("=" * 60)
    print()


def validate_version(version: str) -> bool:
    """
    Validate version format (semantic versioning).
    
    Args:
        version: Version string (e.g., "1.0.0")
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def update_config_py(version: str) -> bool:
    """Update version in config.py"""
    file_path = Path('config.py')
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Update APP_VERSION
        pattern = r'APP_VERSION\s*=\s*["\'][\d.]+["\']'
        replacement = f'APP_VERSION = "{version}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            print(f"⚠️  No changes in {file_path}")
            return False
        
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✅ Updated {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def update_installer_nsi(version: str) -> bool:
    """Update version in build-nuitka/installer_nuitka.nsi"""
    success = True
    
    # Update installer files - check both old and new locations
    installer_paths = [
        Path('build-nuitka') / 'installer_nuitka.nsi',
        Path('build') / 'installer.nsi',
        Path('build') / 'installer_nuitka.nsi',
    ]
    
    for file_path in installer_paths:
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path} (skipping)")
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Update !define APP_VERSION
            pattern = r'!define\s+APP_VERSION\s+"[\d.]+"'
            replacement = f'!define APP_VERSION "{version}"'
            
            new_content = re.sub(pattern, replacement, content)
            
            if new_content == content:
                print(f"⚠️  No changes in {file_path}")
            else:
                file_path.write_text(new_content, encoding='utf-8')
                print(f"✅ Updated {file_path}")
            
        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
            success = False
    
    return success





def update_update_json(version: str) -> bool:
    """Update version in update.json.example"""
    file_path = Path('update.json.example')
    
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path} (optional)")
        return True  # Not critical
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Update version field
        pattern = r'"version"\s*:\s*"[\d.]+"'
        replacement = f'"version": "{version}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            print(f"⚠️  No changes in {file_path}")
            return True
        
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✅ Updated {file_path}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error updating {file_path}: {e} (optional)")
        return True  # Not critical


def create_version_log(old_version: str, new_version: str) -> bool:
    """Create a version change log entry."""
    log_file = Path('VERSION_HISTORY.md')
    
    try:
        # Read existing content or create new
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
        else:
            content = "# Version History\n\n"
        
        # Add new entry at the top (after header)
        date_str = datetime.now().strftime('%Y-%m-%d')
        new_entry = f"## Version {new_version} ({date_str})\n\n"
        new_entry += f"- Updated from version {old_version}\n"
        new_entry += "- [Add your changes here]\n\n"
        
        # Insert after first line (header)
        lines = content.split('\n', 2)
        if len(lines) >= 2:
            content = lines[0] + '\n' + lines[1] + '\n\n' + new_entry + (lines[2] if len(lines) > 2 else '')
        else:
            content += new_entry
        
        log_file.write_text(content, encoding='utf-8')
        print(f"✅ Updated {log_file}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error updating {log_file}: {e} (optional)")
        return True  # Not critical


def get_current_version() -> str:
    """Get current version from config.py"""
    try:
        file_path = Path('config.py')
        content = file_path.read_text(encoding='utf-8')
        
        match = re.search(r'APP_VERSION\s*=\s*["\'](["\d.]+)["\']', content)
        if match:
            return match.group(1)
        return "unknown"
    except:
        return "unknown"


def main():
    """Main function."""
    print_header()
    
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <version>")
        print("Example: python update_version.py 1.0.1")
        print()
        print(f"Current version: {get_current_version()}")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    # Validate version format
    if not validate_version(new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("Version must be in format: X.Y.Z (e.g., 1.0.0)")
        sys.exit(1)
    
    # Get current version
    old_version = get_current_version()
    
    print(f"Current version: {old_version}")
    print(f"New version: {new_version}")
    print()
    
    # Confirm
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    print()
    print("Updating files...")
    print("-" * 60)
    
    # Update all files
    success = True
    success &= update_config_py(new_version)
    success &= update_installer_nsi(new_version)

    success &= update_update_json(new_version)
    success &= create_version_log(old_version, new_version)
    
    print("-" * 60)
    print()
    
    if success:
        print("✅ Version updated successfully!")
        print()
        print("Next steps:")
        print("1. Review the changes")
        print("2. Update VERSION_HISTORY.md with your changes")
        print("3. Commit the changes: git add . && git commit -m 'Bump version to {}'".format(new_version))
        print("4. Create a tag: git tag v{}".format(new_version))
        print("5. Build the application: python build_nuitka.py")
    else:
        print("⚠️  Some files were not updated. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
