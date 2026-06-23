#!/usr/bin/env python3
"""
System check for CryoSPARC → RELION conversion tools.
Validates all dependencies and provides detailed setup instructions.

Run this before using the conversion tools to ensure everything is installed.
"""

import sys
import subprocess
from pathlib import Path

class SetupChecker:
    def __init__(self):
        self.all_good = True
        self.warnings = []
        self.info = []
    
    def header(self, text):
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def success(self, text):
        print(f"✓ {text}")
    
    def error(self, text):
        print(f"✗ {text}")
        self.all_good = False
    
    def warning(self, text):
        print(f"⚠ {text}")
        self.warnings.append(text)
    
    def info_msg(self, text):
        print(f"ℹ {text}")
        self.info.append(text)
    
    def check_python(self):
        """Check Python version."""
        self.header("Python Version")
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        
        if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 7):
            self.error(f"Python {version_str} (requires 3.7+)")
        else:
            self.success(f"Python {version_str}")
    
    def check_package(self, package_name, import_name=None, min_version=None):
        """Check if a package is installed."""
        if import_name is None:
            import_name = package_name
        
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            
            if min_version and version != 'unknown':
                try:
                    v_tuple = tuple(map(int, version.split('.')))
                    min_tuple = tuple(map(int, min_version.split('.')))
                    if v_tuple < min_tuple:
                        self.warning(f"{package_name} {version} (recommends {min_version}+)")
                        return True
                except:
                    pass
            
            self.success(f"{package_name} {version}")
            return True
        except ImportError:
            self.error(f"{package_name} NOT installed")
            return False
    
    def check_command(self, command, package_name=None):
        """Check if a command exists in PATH."""
        try:
            result = subprocess.run([command, "--version"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.decode().split('\n')[0]
                self.success(f"{command}: {output[:50]}")
                return True
        except:
            pass
        
        self.error(f"{command} NOT found in PATH")
        if package_name:
            self.info_msg(f"Install with: conda install {package_name} OR pip install {package_name}")
        return False
    
    def run(self):
        """Run all checks."""
        print("\n" + "="*60)
        print("  CryoSPARC → RELION CONVERSION TOOL - SETUP CHECK")
        print("="*60)
        
        # Python
        self.check_python()
        
        # Core dependencies
        self.header("Core Dependencies (REQUIRED)")
        pyem_ok = self.check_package("pyem", min_version="0.66")
        pandas_ok = self.check_package("pandas")
        starfile_ok = self.check_package("starfile")
        
        if not all([pyem_ok, pandas_ok, starfile_ok]):
            self.error("Missing core dependencies!")
            print("\nInstall all dependencies with:")
            print("  conda install -c conda-forge pyem pandas starfile")
            print("  OR")
            print("  pip install pyem pandas starfile")
        
        # Optional dependencies
        self.header("Optional Dependencies")
        self.check_package("numpy")
        self.check_package("scipy")
        
        # GUI framework (for GUI version)
        self.header("GUI Framework (for cryo2relion_gui.py)")
        try:
            import tkinter
            self.success("tkinter (Python built-in)")
        except ImportError:
            self.warning("tkinter not available - GUI won't work")
            self.info_msg("Linux: sudo apt-get install python3-tk")
            self.info_msg("macOS: Should be included with Python")
            self.info_msg("Windows: Should be included with Python")
        
        # RELION tools (optional but recommended)
        self.header("RELION Tools (RECOMMENDED for final step)")
        relion_ok = self.check_command("relion_reconstruct", "relion")
        if not relion_ok:
            self.info_msg("RELION is needed to test your conversions")
            self.info_msg("See: https://relion.readthedocs.io/en/latest/Installation.html")
        
        # PyEM tools
        self.header("PyEM Command-Line Tools")
        self.check_command("csparc2star.py", "pyem")
        self.check_command("star.py", "pyem")
        
        # GUI availability
        self.header("Conversion Tools Available")
        try:
            import tkinter
            self.success("cryo2relion_gui.py - Full GUI available")
        except ImportError:
            self.warning("cryo2relion_gui.py - GUI not available (tkinter missing)")
        
        self.success("cryo2relion_cli.py - Command-line tool available")
        
        # Summary
        self.header("Summary")
        if self.all_good:
            print("✓ All required dependencies installed!\n")
            print("You can now use:")
            print("  • python cryo2relion_gui.py   (GUI version)")
            print("  • python cryo2relion_cli.py --help (CLI version)")
        else:
            print("✗ Missing required dependencies.\n")
            print("Install them with:")
            print("  conda install -c conda-forge pyem pandas starfile")
            print("\nThen re-run this check.")
            return 1
        
        if self.warnings:
            print("\nWarnings:")
            for w in self.warnings:
                print(f"  ⚠ {w}")
        
        return 0


if __name__ == "__main__":
    checker = SetupChecker()
    sys.exit(checker.run())
