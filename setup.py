#!/usr/bin/env python

from distutils.core import setup

setup(
        name='flytec-utils',
        version='20110414',
        description='Utilities for Flytec and Brauniger flight recorders',
        author='Tom Payne',
        author_email='twpayne@gmail.com',
        url='https://github.com/twpayne/flytec-utils',
        packages=['flytec'],
        scripts=['scripts/flytec', 'scripts/flytec-gui'])
