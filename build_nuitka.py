#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support CRM - Nuitka Build Script
Builds the application using Nuitka compiler
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Import version from config
sys.path.insert(0, str(Path(__file__).parent))
from config import APP_VERSION

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print header text"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_step(step, text):
    """Print step text"""
    print(f"{Colors.OKCYAN}[{step}] {text}{Colors.ENDC}")

def print_success(text):
    """Print success text"""
    try:
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text):
    """Print error text"""
    try:
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning text"""
    try:
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.WARNING}[WARNING] {text}{Colors.ENDC}")

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def clean_build():
    """Clean previous build artifacts"""
    print_step("1/4", "Cleaning previous Nuitka builds...")
    
    dirs_to_clean = [
        "dist/SupportCRM",
        "dist/nuitka",
        "build/nuitka",
    ]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")
    
    print_success("Clean completed")

def build_with_nuitka():
    """Build application with Nuitka"""
    print_step("2/4", "Building with Nuitka (this may take several minutes)...")
    
    # Create output directory
    os.makedirs("dist/SupportCRM", exist_ok=True)
    
    # Use the current Python interpreter (respects virtual environment)
    python_exe = sys.executable
    
    # Convert version to Windows format (X.Y.Z -> X.Y.Z.0)
    file_version = f"{APP_VERSION}.0"
    
    # Nuitka command - using list for proper subprocess handling
    nuitka_cmd = [
        python_exe, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-icon-from-ico=Logo/favicon.ico",
        "--windows-uac-admin",
        "--company-name=DionyTech",
        "--product-name=Support CRM",
        f"--file-version={file_version}",
        f"--product-version={APP_VERSION}",
        "--file-description=Support CRM - Customer Support Management System",
        "--windows-console-mode=disable",
        "--output-dir=dist/SupportCRM",
        "--include-data-dir=resources=resources",
        "--include-data-dir=Logo=Logo",
        "--include-data-dir=db=db",
        "--include-module=email",
        "--include-module=email.mime",
        "--include-module=email.mime.text",
        "--include-module=email.mime.multipart",
        "--include-module=email.mime.application",
        "--include-module=smtplib",
        "--include-module=ssl",
        "--include-module=reportlab",
        "--include-module=reportlab.pdfgen",
        "--include-module=reportlab.lib",
        "--include-module=reportlab.platypus",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=PyQt6",
        "--assume-yes-for-downloads",
        "main.py"
    ]
    
    print(f"  Running Nuitka build...")
    print(f"  {Colors.WARNING}Note: First build may take 5-15 minutes...{Colors.ENDC}")
    
    # Use subprocess directly without shell=True to avoid argument parsing issues
    try:
        result = subprocess.run(
            nuitka_cmd,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
        print_success("Nuitka build completed")
        return True
    except subprocess.CalledProcessError as e:
        print_error("Nuitka build failed!")
        print(f"Exit code: {e.returncode}")
        return False

def verify_build():
    """Verify that build was successful"""
    print_step("3/4", "Verifying build...")
    
    # Nuitka creates main.dist directory with main.exe inside
    dist_dir = "dist/SupportCRM/main.dist"
    exe_path = os.path.join(dist_dir, "main.exe")
    
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print_success(f"Found: {exe_path} ({size_mb:.1f} MB)")
        
        # Rename to SupportCRM.exe
        new_path = os.path.join(dist_dir, "SupportCRM.exe")
        shutil.move(exe_path, new_path)
        print_success(f"Renamed to: {new_path}")
        
        # Rename the directory
        final_dir = "dist/SupportCRM/SupportCRM"
        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
        shutil.move(dist_dir, final_dir)
        print_success(f"Directory renamed to: {final_dir}")
        return True
    else:
        print_error(f"Missing: {exe_path}")
        return False

def create_installer():
    """Create NSIS installer"""
    print_step("4/4", "Creating installer with NSIS...")
    
    # Find NSIS
    nsis_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    
    nsis_exe = None
    for path in nsis_paths:
        if os.path.exists(path):
            nsis_exe = path
            break
    
    if not nsis_exe:
        print_warning("NSIS not found - skipping installer creation")
        print("  Install NSIS from: https://nsis.sourceforge.io/")
        print("  Then run: makensis build\\installer_nuitka.nsi")
        return False
    
    print(f"  Using NSIS: {nsis_exe}")
    
    # Check if NSIS script exists
    nsis_script = "build-nuitka/installer_nuitka.nsi"
    if not os.path.exists(nsis_script):
        print_error(f"NSIS script not found: {nsis_script}")
        return False
    
    # Run NSIS
    print("  Compiling installer...")
    success, output = run_command(f'"{nsis_exe}" {nsis_script}')
    
    if success:
        installer_name = f"dist/SupportCRM-Setup-{APP_VERSION}.exe"
        print_success(f"Installer created: {installer_name}")
        return True
    else:
        print_error("NSIS compilation failed")
        print(output)
        return False

def main():
    """Main build process"""
    print_header("Support CRM - Nuitka Build Script")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print_error("Error: main.py not found!")
        print("Please run this script from the project root directory.")
        return 1
    
    # Check if Nuitka is installed
    print("Checking Nuitka installation...")
    success, output = run_command("python -m nuitka --version")
    if not success:
        print_error("Nuitka not found!")
        print("\nTo install Nuitka, run:")
        print("  pip install nuitka")
        print("\nFor Windows, you also need a C compiler:")
        print("  - Visual Studio 2022 (recommended)")
        print("  - Or MinGW64")
        return 1
    
    print_success(f"Nuitka found: {output.strip()}")
    
    try:
        # Step 1: Clean
        clean_build()
        
        # Step 2: Build with Nuitka
        if not build_with_nuitka():
            return 1
        
        # Step 3: Verify
        if not verify_build():
            return 1
        
        # Step 4: Create installer (optional)
        installer_created = create_installer()
        
        # Summary
        print_header("Build Summary")
        
        print_success("Nuitka Build: dist/SupportCRM/SupportCRM/")
        if installer_created:
            print_success(f"Installer: dist/SupportCRM-Setup-{APP_VERSION}.exe")
        
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Build completed successfully!{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}Test the executable:{Colors.ENDC}")
        print(f"  dist/SupportCRM/SupportCRM/SupportCRM.exe")
        if installer_created:
            print(f"\n{Colors.OKCYAN}Or install using:{Colors.ENDC}")
            print(f"  dist/SupportCRM-Setup-{APP_VERSION}.exe\n")
        else:
            print()
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nBuild cancelled by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
