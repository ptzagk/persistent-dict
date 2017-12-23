#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import absolute_import

import os

from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='persistent-dict',
    version='0.1.1',
    packages=find_packages('src', exclude=('tests', )),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    description='A Python Dict which stores data in Redis.',
    author='Richard O\'Dwyer',
    author_email='richard@richard.do',
    license='MIT',
    long_description='https://github.com/richardasaurus/persistent-dict',
    install_requires=install_requires,
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent', 'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ])
