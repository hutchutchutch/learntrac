#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='CognitoAuthPlugin',
    version='1.0.0',
    description='AWS Cognito authentication plugin for Trac',
    author='LearnTrac Team',
    author_email='admin@learntrac.com',
    url='https://github.com/learntrac/cognitoauth',
    license='BSD',
    packages=find_packages(),
    install_requires=[
        'Trac>=1.0',
        'PyJWT>=1.7.1,<2.0.0',  # Compatible with Python 2.7
        'cryptography>=2.8,<3.0.0',  # For PyJWT RSA support
    ],
    entry_points={
        'trac.plugins': [
            'cognitoauth.auth = cognitoauth.auth',
            'cognitoauth.login = cognitoauth.login',
        ]
    },
    classifiers=[
        'Framework :: Trac',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
)