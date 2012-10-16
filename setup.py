#!/usr/bin/env python

import os
from setuptools import setup


version = '0.9.2'

long_description = open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.rst')).read()

setup(
        author='Tom Payne',
        author_email='twpayne@gmail.com',
        description='Utilities for flight recorders',
        long_description=long_description,
        name='flightrecorder',
        packages=['flightrecorder'],
        scripts=['scripts/flightrecorder'],
        setup_requires=['nose'],
        #test_suite='tests',
        url='https://github.com/twpayne/flightrecorder',
        version=version,
        zip_safe=True)
