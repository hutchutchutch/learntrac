#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='PDFUploadMacro',
    version='1.0.0',
    description='Wiki macro for uploading PDFs to LearnTrac system',
    author='LearnTrac Team',
    author_email='admin@learntrac.local',
    url='http://learntrac.local',
    packages=find_packages(),
    entry_points={
        'trac.plugins': [
            'pdfuploadmacro = pdfuploadmacro',
        ],
    },
    install_requires=['Trac>=1.0'],
)