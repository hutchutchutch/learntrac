"""
Setup script for Modern Authentication Plugin for Trac
Python 2.7 Compatible
"""

from setuptools import setup, find_packages

setup(
    name='TracModernAuth',
    version='1.0.0',
    author='LearnTrac Team',
    author_email='admin@learntrac.local',
    description='Modern authentication system for Trac with secure session tokens',
    long_description='''
    Modern Authentication Plugin for Trac
    
    Upgrades Trac's default cookie-based authentication to a modern, secure system:
    - Secure HMAC-signed session tokens
    - CSRF protection  
    - Rate limiting and brute force protection
    - Redis-based session storage with fallback
    - Modern security headers
    - Python 2.7 compatible
    
    Provides enterprise-grade security while maintaining full compatibility
    with Trac's Python 2.7 environment.
    ''',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'modern_auth': ['templates/*.html', 'htdocs/*'],
    },
    install_requires=[
        'Trac>=1.0',
        'redis>=2.10.6',  # Last version supporting Python 2.7
    ],
    entry_points={
        'trac.plugins': [
            'modern_auth.auth = modern_auth.auth',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Trac',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Security',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
    keywords='trac authentication security session csrf rate-limiting',
    zip_safe=False,
)