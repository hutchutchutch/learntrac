# -*- coding: utf-8 -*-
"""
Cognito Authentication Plugin for Trac
Provides AWS Cognito authentication integration
"""

from cognitoauth.auth import CognitoAuthenticator
from cognitoauth.login import CognitoLoginModule

__all__ = ['CognitoAuthenticator', 'CognitoLoginModule']