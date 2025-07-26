#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Troubleshooting script for PDFUploadMacro
Helps diagnose common installation and configuration issues
"""

import sys
import os
import subprocess

def check_python_version():
    """Check Python version compatibility"""
    print("1. Checking Python version...")
    version = sys.version_info
    print("   Python %d.%d.%d" % (version.major, version.minor, version.micro))
    
    if version.major == 2 and version.minor >= 7:
        print("   ✓ Python 2.7+ detected (compatible)")
        return True
    elif version.major == 3:
        print("   ⚠ Python 3.x detected - may work but not officially tested")
        return True
    else:
        print("   ✗ Python version too old - requires 2.7+")
        return False

def check_trac_installation():
    """Check if Trac is installed and get version"""
    print("\n2. Checking Trac installation...")
    try:
        import trac
        print("   ✓ Trac is installed")
        print("   Version: %s" % trac.__version__)
        
        # Check version compatibility
        version_parts = trac.__version__.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        
        if major >= 1:
            print("   ✓ Trac version is compatible (1.0+)")
            return True
        else:
            print("   ✗ Trac version too old - requires 1.0+")
            return False
    except ImportError:
        print("   ✗ Trac is not installed or not in Python path")
        print("   Install with: pip install Trac")
        return False

def check_plugin_installation():
    """Check if PDFUploadMacro is installed"""
    print("\n3. Checking plugin installation...")
    try:
        import pdfuploadmacro
        print("   ✓ PDFUploadMacro is installed")
        
        # Try to get installation location
        location = pdfuploadmacro.__file__
        print("   Location: %s" % os.path.dirname(location))
        
        # Check if it's a development install
        if 'site-packages' in location:
            print("   Type: Standard installation")
        else:
            print("   Type: Development installation")
        
        return True
    except ImportError:
        print("   ✗ PDFUploadMacro is not installed")
        print("   Install with: python setup.py install")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\n4. Checking dependencies...")
    deps = {
        'requests': 'HTTP library for API calls',
        'setuptools': 'Python packaging tools',
    }
    
    all_ok = True
    for module, description in deps.items():
        try:
            __import__(module)
            print("   ✓ %s - %s" % (module, description))
        except ImportError:
            print("   ✗ %s - %s (NOT INSTALLED)" % (module, description))
            print("     Install with: pip install %s" % module)
            all_ok = False
    
    return all_ok

def check_trac_plugin_enabled():
    """Check if plugin is listed in Trac (requires trac-admin)"""
    print("\n5. Checking Trac plugin registry...")
    
    # This check requires access to a Trac environment
    # We'll provide instructions instead
    print("   ℹ To check if the plugin is enabled in Trac:")
    print("   Run: trac-admin /path/to/trac config get components pdfuploadmacro.*")
    print("   Expected: enabled")
    print("\n   Or check trac.ini for:")
    print("   [components]")
    print("   pdfuploadmacro.* = enabled")
    
    return None

def check_api_connectivity():
    """Check if LearnTrac API is reachable"""
    print("\n6. Checking API connectivity...")
    
    try:
        import requests
        
        # Try default endpoint
        api_url = "http://localhost:8000/api/trac/health"
        print("   Testing: %s" % api_url)
        
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                print("   ✓ API is reachable")
                return True
            else:
                print("   ⚠ API returned status %d" % response.status_code)
                return False
        except requests.exceptions.ConnectionError:
            print("   ✗ Cannot connect to API")
            print("   Make sure LearnTrac API is running on port 8000")
            return False
        except requests.exceptions.Timeout:
            print("   ✗ API request timed out")
            return False
            
    except ImportError:
        print("   ⚠ requests library not available - skipping API check")
        return None

def check_file_permissions():
    """Check file permissions"""
    print("\n7. Checking file permissions...")
    
    # Check temp directory
    import tempfile
    temp_dir = tempfile.gettempdir()
    print("   Temp directory: %s" % temp_dir)
    
    if os.access(temp_dir, os.W_OK):
        print("   ✓ Temp directory is writable")
        return True
    else:
        print("   ✗ Temp directory is not writable")
        return False

def check_web_server():
    """Provide web server configuration hints"""
    print("\n8. Web server configuration...")
    print("   ℹ For Apache with mod_wsgi:")
    print("   - Ensure WSGIScriptAlias includes Trac")
    print("   - Set appropriate file upload limits")
    print("   - Configure timeouts for large uploads")
    print("\n   ℹ For nginx:")
    print("   - Set client_max_body_size to allow PDFs")
    print("   - Configure proxy timeouts")
    print("\n   ℹ For standalone tracd:")
    print("   - No special configuration needed")

def generate_test_macro():
    """Generate a test wiki page"""
    print("\n9. Test wiki macro...")
    print("   Create a new wiki page with this content:")
    print("   " + "-"*50)
    print("   = Test PDF Upload =")
    print("   ")
    print("   Testing the PDF upload macro:")
    print("   ")
    print("   [[PDFUpload]]")
    print("   " + "-"*50)

def main():
    """Run all checks"""
    print("PDFUploadMacro Troubleshooting")
    print("="*50)
    
    # Run checks
    results = {
        'Python': check_python_version(),
        'Trac': check_trac_installation(),
        'Plugin': check_plugin_installation(),
        'Dependencies': check_dependencies(),
        'Plugin Enabled': check_trac_plugin_enabled(),
        'API': check_api_connectivity(),
        'Permissions': check_file_permissions(),
    }
    
    # Web server info
    check_web_server()
    
    # Test macro
    generate_test_macro()
    
    # Summary
    print("\n" + "="*50)
    print("Summary:")
    print("-"*50)
    
    issues = []
    for check, result in results.items():
        if result is True:
            print("✓ %s: OK" % check)
        elif result is False:
            print("✗ %s: FAILED" % check)
            issues.append(check)
        else:
            print("ℹ %s: Manual check required" % check)
    
    if issues:
        print("\n⚠ Issues found with: %s" % ", ".join(issues))
        print("\nRecommended actions:")
        
        if 'Plugin' in issues:
            print("1. Install the plugin:")
            print("   cd /path/to/pdfuploadmacro")
            print("   python setup.py install")
        
        if 'Dependencies' in issues:
            print("2. Install missing dependencies:")
            print("   pip install requests")
        
        if 'API' in issues:
            print("3. Start the LearnTrac API:")
            print("   cd /path/to/learntrac")
            print("   python -m uvicorn src.main:app --reload")
    else:
        print("\n✓ All automated checks passed!")
        print("\nNext steps:")
        print("1. Enable the plugin in trac.ini")
        print("2. Configure the API endpoint")
        print("3. Set appropriate permissions")
        print("4. Test with the wiki macro")
    
    return 0 if not issues else 1

if __name__ == '__main__':
    sys.exit(main())