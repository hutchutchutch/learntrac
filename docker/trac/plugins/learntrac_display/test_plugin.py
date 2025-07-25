#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for Learntrac Display Plugin
"""

import sys
import os

def test_plugin_structure():
    """Test that all required files exist"""
    
    required_files = [
        'setup.py',
        'learntrac_display/__init__.py',
        'learntrac_display/ticket_display.py',
        'learntrac_display/htdocs/css/learntrac.css',
        'learntrac_display/htdocs/js/learntrac.js',
        'learntrac_display/templates/learntrac_panel.html',
        'README.md'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print("✓ Found: {}".format(file_path))
    
    if missing_files:
        print("\n❌ Missing files:")
        for file_path in missing_files:
            print("  - {}".format(file_path))
        return False
    
    print("\n✓ All required files present!")
    return True

def test_plugin_imports():
    """Test that the plugin can be imported"""
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Try importing the main module
        from learntrac_display import ticket_display
        print("✓ Successfully imported ticket_display module")
        
        # Check for the main component
        if hasattr(ticket_display, 'LearningTicketDisplay'):
            print("✓ Found LearningTicketDisplay component")
        else:
            print("❌ LearningTicketDisplay component not found")
            return False
            
        return True
        
    except ImportError as e:
        print("❌ Import error: {}".format(e))
        return False

def main():
    """Run all tests"""
    
    print("Testing Learntrac Display Plugin Structure...")
    print("=" * 50)
    
    # Change to plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(plugin_dir)
    
    # Run tests
    structure_ok = test_plugin_structure()
    
    print("\nTesting Plugin Imports...")
    print("=" * 50)
    
    imports_ok = test_plugin_imports()
    
    # Summary
    print("\nTest Summary:")
    print("=" * 50)
    
    if structure_ok and imports_ok:
        print("✓ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())