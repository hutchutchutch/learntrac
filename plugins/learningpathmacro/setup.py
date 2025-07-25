from setuptools import setup, find_packages

setup(
    name='TracLearningPathMacro',
    version='0.1.0',
    description='Learning Path Wiki macro for Trac',
    author='LearnTrac Team',
    author_email='learntrac@example.com',
    url='https://github.com/learntrac/learning-path-macro',
    license='BSD',
    packages=find_packages(exclude=['tests*']),
    package_data={
        'learningpathmacro': [
            'templates/*.html',
            'htdocs/css/*.css',
            'htdocs/js/*.js',
        ]
    },
    install_requires=[
        'Trac>=1.4',
    ],
    entry_points={
        'trac.plugins': [
            'learningpathmacro = learningpathmacro.macro',
            'learningpathmacro.api = learningpathmacro.api',
            'learningpathmacro.db = learningpathmacro.db',
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)