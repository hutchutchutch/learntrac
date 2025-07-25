#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

PACKAGE = 'learntrac_display'
VERSION = '0.1.0'

setup(
    name='LearntracDisplay',
    version=VERSION,
    description='Trac plugin for displaying learning questions in ticket view',
    author='Learntrac Team',
    author_email='team@learntrac.com',
    url='https://github.com/learntrac/learntrac-display',
    license='BSD',
    packages=find_packages(exclude=['tests*']),
    package_data={
        'learntrac_display': [
            'templates/*.html',
            'htdocs/css/*.css',
            'htdocs/js/*.js'
        ]
    },
    install_requires=[
        'Trac>=1.0',
        'requests>=2.25.0',
    ],
    entry_points={
        'trac.plugins': [
            'learntrac_display.ticket_display = learntrac_display.ticket_display',
            'learntrac_display.knowledge_graph = learntrac_display.knowledge_graph'
        ]
    },
    classifiers=[
        'Framework :: Trac',
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)