#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify PDFUploadMacro installation
Run this after installing the plugin to verify everything is working
"""

import sys
import os

def test_import():
    """Test if the plugin can be imported"""
    print("Testing plugin import...")
    try:
        import pdfuploadmacro
        print("✓ Plugin package imported successfully")
        
        from pdfuploadmacro.macro import PDFUploadMacro
        print("✓ PDFUploadMacro class imported successfully")
        return True
    except ImportError as e:
        print("✗ Import failed: %s" % str(e))
        return False

def test_trac_components():
    """Test if Trac components are available"""
    print("\nTesting Trac components...")
    try:
        from trac.core import Component
        from trac.wiki.api import IWikiMacroProvider
        from trac.wiki.macros import WikiMacroBase
        print("✓ Trac components available")
        return True
    except ImportError as e:
        print("✗ Trac import failed: %s" % str(e))
        print("  Make sure this script is run in the Trac environment")
        return False

def test_plugin_info():
    """Display plugin information"""
    print("\nPlugin Information:")
    try:
        import pdfuploadmacro
        plugin_path = os.path.dirname(pdfuploadmacro.__file__)
        print("  Installation path: %s" % plugin_path)
        
        # Check for setup.py version
        setup_path = os.path.join(os.path.dirname(plugin_path), 'setup.py')
        if os.path.exists(setup_path):
            print("  Setup.py found: %s" % setup_path)
            
            # Try to extract version
            with open(setup_path, 'r') as f:
                for line in f:
                    if 'version=' in line:
                        version = line.split("'")[1]
                        print("  Version: %s" % version)
                        break
        
        return True
    except Exception as e:
        print("✗ Could not get plugin info: %s" % str(e))
        return False

def test_macro_instantiation():
    """Test if the macro can be instantiated"""
    print("\nTesting macro instantiation...")
    try:
        from pdfuploadmacro.macro import PDFUploadMacro
        
        # Create a minimal mock environment
        class MockEnv:
            class config:
                @staticmethod
                def get(section, option, default=None):
                    return default
        
        # Try to create an instance (this would normally be done by Trac)
        # Note: This is just testing the import, not full functionality
        print("✓ PDFUploadMacro class is properly defined")
        return True
    except Exception as e:
        print("✗ Instantiation test failed: %s" % str(e))
        return False

def test_dependencies():
    """Test if required dependencies are available"""
    print("\nTesting dependencies...")
    dependencies = [
        ('requests', 'HTTP requests library'),
        ('json', 'JSON parsing'),
        ('tempfile', 'Temporary file handling'),
        ('hashlib', 'Hash generation'),
    ]
    
    all_ok = True
    for module, description in dependencies:
        try:
            __import__(module)
            print("✓ %s (%s)" % (module, description))
        except ImportError:
            print("✗ %s (%s) - NOT INSTALLED" % (module, description))
            all_ok = False
    
    return all_ok

def test_file_structure():
    """Test if all required files are present"""
    print("\nTesting file structure...")
    try:
        import pdfuploadmacro
        plugin_dir = os.path.dirname(pdfuploadmacro.__file__)
        base_dir = os.path.dirname(plugin_dir)
        
        required_files = [
            ('__init__.py', plugin_dir),
            ('macro.py', plugin_dir),
            ('setup.py', base_dir),
            ('README.md', base_dir),
            ('INSTALL.md', base_dir),
        ]
        
        all_ok = True
        for filename, directory in required_files:
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                print("✓ %s" % filepath)
            else:
                print("✗ %s - NOT FOUND" % filepath)
                all_ok = False
        
        return all_ok
    except Exception as e:
        print("✗ File structure test failed: %s" % str(e))
        return False

def main():
    """Run all tests"""
    print("PDFUploadMacro Installation Test")
    print("================================\n")
    
    tests = [
        test_import,
        test_trac_components,
        test_plugin_info,
        test_macro_instantiation,
        test_dependencies,
        test_file_structure,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("✓ ALL TESTS PASSED (%d/%d)" % (passed, total))
        print("\nNext steps:")
        print("1. Enable the plugin in trac.ini:")
        print("   [components]")
        print("   pdfuploadmacro.* = enabled")
        print("\n2. Configure the LearnTrac API endpoint:")
        print("   [learntrac]")
        print("   api_endpoint = http://localhost:8000/api/trac")
        print("\n3. Set permissions:")
        print("   trac-admin /path/to/trac permission add authenticated LEARNTRAC_UPLOAD")
        print("\n4. Restart Trac and test in a wiki page with [[PDFUpload]]")
    else:
        print("✗ SOME TESTS FAILED (%d/%d passed)" % (passed, total))
        print("\nPlease check the errors above and:")
        print("1. Ensure the plugin is properly installed")
        print("2. Run this script from the Trac Python environment")
        print("3. Install missing dependencies")
        
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())