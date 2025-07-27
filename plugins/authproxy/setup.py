#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='AuthProxyPlugin',
    version='1.0.0',
    description='Authentication proxy plugin for Trac',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    entry_points={
        'trac.plugins': [
            'authproxy.auth = authproxy.auth',
        ]
    },
    install_requires=['Trac>=1.4'],
)