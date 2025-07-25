#!/usr/bin/env python
"""
Test script for Learning Path Macro authentication integration.

This script tests the Cognito authentication check in the LearningPathMacro.
"""

import unittest
from unittest.mock import Mock, MagicMock
from learningpathmacro.macro import LearningPathMacro


class TestLearningPathAuthentication(unittest.TestCase):
    """Test cases for authentication in Learning Path Macro."""
    
    def setUp(self):
        """Set up test environment."""
        self.macro = LearningPathMacro(Mock())
        
    def test_is_authenticated_with_valid_cognito_session(self):
        """Test authentication check with valid Cognito session."""
        req = Mock()
        req.session = {
            'cognito_username': 'testuser@example.com',
            'authenticated': True,
            'cognito_email': 'testuser@example.com',
            'cognito_name': 'Test User',
            'cognito_groups': ['learners']
        }
        req.authname = 'testuser@example.com'
        
        self.assertTrue(self.macro._is_authenticated(req))
        
    def test_is_authenticated_without_cognito_session(self):
        """Test authentication check without Cognito session."""
        req = Mock()
        req.session = {}
        req.authname = 'anonymous'
        
        self.assertFalse(self.macro._is_authenticated(req))
        
    def test_is_authenticated_with_anonymous_user(self):
        """Test authentication check with anonymous user."""
        req = Mock()
        req.session = {
            'cognito_username': 'testuser@example.com',
            'authenticated': True
        }
        req.authname = 'anonymous'
        
        self.assertFalse(self.macro._is_authenticated(req))
        
    def test_render_auth_required_message(self):
        """Test rendering of authentication required message."""
        req = Mock()
        req.href = Mock()
        req.href.return_value = '/auth/login'
        
        result = self.macro._render_auth_required(req)
        
        # Convert to string to check content
        result_str = str(result)
        
        # Check that key elements are present
        self.assertIn('Authentication Required', result_str)
        self.assertIn('/auth/login', result_str)
        self.assertIn('learningpath-auth-required', result_str)
        
    def test_get_user_info(self):
        """Test getting user information from session."""
        req = Mock()
        req.session = {
            'cognito_username': 'testuser@example.com',
            'cognito_email': 'testuser@example.com',
            'cognito_name': 'Test User',
            'cognito_groups': ['learners', 'admins']
        }
        
        user_info = self.macro._get_user_info(req)
        
        self.assertEqual(user_info['username'], 'testuser@example.com')
        self.assertEqual(user_info['email'], 'testuser@example.com')
        self.assertEqual(user_info['name'], 'Test User')
        self.assertEqual(user_info['groups'], ['learners', 'admins'])
        
    def test_expand_macro_without_authentication(self):
        """Test macro expansion without authentication."""
        formatter = Mock()
        formatter.req = Mock()
        formatter.req.session = {}
        formatter.req.authname = 'anonymous'
        formatter.req.href = Mock()
        formatter.req.href.return_value = '/auth/login'
        
        result = self.macro.expand_macro(formatter, 'LearningPath', 'topic=mathematics')
        
        # Should return auth required message
        result_str = str(result)
        self.assertIn('Authentication Required', result_str)
        self.assertIn('learningpath-auth-required', result_str)
        
    def test_expand_macro_with_authentication(self):
        """Test macro expansion with authentication."""
        formatter = Mock()
        formatter.req = Mock()
        formatter.req.session = {
            'cognito_username': 'testuser@example.com',
            'authenticated': True,
            'cognito_name': 'Test User'
        }
        formatter.req.authname = 'testuser@example.com'
        formatter.req.perm = Mock()
        formatter.req.perm.__contains__ = Mock(return_value=True)
        formatter.req.href = Mock()
        formatter.req.href.wiki = Mock(return_value='/wiki/path')
        
        # Mock Chrome methods
        import trac.web.chrome
        trac.web.chrome.add_stylesheet = Mock()
        trac.web.chrome.add_script = Mock()
        
        result = self.macro.expand_macro(formatter, 'LearningPath', 'topic=mathematics')
        
        # Should return learning path content
        result_str = str(result)
        self.assertIn('learningpath-container', result_str)
        self.assertIn('Learning Path: Mathematics', result_str)
        self.assertIn('Welcome, Test User!', result_str)


if __name__ == '__main__':
    unittest.main()