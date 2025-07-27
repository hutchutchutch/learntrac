#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for TextbookList macro installation
"""

import sys
import os

def test_import():
    """Test if the TextbookList macro can be imported"""
    print("Testing TextbookList macro import...")
    
    try:
        from pdfuploadmacro.textbook_list import TextbookListMacro
        print("✓ Successfully imported TextbookListMacro")
        
        # Check if it's a valid wiki macro
        from trac.wiki.macros import WikiMacroBase
        if issubclass(TextbookListMacro, WikiMacroBase):
            print("✓ TextbookListMacro is a valid WikiMacroBase subclass")
        else:
            print("✗ TextbookListMacro is not a WikiMacroBase subclass")
            return False
            
        # Check for expand_macro method
        if hasattr(TextbookListMacro, 'expand_macro'):
            print("✓ TextbookListMacro has expand_macro method")
        else:
            print("✗ TextbookListMacro missing expand_macro method")
            return False
            
        return True
        
    except ImportError as e:
        print("✗ Failed to import TextbookListMacro: %s" % str(e))
        return False
    except Exception as e:
        print("✗ Unexpected error: %s" % str(e))
        return False

def test_package():
    """Test if the package exports both macros"""
    print("\nTesting package exports...")
    
    try:
        import pdfuploadmacro
        
        if hasattr(pdfuploadmacro, 'PDFUploadMacro'):
            print("✓ PDFUploadMacro is exported")
        else:
            print("✗ PDFUploadMacro is not exported")
            
        if hasattr(pdfuploadmacro, 'TextbookListMacro'):
            print("✓ TextbookListMacro is exported")
        else:
            print("✗ TextbookListMacro is not exported")
            
        # Check __all__
        if hasattr(pdfuploadmacro, '__all__'):
            print("  Exported names: %s" % ', '.join(pdfuploadmacro.__all__))
            
        return True
        
    except Exception as e:
        print("✗ Failed to test package: %s" % str(e))
        return False

def main():
    """Run all tests"""
    print("TextbookList Macro Installation Test")
    print("="*40)
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    results = []
    results.append(test_import())
    results.append(test_package())
    
    print("\n" + "="*40)
    if all(results):
        print("✓ All tests passed!")
        print("\nYou can now use [[TextbookList]] in your wiki pages")
        return 0
    else:
        print("✗ Some tests failed")
        print("\nPlease check the error messages above")
        return 1

if __name__ == '__main__':
    sys.exit(main())