# setup.py

from setuptools import setup, find_packages

setup(
    name="gann_trading",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'breeze-connect>=1.0.34',
        'python-dotenv>=1.0.0',
        'pandas>=2.1.1',
        'numpy>=1.24.3',
        'sqlalchemy>=1.4.0',
        'fastapi>=0.68.0',
        'click>=8.0.0',
        'pyotp>=2.9.0',
        'h5py>=3.0.0',
    ],
    entry_points={
        'console_scripts': [
            'gann-trading=interface.cli:cli',
        ],
    },
)