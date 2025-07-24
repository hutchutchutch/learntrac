#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TracLearn Plugin Setup Script
"""

from setuptools import setup, find_packages

# Read version from __init__.py
with open('traclearn/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip("'\"")
            break

# Read long description from README
try:
    with open('README.md', 'r') as f:
        long_description = f.read()
except:
    long_description = ''

setup(
    name='TracLearn',
    version=version,
    description='Educational Learning Management Plugin for Trac',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='TracLearn Team',
    author_email='traclearn@example.com',
    url='https://github.com/example/traclearn',
    license='BSD',
    packages=find_packages(exclude=['tests*']),
    package_data={
        'traclearn': [
            'templates/*.html',
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'htdocs/images/*.*',
            'locale/*/LC_MESSAGES/*.mo',
        ],
    },
    install_requires=[
        'Trac>=1.4',
        'requests>=2.20.0',
        'Jinja2>=2.10',
    ],
    extras_require={
        'postgres': ['psycopg2-binary>=2.8'],
        'mysql': ['MySQL-python>=1.2.5'],
        'voice': ['SpeechRecognition>=3.8.1'],
    },
    entry_points={
        'trac.plugins': [
            'traclearn = traclearn',
            'traclearn.setup = traclearn:TracLearnSetup',
            'traclearn.learning_manager = traclearn.components.learning_manager',
            'traclearn.analytics = traclearn.components.analytics_collector',
            'traclearn.ai = traclearn.components.ai_integration',
            'traclearn.web = traclearn.web.handlers',
            'traclearn.fields = traclearn.ticket_extensions.learning_fields',
        ],
    },
    classifiers=[
        'Framework :: Trac',
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Education',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    python_requires='>=2.7, <3',
)