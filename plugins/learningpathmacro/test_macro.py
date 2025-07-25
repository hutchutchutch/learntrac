#!/usr/bin/env python
"""
Test script for Learning Path Macro

This script tests the basic functionality of the Learning Path macro.
"""

import sys
import os
from trac.test import EnvironmentStub, MockRequest
from trac.wiki.formatter import Formatter
from io import StringIO


def test_learning_path_macro():
    """Test the Learning Path macro."""
    
    # Create test environment
    env = EnvironmentStub(enable=['learningpathmacro.*'])
    
    # Create mock request
    req = MockRequest(env, authname='testuser')
    req.perm = MockPerm()
    
    # Test cases
    test_cases = [
        # Basic usage
        ('[[LearningPath(topic=python)]]', 'Basic topic'),
        
        # With view parameter
        ('[[LearningPath(topic=python, view=tree)]]', 'Tree view'),
        ('[[LearningPath(topic=python, view=list)]]', 'List view'),
        ('[[LearningPath(topic=python, view=timeline)]]', 'Timeline view'),
        
        # With options
        ('[[LearningPath(topic=web-dev, show_progress=true, depth=2)]]', 'With options'),
        
        # Error cases
        ('[[LearningPath()]]', 'Missing topic parameter'),
        ('[[LearningPath(topic=test, view=invalid)]]', 'Invalid view type'),
    ]
    
    # Run tests
    for wiki_text, description in test_cases:
        print(f"\n--- Testing: {description} ---")
        print(f"Wiki text: {wiki_text}")
        
        try:
            # Create formatter
            context = MockContext(env, req)
            formatter = Formatter(env, context)
            
            # Parse and format
            output = StringIO()
            formatter.format(wiki_text, output)
            result = output.getvalue()
            
            print(f"Success! Output length: {len(result)} characters")
            
            # Check for error messages
            if 'system-message' in result:
                print("Note: Output contains error message (expected for error test cases)")
            
        except Exception as e:
            print(f"Error: {str(e)}")


class MockPerm:
    """Mock permission object."""
    def __contains__(self, perm):
        return True
    
    def __getitem__(self, realm):
        return self


class MockContext:
    """Mock context object."""
    def __init__(self, env, req):
        self.env = env
        self.req = req
        self.resource = None
        self.href = req.href
        self.perm = req.perm


if __name__ == '__main__':
    print("Testing Learning Path Macro...")
    
    # Add plugin directory to Python path
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, plugin_dir)
    
    try:
        test_learning_path_macro()
        print("\nAll tests completed!")
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        import traceback
        traceback.print_exc()