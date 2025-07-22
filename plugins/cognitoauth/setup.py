from setuptools import setup, find_packages

setup(
    name='TracCognitoAuth',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pyjwt'
    ],
    entry_points={
        'trac.plugins': [
            'cognitoauth = cognitoauth.plugin'
        ]
    }
)