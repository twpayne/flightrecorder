#!/usr/bin/env python

from setuptools import setup


version = '0.9'

setup(
        author='Tom Payne',
        author_email='twpayne@gmail.com',
        description='Utilities for flight recorders',
        name='flightrecorder',
        packages=['flightrecorder'],
        scripts=['scripts/flightrecorder'],
        setup_requires=['nose'],
        #test_suite='tests',
        url='https://github.com/twpayne/flightrecorder',
        version=version,
        zip_safe=True)
