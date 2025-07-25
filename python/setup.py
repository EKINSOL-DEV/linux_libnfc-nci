#!/usr/bin/env python3
"""
Setup script for building the Python NFC extension module.

This script builds a Python C extension that interfaces with the Linux NFC library.
"""

from distutils.core import setup, Extension
import os
import subprocess

# Get the directory containing this setup.py
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Library and include paths
lib_path = os.path.join(project_root)
include_paths = [
    os.path.join(project_root, 'src/include'),
    os.path.join(project_root, 'src/nxp_nci_hal_libnfc-nci/src/include'),
    os.path.join(project_root, 'src/nxp_nci_hal_libnfc-nci/src/gki/ulinux'),
    os.path.join(project_root, 'src/nxp_nci_hal_libnfc-nci/src/gki/common'),
    os.path.join(project_root, 'src/android/utility'),
    os.path.join(project_root, 'src/libnfc-utils/inc'),
]

# Check if the library exists
lib_file = os.path.join(lib_path, '.libs/libnfc_nci_linux.so')
if not os.path.exists(lib_file):
    lib_file = os.path.join(lib_path, 'libnfc_nci_linux.so')
    if not os.path.exists(lib_file):
        print("Warning: libnfc_nci_linux.so not found. Make sure to build the library first.")
        print(f"Expected location: {lib_file}")
        print("Run 'make' in the project root directory to build the library.")

# Define the extension module
nfc_extension = Extension(
    'nfc_native',
    sources=[
        'nfc_python_wrapper.c'
    ],
    include_dirs=include_paths,
    library_dirs=[
        lib_path,
        os.path.join(lib_path, '.libs'),
    ],
    libraries=['nfc_nci_linux'],
    extra_compile_args=[
        '-DLINUX',
        '-DNXP_EXTNS=TRUE',
        '-DSNEP_ENABLED',
        '-std=c99',
        '-Wall',
    ],
    extra_link_args=[
        '-Wl,-rpath,' + lib_path,
        '-Wl,-rpath,' + os.path.join(lib_path, '.libs'),
        '-lgpiod',
        '-ldl',
        '-lrt',
        '-pthread'
    ]
)

# Setup configuration
setup(
    name='nfc_reader',
    version='1.0.0',
    description='Python interface for Linux NFC library',
    long_description='''
    A Python extension module that provides a high-level interface to the Linux NFC library.
    This module allows Python applications to interact with NFC tags and read NDEF data,
    particularly text records.
    
    Features:
    - Initialize and manage NFC stack
    - Detect NFC tags
    - Read NDEF text records
    - Extract text content and language information
    - Get tag information and metadata
    
    Requirements:
    - Linux NFC library (libnfc_nci_linux.so)
    - NFC hardware support
    - Root privileges (typically required for NFC hardware access)
    ''',
    author='NFC Python Interface',
    author_email='nfc@example.com',
    url='https://github.com/nxp/linux_libnfc-nci',
    ext_modules=[nfc_extension],
    py_modules=['nfc_reader'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: C',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Hardware',
        'Topic :: Communications',
    ],
    python_requires='>=3.6',
)